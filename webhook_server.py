import os
import re
import stripe
import logging
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# ---------------------------------------------------------------------------
#  テストモード（サンドボックス）のイベントを受け付けるかどうか
# ---------------------------------------------------------------------------
#  2026-09-02 にサンドボックスで解約テストを行った際、転送先が本番の Supabase を
#  参照していたため、本番ユーザー（40c88daa-...）のプランが Free に書き換えられた。
#  気づいたのは 10/05 で、その間ずっと課金だけが続いていた。
#
#  Stripe のイベントには livemode フラグが入っているので、本番サーバーでは
#  テストモードのイベントを最初から拒否する。これが構造的な再発防止になる。
#  検証専用のサービスを立てる場合のみ、そちらに ALLOW_TEST_MODE=true を設定する。
ALLOW_TEST_MODE = os.environ.get("ALLOW_TEST_MODE", "").strip().lower() in ("1", "true", "yes")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
app = FastAPI()

# プランは Free / Pro の2種類に統合した。
# Max は廃止したが、過去の契約が残っていた場合に備えて判定には含める。
PLAN_WEIGHTS = {"Free": 0, "Pro": 1, "Max": 2}

# 「まだ有効」とみなす契約のステータス。
#   past_due は支払いに失敗して Stripe が再試行している最中の状態。
#   契約自体は生きているので、ここで降格すると復旧時に上げ直すことになり、
#   利用者から見ると理由なくプランが行き来する。含めておく。
ACTIVE_SUB_STATUSES = ("active", "trialing", "past_due")

# metadata は Stripe のダッシュボードから手で編集できる。
# 検索クエリに埋め込む前に、UUID の形であることを必ず確認する。
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


# Render死活監視用ヘルスチェック
@app.get("/")
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
#  補助関数
# ---------------------------------------------------------------------------

def _apply_plan(user_id, new_plan, reason):
    """
    昇格専用のアトミックRPCを呼ぶ。
    現在のプランより重みが低い場合は RPC 側で無視されるため、
    何度呼んでも勝手に降格することはない。
    """
    try:
        result = supabase.rpc('update_plan_atomic', {
            'target_user_id': user_id,
            'new_plan': new_plan,
            'new_weight': PLAN_WEIGHTS[new_plan]
        }).execute()

        if result.data:
            plan_result = result.data
            action = plan_result.get('action', 'unknown')
            logger.info(
                f"Plan update result: user={user_id}, action={action}, "
                f"plan={new_plan}, reason={reason}"
            )
        else:
            logger.error(f"No data returned from RPC. user={user_id}, reason={reason}")

    except Exception as e:
        logger.error(f"❌ RPC failed for user {user_id} ({reason}): {e}")


def _subscription_id_from_invoice(invoice):
    """
    請求書オブジェクトからサブスクリプションIDを取り出す。

    Stripe は API バージョンによってこの値の格納場所を変えてきた経緯がある。
    一箇所だけを見ていると、ある日突然 None になって更新処理が静かに止まるので、
    既知の場所を順に探し、見つからなければ None を返す。
    """
    sub_id = invoice.get("subscription")
    if sub_id:
        return sub_id

    parent = invoice.get("parent") or {}
    details = parent.get("subscription_details") or {}
    sub_id = details.get("subscription")
    if sub_id:
        return sub_id

    try:
        for line in (invoice.get("lines") or {}).get("data", []):
            line_parent = line.get("parent") or {}
            item_details = line_parent.get("subscription_item_details") or {}
            sub_id = item_details.get("subscription")
            if sub_id:
                return sub_id
            sub_id = line.get("subscription")
            if sub_id:
                return sub_id
    except Exception as e:
        logger.warning(f"Failed to scan invoice lines for subscription id: {e}")

    return None


