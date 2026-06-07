import streamlit as st
import pandas as pd
import requests
import datetime
import feedparser
from core import (
    THEMES, make_dharma_wheel,
    load_watchlist, save_watchlist, MAX_WATCHLIST, get_stock_name,
)

# ── 頁面設定 ─────────────────────────────────────────────────

st.set_page_config(page_title="選股策略｜勸世股經", page_icon=make_dharma_wheel(), layout="wide")

_theme_key = st.session_state.get("theme", "廟宇金紅")
_theme_css = THEMES.get(_theme_key, THEMES["廟宇金紅"])["css"]
if _theme_css:
    st.markdown(f"<style>{_theme_css}</style>", unsafe_allow_html=True)

st.markdown(
    '<p style="font-size:.85rem;color:var(--muted);margin-bottom:4px">'
    '<span style="font-family:Material Icons Round;vertical-align:middle">trending_up</span>'
    '  勸世股經｜選股策略</p>'
    '<h2 style="color:var(--title);margin-top:0">上市股票篩選</h2>',
    unsafe_allow_html=True,
)

# ── 資料抓取 ─────────────────────────────────────────────────

_HEADERS = {"User-Agent": "Mozilla/5.0"}

@st.cache_data(ttl=3600)
def _fetch_day_all() -> pd.DataFrame:
    """TWSE STOCK_DAY_ALL：今日收盤價、成交量"""
    try:
        r = requests.get(
            "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json",
            headers=_HEADERS, timeout=15,
        )
        j = r.json()
        if j.get("stat") == "OK" and j.get("data"):
            return pd.DataFrame(j["data"], columns=j["fields"])
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def _fetch_bwibbu() -> pd.DataFrame:
    """TWSE BWIBBU_d：本益比、殖利率、股價淨值比（最近交易日）"""
    for delta in range(7):
        d = (datetime.date.today() - datetime.timedelta(days=delta)).strftime("%Y%m%d")
        try:
            r = requests.get(
                f"https://www.twse.com.tw/exchangeReport/BWIBBU_d"
                f"?response=json&date={d}&selectType=ALL",
                headers=_HEADERS, timeout=15,
            )
            j = r.json()
            if j.get("stat") == "OK" and j.get("data"):
                return pd.DataFrame(j["data"], columns=j["fields"])
        except Exception:
            pass
    return pd.DataFrame()

def _to_float(s) -> float:
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, TypeError):
        return float("nan")

