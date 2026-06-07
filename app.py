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

WISDOM = [
    "借錢買股票，贏了還是要還，輸了要還更多——槓桿是把雙刃刀，別讓財務槓桿變成人生枷鎖。",
    "股票是對抗通膨的工具，穩定的收入仍得靠日復一日的本業——別把手段當目的。",
    "賣出前，股票只是螢幕上的數字；看著漲跌起伏是精神上的虛幻，變現花出去才是真實的享受。",
    "追高殺低是本能，逆向操作是修練——大多數人一輩子只練到本能。",
    "停損是技術，停利是智慧；能同時做到的人，才稱得上投資人，而非賭徒。",
    "本金虧掉 50%，要漲 100% 才能回本——保護本金，永遠比追求獲利更重要。",
    "看財經節目愈多，愈以為自己懂市場——真正的市場，從不接受任何人的預測。",
    "漲的時候你覺得自己是天才，跌的時候市場才告訴你是普通人。",
    "每次「這次不一樣」的感覺，幾乎都以一樣的方式虧損收場。",
    "分散投資不是因為你聰明，而是承認自己無法預知哪一個會先出事。",
    "市場永遠不缺機會，缺的是等待的耐心和進場的紀律。",
    "新聞上的好消息通常是出貨訊號，壞消息有時才是機會的開始。",
    "把「短套」說成「長期投資」，是不願承認錯誤的自我安慰，不是策略。",
    "每天盯盤的時間拿去提升本業技能，可能比股票賺更多。",
    "市場先生情緒不穩定，但他給的價格是你唯一能利用的機會——學會等他失控。",
    "財報公佈前買進、消息出來後賣出——這不叫精準預測，叫做被主力耍了。",
    "急著解套的心情，通常是再次虧損的起點。",
    "買股票前先問自己：這家公司消失了，世界有什麼不同？沒有答案，就不要碰。",
    "「低點再買」和「攤平」的差別，在於你有沒有真正研究過這間公司。",
    "主力看的是你的停損點在哪；你的停損點，就是他們的獲利點。",
    "退休金不能拿去賭——能輸得起的錢才能進股市，先搞清楚自己在玩什麼。",
    "每一筆帳面獲利都是假的，每一筆實際入帳才是真的——養成賣出的習慣。",
    "市場可以讓你長期錯，但不會讓你永遠錯——前提是你還有本金撐到那一天。",
    "股票影響了你的睡眠、心情和家人，表示你押注太重了。",
    "聽到「飆股內線消息」的時候，你已經是最後一個知道的人了。",
    "財富自由的前提，是先從「帳面焦慮」中自由——平靜才是真正的資產。",
    "下跌時恐慌、上漲時貪婪——能逆著群眾走的人，才能賺到群眾的錢。",
    "複利的威力需要時間，但大多數人等不到那一天就砍掉了。",
    "最好的投資，是讓你睡得著覺的投資。",
    "每次大跌都有人說「這次是末日」，每次大漲都有人說「這次不會跌」——兩種人最後都輸了。",
]

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

st.set_page_config(page_title="勸世股經-台股價量評估儀表板", page_icon="📈", layout="wide")
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

st.markdown(
    """<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,"""
    """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>"""
    """<path fill='%23FFD700' d='M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41"""
    """-7.09 7.97-4-4L2 16.99z'/></svg>">""",
    unsafe_allow_html=True,
)

_today_wisdom = WISDOM[datetime.date.today().toordinal() % len(WISDOM)]
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
        if st.button("← 往前", use_container_width=True):
            st.session_state.anchor -= datetime.timedelta(days=step)
            st.rerun()
    with col2:
        if st.button("往後 →", use_container_width=True):
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
