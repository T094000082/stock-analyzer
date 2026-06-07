import streamlit as st
import math
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image, ImageDraw
from core import (
    WATCHLIST_FILE, MAX_WATCHLIST, WISDOM, SIGNAL_CFG,
    load_watchlist, save_watchlist, fetch_stock_data,
    get_stock_name, search_stocks, today_wisdom,
)

# ── 主題定義 ──────────────────────────────────────────────

THEMES = {
    "廟宇金紅": {
        "label": "🏯 廟宇金紅",
        "css": """
:root { --bg:#1c0d00; --card-bg:#2d1800; --card-border:#6b3800;
        --title:#FFD700; --text:#f5e6c8; --muted:#c4a070;
        --up:#ff6666; --down:#44cc88; --accent:#ffaa00; }
.stApp { background: radial-gradient(circle at 12% 10%,#3d1500 0%,transparent 40%),
         radial-gradient(circle at 90% 12%,#2a1000 0%,transparent 35%), #1c0d00; }
.top-banner { background:linear-gradient(120deg,#2d1800 0%,#3d2200 55%,#2d1800 100%);
              border-color:#6b3800; box-shadow:0 14px 28px rgba(180,80,0,.25); }
.marquee-track { color:#FFD700; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#1c0d00 0%,#2d1800 100%);
                             border-right-color:#6b3800; }
[data-testid="stHeader"] { background:#1c0d00 !important; border-bottom:1px solid #6b3800; }
[data-testid="stHeader"] * { color:#c4a070 !important; }
""",
    },
    "佛系水墨": {
        "label": "🖌️ 佛系水墨",
        "css": """
:root { --bg:#f5f2ec; --card-bg:#faf8f3; --card-border:#d4c9b0;
        --title:#1a1a14; --text:#2d2d20; --muted:#7a7060;
        --up:#b02020; --down:#1a6e38; --accent:#4a6e70; }
.stApp { background: radial-gradient(circle at 12% 10%,#e8e2d4 0%,transparent 35%),
         radial-gradient(circle at 90% 12%,#eae5d8 0%,transparent 30%), #f5f2ec; }
.top-banner { background:linear-gradient(120deg,#faf8f3 0%,#f0ece0 55%,#faf8f3 100%);
              border-color:#d4c9b0; }
.marquee-track { color:#1a1a14; font-style:normal; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#f0ece0 0%,#f8f6f0 100%);
                             border-right-color:#d4c9b0; }
[data-testid="stHeader"] { background:#faf8f3 !important; border-bottom:1px solid #d4c9b0; }
[data-testid="stHeader"] * { color:#7a7060 !important; }
""",
    },
    "清新商務": {
        "label": "💼 清新商務",
        "css": "",
    },
    "科技暗黑": {
        "label": "🖥️ 科技暗黑",
        "css": """
:root { --bg:#080e1a; --card-bg:#0d1526; --card-border:#1e3050;
        --title:#d0e8ff; --text:#90b8e0; --muted:#506080;
        --up:#ff4488; --down:#00e888; --accent:#00ccff; }
.stApp { background: radial-gradient(circle at 12% 10%,#0d1f3a 0%,transparent 35%),
         radial-gradient(circle at 90% 12%,#081a10 0%,transparent 30%), #080e1a; }
.top-banner { background:linear-gradient(120deg,#0d1526 0%,#0a1e38 55%,#0d1526 100%);
              border-color:#1e3050; box-shadow:0 14px 28px rgba(0,100,200,.15); }
.marquee-track { color:#00ccff; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#080e1a 0%,#0d1526 100%);
                             border-right-color:#1e3050; }
[data-testid="stHeader"] { background:#080e1a !important; border-bottom:1px solid #1e3050; }
[data-testid="stHeader"] * { color:#506080 !important; }
""",
    },
    "傳統紙本": {
        "label": "📰 傳統紙本",
        "css": """
:root { --bg:#f4eed8; --card-bg:#faf6e6; --card-border:#c8b880;
        --title:#1a1200; --text:#2d2400; --muted:#8d7352;
        --up:#cc0000; --down:#006400; --accent:#8b4513; }
.stApp { background: radial-gradient(circle at 12% 10%,#ede6c8 0%,transparent 35%),
         radial-gradient(circle at 90% 12%,#f0eacc 0%,transparent 30%), #f4eed8; }
.top-banner { background:linear-gradient(120deg,#faf6e6 0%,#f5eed4 55%,#faf6e6 100%);
              border-color:#c8b880; }
.marquee-track { color:#1a1200; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#ede6c8 0%,#f8f4e4 100%);
                             border-right-color:#c8b880; }
[data-testid="stHeader"] { background:#f4eed8 !important; border-bottom:1px solid #c8b880; }
[data-testid="stHeader"] * { color:#8d7352 !important; }
""",
    },
    "極簡白": {
        "label": "⬜ 極簡白",
        "css": """
:root { --bg:#ffffff; --card-bg:#f8f8f8; --card-border:#e0e0e0;
        --title:#111111; --text:#444444; --muted:#888888;
        --up:#e53935; --down:#43a047; --accent:#424242; }
.stApp { background:#ffffff; }
.top-banner { background:#f8f8f8; border-color:#e0e0e0;
              box-shadow:0 2px 8px rgba(0,0,0,.06); }
.marquee-track { color:#111111; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#f5f5f5 0%,#fafafa 100%);
                             border-right-color:#e0e0e0; }
[data-testid="stHeader"] { background:#ffffff !important; border-bottom:1px solid #e0e0e0; }
[data-testid="stHeader"] * { color:#888888 !important; }
""",
    },
}