@st.cache_data(ttl=3600)
def build_screen_df() -> pd.DataFrame:
    day = _fetch_day_all()
    bwi = _fetch_bwibbu()

    # ── 整理 STOCK_DAY_ALL ──
    if not day.empty:
        col_code  = next((c for c in day.columns if "代號" in c), None)
        col_name  = next((c for c in day.columns if "名稱" in c), None)
        col_close = next((c for c in day.columns if "收盤" in c), None)
        col_vol   = next((c for c in day.columns if "成交股數" in c), None)

        rename = {}
        if col_code:  rename[col_code]  = "代號"
        if col_name:  rename[col_name]  = "名稱"
        if col_close: rename[col_close] = "收盤價"
        if col_vol:   rename[col_vol]   = "_股數"
        day = day.rename(columns=rename)

        keep = [c for c in ["代號", "名稱", "收盤價", "_股數"] if c in day.columns]
        day = day[keep].copy()
        day["代號"] = day["代號"].astype(str).str.strip()
        if "收盤價" in day.columns:
            day["收盤價"] = day["收盤價"].apply(_to_float)
        if "_股數" in day.columns:
            day["成交量(張)"] = day["_股數"].apply(lambda x: int(_to_float(x) // 1000))
            day.drop(columns=["_股數"], inplace=True)

    # ── 整理 BWIBBU ──
    if not bwi.empty:
        col_code_b = next((c for c in bwi.columns if "代號" in c), None)
        col_pe     = next((c for c in bwi.columns if "本益比" in c), None)
        col_dy     = next((c for c in bwi.columns if "殖利率" in c), None)
        col_pb     = next((c for c in bwi.columns if "淨值比" in c), None)

        rename_b = {}
        if col_code_b: rename_b[col_code_b] = "代號"
        if col_pe:     rename_b[col_pe]     = "本益比"
        if col_dy:     rename_b[col_dy]     = "殖利率(%)"
        if col_pb:     rename_b[col_pb]     = "股價淨值比"
        bwi = bwi.rename(columns=rename_b)

        keep_b = [c for c in ["代號", "本益比", "殖利率(%)", "股價淨值比"] if c in bwi.columns]
        bwi = bwi[keep_b].copy()
        bwi["代號"] = bwi["代號"].astype(str).str.strip()
        for col in ["本益比", "殖利率(%)", "股價淨值比"]:
            if col in bwi.columns:
                bwi[col] = bwi[col].apply(_to_float)

    # ── 合併 ──
    if not day.empty and not bwi.empty:
        df = day.merge(bwi, on="代號", how="left")
    elif not day.empty:
        df = day
    elif not bwi.empty:
        df = bwi
    else:
        return pd.DataFrame()

    return df.reset_index(drop=True)

# ── 新聞抓取 ─────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def fetch_news(code: str, name: str, n: int = 6) -> list[dict]:
    """Google News RSS，回傳最多 n 則，每則含 title / link / source / date。"""
    query = f"{name} {code} 股票".replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    try:
        feed = feedparser.parse(url)
        results = []
        for entry in feed.entries[:n]:
            results.append({
                "title":  entry.get("title", ""),
                "link":   entry.get("link", ""),
                "source": entry.get("source", {}).get("title", ""),
                "date":   entry.get("published", "")[:16],
            })
        return results
    except Exception:
        return []

# ── 篩選條件定義 ─────────────────────────────────────────────

PRICE_OPTS = {
    "不限":       (0,     float("inf")),
    "10元以下":   (0,     10),
    "50元以下":   (0,     50),
    "100元以下":  (0,     100),
    "500元以下":  (0,     500),
    "1000元以下": (0,     1000),
    "1000元以上": (1000,  float("inf")),
}

VOL_OPTS = {
    "不限":           (0,     float("inf")),
    "1,000張以下":    (0,     1_000),
    "1,000~10,000張": (1_000, 10_000),
    "10,000張以上":   (10_000, float("inf")),
    "50,000張以上":   (50_000, float("inf")),
}

PE_OPTS = {
    "不限":     None,
    "10倍以下": (0,  10),
    "10~20倍":  (10, 20),
    "20~30倍":  (20, 30),
    "30倍以上": (30, float("inf")),
    "負值(虧損)": "negative",
}

DY_OPTS = {
    "不限":    (0, float("inf")),
    "2%以上":  (2, float("inf")),
    "3%以上":  (3, float("inf")),
    "5%以上":  (5, float("inf")),
    "8%以上":  (8, float("inf")),
}

# ── Sidebar 篩選器 ────────────────────────────────────────────

with st.sidebar:
    st.markdown('<p class="sidebar-title"><span class="mi">filter_list</span> 篩選條件</p>',
                unsafe_allow_html=True)

    price_sel = st.selectbox("💰 價位", list(PRICE_OPTS.keys()))
    vol_sel   = st.selectbox("📊 成交量", list(VOL_OPTS.keys()))
    pe_sel    = st.selectbox("📈 本益比", list(PE_OPTS.keys()))
    dy_sel    = st.selectbox("💵 殖利率（建議）", list(DY_OPTS.keys()))

    st.divider()
    if st.button("🔍 開始篩選", use_container_width=True, type="primary"):
        st.session_state["screen_run"] = True
    if st.button("↺ 清除重新載入資料", use_container_width=True):
        st.cache_data.clear()
        st.session_state["screen_run"] = False
        st.rerun()

    st.divider()
    theme_labels = [v["label"] for v in THEMES.values()]
    theme_keys   = list(THEMES.keys())
    current_idx  = theme_keys.index(_theme_key) if _theme_key in theme_keys else 0
    chosen_label = st.selectbox("🎨 畫面風格", theme_labels, index=current_idx)
    st.session_state.theme = theme_keys[theme_labels.index(chosen_label)]

# ── 主畫面 ───────────────────────────────────────────────────

if not st.session_state.get("screen_run"):
    st.info("設定左側篩選條件後，點「開始篩選」")
    st.stop()

with st.spinner("載入市場資料中…（首次約需 10 秒）"):
    df = build_screen_df()

if df.empty:
    st.error("無法取得市場資料，請稍後再試")
    st.stop()

# 套用篩選
result = df.copy()

if "收盤價" in result.columns:
    lo, hi = PRICE_OPTS[price_sel]
    result = result[result["收盤價"].between(lo, hi, inclusive="both")]

if "成交量(張)" in result.columns:
    lo, hi = VOL_OPTS[vol_sel]
    result = result[result["成交量(張)"].between(lo, hi, inclusive="both")]

if "本益比" in result.columns and PE_OPTS[pe_sel] is not None:
    if PE_OPTS[pe_sel] == "negative":
        result = result[result["本益比"] < 0]
    else:
        lo, hi = PE_OPTS[pe_sel]
        result = result[(result["本益比"] >= lo) & (result["本益比"] <= hi)]

if "殖利率(%)" in result.columns:
    lo, hi = DY_OPTS[dy_sel]
    result = result[result["殖利率(%)"].between(lo, hi, inclusive="left")]

result = result.reset_index(drop=True)

# 顯示結果
st.markdown(f"### 篩選結果：{len(result)} 筆")

if result.empty:
    st.warning("沒有符合條件的股票，請放寬篩選範圍")
    st.stop()

# 選擇顯示欄位並格式化
show_cols = [c for c in ["代號", "名稱", "收盤價", "成交量(張)", "本益比", "殖利率(%)", "股價淨值比"]
             if c in result.columns]
display = result[show_cols].copy()

for c in ["收盤價", "本益比", "殖利率(%)", "股價淨值比"]:
    if c in display.columns:
        display[c] = display[c].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "-")
if "成交量(張)" in display.columns:
    display["成交量(張)"] = display["成交量(張)"].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else "-"
    )

