"""Streamlit の index.html に SEO / PWA 用のタグを注入する。

Streamlit には meta タグや manifest を設定する API が無いため、
インストール済みパッケージ内の static/index.html を直接書き換える。

- マーカーコメントで囲むことで、何度実行しても重複しない（冪等）
- Streamlit のバージョンが上がって index.html が再生成されても、
  起動のたびに実行すれば再度注入される

使い方:
    python patch_meta.py
Render の Start Command:
    python patch_meta.py && streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
"""

from pathlib import Path
import sys

import streamlit

# ---------------------------------------------------------------
# 設定（ここだけ書き換える）
# ---------------------------------------------------------------
APP_URL = "https://app.mokipra.jp"   # このアプリ自身のURL
SITE_URL = "https://mokipra.jp"      # LP（公式サイト）のURL

TITLE = "Mokipra（モキプラ）- AI模擬面接パートナー"
DESCRIPTION = (
    "AIが面接官として質問し、回答をその場で評価するオンライン模擬面接サービス。"
    "アルバイト・新卒就活・エンジニア転職・大学院入試の面接練習に対応。"
    "音声入力で本番に近い形式の練習ができます。"
)

# config.toml の enableStaticServing = true により
# ./static/ 配下は /app/static/<filename> で配信される
ICON_LINKS = """<link rel="icon" type="image/png" sizes="48x48" href="/app/static/favicon-48.png" />
    <link rel="icon" type="image/png" sizes="96x96" href="/app/static/favicon-96.png" />
    <link rel="icon" type="image/png" sizes="192x192" href="/app/static/favicon-192.png" />
    <link rel="icon" type="image/png" href="/app/static/favicon.png" />
    <link rel="apple-touch-icon" href="/app/static/apple-touch-icon.png" />"""

BEGIN = "<!-- BEGIN MOKIPRA SEO -->"
END = "<!-- END MOKIPRA SEO -->"

# アプリ本体は検索結果に出す必要がない。
# LP（mokipra.jp）を検索結果に出したいので noindex にする。
# このとき canonical は必ず自分自身を指すこと。
# 他ページを指す canonical と noindex を併用すると指示が矛盾し、
# Google が処理を保留する。
META_BLOCK = f"""{BEGIN}
    <meta name="description" content="{DESCRIPTION}" />
    <meta name="robots" content="noindex, follow" />
    <link rel="canonical" href="{APP_URL}/" />

    {ICON_LINKS}

    <!-- PWA（ホーム画面への追加） -->
    <link rel="manifest" href="/app/static/manifest.json" />
    <meta name="theme-color" content="#22385C" />
    <meta name="mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="default" />
    <meta name="apple-mobile-web-app-title" content="Mokipra" />

    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Mokipra" />
    <meta property="og:title" content="{TITLE}" />
    <meta property="og:description" content="{DESCRIPTION}" />
    <meta property="og:url" content="{APP_URL}/" />
    <meta property="og:locale" content="ja_JP" />

    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="{TITLE}" />
    <meta name="twitter:description" content="{DESCRIPTION}" />

    <style>
      /* Streamlit 標準のUIを最初の描画から隠す。
         app.py 側にも同じ指定があるが、そちらは Python 実行後に
         注入されるため、読み込み中の数秒間だけ表示されてしまう。
         ここに置くことで、初回描画の時点から適用される。 */
      [data-testid="stStatusWidget"],
      [data-testid="stToolbar"],
      [data-testid="stToolbarActions"],
      [data-testid="stMainMenu"],
      [data-testid="stAppDeployButton"],
      [data-testid="stDecoration"],
      #MainMenu,
      .stDeployButton,
      .stAppDeployButton {{
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
      }}
      /* ヘッダーは背景だけ透明にする。高さを 0 にすると、
         この中にあるサイドバーの開閉ボタンまで潰れて開けなくなる。 */
      header[data-testid="stHeader"] {{
        background: transparent !important;
      }}
      /* サイドバーと開閉ボタンは常に表示する */
      [data-testid="stSidebar"],
      [data-testid="stSidebarCollapsedControl"],
      [data-testid="stSidebarCollapseButton"],
      [data-testid="collapsedControl"] {{
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
      }}
      /* 読み込み中の地色。白背景が一瞬出るのを防ぐ */
      html, body {{ background: #F4F4F0; }}

      /* ---- 処理中のローディングバー ----
         Streamlit は実行中に stApp の data-test-script-state を
         running に切り替える。これを手がかりに上端へバーを出す。
         標準のステータス表示（Stopボタン）は隠しているため、
         代わりに「今処理中である」ことをこれで伝える。 */
      [data-testid="stApp"]::before {{
        content: "";
        position: fixed;
        top: 0; left: 0;
        height: 3px; width: 100%;
        z-index: 999999;
        background: linear-gradient(90deg,
          rgba(34,56,92,0) 0%,
          #22385C 35%,
          #8FCDEA 65%,
          rgba(34,56,92,0) 100%);
        background-size: 40% 100%;
        background-repeat: no-repeat;
        opacity: 0;
        transition: opacity .18s ease;
        pointer-events: none;
      }}
      [data-testid="stApp"][data-test-script-state="running"]::before,
      [data-testid="stApp"][data-test-script-state="rerunRequested"]::before {{
        opacity: 1;
        animation: mkpLoadBar 1.1s cubic-bezier(.4,0,.2,1) infinite;
      }}
      @keyframes mkpLoadBar {{
        0%   {{ background-position: -40% 0; }}
        100% {{ background-position: 140% 0; }}
      }}

      /* ---- 再実行中に画面が薄くなるのを防ぐ ----
         Streamlit は更新待ちの要素へ data-stale を付けて
         半透明にする。切り替わるたびに全体がもやがかって見えるため、
         不透明のままにする。 */
      [data-stale="true"],
      [data-testid="stElementContainer"][data-stale="true"],
      .element-container[data-stale="true"],
      [data-testid="stVerticalBlock"][data-stale="true"] {{
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
      }}
      [data-testid="stApp"][data-test-script-state="running"] .stMarkdown,
      [data-testid="stApp"][data-test-script-state="running"] [data-testid="stVerticalBlock"] {{
        opacity: 1 !important;
        filter: none !important;
      }}
    </style>
    {END}"""

