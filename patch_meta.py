"""
Streamlit の index.html に SEO 用 meta タグを注入する。

Streamlit は meta description を設定する API を持たないため、
インストール済みパッケージ内の static/index.html を直接書き換える。

- マーカーコメントで囲むことで、何度実行しても重複しない（冪等）
- Streamlit のバージョンが上がって index.html が再生成されても、
  起動のたびに実行すれば再度注入される

使い方:
    python patch_meta.py
Render の Start Command:
    python patch_meta.py && streamlit run app.py --server.port $PORT --server.address 0.0.0.0
"""

from pathlib import Path
import sys

import streamlit

# ---------------------------------------------------------------
# 設定（ここだけ書き換える）
# ---------------------------------------------------------------
SITE_URL = "https://mokipra.jp"
TITLE = "Mokipra（モキプラ）- AI模擬面接パートナー"
DESCRIPTION = (
    "AIが面接官として質問し、回答をその場で評価するオンライン模擬面接サービス。"
    "アルバイト・新卒就活・エンジニア転職・大学院入試の面接練習に対応。"
    "音声入力で本番に近い形式の練習ができます。"
)
# static/ 配下のファイル名は実環境に合わせて変更すること
FAVICON_PATH = "/app/static/favicon.png"
OG_IMAGE_PATH = "/app/static/og.png"

# JS を実行しないクローラ向けのフォールバック本文
NOSCRIPT_TEXT = (
    "Mokipra（モキプラ）は、AIが面接官となって模擬面接を行うWebサービスです。"
    "アルバイト・新卒就活・エンジニア転職・大学院入試の4つの面接シーンに対応し、"
    "回答内容を6段階で評価します。音声入力にも対応しています。"
)

BEGIN = "<!-- BEGIN MOKIPRA SEO -->"
END = "<!-- END MOKIPRA SEO -->"

META_BLOCK = f"""{BEGIN}
    <meta name="description" content="{DESCRIPTION}" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="{SITE_URL}/" />

    <link rel="icon" type="image/png" href="{FAVICON_PATH}" />
    <link rel="apple-touch-icon" href="{FAVICON_PATH}" />

    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Mokipra" />
    <meta property="og:title" content="{TITLE}" />
    <meta property="og:description" content="{DESCRIPTION}" />
    <meta property="og:url" content="{SITE_URL}/" />
    <meta property="og:image" content="{SITE_URL}{OG_IMAGE_PATH}" />
    <meta property="og:locale" content="ja_JP" />

    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{TITLE}" />
    <meta name="twitter:description" content="{DESCRIPTION}" />
    <meta name="twitter:image" content="{SITE_URL}{OG_IMAGE_PATH}" />
    {END}"""

NOSCRIPT_BLOCK = f"""{BEGIN}
    <noscript>
      <h1>{TITLE}</h1>
      <p>{NOSCRIPT_TEXT}</p>
    </noscript>
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

    # <body> 直後に noscript フォールバックを差し込む
    body_idx = html.find("<body")
    if body_idx != -1:
        insert_at = html.find(">", body_idx)
        if insert_at != -1:
            insert_at += 1
            html = html[:insert_at] + f"\n    {NOSCRIPT_BLOCK}" + html[insert_at:]

    try:
        index_path.write_text(html, encoding="utf-8")
    except PermissionError:
        print(f"[patch_meta] 書き込み権限がありません: {index_path}", file=sys.stderr)
        return 1

    print(f"[patch_meta] 注入完了 -> {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())