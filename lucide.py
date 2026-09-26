"""Lucide アイコンをインライン SVG として描画する。

Streamlit では React のアイコンライブラリをそのまま使えないため、
Lucide (https://lucide.dev, ISC License) の SVG パスをここに持ち、
`unsafe_allow_html=True` の箇所へ文字列として差し込む。

絵文字を使わない理由:
- 環境ごとに字形と大きさが変わり、レイアウトが崩れる
- 色を指定できないため、画面の配色から浮く
- 読み上げソフトが意図しない読み方をする

使い方:
    from lucide import icon
    st.markdown(f'<span>{icon("mic")} 音声で回答</span>', unsafe_allow_html=True)

色は currentColor なので、親要素の color をそのまま継いで表示される。
"""

# ---------------------------------------------------------------------------
# パス定義（viewBox 24x24、線画、fill なし）
# ---------------------------------------------------------------------------
_PATHS = {
    # --- 入出力 ---
    "mic": '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>'
           '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/>'
           '<line x1="12" x2="12" y1="19" y2="22"/>',
    "volume": '<path d="M11 4.7a.7.7 0 0 0-1.2-.5L6.4 7.6a1.4 1.4 0 0 1-1 .4H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.4a1.4 1.4 0 0 1 1 .4l3.4 3.4a.7.7 0 0 0 1.2-.5Z"/>'
              '<path d="M16 9a5 5 0 0 1 0 6"/>'
              '<path d="M19.4 5.6a9 9 0 0 1 0 12.7"/>',
    "message": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "send": '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',

    # --- 人・組織 ---
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>'
            '<circle cx="12" cy="7" r="4"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
             '<circle cx="9" cy="7" r="4"/>'
             '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
             '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "building": '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/>'
                '<path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/>'
                '<path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/>'
                '<path d="M10 6h4"/><path d="M10 10h4"/>'
                '<path d="M10 14h4"/><path d="M10 18h4"/>',
    "store": '<path d="m2 7 4.4-4.4A2 2 0 0 1 7.8 2h8.4a2 2 0 0 1 1.4.6L22 7"/>'
             '<path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>'
             '<path d="M15 22v-4a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4"/>'
             '<path d="M2 7h20"/>',
    "graduation-cap": '<path d="M21.4 10.9a1 1 0 0 0 0-1.8L12.8 5.2a2 2 0 0 0-1.6 0L2.6 9.1a1 1 0 0 0 0 1.8l8.6 3.9a2 2 0 0 0 1.6 0z"/>'
                      '<path d="M22 10v6"/>'
                      '<path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',

    # --- 書類 ---
    "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
                 '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
                 '<path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "file-pen": '<path d="M12.5 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8l6 6v2.5"/>'
                '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
                '<path d="M18.4 12.6a2 2 0 0 1 3 3L17 20l-4 1 1-4Z"/>',
    "clipboard-check": '<rect width="8" height="4" x="8" y="2" rx="1"/>'
                       '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
                       '<path d="m9 14 2 2 4-4"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9L9.6 3.9A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',

    # --- 判定 ---
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "circle-x": '<circle cx="12" cy="12" r="10"/>'
                '<path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
    "circle-alert": '<circle cx="12" cy="12" r="10"/>'
                    '<path d="M12 8v4"/><path d="M12 16h.01"/>',
    "triangle-alert": '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3"/>'
                      '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="10"/>'
            '<path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "minus": '<path d="M5 12h14"/>',

    # --- 分析 ---
    "bar-chart": '<path d="M3 3v18h18"/><path d="M18 17V9"/>'
                 '<path d="M13 17V5"/><path d="M8 17v-3"/>',
    "trending-up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
                   '<polyline points="16 7 22 7 22 13"/>',
    "search-check": '<path d="m8 11 2 2 4-4"/><circle cx="11" cy="11" r="8"/>'
                    '<path d="m21 21-4.3-4.3"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/>'
              '<circle cx="12" cy="12" r="2"/>',
    "list-checks": '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/>'
                   '<path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>',

    # --- 状態 ---
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2"/>'
            '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "unlock": '<rect width="18" height="11" x="3" y="11" rx="2"/>'
              '<path d="M7 11V7a5 5 0 0 1 9.9-1"/>',
    "shield-check": '<path d="M20 13c0 5-3.5 7.5-7.7 9a1 1 0 0 1-.7 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.2-2.7a1.2 1.2 0 0 1 1.5 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/>'
                    '<path d="m9 12 2 2 4-4"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "sparkles": '<path d="M12 3 13.6 8.4 19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6Z"/>'
                '<path d="M19 3v3"/><path d="M20.5 4.5h-3"/>'
                '<path d="M5 17v2"/><path d="M6 18H4"/>',
    "star": '<path d="M12 2.5 15 9l6.8 1-4.9 4.8 1.2 6.7L12 18.3 5.9 21.5 7.1 14.8 2.2 10 9 9Z"/>',
    "lightbulb": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5A5.8 5.8 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.8.8 1.3 1.5 1.5 2.5"/>'
                 '<path d="M9 18h6"/><path d="M10 22h4"/>',

    # --- 操作 ---
    "refresh": '<path d="M3 12a9 9 0 0 1 9-9 9.8 9.8 0 0 1 6.7 2.7L21 8"/>'
               '<path d="M21 3v5h-5"/>'
               '<path d="M21 12a9 9 0 0 1-9 9 9.8 9.8 0 0 1-6.7-2.7L3 16"/>'
               '<path d="M8 16H3v5"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
                '<polyline points="7 10 12 15 17 10"/>'
                '<line x1="12" x2="12" y1="15" y2="3"/>',
    "copy": '<rect width="14" height="14" x="8" y="8" rx="2"/>'
            '<path d="M4 16a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2"/>',
    "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    "play": '<path d="M6 3 20 12 6 21Z"/>',
    "settings": '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/>'
                '<line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/>'
                '<line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/>'
                '<line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/>'
                '<line x1="16" x2="16" y1="18" y2="22"/>',

    # --- その他 ---
    "code": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    "megaphone": '<path d="m3 11 18-5v12L3 14v-3z"/>'
                 '<path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
    "credit-card": '<rect width="20" height="14" x="2" y="5" rx="2"/>'
                   '<line x1="2" x2="22" y1="10" y2="10"/>',
    "flask": '<path d="M14 2v6a2 2 0 0 0 .2 1l5.6 10a2 2 0 0 1-1.8 3H6a2 2 0 0 1-1.8-3l5.6-10a2 2 0 0 0 .2-1V2"/>'
             '<path d="M6.5 15h11"/><path d="M8.5 2h7"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-8 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 8-7.9Z"/>',
    "palette": '<path d="M12 22a10 10 0 1 1 10-10c0 1.7-1.3 3-3 3h-1.5a2.5 2.5 0 0 0-1.8 4.2A2 2 0 0 1 14 22Z"/>'
               '<circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/>'
               '<circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/>',
}

