from __future__ import annotations
from typing import Optional, Dict, Any, List
import time
import requests
import pandas as pd

BINANCE_FAPI = "https://fapi.binance.com"
BINANCE_DAPI = "https://dapi.binance.com"  # inverse; we use USDT-margined default


def _get(url: str, params: Optional[Dict[str, Any]] = None, retries: int = 3, sleep_s: float = 0.2) -> Any:
    for i in range(retries):
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
        time.sleep(sleep_s * (2 ** i))
    r.raise_for_status()


def klines(symbol: str, interval: str = "1h", limit: int = 1500, startTime: Optional[int] = None, endTime: Optional[int] = None) -> pd.DataFrame:
    url = f"{BINANCE_FAPI}/fapi/v1/klines"
    params = {"symbol": symbol.replace("/", ""), "interval": interval, "limit": limit}
    if startTime:
        params["startTime"] = startTime
    if endTime:
        params["endTime"] = endTime
    data = _get(url, params)
    cols = ["t","o","h","l","c","v","ct","qv","n","tb","tbv","ig"]
    df = pd.DataFrame(data, columns=cols)
    df = df[["t","o","h","l","c","v","qv"]]
    df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.set_index("t").astype({"o":"float64","h":"float64","l":"float64","c":"float64","v":"float64","qv":"float64"}).sort_index()
    return df


def mark_price(symbol: str) -> float:
    url = f"{BINANCE_FAPI}/fapi/v1/premiumIndex"
    params = {"symbol": symbol.replace("/", "")}
    data = _get(url, params)
    return float(data["markPrice"]) if isinstance(data, dict) else float(data[0]["markPrice"])  # API returns dict


def mark_price_kline(symbol: str, interval: str = "1h", limit: int = 1500, startTime: Optional[int] = None, endTime: Optional[int] = None) -> pd.DataFrame:
    url = f"{BINANCE_FAPI}/fapi/v1/markPriceKlines"
    params = {"symbol": symbol.replace("/", ""), "interval": interval, "limit": limit}
    if startTime:
        params["startTime"] = startTime
    if endTime:
        params["endTime"] = endTime
    data = _get(url, params)
    cols = ["t","o","h","l","c","v","ct","qv","n","tb","tbv","ig"]
    df = pd.DataFrame(data, columns=cols)
    df = df[["t","o","h","l","c","v"]]
    df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.set_index("t").astype("float64").sort_index()
    return df


def get_mark_klines(symbol: str, timeframe: str, limit: int = 1500) -> pd.DataFrame:
    # wrapper to match patches; returns columns: o,h,l,c
    return mark_price_kline(symbol, interval=timeframe, limit=limit)


def funding_rate_history(symbol: str, startTime: Optional[int] = None, endTime: Optional[int] = None, limit: int = 1000) -> pd.Series:
    url = f"{BINANCE_FAPI}/fapi/v1/fundingRate"
    params = {"symbol": symbol.replace("/", ""), "limit": limit}
    if startTime:
        params["startTime"] = startTime
    if endTime:
        params["endTime"] = endTime
    data = _get(url, params)
    df = pd.DataFrame(data)
    df["fundingRate"] = df["fundingRate"].astype("float64")
    s = pd.Series(df["fundingRate"].values, index=pd.to_datetime(df["fundingTime"], unit="ms", utc=True))
    s = s.sort_index(); s.name = "funding"
    return s


def open_interest(symbol: str, interval: str = "5m", startTime: Optional[int] = None, endTime: Optional[int] = None, limit: int = 500) -> pd.Series:
    url = f"{BINANCE_FAPI}/futures/data/openInterestHist"
    # Binance max limit is 500
    params = {"symbol": symbol.replace("/", ""), "period": interval, "limit": min(int(limit), 500)}
    if startTime:
        params["startTime"] = startTime
    if endTime:
        params["endTime"] = endTime
    data = _get(url, params)
    df = pd.DataFrame(data)
    s = pd.Series(df["sumOpenInterest"].astype("float64").values, index=pd.to_datetime(df["timestamp"], unit="ms", utc=True))
    s = s.sort_index(); s.name = "oi"
    return s


# -----------------------
# Paginated helpers (since -> now)
# -----------------------

def _paginate_time(start_ms: int, step_ms: int, *, until_ms: Optional[int] = None):
    """
    Generator that yields (startTime, endTime) windows moving forward.
    step_ms should correspond to limit * interval_ms with a small overlap to avoid gaps.
    """
    cur = start_ms
    end = until_ms or int(pd.Timestamp.utcnow().timestamp() * 1000)
    while cur < end:
        nxt = min(cur + step_ms - 1, end)
        yield cur, nxt
        # advance with small overlap (1 interval) to avoid gaps
        cur = nxt + 1