def _find_other_active_subscription(user_id, canceled_sub_id, customer_id):
    """
    解約されたもの以外に、まだ有効な契約が残っているかを調べる。

    戻り値:
        (True,  サブスクID) 他に有効な契約がある → 降格してはいけない
        (False, None)       他に有効な契約は無い → 降格してよい
        (None,  None)       確認できなかった     → 安全のため降格しない

    なぜ必要か:
        2026-10-30 に、同じ利用者が23分差で2回 Pro を契約した事例があった。
        11-09 に重複分を解約した際、この確認が無かったため、
        まだ有効な契約が1件残っているのに Free へ降格する一歩手前だった。

        さらにこの事例では、同じメールアドレスに対して Stripe の顧客オブジェクトが
        2つ別々に作られていた。customer だけを見ても重複に気づけないため、
        metadata の user_id で横断して探す必要がある。

    確認できなかったときに降格しないのは、
        「解約済みの人が一時的に Pro のまま」より
        「支払っている人が Free に落ちる」方が実害が大きいためである。
    """
    if not _UUID_RE.match(str(user_id or "")):
        logger.error(f"Subscription lookup skipped: user_id is not a UUID. value={user_id!r}")
        return None, None

    # (1) metadata の user_id で検索する。
    #     顧客オブジェクトが分かれていても、これなら横断して拾える。
    try:
        result = stripe.Subscription.search(
            query=f"metadata['user_id']:'{user_id}'",
            limit=100,
        )
        for sub in result.auto_paging_iter():
            if sub.get("id") == canceled_sub_id:
                continue
            if sub.get("status") in ACTIVE_SUB_STATUSES:
                return True, sub.get("id")
    except Exception as e:
        logger.warning(f"Subscription.search failed for user {user_id}: {e}")
        return None, None

    # (2) 同じ顧客の契約も確認する。
    #     Stripe の検索インデックスは反映まで1分ほど遅れることがあり、
    #     直前に作られた契約を (1) だけでは取りこぼす可能性がある。
    if customer_id:
        try:
            for status in ACTIVE_SUB_STATUSES:
                subs = stripe.Subscription.list(
                    customer=customer_id, status=status, limit=100
                )
                for sub in subs.auto_paging_iter():
                    if sub.get("id") == canceled_sub_id:
                        continue
                    return True, sub.get("id")
        except Exception as e:
            logger.warning(f"Subscription.list failed for customer {customer_id}: {e}")
            return None, None

    return False, None


