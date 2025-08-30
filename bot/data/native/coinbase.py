from __future__ import annotations
from typing import Optional, Dict, Any, List
import time
import requests
import pandas as pd

COINBASE = "https://api.exchange.coinbase.com"


def _get(url: str, params: Optional[Dict[str, Any]] = None, retries: int = 3, sleep_s: float = 0.2) -> Any:
    headers = {"User-Agent": "TradeBOTexp2"}
    for i in range(retries):
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        time.sleep(sleep_s * (2 ** i))
    r.raise_for_status()


def klines(product_id: str = "BTC-USD", granularity: int = 3600, start: Optional[str] = None, end: Optional[str] = None, limit: int = 300) -> pd.DataFrame:
    url = f"{COINBASE}/products/{product_id}/candles"
    params = {"granularity": granularity}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    data = _get(url, params=params)
    if not data:
        return pd.DataFrame(columns=["o","h","l","c","v"])
    df = pd.DataFrame(data, columns=["t","l","h","o","c","v"]).astype({"t":"int64"})
    df["t"] = pd.to_datetime(df["t"], unit="s", utc=True)
    df = df.set_index("t").sort_index()
    df = df[["o","h","l","c","v"]].astype("float64")
    return df


def get_spot_klines(symbol: str, timeframe: str) -> pd.DataFrame:
    # map timeframe to granularity seconds
    gran = 3600 if timeframe=="1h" else 14400 if timeframe=="4h" else 86400
    return klines(product_id=symbol, granularity=gran)


def _klines_paginated_gran(product_id: str, gran: int, since_ms: int) -> pd.DataFrame:
    # Coinbase supports start/end ISO8601; fetch forward in windows of 300 bars
    step_s = 300 * gran
    parts: List[pd.DataFrame] = []
    now_s = int(pd.Timestamp.utcnow().timestamp())
    cur_s = int(since_ms // 1000)
    while cur_s < now_s:
        start = pd.to_datetime(cur_s, unit='s', utc=True)
        end_s = min(cur_s + step_s, now_s)
        end = pd.to_datetime(end_s, unit='s', utc=True)
        s_str = start.strftime('%Y-%m-%dT%H:%M:%SZ')
        e_str = end.strftime('%Y-%m-%dT%H:%M:%SZ')
        df = klines(product_id=product_id, granularity=gran, start=s_str, end=e_str, limit=300)
        if len(df) > 0:
            parts.append(df)
        cur_s = end_s + gran  # advance with 1 bar overlap buffer
        time.sleep(0.1)
    if not parts:
        return pd.DataFrame(columns=["o","h","l","c","v"], dtype="float64")
    out = pd.concat(parts).sort_index().drop_duplicates()
    return out


def klines_paginated(product_id: str, timeframe: str, since_ms: int) -> pd.DataFrame:
    if timeframe == "1h":
        return _klines_paginated_gran(product_id, 3600, since_ms)
    if timeframe == "4h":
        # Coinbase lacks 4h granularity; fetch 1h and resample to 4H
        df1h = _klines_paginated_gran(product_id, 3600, since_ms)
        if len(df1h) == 0:
            return df1h
        agg = {"o": "first", "h": "max", "l": "min", "c": "last", "v": "sum"}
        df4h = df1h.resample('4H', label='right', closed='right').agg(agg).dropna(how='any')
        df4h = df4h.astype("float64")
        return df4h
    if timeframe == "1d" or timeframe == "1D":
        return _klines_paginated_gran(product_id, 86400, since_ms)
    # fallback: try direct
    gran = 3600 if timeframe=="1h" else 86400
    return _klines_paginated_gran(product_id, gran, since_ms)