# JS を実行しないクローラ向けのフォールバック本文と、
# Service Worker の登録。SW はキャッシュを行わない最小構成。
NOSCRIPT_TEXT = (
    "Mokipra（モキプラ）は、AIが面接官となって模擬面接を行うWebサービスです。"
    "アルバイト・新卒就活・エンジニア転職・大学院入試の4つの面接シーンに対応し、"
    "グループディスカッション練習もできます。"
)

BODY_BLOCK = f"""{BEGIN}
    <noscript>
      <h1>{TITLE}</h1>
      <p>{NOSCRIPT_TEXT}</p>
      <p><a href="{SITE_URL}">Mokipra 公式サイト</a></p>
    </noscript>
    <script>
      // ホーム画面への追加を有効にするための登録。
      // sw.js 自体はキャッシュを行わないので、デプロイ後に古い画面が
      // 残ることはない。
      if ("serviceWorker" in navigator) {{
        window.addEventListener("load", function () {{
          navigator.serviceWorker
            .register("/app/static/sw.js", {{ scope: "/" }})
            .catch(function (e) {{
              console.warn("service worker registration failed", e);
            }});
        }});
      }}
    </script>
    {END}"""


def strip_existing(html: str) -> str:
    """前回注入したブロックをすべて取り除く。"""
    while BEGIN in html and END in html:
        start = html.index(BEGIN)
        end = html.index(END, start) + len(END)
        html = html[:start] + html[end:]
    return html


def main() -> int:
    index_path = Path(streamlit.__file__).parent / "static" / "index.html"

    if not index_path.exists():
        print(f"[patch_meta] index.html が見つかりません: {index_path}", file=sys.stderr)
        return 1

    html = index_path.read_text(encoding="utf-8")
    html = strip_existing(html)

    if "</head>" not in html:
        print("[patch_meta] </head> が見つかりません。中断します。", file=sys.stderr)
        return 1

    html = html.replace("</head>", f"    {META_BLOCK}\n  </head>", 1)

    # JS を実行しないクローラ向けに lang と title を静的に修正する。
    # set_page_config はクライアント側でしか適用されないため。
    html = html.replace('<html lang="en">', '<html lang="ja">', 1)
    html = html.replace("<title>Streamlit</title>", f"<title>{TITLE}</title>", 1)

    # <body> 直後に noscript と Service Worker 登録を差し込む
    body_idx = html.find("<body")
    if body_idx != -1:
        insert_at = html.find(">", body_idx)
        if insert_at != -1:
            insert_at += 1
            html = html[:insert_at] + f"\n    {BODY_BLOCK}" + html[insert_at:]

    try:
        index_path.write_text(html, encoding="utf-8")
    except PermissionError:
        print(f"[patch_meta] 書き込み権限がありません: {index_path}", file=sys.stderr)
        return 1

    print(f"[patch_meta] 注入完了 -> {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
