import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
from streamlit_cookies_controller import CookieController
import io
import json
import os
import time
import uuid
from datetime import date, datetime

# ==============================================================================
# 1. ページ基本設定（ブランド名：Mokipra）
# ==============================================================================
st.set_page_config(page_title="Mokipra - AI模擬面接パートナー", page_icon="✨", layout="wide")

# Clientの初期化 (Secretsや環境変数からAPIキーを取得)
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "")))

# ==============================================================================
# 🚧 【方法A：一時停止用】Stripe審査・開発中メンテナンス画面
# ※ 本番運用時に機能を有効化したい場合は、以下の `st.stop()` 行をコメントアウト（#）してください
# ==============================================================================
st.title("✨ Mokipra")
st.warning("🚧 現在、システム連携およびサービス準備中のため一時公開を停止しております。正式リリースをお待ちください！")
st.info("💡 Stripe審査・システムテスト用のプレビューページです。API通信は安全に停止されています。")

st.stop()  # ここでアプリの実行を完全停止（API消費0円・無駄なリソース消費を防止）
# ==============================================================================


# ====================================================
# 🍪 クッキー ＆ ユーザー識別管理
# ====================================================
controller = CookieController()

# クッキーからユーザーIDを取得。なければ新規発行して保存
user_id = controller.get('mokipra_user_id')
if not user_id:
    user_id = str(uuid.uuid4())
    controller.set('mokipra_user_id', user_id)

# ====================================================
# 📂 データベース（JSON）関数
# ====================================================
HISTORY_FILE = "history.json"
USAGE_FILE = "usage_db.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"scores": [], "dates": [], "details": []}

def save_history(score, context, date_str):
    data = load_history()
    data["scores"].append(score)
    data["dates"].append(date_str)
    data["details"].append(context)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- ユーザーごとの利用回数・プラン管理 ---
def load_usage():
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_usage(data):
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 現在のユーザーデータを読み込み
usage_data = load_usage()
today_str = str(date.today())

# 新規ユーザー、または日付が変わった場合のリセット処理
if user_id not in usage_data:
    usage_data[user_id] = {"date": today_str, "count": 0, "plan": "Free"}
elif usage_data[user_id]["date"] != today_str:
    usage_data[user_id]["date"] = today_str
    usage_data[user_id]["count"] = 0

save_usage(usage_data)

# 変数に現在のユーザーの情報をセット
current_user_plan = usage_data[user_id]["plan"]
current_daily_usage = usage_data[user_id]["count"]

