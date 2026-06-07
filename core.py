import streamlit as st
import twstock
import json
import os
import datetime
import pandas as pd

WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")
MAX_WATCHLIST = 15

WISDOM = [
    "借錢買股票，贏了還是要還，輸了要還更多——槓桿是把雙刃刀，別讓財務槓桿變成人生枷鎖。",
    "股票是對抗通膨的工具，穩定的收入仍得靠日復一日的本業——別把手段當目的。",
    "賣出前，股票只是螢幕上的數字；看著漲跌起伏是精神上的虛幻，變現花出去才是真實的享受。",
    "追高殺低是本能，逆向操作是修練——大多數人一輩子只練到本能。",
    "停損是智慧，停利是技術；能同時做到的人，才稱得上投資人，而非賭徒。",
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

SIGNAL_CFG = {
    "量增價漲": ("#ff4444", "triangle-up",   "below"),
    "量縮價漲": ("#ff9900", "circle",         "above"),
    "量增價跌": ("#44cc88", "triangle-down",  "above"),
    "量縮價跌": ("#44aaff", "diamond",        "below"),
}

_SEARCH_TYPES = {"股票", "ETF", "ETN", "創新板", "特別股", "受益證券-不動產投資信託"}

# ── 工具函式 ──────────────────────────────────────────────

def load_watchlist() -> list:
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_watchlist(data: list) -> None:
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def volume_label(ratio: float) -> str:
    if ratio < 0.5: return "極度縮量"
    if ratio < 1.0: return "縮量"
    if ratio < 1.5: return "正常"
    if ratio < 2.5: return "放量"
    if ratio < 5.0: return "大量"
    return "異常爆量"

def pv_signal(change: float, ratio: float) -> str:
    if change > 0:
        return "量增價漲" if ratio >= 1.5 else ("量縮價漲" if ratio < 0.8 else "")
    if change < 0:
        return "量增價跌" if ratio >= 1.5 else ("量縮價跌" if ratio < 0.8 else "")
    return ""

def fetch_stock_data(code: str, n_days: int, anchor: datetime.date) -> pd.DataFrame:
    fetch_start = anchor - datetime.timedelta(days=max(n_days * 2 + 30, 90))
    months = []
    cur = fetch_start.replace(day=1)
    while cur <= anchor.replace(day=1):
        months.append((cur.year, cur.month))
        cur = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    stock = twstock.Stock(code, initial_fetch=False)
    all_dfs = []
    for year, month in months:
        try:
            stock.fetch(year, month)
            if not stock.date:
                continue
            all_dfs.append(pd.DataFrame({
                "日期":       [d.strftime("%Y-%m-%d") for d in stock.date],
                "開盤":       stock.open,
                "最高":       stock.high,
                "最低":       stock.low,
                "收盤":       stock.close,
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

    all_df["漲跌"]    = all_df["收盤"].diff().round(2).fillna(0)
    all_df["5日均量"] = all_df["成交量(張)"].rolling(5,  min_periods=1).mean().round(0).astype(int)
    all_df["量比"]    = (all_df["成交量(張)"] / all_df["5日均量"].replace(0, 1)).round(2)
    all_df["量能判斷"] = all_df["量比"].apply(volume_label)
    all_df["訊號"]    = all_df.apply(lambda r: pv_signal(r["漲跌"], r["量比"]), axis=1)
    all_df["MA5"]   = all_df["收盤"].rolling(5,  min_periods=1).mean().round(2)
    all_df["MA10"]  = all_df["收盤"].rolling(10, min_periods=1).mean().round(2)
    all_df["MA20"]  = all_df["收盤"].rolling(20, min_periods=1).mean().round(2)

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
def build_stock_lookup() -> list[tuple[str, str, str]]:
    result = []
    for code, info in twstock.codes.items():
        if hasattr(info, "name") and info.name:
            result.append((code, info.name, getattr(info, "type", "")))
    return sorted(result, key=lambda x: x[0])

def search_stocks(query: str) -> list[tuple[str, str]]:
    query = query.strip()
    if not query:
        return []
    lookup = build_stock_lookup()
    exact = [(c, n) for c, n, t in lookup if c == query]
    if exact:
        return exact
    return [(c, n) for c, n, t in lookup
            if (query in c or query in n) and t in _SEARCH_TYPES][:30]

def today_wisdom() -> str:
    return WISDOM[datetime.date.today().toordinal() % len(WISDOM)]