# ---------------------------------------------------------------------------
#  Webhook 本体
# ---------------------------------------------------------------------------

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        logger.error("Invalid payload received.")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature detected.")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # ★ テストモードのイベントは本番DBに触らせない。
    #   200 を返すのは、Stripe に再送させないため。拒否は意図した結果であって障害ではない。
    if not ALLOW_TEST_MODE and not event.get("livemode", False):
        logger.warning(
            f"Ignored test-mode event: type={event.get('type')}, id={event.get('id')}"
        )
        return {"status": "ignored_test_mode"}

    # ① 決済完了時の処理（Pro へのアップグレード）
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        user_id = getattr(session, 'client_reference_id', None)
        metadata = getattr(session, 'metadata', None)
        new_plan = getattr(metadata, 'plan', None) if metadata else None

        # Price判定のフォールバック
        if not new_plan:
            amount = getattr(session, 'amount_total', 0)
            currency = getattr(session, 'currency', 'jpy')
            currency = currency.lower() if currency else 'jpy'

            if currency in ['jpy', 'usd']:
                # 金額からの判定。980円は旧Maxプランで、現在は新規契約されない。
                if amount == 480:
                    new_plan = "Pro"
                elif amount == 980:
                    new_plan = "Max"   # 旧プランの契約が残っている場合のみ
                else:
                    new_plan = "Free"
            else:
                new_plan = "Free"

        if user_id and new_plan in PLAN_WEIGHTS:
            _apply_plan(user_id, new_plan, "checkout")
        else:
            # ここを素通りさせると「払ったのにプランが上がらない」状態になる。
            logger.error(
                f"Upgrade skipped: user_id or plan missing. "
                f"user_id={user_id}, plan={new_plan}, "
                f"session={getattr(session, 'id', None)}"
            )

    # ② 月次更新の支払い成功（プランの再確認）
    #
    #    これを入れる前は、何らかの理由でプランが Free に落ちると、
    #    毎月課金され続けても二度と Pro に戻らなかった。
    #    実際 2026-09-02 の事故でその状態になり、9/18 の更新でも復旧しなかった。
    #    更新のたびに正しいプランを入れ直すことで、ズレが自動的に直る。
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        billing_reason = invoice.get('billing_reason')
        invoice_id = invoice.get('id')

        if billing_reason == 'subscription_create':
            # 新規契約は ① 側で処理済み。二重に走らせない。
            logger.info(
                f"invoice.payment_succeeded skipped (handled by checkout): invoice={invoice_id}"
            )
        else:
            sub_id = _subscription_id_from_invoice(invoice)

            if not sub_id:
                logger.info(
                    f"invoice.payment_succeeded skipped (not a subscription invoice): "
                    f"invoice={invoice_id}, billing_reason={billing_reason}"
                )
            else:
                try:
                    subscription = stripe.Subscription.retrieve(sub_id)
                    sub_metadata = subscription.get('metadata') or {}
                    user_id = sub_metadata.get('user_id')
                    new_plan = sub_metadata.get('plan') or "Pro"

                    if user_id and new_plan in PLAN_WEIGHTS:
                        _apply_plan(user_id, new_plan, f"renewal:{billing_reason}")
                    else:
                        # 2026-08-18 以前に作られた契約は metadata に user_id を持たない。
                        # そういう契約が更新され続ける限り、ここに出続ける。
                        logger.error(
                            f"Renewal skipped: user_id not found in subscription metadata. "
                            f"subscription={sub_id}, invoice={invoice_id}, "
                            f"customer={invoice.get('customer')}"
                        )

                except Exception as e:
                    logger.error(
                        f"❌ Failed to handle invoice.payment_succeeded. "
                        f"subscription={sub_id}, invoice={invoice_id}: {e}"
                    )

    # ③ サブスクリプション解約時の処理（Freeへの強制ダウングレード）
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']

        # 決済時に埋め込んだ metadata からユーザーIDを取得
        metadata = getattr(subscription, 'metadata', None)
        user_id = getattr(metadata, 'user_id', None) if metadata else None
        canceled_sub_id = getattr(subscription, 'id', None)
        customer_id = getattr(subscription, 'customer', None)

        if user_id:
            # ★ 2026-11-13 追加：降格する前に、他の有効な契約が無いことを確認する。
            #   これが無いと、契約を2つ持つ人の片方を解約しただけで
            #   「支払っているのに Free」という状態を作ってしまう。
            has_other, other_sub_id = _find_other_active_subscription(
                user_id, canceled_sub_id, customer_id
            )

            if has_other:
                logger.info(
                    f"Downgrade skipped: user={user_id} still has an active subscription "
                    f"({other_sub_id}). canceled={canceled_sub_id}"
                )
            elif has_other is None:
                # 確認できなかったので降格しない。
                # 本当に解約済みだった場合はプランが残るが、それは手で直せる。
                # 逆に誤って降格すると、支払っている利用者がサービスを使えなくなる。
                logger.error(
                    f"Downgrade skipped: could not verify remaining subscriptions. "
                    f"user={user_id}, canceled={canceled_sub_id}, customer={customer_id}. "
                    f"Plan left unchanged on purpose. Check manually."
                )
            else:
                try:
                    # ★ 変更点：ダウングレード専用のRPCを呼び出す ★
                    result = supabase.rpc('downgrade_to_free', {
                        'target_user_id': user_id
                    }).execute()

                    logger.info(f"Subscription canceled: user={user_id} downgraded to Free.")
                except Exception as e:
                    logger.error(f"❌ Downgrade RPC failed for user {user_id}: {e}")
        else:
            # user_id が取得できないと黙ってダウングレードが失敗するため、必ずログに残す
            logger.error(
                f"Downgrade skipped: user_id not found. "
                f"subscription={getattr(subscription, 'id', None)}, "
                f"customer={getattr(subscription, 'customer', None)}"
            )

    return {"status": "success"}
