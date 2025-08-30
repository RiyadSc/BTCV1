from __future__ import annotations
from typing import Optional
import pandas as pd
from bot.indicators.core import ema, atr
import pandas as pd


def signals_cat(
    df: pd.DataFrame,
    funding: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    fast_ema: int = 48,
    slow_ema: int = 180,
    enable_momentum_filter: bool = True,
) -> pd.Series:
    f = funding.reindex(df.index).ffill().fillna(0) if funding is not None else pd.Series(0.0, index=df.index)
    b = basis.reindex(df.index).fillna(0) if basis is not None else pd.Series(0.0, index=df.index)

    # Handle both old ('c') and new ('close') column names
    close_col = "close" if "close" in df.columns else "c"
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"
    
    fast = ema(df[close_col], fast_ema)
    slow = ema(df[close_col], slow_ema)
    trend_up = fast > slow
    trend_dn = fast < slow

    # Carry alignment: make longs less strict (either funding<=0 or basis<=0), keep shorts strict
    long_ok = trend_up & ((f <= 0) | (b <= 0))
    short_ok = trend_dn & (f >= 0.0002) & (b >= 0)

    hi20 = df[high_col].rolling(14).max()
    lo20 = df[low_col].rolling(14).min()

    # Require trend to persist >=1 bar and have minimum slope (more relaxed)
    slope = (fast - slow) / df[close_col]
    slope_ok = slope >= 0.0003
    trend_up_persist = trend_up & trend_up.shift(1).fillna(False) & slope_ok
    trend_dn_persist = trend_dn & trend_dn.shift(1).fillna(False) & (slope <= -0.0003)

    # Avoid tight-range breakouts: require Donchian width relative to ATR to be sufficiently wide
    from bot.indicators.core import atr
    atrn = atr(df, 14) / df[close_col]
    width_norm = (hi20 - lo20) / df[close_col]
    range_ok = width_norm >= 0.80 * atrn

    # Multi-timeframe gating (computed but not enforced here)
    close_4h = df[close_col].resample('4H', label='right', closed='right').last()
    ema4_fast = ema(close_4h, 48)
    ema4_slow = ema(close_4h, 180)
    trend4_up = (ema4_fast > ema4_slow).reindex(df.index).ffill().fillna(False)
    trend4_dn = (ema4_fast < ema4_slow).reindex(df.index).ffill().fillna(False)

    long_entry = trend_up_persist & long_ok & (df[close_col] > hi20.shift(1)) & range_ok
    short_entry = trend_dn_persist & short_ok & (df[close_col] < lo20.shift(1)) & range_ok

    # Add momentum confirmation filter
    if enable_momentum_filter:
        from bot.indicators.momentum import confluence_score
        momentum = confluence_score(df, funding)
        
        # Require positive momentum for longs, negative for shorts
        momentum_threshold = 0.2
        long_entry &= momentum > momentum_threshold
        short_entry &= momentum < -momentum_threshold

    sig = pd.Series(0, index=df.index, dtype="int8")
    sig[long_entry] = 1
    sig[short_entry] = -1
    return sig
