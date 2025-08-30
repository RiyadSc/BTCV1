from __future__ import annotations
from typing import Optional, Tuple
import time
import pandas as pd

from .ccxt_client import make_exchange
from .native.binance import get_mark_klines
from .native.coinbase import get_spot_klines
from pathlib import Path
from bot.utils.io import write_parquet, ensure_dir


def _to_ohlcv_df(raw: list) -> pd.DataFrame:
    df = pd.DataFrame(raw, columns=["t","o","h","l","c","v"])
    df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.set_index("t").sort_index()
    df = df.astype({"o":"float64","h":"float64","l":"float64","c":"float64","v":"float64"})
    return df


def fetch_ohlcv_once(exchange_id: str, symbol: str, timeframe: str = "1h", limit: int = 1500, **kwargs) -> pd.DataFrame:
    ex = make_exchange(exchange_id)
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, params=kwargs or {})
    return _to_ohlcv_df(raw)


def fetch_ohlcv_paged(exchange_id: str, symbol: str, timeframe: str = "1h", limit: int = 1500, since_ms: Optional[int] = None, max_bars: int = 50000) -> pd.DataFrame:
    ex = make_exchange(exchange_id)
    all_rows: list = []
    since = since_ms
    while True:
        raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, since=since)
        if not raw:
            break
        all_rows += raw
        if len(all_rows) >= max_bars:
            break
        last_ts = raw[-1][0]
        # advance by 1 ms to avoid duplicates
        since = int(last_ts) + 1
        time.sleep(ex.rateLimit / 1000.0)
        # Do not stop on partial pages; continue until empty response or max_bars reached
    if not all_rows:
        return pd.DataFrame(columns=["o","h","l","c","v"], dtype="float64")
    return _to_ohlcv_df(all_rows)


def fetch_funding_rates(exchange_id: str, symbol: str, since_ms: Optional[int] = None, limit: int = 1000) -> pd.Series:
    ex = make_exchange(exchange_id)
    if not ex.has.get("fetchFundingRateHistory"):
        raise NotImplementedError(f"Exchange {exchange_id} does not support fetchFundingRateHistory")
    params = {}
    rows = ex.fetchFundingRateHistory(symbol=symbol, since=since_ms, limit=limit, params=params)
    if not rows:
        return pd.Series(dtype="float64")
    df = pd.DataFrame(rows)
    # 'fundingRate' and 'timestamp' are typical fields in ccxt for this call
    ts = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    s = pd.Series(df["fundingRate"].astype("float64").values, index=ts).sort_index()
    return s


def fetch_open_interest(exchange_id: str, symbol: str, timeframe: str = "1h", since_ms: Optional[int] = None, limit: int = 500) -> pd.Series:
    ex = make_exchange(exchange_id)
    if not ex.has.get("fetchOpenInterestHistory"):
        raise NotImplementedError(f"Exchange {exchange_id} does not support fetchOpenInterestHistory")
    rows = ex.fetchOpenInterestHistory(symbol, timeframe=timeframe, since=since_ms, limit=limit)
    if not rows:
        return pd.Series(dtype="float64")
    df = pd.DataFrame(rows)
    ts = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    s = pd.Series(df["openInterestAmount"].astype("float64").values, index=ts).sort_index()
    return s


def compute_relative_basis(perp_df: pd.DataFrame, spot_df: pd.DataFrame) -> pd.Series:
    idx = perp_df.index.union(spot_df.index)
    # Handle both old ('c') and new ('close') column names
    perp_close = perp_df["close"] if "close" in perp_df.columns else perp_df["c"]
    spot_close = spot_df["close"] if "close" in spot_df.columns else spot_df["c"]
    
    pc = perp_close.reindex(idx).ffill()
    sc = spot_close.reindex(idx).ffill()
    basis = (pc - sc) / sc
    basis.name = "basis"
    return basis


def save_market_data(out_dir: str, timeframe: str, spot_df: pd.DataFrame, perp_df: pd.DataFrame, funding: Optional[pd.Series], open_interest: Optional[pd.Series]) -> None:
    ensure_dir(out_dir)
    write_parquet(spot_df, f"{out_dir}/spot_{timeframe}.parquet")
    write_parquet(perp_df, f"{out_dir}/perp_{timeframe}.parquet")
    if funding is not None and len(funding) > 0:
        funding_df = funding.to_frame("funding")
        write_parquet(funding_df, f"{out_dir}/funding.parquet")
    if open_interest is not None and len(open_interest) > 0:
        oi_df = open_interest.to_frame("oi")
        write_parquet(oi_df, f"{out_dir}/open_interest.parquet")