# ── 頁面設定 ──────────────────────────────────────────────

def _make_dharma_wheel(size: int = 64, color=(255, 215, 0)) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = size / 2
    r_out = size / 2 - 2
    r_hub = size / 7
    lw = max(2, size // 18)
    draw.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], outline=color, width=lw)
    for i in range(8):
        a = math.radians(i * 45)
        draw.line([
            cx + r_hub * math.cos(a), cy + r_hub * math.sin(a),
            cx + r_out * math.cos(a), cy + r_out * math.sin(a),
        ], fill=color, width=lw)
    draw.ellipse([cx - r_hub, cy - r_hub, cx + r_hub, cy + r_hub], fill=color)
    return img

st.set_page_config(page_title="勸世股經-台股價量評估儀表板", page_icon=_make_dharma_wheel(), layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;800&family=IBM+Plex+Sans:wght@500;700&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons+Round');

    :root {
        --bg: #f4f7fb;
        --card-bg: #ffffff;
        --card-border: #dfe7f2;
        --title: #14233c;
        --text: #31435f;
        --muted: #6780a0;
        --up: #d33f49;
        --down: #1a936f;
        --accent: #2155cd;
    }

    .stApp {
        background:
            radial-gradient(circle at 12% 10%, #e8f0ff 0%, transparent 35%),
            radial-gradient(circle at 90% 12%, #edf7f1 0%, transparent 30%),
            var(--bg);
        color: var(--text);
        font-family: 'Noto Sans TC', sans-serif;
    }

    .top-banner {
        background: linear-gradient(120deg, #f7fbff 0%, #edf4ff 55%, #f5fbff 100%);
        border: 1px solid var(--card-border);
        border-radius: 18px;
        padding: 18px 20px;
        margin-bottom: 10px;
        box-shadow: 0 14px 28px rgba(18, 38, 73, 0.08);
    }

    .top-banner h1 {
        margin: 0;
        color: var(--title);
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 1.78rem;
        letter-spacing: 0.01em;
    }

    .top-banner p {
        margin: 8px 0 0 0;
        color: var(--muted);
        font-size: 0.95rem;
    }

    .metric-card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 14px;
        padding: 12px 14px;
        box-shadow: 0 8px 20px rgba(15, 40, 75, 0.07);
        min-height: 92px;
    }

    .metric-label {
        font-size: 0.82rem;
        color: var(--muted);
        margin-bottom: 4px;
    }

    .metric-value {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--title);
        line-height: 1.2;
    }

    .metric-note {
        margin-top: 4px;
        font-size: 0.82rem;
        color: var(--muted);
    }

    .up { color: var(--up); }
    .down { color: var(--down); }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
        border-right: 1px solid var(--card-border);
    }

    .marquee-wrap {
        overflow: hidden;
        white-space: nowrap;
        margin-bottom: 10px;
    }

    .marquee-track {
        display: inline-block;
        animation: scroll-marquee 45s linear infinite;
        color: var(--title);
        font-family: 'Noto Sans TC', sans-serif;
        font-size: 1.72rem;
        font-weight: 800;
        letter-spacing: 0.02em;
    }

    @keyframes scroll-marquee {
        0%   { transform: translateX(100vw); }
        100% { transform: translateX(-100%); }
    }

    .brand-label {
        font-size: 0.85rem;
        color: var(--muted);
        letter-spacing: 0.08em;
        margin-bottom: 6px;
        font-family: 'IBM Plex Sans', sans-serif;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .mi {
        font-family: 'Material Icons Round';
        font-style: normal;
        font-weight: normal;
        line-height: 1;
        display: inline-block;
        vertical-align: -0.15em;
        user-select: none;
    }

    .sidebar-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--title);
        padding: 6px 0 4px 0;
        margin: 0 0 6px 0;
    }

    .sidebar-title .mi {
        font-size: 1.2rem;
        color: var(--accent);
    }

    @media (max-width: 900px) {
        .top-banner h1 { font-size: 1.4rem; }
        .metric-value { font-size: 1.15rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

_theme_key = st.session_state.get("theme", "廟宇金紅")
_theme_css = THEMES.get(_theme_key, THEMES["廟宇金紅"])["css"]
if _theme_css:
    st.markdown(f"<style>{_theme_css}</style>", unsafe_allow_html=True)


_today_wisdom = today_wisdom()
st.markdown(
    f"""
    <div class="top-banner">
      <div class="brand-label">
        <span class="mi" style="font-size:1rem">trending_up</span>
        勸世股經｜台股價量評估儀表板
      </div>
      <div class="marquee-wrap">
        <div class="marquee-track">
          {_today_wisdom} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
          {_today_wisdom}
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_watchlist()
if "current_code" not in st.session_state:
    st.session_state.current_code = ""
if "n_days" not in st.session_state:
    st.session_state.n_days = 7
if "anchor" not in st.session_state:
    st.session_state.anchor = datetime.date.today()
if "theme" not in st.session_state:
    st.session_state.theme = "廟宇金紅"

# ── 側邊欄 ────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<p class="sidebar-title"><span class="mi">search</span> 查詢股票</p>', unsafe_allow_html=True)
    search_query = st.text_input(
        "輸入代號或公司名稱",
        placeholder="例：2330 或 台積電",
    ).strip()

    selected_code = None
    selected_name = ""

    if search_query:
        matches = search_stocks(search_query)
        if not matches:
            st.caption("⚠️ 找不到相符股票")
        elif len(matches) == 1:
            selected_code, selected_name = matches[0]
            st.caption(f"✓ {selected_code}　{selected_name}")
        else:
            options = [f"{c}　{n}" for c, n in matches]
            chosen = st.selectbox(
                f"找到 {len(matches)} 筆，請選擇",
                options,
                key="stock_select",
            )
            idx = options.index(chosen)
            selected_code, selected_name = matches[idx]

    if st.button("查詢", use_container_width=True):
        if selected_code:
            st.session_state.current_code = selected_code
            wl = st.session_state.watchlist
            if selected_code not in wl:
                if len(wl) >= MAX_WATCHLIST:
                    st.warning(f"清單已滿（上限 {MAX_WATCHLIST} 筆），請先刪除再新增")
                else:
                    wl.append(selected_code)
                    save_watchlist(wl)
        elif search_query:
            st.warning("請從搜尋結果中選擇股票")

    st.divider()
    st.slider(
        "顯示交易日數", min_value=1, max_value=30,
        step=1, key="n_days",
    )

    st.caption("查詢截至日期")
    picked = st.date_input(
        "截至日期",
        value=st.session_state.anchor,
        max_value=datetime.date.today(),
        label_visibility="collapsed",
    )
    st.session_state.anchor = picked

    step = st.session_state.n_days
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀ 往前", use_container_width=True):
            st.session_state.anchor -= datetime.timedelta(days=step)
            st.rerun()
    with col2:
        if st.button("往後 ▶", use_container_width=True):
            new_d = st.session_state.anchor + datetime.timedelta(days=step)
            st.session_state.anchor = min(new_d, datetime.date.today())
            st.rerun()

    st.divider()
    st.markdown(
        f'<p class="sidebar-title"><span class="mi">bookmarks</span> 我的清單（{len(st.session_state.watchlist)}/{MAX_WATCHLIST}）</p>',
        unsafe_allow_html=True,
    )

    for code in list(st.session_state.watchlist):
        name = get_stock_name(code)
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(f"{code} {name}", key=f"sel_{code}", use_container_width=True):
                st.session_state.current_code = code
        with col2:
            if st.button("✕", key=f"del_{code}"):
                st.session_state.watchlist.remove(code)
                save_watchlist(st.session_state.watchlist)
                if st.session_state.current_code == code:
                    st.session_state.current_code = ""
                st.rerun()

    st.divider()
    theme_labels = [v["label"] for v in THEMES.values()]
    theme_keys   = list(THEMES.keys())
    current_idx  = theme_keys.index(st.session_state.theme) if st.session_state.theme in theme_keys else 0
    st.markdown('<p class="sidebar-title"><span class="mi">palette</span> 畫面風格</p>', unsafe_allow_html=True)
    chosen_label = st.selectbox("", theme_labels, index=current_idx, label_visibility="collapsed")
    st.session_state.theme = theme_keys[theme_labels.index(chosen_label)]

# ── 主畫面 ────────────────────────────────────────────────

current = st.session_state.current_code

if not current:
    st.info("請在左側輸入股票代號或點選清單中的股票")
else:
    name = get_stock_name(current)
    n_days = st.session_state.n_days
    anchor = st.session_state.anchor
    st.subheader(f"{current}　{name}　｜　截至 {anchor}　近 {n_days} 個交易日")

    with st.spinner("資料載入中..."):
        try:
            df = fetch_stock_data(current, n_days, anchor)

            latest = df.iloc[-1]
            latest_change = float(latest["漲跌"])
            latest_close = float(latest["收盤"])
            latest_ratio = float(latest["量比"])
            latest_volume = int(latest["成交量(張)"])
            latest_label = str(latest["量能判斷"])
            latest_signal = str(latest["訊號"]) if str(latest["訊號"]) else "無明確訊號"

            def class_by_value(v: float) -> str:
                if v > 0:
                    return "up"
                if v < 0:
                    return "down"
                return ""

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                      <div class="metric-label">最新收盤</div>
                      <div class="metric-value">{latest_close:.2f}</div>
                      <div class="metric-note">交易日：{latest['日期']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with k2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                      <div class="metric-label">當日漲跌</div>
                      <div class="metric-value {class_by_value(latest_change)}">{latest_change:+.2f}</div>
                      <div class="metric-note">相較前一交易日</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with k3:
                st.markdown(
                    f"""
                    <div class="metric-card">
                      <div class="metric-label">量比 / 量能</div>
                      <div class="metric-value">{latest_ratio:.2f}</div>
                      <div class="metric-note">{latest_label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with k4:
                st.markdown(
                    f"""
                    <div class="metric-card">
                      <div class="metric-label">成交量(張)</div>
                      <div class="metric-value">{latest_volume:,}</div>
                      <div class="metric-note">訊號：{latest_signal}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # 加序號欄，並重新排列欄位順序
            df.insert(0, "序號", range(1, len(df) + 1))
            df = df[["序號", "日期", "訊號", "成交量(張)", "量能判斷", "量比",
                      "開盤", "最高", "最低", "收盤", "漲跌",
                      "5日均量", "MA5", "MA10", "MA20"]]

            # 漲跌 / 量比顏色標示
            def color_change(val):
                if isinstance(val, (int, float)):
                    if val > 0: return "color: red"
                    if val < 0: return "color: green"
                return ""

            LABEL_COLOR = {
                "極度縮量": "color: #888888",
                "縮量":     "color: #aaaaaa",
                "正常":     "",
                "放量":     "color: #ff9900",
                "大量":     "color: #ff4444",
                "異常爆量": "color: #ff0000; font-weight:bold",
            }
            SIGNAL_COLOR = {
                "量增價漲": "color: #ff4444; font-weight:bold",
                "量縮價漲": "color: #ff9900",
                "量增價跌": "color: #44cc88; font-weight:bold",
                "量縮價跌": "color: #44aaff",
            }
            def color_label(val):
                return LABEL_COLOR.get(val, "")
            def color_signal(val):
                return SIGNAL_COLOR.get(val, "")

            # pandas 3.x 使用 Styler.map；舊版使用 Styler.applymap
            def styler_cell_map(styler, func, subset):
                if hasattr(styler, "map"):
                    return styler.map(func, subset=subset)
                return styler.applymap(func, subset=subset)

            styled = (
                df.style
                .format({
                    "開盤": "{:.2f}", "最高": "{:.2f}",
                    "最低": "{:.2f}", "收盤": "{:.2f}",
                    "漲跌": "{:.2f}", "量比": "{:.2f}",
                    "MA5":  "{:.2f}", "MA10": "{:.2f}", "MA20": "{:.2f}",
                    "成交量(張)": "{:,}", "5日均量": "{:,}",
                })
            )
            styled = styler_cell_map(styled, color_change, subset=["漲跌"])
            styled = styler_cell_map(styled, color_label, subset=["量能判斷"])
            styled = styler_cell_map(styled, color_signal, subset=["訊號"])

            # K 線圖 + 成交量組合圖
            colors = ["red" if r["漲跌"] >= 0 else "green" for _, r in df.iterrows()]

            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                row_heights=[0.65, 0.35],
                vertical_spacing=0.03,
            )

            fig.add_trace(go.Candlestick(
                x=df["日期"],
                open=df["開盤"],
                high=df["最高"],
                low=df["最低"],
                close=df["收盤"],
                increasing_line_color="red",
                decreasing_line_color="green",
                name="K線",
            ), row=1, col=1)

            for ma, color in [("MA5", "#FFD700"), ("MA10", "#A855F7"), ("MA20", "#FF8C00")]:
                fig.add_trace(go.Scatter(
                    x=df["日期"],
                    y=df[ma],
                    mode="lines",
                    name=ma,
                    line=dict(color=color, width=1.5),
                    hovertemplate=f"{ma}：%{{y:.2f}}<extra></extra>",
                ), row=1, col=1)

            # 價量訊號標記
            for sig, (clr, sym, pos) in SIGNAL_CFG.items():
                mask = df["訊號"] == sig
                if not mask.any():
                    continue
                y_vals = (df["最低"] * 0.997 if pos == "below" else df["最高"] * 1.003)
                fig.add_trace(go.Scatter(
                    x=df["日期"][mask],
                    y=y_vals[mask],
                    mode="markers",
                    name=sig,
                    marker=dict(symbol=sym, color=clr, size=10),
                    hovertemplate=f"<b>{sig}</b><extra></extra>",
                ), row=1, col=1)

            fig.add_trace(go.Bar(
                x=df["日期"],
                y=df["成交量(張)"],
                marker_color=colors,
                name="成交量(張)",
                opacity=0.8,
                customdata=list(zip(df["5日均量"], df["量比"], df["量能判斷"])),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "成交量：%{y:,} 張<br>"
                    "5日均量：%{customdata[0]:,} 張<br>"
                    "量比：%{customdata[1]:.2f}<br>"
                    "判斷：<b>%{customdata[2]}</b>"
                    "<extra></extra>"
                ),
            ), row=2, col=1)

            fig.update_layout(
                height=520,
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", y=1.05),
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                font_color="#20324d",
            )
            fig.update_yaxes(gridcolor="#e5ecf6")
            fig.update_xaxes(gridcolor="#e5ecf6")
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.dataframe(styled, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="匯出 CSV",
                data=csv,
                file_name=f"{current}_{name}_{df['日期'].iloc[0]}_{df['日期'].iloc[-1]}.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"查詢失敗：{e}\n請確認股票代號是否正確")