def klines_paginated(symbol: str, interval: str, since_ms: int, limit: int = 1500) -> pd.DataFrame:
    """Fetch Binance klines forward from since_ms to now, concatenating pages."""
    # interval to milliseconds
    tf_ms = {
        "5m": 5 * 60_000,
        "15m": 15 * 60_000,
        "1h": 60 * 60_000,
        "4h": 4 * 60 * 60_000,
        "1d": 24 * 60 * 60_000,
    }[interval]
    step_ms = tf_ms * limit
    parts: List[pd.DataFrame] = []
    for st, en in _paginate_time(since_ms, step_ms):
        df = klines(symbol, interval, limit=limit, startTime=st, endTime=en)
        if len(df) == 0:
            continue
        parts.append(df)
    if not parts:
        return pd.DataFrame(columns=["o","h","l","c","v","qv"], dtype="float64")
    out = pd.concat(parts).sort_index().drop_duplicates()
    return out


def mark_klines_paginated(symbol: str, interval: str, since_ms: int, limit: int = 1500) -> pd.DataFrame:
    tf_ms = {
        "5m": 5 * 60_000,
        "15m": 15 * 60_000,
        "1h": 60 * 60_000,
        "4h": 4 * 60 * 60_000,
        "1d": 24 * 60 * 60_000,
    }[interval]
    step_ms = tf_ms * limit
    parts: List[pd.DataFrame] = []
    for st, en in _paginate_time(since_ms, step_ms):
        df = mark_price_kline(symbol, interval, limit=limit, startTime=st, endTime=en)
        if len(df) == 0:
            continue
        parts.append(df)
    if not parts:
        return pd.DataFrame(columns=["o","h","l","c","v"], dtype="float64")
    out = pd.concat(parts).sort_index().drop_duplicates()
    return out


def funding_paginated(symbol: str, since_ms: int, page_limit: int = 1000) -> pd.Series:
    step_ms = 8 * 60 * 60 * 1000 * page_limit  # 8h intervals times limit
    parts: List[pd.Series] = []
    for st, en in _paginate_time(since_ms, step_ms):
        s = funding_rate_history(symbol, startTime=st, endTime=en, limit=page_limit)
        if len(s) == 0:
            continue
        parts.append(s)
    if not parts:
        return pd.Series(dtype="float64", name="funding")
    out = pd.concat(parts).sort_index().drop_duplicates()
    out.name = "funding"
    return out


def open_interest_paginated(symbol: str, interval: str, since_ms: int, page_limit: int = 500) -> pd.Series:
    """
    Robust OI pagination: step backward using endTime only so the server controls windowing.
    Continue until we pass since_ms. This avoids 400s caused by over-wide [start,end] ranges.
    """
    parts: List[pd.Series] = []
    end_ms = int(pd.Timestamp.utcnow().timestamp() * 1000)
    while True:
        try:
            s = open_interest(symbol, interval=interval, endTime=end_ms, limit=page_limit)
        except Exception:
            # back off a little on failures
            end_ms -= 60 * 60 * 1000
            continue
        if len(s) == 0:
            break
        parts.append(s)
        oldest = int(s.index[0].timestamp() * 1000)
        if oldest <= since_ms:
            break
        end_ms = oldest - 1
        time.sleep(0.1)
    if not parts:
        return pd.Series(dtype="float64", name="oi")
    out = pd.concat(parts).sort_index().drop_duplicates()
    # Trim strictly to since_ms
    out = out[out.index >= pd.to_datetime(since_ms, unit='ms', utc=True)]
    out.name = "oi"
    return out


def taker_buy_sell_ratio(symbol: str, interval: str = "1h", limit: int = 1500) -> pd.Series:
    url = f"{BINANCE_FAPI}/futures/data/takerlongshortRatio"
    params = {"symbol": symbol.replace("/", ""), "period": interval, "limit": limit}
    data = _get(url, params)
    df = pd.DataFrame(data)
    s = pd.Series(df["longShortRatio"].astype("float64").values, index=pd.to_datetime(df["timestamp"], unit="ms", utc=True))
    s = s.sort_index(); s.name = "ls_ratio"
    return s


def long_short_account_ratio(symbol: str, interval: str = "1h", limit: int = 1500) -> pd.Series:
    url = f"{BINANCE_FAPI}/futures/data/globalLongShortAccountRatio"
    params = {"symbol": symbol.replace("/", ""), "period": interval, "limit": limit}
    data = _get(url, params)
    df = pd.DataFrame(data)
    s = pd.Series(df["longShortRatio"].astype("float64").values, index=pd.to_datetime(df["timestamp"], unit="ms", utc=True))
    s = s.sort_index(); s.name = "account_ls_ratio"
    return s


def stream_book_ticker(symbol: str) -> float:
    url = f"{BINANCE_FAPI}/fapi/v1/ticker/bookTicker"
    p = {"symbol": symbol.replace("/", "")}
    r = requests.get(url, params=p, timeout=10); r.raise_for_status()
    j = r.json()
    bid = float(j['bidPrice']); ask = float(j['askPrice'])
    mid = 0.5*(bid+ask)
    spr = (ask - bid)/mid if mid else 0.0
    return spr