def save_mark_and_basis(spot_df: pd.DataFrame, perp_mark_df: pd.DataFrame, out_dir: Path, timeframe: str) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(index=spot_df.index.union(perp_mark_df.index)).sort_index()
    df['spot_close'] = spot_df['c'].reindex(df.index)
    df['perp_mark_close'] = perp_mark_df['c'].reindex(df.index)
    df = df.dropna(subset=['spot_close', 'perp_mark_close'])
    basis_rel = (df['perp_mark_close'] - df['spot_close']) / df['spot_close']
    write_parquet(df[['perp_mark_close']], str(out_dir / f"perp_mark_{timeframe}.parquet"))
    write_parquet(basis_rel.to_frame('basis_rel'), str(out_dir / f"basis_rel_{timeframe}.parquet"))


def fetch_and_persist_mark_and_basis(perp_symbol: str, spot_symbol: str, timeframe: str, out_dir: str):
    perp_mark = get_mark_klines(perp_symbol, timeframe)
    spot = get_spot_klines(spot_symbol, timeframe)
    save_mark_and_basis(spot, perp_mark, Path(out_dir), timeframe)


def resample_oi_to_timeframe(oi: pd.Series, timeframe: str, index_like: Optional[pd.DatetimeIndex] = None) -> Tuple[pd.Series, pd.Series]:
    """Align OI (USD) to bar right edge and compute Δ% change.

    - Resample with last() per timeframe
    - Do not interpolate; forward-fill only to align to provided index if given
    """
    if not isinstance(oi.index, pd.DatetimeIndex):
        raise ValueError("OI series must have a DatetimeIndex")
    oi_res = oi.resample(timeframe, label="right", closed="right").last()
    if index_like is not None:
        oi_res = oi_res.reindex(index_like)
    oi_chg = oi_res.pct_change()
    return oi_res.rename('oi_usd'), oi_chg.rename('oi_pct')


def persist_oi_processed(oi_raw: pd.Series, tf_index: pd.DatetimeIndex, out_dir: str, timeframe: str) -> None:
    if len(oi_raw) == 0:
        return
    # First resample OI from 5m to target timeframe (1h) using last()
    oi_resampled = oi_raw.resample(timeframe, label="right", closed="right").last()
    # Forward-fill to align with tf_index, but limit to reasonable gaps
    oi_aligned = oi_resampled.reindex(tf_index).ffill(limit=2)  # max 2 bars forward-fill
    oi_pct = oi_aligned.pct_change().fillna(0.0)
    
    base = Path(out_dir) / "processed" / "btc" / timeframe
    base.mkdir(parents=True, exist_ok=True)
    write_parquet(oi_aligned.rename('oi_usd').to_frame(), str(base / "oi_usd.parquet"))
    write_parquet(oi_pct.rename('oi_pct').to_frame(), str(base / "oi_pct.parquet"))


def load_market_data(in_dir: str, timeframe: str) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.Series], Optional[pd.Series]]:
    spot = pd.read_parquet(f"{in_dir}/spot_{timeframe}.parquet")
    perp = pd.read_parquet(f"{in_dir}/perp_{timeframe}.parquet")
    funding = None
    oi = None
    try:
        funding = pd.read_parquet(f"{in_dir}/funding.parquet")["funding"]
        # Keep funding at original 8-hour intervals only - do NOT forward fill
        # This prevents leakage from applying funding at wrong times
    except Exception:
        funding = None
    try:
        oi_raw = pd.read_parquet(f"{in_dir}/open_interest.parquet")["oi"]
        # Resample OI from 5-minute to target timeframe
        if len(oi_raw) > 0:
            # Resample to target timeframe using last() (right edge)
            oi = oi_raw.resample(timeframe, label="right", closed="right").last()
            # Forward-fill to align with perp index, but limit gaps
            oi = oi.reindex(perp.index).ffill(limit=2)
    except Exception:
        oi = None
    return spot, perp, funding, oi
