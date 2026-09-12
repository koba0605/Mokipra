"""音声認識の共通処理。

app.py（面接）と gd.py（グループディスカッション）の両方から使う。

【設計方針】
無音を API に送ってしまうと、Whisper 系のモデルは学習データ（字幕付き動画）に
頻出する定型句を「推測で」出力する。「ご視聴ありがとうございました」などがそれ。
文字列の照合だけでは種類が無限にあって追いきれないので、
**API に送る前に波形を解析して無音を弾く** のが本質的な対処になる。

さらに、精度向上のつもりで渡していた prompt（面接文脈のヒント）が、
無音時にはそのヒントに沿った文章を生成させる原因になっていた。
prompt は無音を排除できたうえで、短く限定的に使う。
"""

import array
import io
import math
import re
import wave

# numpy は Streamlit の依存として入っているが、間接依存に頼らず
# 無くても動くようにしておく（無い場合は標準ライブラリで計算する）。
try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

# ---------------------------------------------------------------------------
# しきい値
# ---------------------------------------------------------------------------
MIN_BYTES = 8000          # これ未満は録音が成立していない
MIN_DURATION = 0.6        # 秒。これ未満は言い切れていない
RMS_SILENCE = 0.004       # 全体の実効値がこれ未満なら無音とみなす
WINDOW_RMS = 0.012        # 有声と判定する窓の実効値
MIN_VOICED_RATIO = 0.04   # 有声窓の割合がこれ未満なら発話なしとみなす
MAX_BYTES = 24 * 1024 * 1024

# 無音時に出力されがちな定型句（保険。主たる防御は波形解析）
_HALLUCINATIONS = (
    "ご視聴ありがとうございました", "ご視聴ありがとうございます",
    "最後までご視聴いただきありがとうございました",
    "本日はお越しいただきありがとうございます",
    "本日はありがとうございました", "本日はよろしくお願いします",
    "チャンネル登録をお願いします", "チャンネル登録よろしくお願いします",
    "高評価とチャンネル登録をお願いします",
    "お疲れ様でした", "おつかれさまでした",
    "ありがとうございました", "ありがとうございます",
    "よろしくお願いします", "よろしくお願いいたします",
    "字幕は自動生成されています", "音声はありません", "音声が聞き取れません",
    "終わり", "以上です", "はい", "えー", "あー",
)

_PUNCT = re.compile(r"[。、,.!?！？\s・]")


def _norm(t: str) -> str:
    return _PUNCT.sub("", t or "")


def looks_like_hallucination(text: str) -> bool:
    """無音時に出る定型句かどうか。長い出力は本物とみなす。"""
    t = _norm(text)
    if len(t) > 25:
        return False
    return any(t == _norm(h) for h in _HALLUCINATIONS)


