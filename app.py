import streamlit as st
import twstock
import json
import os
import datetime
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

def volume_label(ratio: float) -> str:
    if ratio < 0.5:  return "極度縮量"
    if ratio < 1.0:  return "縮量"
    if ratio < 1.5:  return "正常"
    if ratio < 2.5:  return "放量"
    if ratio < 5.0:  return "大量"
    return "異常爆量"

# 訊號設定：{訊號名稱: (顏色, marker符號, 位置above/below)}
SIGNAL_CFG = {
    "量增價漲": ("#ff4444", "triangle-up",   "below"),
    "量縮價漲": ("#ff9900", "circle",         "above"),
    "量增價跌": ("#44cc88", "triangle-down",  "above"),
    "量縮價跌": ("#44aaff", "diamond",        "below"),
}

def pv_signal(change: float, ratio: float) -> str:
    if change > 0:
        return "量增價漲" if ratio >= 1.5 else ("量縮價漲" if ratio < 0.8 else "")
    if change < 0:
        return "量增價跌" if ratio >= 1.5 else ("量縮價跌" if ratio < 0.8 else "")
    return ""

def fetch_stock_data(code: str, n_days: int, anchor: datetime.date) -> pd.DataFrame:
    # 計算需要哪些月份
    fetch_start = anchor - datetime.timedelta(days=max(n_days * 2 + 30, 90))
    months = []
    cur = fetch_start.replace(day=1)
    while cur <= anchor.replace(day=1):
        months.append((cur.year, cur.month))
        cur = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    # 每月獨立 fetch（twstock.fetch 每次都會覆蓋，不能累加）
    stock = twstock.Stock(code, initial_fetch=False)
    all_dfs = []
    for year, month in months:
        try:
            stock.fetch(year, month)
            if not stock.date:
                continue
            all_dfs.append(pd.DataFrame({
                "日期":      [d.strftime("%Y-%m-%d") for d in stock.date],
                "開盤":      stock.open,
                "最高":      stock.high,
                "最低":      stock.low,
                "收盤":      stock.close,
                "成交量(張)": [int(v // 1000) if v else 0 for v in stock.capacity],
            }))
        except Exception:
            pass

    if not all_dfs:
        raise ValueError("無法取得股票資料")

    all_df = (
        pd.concat(all_dfs, ignore_index=True)
        .dropna(subset=["收盤"])
        .assign(_dt=lambda df: pd.to_datetime(df["日期"]))
        .sort_values("_dt")
        .drop_duplicates("日期")
        .reset_index(drop=True)
    )
    if all_df.empty:
        raise ValueError("此股票無交易資料")

    all_df["漲跌"]   = all_df["收盤"].diff().round(2).fillna(0)
    all_df["5日均量"] = all_df["成交量(張)"].rolling(5,  min_periods=1).mean().round(0).astype(int)
    all_df["量比"]   = (all_df["成交量(張)"] / all_df["5日均量"].replace(0, 1)).round(2)
    all_df["量能判斷"] = all_df["量比"].apply(volume_label)
    all_df["訊號"]   = all_df.apply(lambda r: pv_signal(r["漲跌"], r["量比"]), axis=1)
    all_df["MA5"]  = all_df["收盤"].rolling(5,  min_periods=1).mean().round(2)
    all_df["MA10"] = all_df["收盤"].rolling(10, min_periods=1).mean().round(2)
    all_df["MA20"] = all_df["收盤"].rolling(20, min_periods=1).mean().round(2)

    filtered = all_df[all_df["_dt"] <= pd.Timestamp(anchor)].drop(columns=["_dt"])
    if filtered.empty:
        raise ValueError(f"{anchor} 前無交易資料")
    return filtered.tail(n_days).reset_index(drop=True)

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
if "anchor" not in st.session_state:
    st.session_state.anchor = datetime.date.today()

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
    anchor = st.session_state.anchor
    st.subheader(f"{current}　{name}　｜　截至 {anchor}　近 {n_days} 個交易日")

    with st.spinner("資料載入中..."):
        try:
            df = fetch_stock_data(current, n_days, anchor)

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

            styled = (
                df.style
                .format({
                    "開盤": "{:.2f}", "最高": "{:.2f}",
                    "最低": "{:.2f}", "收盤": "{:.2f}",
                    "漲跌": "{:.2f}", "量比": "{:.2f}",
                    "MA5":  "{:.2f}", "MA10": "{:.2f}", "MA20": "{:.2f}",
                    "成交量(張)": "{:,}", "5日均量": "{:,}",
                })
                .applymap(color_change,  subset=["漲跌"])
                .applymap(color_label,   subset=["量能判斷"])
                .applymap(color_signal,  subset=["訊號"])
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="匯出 CSV",
                data=csv,
                file_name=f"{current}_{name}_{df['日期'].iloc[0]}_{df['日期'].iloc[-1]}.csv",
                mime="text/csv",
            )

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
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font_color="#fafafa",
            )
            fig.update_yaxes(gridcolor="#2a2a2a")
            fig.update_xaxes(gridcolor="#2a2a2a")

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"查詢失敗：{e}\n請確認股票代號是否正確")