# 用 HTML 表格渲染（st.dataframe 在深色主題下文字不可見）
def _to_html_table(df: pd.DataFrame) -> str:
    th = "".join(
        f'<th style="padding:8px 14px;background:var(--card-bg);color:var(--title);'
        f'border-bottom:2px solid var(--card-border);text-align:left;'
        f'font-size:.84rem;white-space:nowrap">{c}</th>'
        for c in df.columns
    )
    rows_html = ""
    for i, (_, row) in enumerate(df.iterrows()):
        bg = "var(--card-bg)" if i % 2 == 0 else "var(--bg)"
        tds = "".join(
            f'<td style="padding:6px 14px;color:var(--text);font-size:.84rem;'
            f'border-bottom:1px solid var(--card-border);white-space:nowrap">{v}</td>'
            for v in row
        )
        rows_html += f'<tr style="background:{bg}">{tds}</tr>'
    return (
        '<div style="overflow-x:auto;border:1px solid var(--card-border);'
        'border-radius:10px;margin-top:8px">'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table></div>'
    )

st.markdown(_to_html_table(display), unsafe_allow_html=True)

# 匯出
csv = display.to_csv(index=False, encoding="utf-8-sig")
st.download_button(
    label="匯出 CSV",
    data=csv,
    file_name=f"選股結果_{datetime.date.today()}.csv",
    mime="text/csv",
)

# 加入自選清單
st.divider()
st.markdown("#### 加入自選清單")
wl = load_watchlist()
codes_to_add = st.multiselect(
    "選擇要加入的股票",
    options=[f"{r['代號']} {r.get('名稱', '')}" for _, r in result[["代號"] + (["名稱"] if "名稱" in result.columns else [])].iterrows()],
)
if st.button("加入", use_container_width=False) and codes_to_add:
    added = 0
    for item in codes_to_add:
        code = item.split()[0]
        if code not in wl:
            if len(wl) < MAX_WATCHLIST:
                wl.append(code)
                added += 1
            else:
                st.warning(f"清單已滿（上限 {MAX_WATCHLIST} 筆）")
                break
    if added:
        save_watchlist(wl)
        st.success(f"已加入 {added} 筆")

# ── 新聞查詢 ─────────────────────────────────────────────────

st.divider()
st.markdown("#### 📰 個股新聞")

has_name = "名稱" in result.columns
news_options = [
    f"{r['代號']}　{r['名稱']}" if has_name else r["代號"]
    for _, r in result.iterrows()
]
news_sel = st.selectbox("選擇股票查看新聞", ["— 請選擇 —"] + news_options, key="news_sel")

if news_sel and news_sel != "— 請選擇 —":
    parts   = news_sel.split("　")
    n_code  = parts[0].strip()
    n_name  = parts[1].strip() if len(parts) > 1 else n_code

    # 快速連結
    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button(
            "📰 Google 新聞",
            f"https://news.google.com/search?q={n_name}+{n_code}&hl=zh-TW&gl=TW",
        )
    with c2:
        st.link_button(
            "📋 公開資訊觀測站",
            f"https://mops.twse.com.tw/mops/web/t05st01_1?stock_id={n_code}",
        )
    with c3:
        st.link_button(
            "📊 Yahoo 股市",
            f"https://tw.stock.yahoo.com/quote/{n_code}",
        )

    # RSS 新聞列表
    with st.spinner("抓取新聞中…"):
        news_list = fetch_news(n_code, n_name)

    if not news_list:
        st.caption("目前無法取得新聞，請使用上方連結查看。")
    else:
        for item in news_list:
            st.markdown(
                f"**[{item['title']}]({item['link']})**  \n"
                f"<span style='color:var(--muted);font-size:.82rem'>"
                f"{item['source']}　{item['date']}"
                f"</span>",
                unsafe_allow_html=True,
            )
            st.divider()
