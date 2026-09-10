# Mokipra - AI模擬面接パートナー

<div align="center">

![Mokipra](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.63-FF4B4B)

**AIが面接官になる、リアルな面接練習サービス**

[サービスサイト](https://mokipra.jp) • [アプリを開く](https://app.mokipra.jp) • [技術スタック](#技術スタック) • [バグ報告](https://github.com/koba0605/Mokipra/issues)

</div>

---

## Mokipra とは

Mokipra は、**AI が面接官になってリアルな面接練習ができる** Web サービスです。

就活生や転職希望者が、相手を探さずにひとりで、何度でも面接の練習をできます。
2026年9月からは、**AI参加者4名とのグループディスカッション練習**にも対応しました。

- 音声による自然な面接体験
- AI による自動採点と改善アドバイス
- グループディスカッション練習（Pro / Max）
- 4つの面接シーンに対応
- PDF 資料の読み込み対応（Max プラン）

---

## 主な機能

### リアルな音声面接

- OpenAI のモデルが面接官を担当（Max プランは GPT-4o）
- 音声合成による、本番に近い受け答え
- Whisper による音声入力に対応
- 1回あたりの質疑応答は Free が4ターン、Pro / Max が10ターン

### 自動採点と改善フィードバック

- 面接終了後、AI が100点満点で採点
- 「強み」「改善点」「次のステップ」を提示
- 話し方やスピードの診断も併せて表示

### グループディスカッション練習（Pro / Max）

一人では練習しにくいグループディスカッションを、AI 参加者4名とのやり取りで再現します。

- **自分でタイミングを選んで発言する形式**
  順番は回ってきません。黙っていても議論は進み、一定時間発言しないと
  AI から話を振られます。振られてからの発言は「自発的な発言」に数えません。
- **役割を選んで練習できる**
  司会（ファシリテーター）／書記／タイムキーパー／役割なし。
  選ばなかった役割は AI 参加者が担当します。
- **5軸10段階の評価**
  参加姿勢・発言の質・他者への反応・議論への貢献・発言量のバランス。
  参加姿勢と発言量は発言ログから機械的に算出し、残る3軸を AI が判定します。
- **役割ごとの職務チェック**
  「冒頭で進め方を提案した」「発言の少ない人に振った」などを1項目ずつ
  達成／未達で判定し、未達の項目にはその場面で言うべきだった台詞を提示します。
- **議論の長さと雰囲気を選択**
  10〜50ターン、厳格／標準／緩いの3種類。企業ごとの選考時間や温度感に合わせられます。
- **お題のランダム生成**
  具体的／抽象的、業種指定に対応。実際に出題されたお題を自分で入力することもできます。

### 複数のシチュエーション

- アルバイト面接
- 新卒採用面接
- ITエンジニア採用面接
- 大学院・推薦入試面接

### エントリーシート対応（Max プラン）

- PDF を読み込んで、内容に基づいた面接が可能
- 研究計画書や志願理由書にも対応

---

## プラン・価格

| プラン | 月額 | 1日の回数 | 1回のターン数 | グループディスカッション | PDF読み込み |
|--------|------|-----------|---------------|--------------------------|-------------|
| **Free** | 無料 | 1回 | 4ターン | − | − |
| **Pro** | ¥480 | 10回 | 10ターン | ○ | − |
| **Max** | ¥980 | 10回 | 10ターン | ○ | ○ |

決済は Stripe。いつでも解約でき、解約時は webhook 経由で自動的に Free へ戻ります。

---

## 今すぐ試す

### ブラウザで体験

[Mokipra を開く](https://app.mokipra.jp)

メールアドレスの登録のみで始められます。クレジットカードは不要です。

### ローカルで開発

```bash
git clone https://github.com/koba0605/Mokipra.git
cd Mokipra

pip install -r requirements.txt

streamlit run app.py
```

`.streamlit/secrets.toml` に以下を設定してください。

```toml
OPENAI_API_KEY   = "sk-..."
SUPABASE_URL     = "https://xxxx.supabase.co"
SUPABASE_KEY     = "..."
STRIPE_SECRET_KEY = "sk_test_..."
STRIPE_PRICE_ID_PRO = "price_..."
STRIPE_PRICE_ID_MAX = "price_..."
APP_URL = "http://localhost:8501"
```

---

## 構成

```
mokipra.jp        →  静的HTMLのランディングページ（Cloudflare Pages）
app.mokipra.jp    →  Streamlit アプリ本体（Render）
webhook           →  Stripe イベント受信用の FastAPI（Render）
```

ランディングページを分離しているのは、Streamlit が SPA のため
Googlebot がレンダリングを完了できず、検索結果に本文が表示されなかったためです。
LP を素の HTML にすることで、meta タグ・構造化データ・本文をすべて制御できます。

### ファイル構成

| ファイル | 役割 |
|----------|------|
| `app.py` | アプリ本体。認証、面接、採点、決済、画面遷移 |
| `gd.py` | グループディスカッション機能。`app.py` から `gd.render()` で呼び出す |
| `webhook_server.py` | Stripe webhook（プランの昇格・解約時のダウングレード） |
| `patch_meta.py` | 起動時に Streamlit の `index.html` へ meta タグを注入 |
| `.github/workflows/` | Supabase のキープアライブと暗号化バックアップ |

---

## 技術スタック

### フロントエンド
- **Streamlit** — アプリのUI
- **Cloudflare Pages** — ランディングページのホスティング
- **Cloudflare DNS** — ドメイン管理

### バックエンド
- **Render** — Streamlit アプリと webhook サーバーのホスティング
- **FastAPI** — Stripe webhook の受信

### データベース・認証
- **Supabase** — PostgreSQL + 認証
- RLS（行レベルセキュリティ）でユーザーごとにデータを分離

### AI・音声技術
- **OpenAI API** — GPT-4o / GPT-4o-mini（面接AI・採点）、Whisper（音声認識）、TTS（音声合成）
- **Google Cloud TTS / ElevenLabs** — 音声合成のフォールバック

### 決済
- **Stripe** — サブスクリプション決済
- webhook でプランの昇格・解約を自動反映

### 運用
- **GitHub Actions** — Supabase のキープアライブ（週2回）と、
  GPG で暗号化した `pg_dump` の週次バックアップ
- **Google Search Console** — 検索パフォーマンスの計測
- **A8.net** — アフィリエイト広告（無料プランのみ表示）

---

## セキュリティ

- **認証** — Supabase Auth によるメールアドレス・パスワードログイン
- **データ分離** — RLS により、ユーザーは自分のデータのみアクセス可能
- **APIキー管理** — 環境変数と Streamlit Secrets で管理。リポジトリには含めない
- **XSS対策** — ユーザー入力と LLM 出力の両方を、HTML 出力前にエスケープ
- **プロンプトインジェクション対策** — ユーザー入力をタグで区切り、
  指示ではなくデータとして扱うよう明示。入力長も制限
- **バックアップ** — 週次の暗号化ダンプ。公開リポジトリのため GPG（AES256）で暗号化

---

## 開発の記録

1. **MVP 開発** — Streamlit でプロトタイプを構築
2. **データベース移行** — JSON ファイルから Supabase へ
3. **決済システム** — Stripe 導入、webhook による自動処理
4. **セキュリティ強化** — RLS 実装、キー管理の見直し
5. **Render へ移行** — 独自ドメイン（mokipra.jp）を設定
6. **SEO対応** — LP を静的 HTML として分離、Cloudflare Pages へ
7. **運用基盤** — GitHub Actions による自動バックアップとキープアライブ
8. **GD機能** — グループディスカッション練習を `gd.py` として追加

---

## お問い合わせ

- **メール**: mokipra.ai.official@gmail.com
- **GitHub**: [@koba0605](https://github.com/koba0605)

---

<div align="center">

[⬆ トップへ](#mokipra---ai模擬面接パートナー)

</div>
