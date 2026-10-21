-- ============================================================================
--  restore_grants.sql
--  バックアップから復旧したあとに必ず実行する補完スクリプト
-- ----------------------------------------------------------------------------
--  2026-10-21、実際の暗号化バックアップ（mokipra_20261018.sql.gpg）を復号して
--  中身を検証した結果、ダンプに含まれないものが2種類あることを確認した。
--
--    含まれる  : テーブル定義 / データ / RLS の有効化 / ポリシー2件 / 関数4件
--    含まれない: GRANT 文         ← pg_dump --no-privileges のため
--                イベントトリガー ← 所有者の権限の都合で dump 対象から外れている
--
--  さらに 2026-10-30 より、Supabase は public スキーマの新規テーブルへ
--  Data API のアクセス権を自動付与しなくなる。
--  そのため復元しただけでは、テーブルはできてもアプリの全クエリが
--  42501 (permission denied) で失敗する。データは無事なのに起動しない状態になる。
--
--  使い方:
--    1. 暗号化バックアップを復号し、新しい Supabase プロジェクトへ復元する
--    2. Supabase ダッシュボードの SQL Editor でこのファイルを実行する
--    3. 末尾の確認クエリで、意図どおりになったことを目視する
--
--  注意:
--    対象は 2026-10-21 時点のスキーマ（テーブル3・関数3）に基づく。
--    テーブルや関数を追加したら、このファイルにも必ず追記すること。
--    追記を忘れると、そのオブジェクトだけ復旧後に動かない。
-- ============================================================================


-- ----------------------------------------------------------------------------
--  0. スキーマそのものへの USAGE
-- ----------------------------------------------------------------------------
--  テーブル単位の grant があっても、スキーマに USAGE が無いと到達できない。
grant usage on schema public to authenticated, service_role;


-- ----------------------------------------------------------------------------
--  1. テーブル
-- ----------------------------------------------------------------------------
--  anon（未ログイン）には何も与えない。
--  Mokipra はログイン必須で、未ログイン状態で読む必要のあるテーブルが無い。
--  権限は与えない方が攻撃面が小さい。
--
--  grant は「テーブルに触れてよいか」、RLS は「どの行に触れてよいか」を決める。
--  両方そろって初めて、自分の行だけにアクセスできる状態になる。
--  ポリシーはダンプに含まれるので、ここで足すのは grant だけでよい。

-- 面接履歴（ポリシー "Manage own history" が auth.uid() = user_id で行を制限）
grant select, insert, update, delete on public.interview_history to authenticated;
grant select, insert, update, delete on public.interview_history to service_role;

-- 利用状況・プラン（ポリシー "Manage own usage" が同様に制限）
grant select, insert, update, delete on public.user_usage to authenticated;
grant select, insert, update, delete on public.user_usage to service_role;

-- キープアライブ用
--   GitHub Actions から postgres ロールで直接接続して INSERT しており、
--   Data API は経由しない。ポリシーも無いが、postgres は RLS を迂回するため動く。
--   authenticated には与えない。ダッシュボードからの確認用に service_role のみ。
grant select, insert, delete on public.keep_alive to service_role;


-- ----------------------------------------------------------------------------
--  2. シーケンス
-- ----------------------------------------------------------------------------
--  identity 列や serial 列を持つテーブルに INSERT するには、
--  その裏にあるシーケンスへの USAGE が必要。
--  テーブルの grant だけ直して、ここで詰まることが多い。
grant usage, select on all sequences in schema public to authenticated, service_role;


-- ----------------------------------------------------------------------------
--  3. 関数（RPC）
-- ----------------------------------------------------------------------------
--  EXECUTE 権限も --no-privileges で落ちている。これが無いと決済が丸ごと動かない。
--  以下のシグネチャは 2026-10-21 にバックアップの実物と照合済み。

-- アプリから呼ぶ（利用回数のインクリメント）
grant execute on function public.increment_usage(target_user_id uuid) to authenticated;

-- webhook から呼ぶ（プランの昇格・降格）
grant execute on function public.update_plan_atomic(target_user_id uuid, new_plan text, new_weight integer) to service_role;
grant execute on function public.downgrade_to_free(target_user_id uuid) to service_role;


-- ----------------------------------------------------------------------------
--  4. イベントトリガー（RLS の自動有効化）
-- ----------------------------------------------------------------------------
--  関数 public.rls_auto_enable() はダンプに含まれるが、
--  それを起動するイベントトリガーは含まれていない。
--  このため、復元しただけでは関数が存在するのに一度も呼ばれない。
--
--  この仕組みが無いと、今後 public にテーブルを作ったとき RLS が無効のままになる。
--  2026-10-30 以降は Data API の grant も自動では付かないので、
--  「RLS 無効のまま grant だけ手で付ける」という最悪の組み合わせを招きやすい。
--
--  ※ イベントトリガーの作成には強い権限が必要。
--    復旧先で権限が足りず失敗する場合は、Supabase サポートに相談するか、
--    「テーブル作成時は必ず RLS を有効化する」運用で代替すること。
--
--  名前・イベント・タグは 2026-10-21 に現行プロジェクトの pg_event_trigger と
--  照合済み（ensure_rls / ddl_command_end / CREATE TABLE ほか2タグ）。
--
--  なお、同じ一覧に出てくる issue_graphql_placeholder、issue_pg_cron_access、
--  issue_pg_graphql_access、issue_pg_net_access、pgrst_ddl_watch、pgrst_drop_watch は
--  Supabase が全プロジェクトに自動で作るもの。復旧時に自分で作り直す必要はない。
--  自前で用意したイベントトリガーは ensure_rls だけ。

do $$
begin
  if not exists (select 1 from pg_event_trigger where evtname = 'ensure_rls') then
    create event trigger ensure_rls
      on ddl_command_end
      when tag in ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      execute function public.rls_auto_enable();
  end if;
exception
  when insufficient_privilege then
    raise notice 'イベントトリガー ensure_rls を作成できませんでした（権限不足）。手動で RLS を有効化する運用に切り替えてください。';
end
$$;


-- ============================================================================
--  確認クエリ
-- ============================================================================
--  「実行したから大丈夫」ではなく「結果を見て確認した」で完了とする。

-- テーブルの権限（anon が出てこないこと。authenticated / service_role に4権限あること）
select table_name,
       grantee,
       string_agg(privilege_type, ', ' order by privilege_type) as privileges
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated', 'service_role')
group by table_name, grantee
order by table_name, grantee;

-- 関数の権限
select p.proname as function_name,
       pg_get_function_identity_arguments(p.oid) as args,
       array_to_string(p.proacl, E'\n') as acl
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
order by p.proname;

-- RLS とポリシー（3テーブルとも rls_enabled = true であること）
select c.relname as table_name,
       c.relrowsecurity as rls_enabled,
       count(pol.polname) as policy_count
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join pg_policy pol on pol.polrelid = c.oid
where n.nspname = 'public'
  and c.relkind = 'r'
group by c.relname, c.relrowsecurity
order by c.relname;

-- イベントトリガー
--   ensure_rls が存在し、evtenabled = 'O'（有効）であること。
--   他に出てくる issue_* と pgrst_* は Supabase 標準のもので、あって正常。
select evtname, evtevent, evttags, evtenabled, p.proname as function_name
from pg_event_trigger e
join pg_proc p on p.oid = e.evtfoid
order by evtname;