# ====================================================
# 🎨 カスタムCSS
# ====================================================
st.markdown("""
    <style>
    header { visibility: hidden !important; }
    #MainMenu { visibility: hidden !important; }
    .stDeployButton {display:none !important;}
    .stApp { background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%); font-family: 'Inter', sans-serif; }
    .app-title { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 2.8rem; margin-bottom: 0.5rem; }
    .glass-card { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 20px; padding: 24px; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05); margin-bottom: 20px; }
    .status-badge { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white; padding: 8px 16px; border-radius: 30px; font-weight: bold; font-size: 0.9rem; display: inline-block; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.2); }
    .ad-card { background: #ffffff; border: 2px dashed #93c5fd; border-radius: 16px; padding: 16px; text-align: center; transition: all 0.3s ease; cursor: pointer; margin-bottom: 12px; }
    .ad-card:hover { border-color: #3b82f6; transform: translateY(-3px); box-shadow: 0 10px 20px rgba(59, 130, 246, 0.1); }
    .stButton>button { border-radius: 12px !important; font-weight: 600 !important; transition: all 0.3s ease !important; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="app-title">✨ Mokipra - AI模擬面接パートナー</h1>', unsafe_allow_html=True)

# --- チャット状態の初期化 ---
if "setup_complete" not in st.session_state: st.session_state.setup_complete = False
if "turn_count" not in st.session_state: st.session_state.turn_count = 0
if "start_time" not in st.session_state: st.session_state.start_time = time.time()
if "audio_history" not in st.session_state: st.session_state.audio_history = []

PLAN_LIMITS = {"Free": 1, "Pro": 10, "Max": 50}
current_limit = PLAN_LIMITS[current_user_plan]
TOTAL_TURNS = 4
INTERVIEWER_IMAGE = "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=800&q=80"

# --- サイドバー ---
with st.sidebar:
    st.markdown("### 👤 Mokipra Dashboard")
    st.write(f"現在のプラン: **{current_user_plan}**")
    st.write(f"本日の使用状況: **{current_daily_usage} / {current_limit} 回**")
    st.progress(current_daily_usage / current_limit if current_limit > 0 else 1.0)
    
    st.markdown("---")
    st.link_button("📝 バグ報告・ご要望はこちら", "https://docs.google.com/forms/", use_container_width=True)

    st.markdown("---")
    st.caption("🛠️ 開発者用テストパネル")
    test_plan = st.selectbox("プラン切り替え", ["Free", "Pro", "Max"])
    if st.button("適用する", use_container_width=True):
        # テスト用にデータベースのプランを強制変更して永続化
        usage_data[user_id]["plan"] = test_plan
        save_usage(usage_data)
        st.rerun()

# ====================================================
# 【画面1】制限チェック ＆ 事前設定
# ====================================================
if current_daily_usage >= current_limit and not st.session_state.setup_complete:
    st.error("⚠️ 本日の面接練習回数の上限に達しました。明日リセットされます。")
    st.link_button("💎 Proプラン(480円)に登録", "https://stripe.com/jp", use_container_width=True)
    st.link_button("🔥 Maxプラン(980円)に登録", "https://stripe.com/jp", use_container_width=True)

elif not st.session_state.setup_complete:
    st.markdown("""
    <div class="glass-card">
        <h3 style="margin-top:0; color:#1e293b;">📋 面接シチュエーションの設定</h3>
        <p style="color:#475569;">本番に近い環境を作るため、練習したい面接の種別を選択してください。</p>
    </div>
    """, unsafe_allow_html=True)
    
    modes = ["アルバイト用", "新卒就活用（一般）", "IT・情報セキュリティエンジニア就活用（Max限定）", "大学院入試用（Max限定）"]
    interview_mode = st.radio("▼ 面接種別を選択", modes)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 面接をスタートする", type="primary", use_container_width=True):
        
        # スタート時にデータベースの回数を+1して保存
        usage_data[user_id]["count"] += 1
        save_usage(usage_data)

        expertise_instruction = "応募者の人柄や意欲、一般的な経験について優しく深掘りしてください。"
        if current_user_plan == "Max":
            expertise_instruction = "あなたは業界のトップエキスパートです。ユーザーの回答に対し、専門的な技術知識、論理的思考力、または具体的な課題解決能力を問う、非常に鋭く高度な深掘り質問を行ってください。"

        dynamic_system_prompt = f"""
        あなたは【{interview_mode}】の面接官です。ユーザーは応募者です。
        【面接の進め方】
        1. まず最初に、面接官として挨拶をして、1つ目の質問を投げかけてください。
        2. 以降は、ユーザーの回答を受け止め、「回答内容に対する的確な深掘り質問（1〜2文）」を行ってください。
        3. {expertise_instruction}
        4. あらかじめ用意された質問を順番に読むのではなく、実際の面接のように「相手の前の回答」を踏まえた会話のキャッチボールをしてください。
        【禁止事項】面接に関係のない話題には「面接を続けましょう」と返し、絶対に雑談に乗らないでください。
        """
        st.session_state.messages = [{"role": "system", "content": dynamic_system_prompt}]
        st.session_state.audio_history = []
        st.session_state.interview_context = interview_mode
        st.session_state.setup_complete = True
        
        with st.spinner("面接官が入室しています..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini", messages=st.session_state.messages, temperature=0.7
            )
            first_reply = response.choices[0].message.content
            audio_response = client.audio.speech.create(
                model="tts-1", voice="onyx", speed=1.0, input=first_reply
            )
            st.session_state.audio_history.append(audio_response.content)
            st.session_state.messages.append({"role": "assistant", "content": first_reply})
            
        st.session_state.start_time = time.time()
        st.rerun()

# ====================================================
# 【画面2】2カラムメイン画面
# ====================================================
else:
    left_col, right_col = st.columns([1.3, 0.7], gap="large")

    with left_col:
        tab_chat, tab_redo, tab_mypage = st.tabs(["🎙️ 面接セッション", "🔄 リトライ", "📈 マイページ (成績)"])

        with tab_chat:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("##### 🏢 担当面接官")
            st.markdown(f'<img src="{INTERVIEWER_IMAGE}" width="150" style="border-radius: 10px;">', unsafe_allow_html=True)
            st.markdown("---")

            audio_idx = 0
            for msg in st.session_state.messages:
                if msg["role"] != "system" and not msg["content"].startswith("【総合面接結果報告書】"):
                    avatar_icon = "👔" if msg["role"] == "assistant" else "👤"
                    with st.chat_message(msg["role"], avatar=avatar_icon):
                        st.markdown(msg["content"])
                        if msg["role"] == "assistant" and audio_idx < len(st.session_state.audio_history):
                            st.audio(st.session_state.audio_history[audio_idx], format="audio/mp3")
                            audio_idx += 1
            st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.turn_count < TOTAL_TURNS:
                st.markdown("---")
                audio = mic_recorder(start_prompt="🎤 タップして声で回答", stop_prompt="⏹️ 録音を終了して送信", key='recorder')
                
                user_text = None
                if audio is not None and "bytes" in audio:
                    with st.spinner("音声を解析中..."):
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", file=io.BytesIO(audio["bytes"]), language="ja"
                        )
                        user_text = transcript.text

                text_input = st.chat_input("またはテキストで回答を入力...")
                if text_input: user_text = text_input

                if user_text:
                    elapsed_time = int(time.time() - st.session_state.start_time)
                    st.session_state.turn_count += 1
                    st.session_state.messages.append({"role": "user", "content": f"{user_text} (※回答時間: {elapsed_time}秒)"})

                    with st.chat_message("user", avatar="👤"):
                        st.markdown(f"{user_text} \n\n*(⏱️ タイム: {elapsed_time}秒)*")

                    with st.chat_message("assistant", avatar="👔"):
                        with st.spinner("面接官が回答を考案中..."):
                            if st.session_state.turn_count >= TOTAL_TURNS:
                                st.session_state.messages.append({"role": "system", "content": "これが最後のやり取りです。質問はせず、面接を締めくくる挨拶のみを手短に行ってください。"})
                                
                            response = client.chat.completions.create(
                                model="gpt-4o-mini", messages=st.session_state.messages, temperature=0.7
                            )
                            ai_reply = response.choices[0].message.content
                            st.markdown(ai_reply)

                        with st.spinner("音声生成中..."):
                            audio_response = client.audio.speech.create(
                                model="tts-1", voice="onyx", speed=1.0, input=ai_reply
                            )
                            st.session_state.audio_history.append(audio_response.content)
                            st.audio(audio_response.content, format="audio/mp3", autoplay=True)

                    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                    st.session_state.start_time = time.time()
                    st.rerun()

        with tab_redo:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if 0 < st.session_state.turn_count < TOTAL_TURNS:
                st.info("一つ前の質疑応答を取り消して、回答をもう一度やり直すことができます。")
                if st.button("↩️ 1つ前の質問に戻る", use_container_width=True):
                    st.session_state.messages = st.session_state.messages[:-2]
                    st.session_state.audio_history.pop()
                    st.session_state.turn_count -= 1
                    st.session_state.start_time = time.time()
                    st.rerun()
            else:
                st.write("現在やり直せる回答はありません。")
            st.markdown('</div>', unsafe_allow_html=True)

        with tab_mypage:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📈 過去の面接スコア推移")
            history_data = load_history()
            if len(history_data["scores"]) > 0:
                st.line_chart(history_data["scores"])
                for d, s, ctx in zip(reversed(history_data["dates"]), reversed(history_data["scores"]), reversed(history_data["details"])):
                    st.caption(f"{d} - {ctx} : **{s}点**")
            else:
                st.info("面接を最後まで完了すると、ここに成長グラフが表示されます。")
            st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown(f"""
        <div class="glass-card">
            <h4 style="margin-top:0; color:#1e293b;">📊 Status</h4>
            <p style="margin:5px 0;"><span class="status-badge">{st.session_state.interview_context}</span></p>
            <p style="margin:10px 0 5px 0; font-size:0.9rem; font-weight:bold;">進行状況: {st.session_state.turn_count} / {TOTAL_TURNS}</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(st.session_state.turn_count / TOTAL_TURNS)

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Sponsored")
        st.markdown("""
        <a href="#" target="_blank" style="text-decoration:none; color:inherit;">
            <div class="ad-card">
                <span style="font-size:24px;">👔</span><br>
                <b>【PR】優良企業オファーを獲得</b><br>
                <span style="font-size:0.8rem; color:#64748b;">あなたに合った企業をプロが無料で紹介！</span>
            </div>
        </a>
        <a href="#" target="_blank" style="text-decoration:none; color:inherit;">
            <div class="ad-card">
                <span style="font-size:24px;">💻</span><br>
                <b>【PR】未経験からITエンジニアへ</b><br>
                <span style="font-size:0.8rem; color:#64748b;">無料プログラミングスクール登録はこちら</span>
            </div>
        </a>
        """, unsafe_allow_html=True)

        if st.session_state.turn_count >= TOTAL_TURNS:
            st.markdown("---")
            st.success("🎉 面接セッション終了！")
            
            if "final_eval" not in st.session_state:
                with st.spinner("AIが総合アドバイスシートを作成中..."):
                    
                    if current_user_plan == "Free":
                        rewrite_instruction = "・✨ プロの模範解答: 実際の模範解答は出力せず、「【🔒 Proプラン限定機能】プロによる模範解答（リライト）を確認するには、Proプラン以上の登録が必要です。」という案内文だけを記載してください。"
                    else:
                        rewrite_instruction = "・✨ プロの模範解答: （ユーザーの回答の中で一番惜しかったものを1つ選び、「こう答えれば完璧だった」という具体的なセリフを作成）"

                    eval_prompt = [
                        {"role": "system", "content": f"""
        あなたはベテラン面接官です。面接結果として以下を出力してください。
        必ず『総合スコア（数字のみ）』を本文の先頭に含めてください。

        【総合面接結果報告書】
        ・総合スコア: 〇〇点 / 100点
        ・良かった点 / 改善アドバイス
        ・⏱️ 回答スピードの評価: （ユーザーの回答時間を見て評価）
        {rewrite_instruction}
        """}
                    ] + st.session_state.messages[1:]

                    eval_response = client.chat.completions.create(
                        model="gpt-4o-mini", messages=eval_prompt, temperature=0.7
                    )
                    eval_text = eval_response.choices[0].message.content
                    st.session_state.final_eval = eval_text
                    
                    import re
                    match = re.search(r'スコア[^\d]*(\d{1,3})', eval_text)
                    score = int(match.group(1)) if match else 50
                    save_history(score, st.session_state.interview_context, datetime.now().strftime("%Y-%m-%d %H:%M"))

            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.info(st.session_state.final_eval)
            
            if current_user_plan == "Free":
                st.warning("💡 Proプランに登録すると、あなたの回答をプロが添削した「模範解答」が見られるようになります！")
                st.link_button("💎 Proプランにアップグレード", "https://stripe.com/jp", use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("🔄 新しい面接を開始する", type="primary", use_container_width=True):
                st.session_state.setup_complete = False
                st.session_state.turn_count = 0
                if "final_eval" in st.session_state: del st.session_state["final_eval"]
                st.rerun()