# 旧 line_icon の名前を Lucide 名へ対応づける
_ALIASES = {
    "score": "bar-chart",
    "shop": "store",
    "cap": "graduation-cap",
    "group": "users",
    "doc": "file-text",
    "doc-pen": "file-pen",
    "warn": "triangle-alert",
    "error": "circle-x",
    "ok": "circle-check",
    "pro": "sparkles",
    "chart": "trending-up",
}


def icon(name, size=18, stroke=1.75, cls="", title=""):
    """インライン SVG の文字列を返す。

    name   : アイコン名。未定義なら何も描かず空文字を返す
    size   : 一辺の px
    stroke : 線の太さ。小さく使うときは 2 前後が見やすい
    cls    : 付与する class 名
    title  : 読み上げ用の説明。省略時は装飾として扱う
    """
    key = _ALIASES.get(name, name)
    path = _PATHS.get(key)
    if not path:
        return ""

    a11y = f"<title>{title}</title>" if title else ""
    aria = "" if title else ' aria-hidden="true"'
    klass = f' class="{cls}"' if cls else ""

    return (
        f'<svg{klass} xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align:-0.15em;flex:0 0 auto;"{aria}>{a11y}{path}</svg>'
    )


def available():
    """使えるアイコン名の一覧。表記ゆれの確認に使う。"""
    return sorted(set(_PATHS) | set(_ALIASES))
