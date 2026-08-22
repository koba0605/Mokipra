# Mokipra - AI模擬面接パートナー

<div align="center">

![Mokipra](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11+-blue)

**AIが面接官になる、リアルな面接練習サービス**

[🚀 デモを試す](https://mokipra-app.streamlit.app) • [📖 ドキュメント](#-技術スタック) • [🐛 バグ報告](https://github.com/koba0605/Mokipra/issues)

</div>

---

## 🎯 Mokipra とは

Mokipra は、**AI が面接官になってリアルな面接練習ができる** SaaS（Web サービス）です。

就活生や転職希望者が、本番の面接に向けて何度でも練習できます。

- ✅ 音声による自然な面接体験
- ✅ AI による自動採点と改善アドバイス
- ✅ 複数のシチュエーションに対応
- ✅ PDF 資料の読み込み対応（Max プラン）

---

## ✨ 主な機能

### 🎤 リアルな音声面接

- OpenAI の最新モデル（GPT-4o）が面接官を担当
- 自然な音声合成で、本番の面接に近い体験
- ユーザーの音声入力にリアルタイム対応

### 📊 自動採点と改善フィードバック

- 面接終了後、AI が自動的に採点
- 「強み」「改善点」「次のステップ」を提示
- 何度でも練習して上達をサポート

### 🎓 複数のシチュエーション

以下のような様々な面接に対応：

- 🏪 **アルバイト面接**
- 🎯 **新卒採用面接**
- 💻 **ITエンジニア採用面接**
- 🎓 **大学院入試面接**

### 📄 エントリーシート対応（Max プラン）

- PDF を読み込んで、内容に基づいた面接が可能
- 研究計画書や志願理由書にも対応
- より個別化された深い面接練習

---

## 💰 プラン・価格

| プラン | 月額 | 1日の回数 | 特徴 |
|--------|------|---------|------|
| **Free** | 無料 | 1回 | お試し版 |
| **Pro** | ¥480 | 10回 | 本格練習用 |
| **Max** | ¥980 | 20回 | PDF読み込み機能付き |

---

## 🚀 今すぐ試す

### デモ版で体験

[**🎤 Mokipra を今すぐ試す**](https://mokipra-app.streamlit.app)

ブラウザで開いて、メールアドレスで新規登録するだけで、すぐに面接練習が開始できます。

### ローカルで開発

```bash
# リポジトリをクローン
git clone https://github.com/koba0605/Mokipra.git
cd Mokipra

# 依存パッケージをインストール
pip install -r requirements.txt

# Streamlit で起動
streamlit run app.py
```

---

## 🛠 技術スタック

Mokipra は、複数のクラウドサービスを連携させた **本物の SaaS** として構築されています。

### フロントエンド
- **Streamlit** - ユーザーインターフェース
- **Streamlit Community Cloud** - 本番環境ホスティング
- **Google Analytics** - トラフィック分析

### バックエンド
- **FastAPI** - webhook サーバー
- **Render** - webhook サーバーホスティング

### データベース・認証
- **Supabase** - PostgreSQL データベース + 認証
- RLS（行レベルセキュリティ）で個人情報を厳格に保護

### AI・音声技術
- **OpenAI API** - GPT-4o（面接AI）、Whisper（音声認識）、TTS（音声合成）
- **Google Cloud TTS / ElevenLabs** - 高品質な音声合成

### 決済
- **Stripe** - 安全な決済処理
- webhook による自動決済処理

### その他
- **GitHub** - ソースコード管理
- **A8.net** - アフィリエイト広告

---

## 🔒 セキュリティ

- 🔐 **認証**: Supabase Auth でメールアドレス・パスワードログイン
- 🛡️ **データ保護**: RLS により、ユーザーは自分のデータのみアクセス可能
- 🔑 **API キー管理**: Streamlit Secrets と Render Environment で安全に管理
- 💳 **決済**: Stripe で安全に処理、webhook による自動更新

---

## 📊 開発過程

Mokipra の開発では、以下の段階を経て現在の形になりました：

1. **MVP 開発** - Streamlit でフロントエンド構築
2. **データベース移行** - JSON ファイルから Supabase へ刷新
3. **決済システム** - Stripe 導入、webhook 自動化
4. **セキュリティ強化** - RLS 実装、API キー管理
5. **本番デプロイ** - Streamlit Cloud + Render での運用


---

## 🤝 貢献

プルリクエストやバグ報告は大歓迎です！

[Issues](https://github.com/koba0605/Mokipra/issues) でバグ報告、[Discussions](https://github.com/koba0605/Mokipra/discussions) で機能提案をお願いします。

---

## 📧 お問い合わせ

- **メール**: mokipra.ai.official@gmail.com
- **GitHub**: [@koba0605](https://github.com/koba0605)

---

<div align="center">

Made with ❤️ by Mokipra Team

[⬆ トップへ](#mokipra---ai模擬面接パートナー)

</div>
