from __future__ import annotations
from typing import Optional, Dict, Any, List
import time
import requests
import pandas as pd

BYBIT_API = "https://api.bybit.com"


def _get(url: str, params: Optional[Dict[str, Any]] = None, retries: int = 3, sleep_s: float = 0.25) -> Any:
    for i in range(retries):
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            j = r.json()
            # Bybit v5 returns retCode/retMsg
            if isinstance(j, dict) and j.get("retCode") == 0:
                return j
            # If not OK, backoff
        time.sleep(sleep_s * (2 ** i))
    r.raise_for_status()


def open_interest_once(symbol: str, interval: str = "5min", *, startTime: Optional[int] = None, endTime: Optional[int] = None, limit: int = 200, cursor: Optional[str] = None) -> tuple[pd.Series, Optional[str]]:
    """
    Fetch one page of Bybit OI.

    Returns (series, nextPageCursor)
    """
    url = f"{BYBIT_API}/v5/market/open-interest"
    params: Dict[str, Any] = {
        "category": "linear",
        "symbol": symbol.replace("/", ""),
        "intervalTime": interval,
        "limit": min(int(limit), 200),
    }
    if startTime is not None:
        params["startTime"] = int(startTime)
    if endTime is not None:
        params["endTime"] = int(endTime)
    if cursor:
        params["cursor"] = cursor

    data = _get(url, params)
    result = data.get("result") or {}
    rows = result.get("list") or []
    nxt = result.get("nextPageCursor") or None
    if not rows:
        return pd.Series(dtype="float64", name="oi"), None

    df = pd.DataFrame(rows)
    # openInterest is a string; timestamp in ms as string
    s = pd.Series(df["openInterest"].astype("float64").values, index=pd.to_datetime(df["timestamp"].astype("int64"), unit="ms", utc=True))
    s = s.sort_index(); s.name = "oi"
    return s, nxt


def open_interest(symbol: str, interval: str = "5min", startTime: Optional[int] = None, endTime: Optional[int] = None, limit: int = 200) -> pd.Series:
    s, _ = open_interest_once(symbol, interval, startTime=startTime, endTime=endTime, limit=limit)
    return s


def open_interest_paginated(symbol: str, interval: str, since_ms: int, *, window_days: int = 30) -> pd.Series:
    """
    Fetch Bybit OI forward from since_ms to now, using windowed time ranges and page via nextPageCursor.
    """
    parts: List[pd.Series] = []
    cur_start = pd.Timestamp(since_ms, unit='ms', tz='UTC')
    now = pd.Timestamp.now(tz='UTC')
    while cur_start < now:
        cur_end = min(cur_start + pd.Timedelta(days=window_days), now)
        cursor: Optional[str] = None
        while True:
            try:
                s, cursor = open_interest_once(
                    symbol,
                    interval,
                    startTime=int(cur_start.timestamp() * 1000),
                    endTime=int(cur_end.timestamp() * 1000),
                    limit=200,
                    cursor=cursor,
                )
            except Exception:
                # back off slightly and retry the page
                time.sleep(0.5)
                break
            if len(s) == 0:
                break
            parts.append(s)
            if not cursor:
                break
            time.sleep(0.1)
        cur_start = cur_end
        time.sleep(0.2)

    if not parts:
        return pd.Series(dtype="float64", name="oi")
    out = pd.concat(parts).sort_index().drop_duplicates()
    out = out[out.index >= pd.to_datetime(since_ms, unit='ms', utc=True)]
    out.name = "oi"
    return out


