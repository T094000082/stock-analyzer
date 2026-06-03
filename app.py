import streamlit as st
import twstock
import json
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")
MAX_WATCHLIST = 15

# ── 工具函式 ──────────────────────────────────────────────

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_watchlist(data):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def fetch_stock_data(code: str, n_days: int) -> pd.DataFrame:
    from datetime import datetime, timedelta
    stock = twstock.Stock(code)
    if len(stock.date) < n_days:
        prev = (datetime.today().replace(day=1) - timedelta(days=1))
        stock.fetch(prev.year, prev.month)
    df = pd.DataFrame({
        "日期":      [d.strftime("%Y-%m-%d") for d in stock.date[-n_days:]],
        "開盤":      stock.open[-n_days:],
        "最高":      stock.high[-n_days:],
        "最低":      stock.low[-n_days:],
        "收盤":      stock.close[-n_days:],
        "成交量(張)": [int(v // 1000) if v else 0 for v in stock.capacity[-n_days:]],
    })
    df = df.dropna(subset=["收盤"]).reset_index(drop=True)
    if df.empty:
        raise ValueError("此股票近期無交易資料")
    df["漲跌"] = df["收盤"].diff().round(2).fillna(0)
    return df

def get_stock_name(code: str) -> str:
    try:
        info = twstock.codes.get(code)
        return info.name if info else code
    except Exception:
        return code

@st.cache_data
def build_stock_lookup() -> list[tuple[str, str]]:
    result = []
    for code, info in twstock.codes.items():
        if hasattr(info, "name") and info.name:
            result.append((code, info.name))
    return sorted(result, key=lambda x: x[0])

def search_stocks(query: str) -> list[tuple[str, str]]:
    query = query.strip()
    if not query:
        return []
    lookup = build_stock_lookup()
    exact = [(c, n) for c, n in lookup if c == query]
    if exact:
        return exact
    return [(c, n) for c, n in lookup if query in c or query in n][:30]

# ── 頁面設定 ──────────────────────────────────────────────

st.set_page_config(page_title="台股價量評估", page_icon="📈", layout="wide")
st.title("📈 台股價量評估")

if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_watchlist()
if "current_code" not in st.session_state:
    st.session_state.current_code = ""
if "n_days" not in st.session_state:
    st.session_state.n_days = 7

# ── 側邊欄 ────────────────────────────────────────────────

with st.sidebar:
    st.header("🔍 查詢股票")
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
    st.session_state.n_days = st.slider(
        "顯示交易日數", min_value=1, max_value=30,
        value=st.session_state.n_days, step=1,
    )
    st.divider()
    st.subheader(f"📋 我的清單（{len(st.session_state.watchlist)}/{MAX_WATCHLIST}）")

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

# ── 主畫面 ────────────────────────────────────────────────

current = st.session_state.current_code

if not current:
    st.info("請在左側輸入股票代號或點選清單中的股票")
else:
    name = get_stock_name(current)
    n_days = st.session_state.n_days
    st.subheader(f"{current}　{name}　｜　近 {n_days} 個交易日")

    with st.spinner("資料載入中..."):
        try:
            df = fetch_stock_data(current, n_days)

            # 漲跌顏色標示
            def color_change(val):
                if val > 0:
                    return "color: red"
                elif val < 0:
                    return "color: green"
                return ""

            styled = df.style.applymap(color_change, subset=["漲跌"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

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

            fig.add_trace(go.Bar(
                x=df["日期"],
                y=df["成交量(張)"],
                marker_color=colors,
                name="成交量(張)",
                opacity=0.8,
            ), row=2, col=1)

            fig.update_layout(
                height=520,
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", y=1.05),
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font_color="#fafafa",
            )
            fig.update_yaxes(gridcolor="#2a2a2a")
            fig.update_xaxes(gridcolor="#2a2a2a")

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"查詢失敗：{e}\n請確認股票代號是否正確")