# ---------------------------------------------------------------------------
# 波形の解析
# ---------------------------------------------------------------------------
def analyze(audio_bytes: bytes):
    """WAV を解析して (継続秒数, 全体RMS, 有声割合) を返す。

    解析できない形式なら None を返し、呼び出し側は解析なしで続行する。
    """
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as w:
            n_frames = w.getnframes()
            width = w.getsampwidth()
            channels = w.getnchannels()
            rate = w.getframerate()
            raw = w.readframes(n_frames)
    except Exception:
        return None

    if not raw or not rate:
        return None

    if width not in (1, 2, 4):
        return None

    if np is not None:
        dtype = {1: np.uint8, 2: np.int16, 4: np.int32}[width]
        arr = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        if arr.size == 0:
            return None
        if width == 1:
            arr = (arr - 128.0) / 128.0
        else:
            arr = arr / float(np.iinfo(dtype).max)
        if channels > 1:
            usable = (arr.size // channels) * channels
            arr = arr[:usable].reshape(-1, channels).mean(axis=1)

        duration = arr.size / float(rate)
        overall_rms = float(np.sqrt(np.mean(np.square(arr))))

        win = max(1, int(rate * 0.05))
        usable = (arr.size // win) * win
        if usable == 0:
            return duration, overall_rms, 0.0
        windows = arr[:usable].reshape(-1, win)
        win_rms = np.sqrt(np.mean(np.square(windows), axis=1))
        voiced_ratio = float(np.mean(win_rms > WINDOW_RMS))
        return duration, overall_rms, voiced_ratio

    # --- numpy が無い場合のフォールバック ---
    typecode = {1: "B", 2: "h", 4: "i"}[width]
    samples = array.array(typecode)
    samples.frombytes(raw[: len(raw) - (len(raw) % width)])
    if not samples:
        return None

    scale = 128.0 if width == 1 else float(2 ** (width * 8 - 1))
    offset = 128.0 if width == 1 else 0.0
    vals = [(v - offset) / scale for v in samples]

    if channels > 1:
        usable = (len(vals) // channels) * channels
        vals = [sum(vals[i:i + channels]) / channels
                for i in range(0, usable, channels)]

    duration = len(vals) / float(rate)
    overall_rms = math.sqrt(sum(v * v for v in vals) / len(vals))

    win = max(1, int(rate * 0.05))
    n_win = len(vals) // win
    if n_win == 0:
        return duration, overall_rms, 0.0
    voiced = 0
    for i in range(n_win):
        chunk = vals[i * win:(i + 1) * win]
        if math.sqrt(sum(v * v for v in chunk) / win) > WINDOW_RMS:
            voiced += 1
    voiced_ratio = voiced / n_win
    return duration, overall_rms, voiced_ratio


# ---------------------------------------------------------------------------
# 文字起こし
# ---------------------------------------------------------------------------
# 新しいモデルの方が日本語の精度が高い。使えない場合は whisper-1 に落とす。
# gpt-4o-transcribe は prompt の効きも whisper-1 より安定している。
_MODELS = ("gpt-4o-transcribe", "whisper-1")

# 認識結果によく混ざる不要な記号や重複表現を落とす
_CLEANUP = (
    (re.compile(r"[「」『』]"), ""),
    (re.compile(r"[ \u3000]{2,}"), " "),
    (re.compile(r"(。){2,}"), "。"),
)


def _cleanup(text: str) -> str:
    for pat, rep in _CLEANUP:
        text = pat.sub(rep, text)
    return text.strip()


def build_hint(base: str = "", terms=None) -> str:
    """文字起こしのヒント文を組み立てる。

    固有名詞（氏名・大学名・企業名・専門用語）を列挙して渡すと、
    その語を優先して当てるようになる。人名の漢字表記もここで矯正できる。
    漢字から読みを逆算するより、正解を先に教える方が確実。

    長い文脈説明を入れると、無音時にその文脈へ引きずられた文章を
    生成する原因になるため、語の列挙にとどめる。
    """
    parts = []
    if terms:
        cleaned = []
        for t in terms:
            t = (t or "").strip()
            if t and t not in cleaned:
                cleaned.append(t)
        if cleaned:
            # 語を並べるだけの形にする（文章にしない）
            parts.append("、".join(cleaned[:20]))
    if base:
        parts.append(base)
    hint = " ".join(parts).strip()
    return hint[:220]


def transcribe(client, audio_bytes: bytes, hint: str = ""):
    """音声を文字起こしする。戻り値は (テキスト, エラーメッセージ)。

    client : OpenAI クライアント
    hint   : 固有名詞や専門用語の列挙。build_hint() で組み立てる。
             無音は事前に弾いているため、ここで定型句を誘発する心配は小さい。
    """
    if not audio_bytes:
        return "", "音声データが空です。"
    if len(audio_bytes) < MIN_BYTES:
        return "", "録音が短すぎます。マイクに向かって話してから停止してください。"
    if len(audio_bytes) > MAX_BYTES:
        return "", "録音が長すぎます。1回の回答は3分以内を目安にしてください。"

    # --- API に送る前に無音を弾く ---
    stats = analyze(audio_bytes)
    if stats is not None:
        duration, overall_rms, voiced_ratio = stats
        if duration < MIN_DURATION:
            return "", "録音が短すぎます。もう少し長く話してください。"
        if overall_rms < RMS_SILENCE or voiced_ratio < MIN_VOICED_RATIO:
            return "", ("音声が検出できませんでした。マイクが有効か確認し、"
                        "少し大きめの声で話してください。")

    last_error = None
    for model in _MODELS:
        try:
            buf = io.BytesIO(audio_bytes)
            buf.name = "answer.wav"
            kwargs = {
                "model": model,
                "file": buf,
                "language": "ja",
                "temperature": 0,
            }
            if hint:
                kwargs["prompt"] = hint
            result = client.audio.transcriptions.create(**kwargs)
            text = (getattr(result, "text", "") or "").strip()

            if not text:
                return "", "音声を認識できませんでした。もう一度お試しください。"
            if looks_like_hallucination(text):
                return "", "発話を検出できませんでした。もう一度録音してください。"
            return _cleanup(text), None
        except Exception as e:
            last_error = e
            continue  # 次のモデルで再試行

    return "", f"音声の変換に失敗しました。テキスト入力をご利用ください。（{last_error}）"
