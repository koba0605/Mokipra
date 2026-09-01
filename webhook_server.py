import os
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

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
app = FastAPI()

PLAN_WEIGHTS = {"Free": 0, "Pro": 1, "Max": 2}


# Render死活監視用ヘルスチェック
@app.get("/")
def health_check():
    return {"status": "ok"}


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

    # ① 決済完了時の処理（Pro / Max へのアップグレード）
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
                new_plan = "Pro" if amount == 480 else "Max" if amount == 980 else "Free"
            else:
                new_plan = "Free"

        if user_id and new_plan in PLAN_WEIGHTS:
            try:
                # 昇格専用のアトミックRPCを呼び出す
                result = supabase.rpc('update_plan_atomic', {
                    'target_user_id': user_id,
                    'new_plan': new_plan,
                    'new_weight': PLAN_WEIGHTS[new_plan]
                }).execute()

                if result.data:
                    plan_result = result.data
                    action = plan_result.get('action', 'unknown')
                    logger.info(f"Plan update result: user={user_id}, action={action}, plan={new_plan}")
                else:
                    logger.error("No data returned from RPC")

            except Exception as e:
                logger.error(f"❌ RPC failed for user {user_id}: {e}")

    # ② サブスクリプション解約時の処理（Freeへの強制ダウングレード）
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']

        # 決済時に埋め込んだ metadata からユーザーIDを取得
        metadata = getattr(subscription, 'metadata', None)
        user_id = getattr(metadata, 'user_id', None) if metadata else None

        if user_id:
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
