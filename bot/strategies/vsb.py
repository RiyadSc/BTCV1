from __future__ import annotations
from typing import Optional
import pandas as pd
from bot.indicators.core import realized_vol, atr


def signals_vsb(
    df: pd.DataFrame,
    oi: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    window: int = 180,
    rv_percentile: float = 0.35,
    atr_percentile: float = 0.45,
    oi_gate: float = 0.02,
) -> pd.Series:
    # Handle both old ('c') and new ('close') column names
    close_col = "close" if "close" in df.columns else "c"
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"
    
    # compression
    rv10 = realized_vol(df[close_col], 10)
    atrn = atr(df, 14) / df[close_col]
    # rolling 180D window percentiles (strictly trailing), thresholds frozen at signal time
    rv_thresh = rv10.rolling(window, min_periods=20).quantile(rv_percentile)
    atr_thresh = atrn.rolling(window, min_periods=20).quantile(atr_percentile)
    compressed = (rv10 <= rv_thresh) & (atrn <= atr_thresh)

    # breakout
    hi20 = df[high_col].rolling(14).max().shift(1)
    lo20 = df[low_col].rolling(14).min().shift(1)
    brk_up = compressed & (df[close_col] > hi20)
    brk_dn = compressed & (df[close_col] < lo20)

    # confirmation
    conf_up = pd.Series(True, index=df.index)
    conf_dn = pd.Series(True, index=df.index)
    if oi is not None and len(oi) > 0:
        oi_al = oi.reindex(df.index).ffill()
        oi_chg = oi_al.pct_change(1).fillna(0)
        conf_up &= (oi_chg >= oi_gate)
        conf_dn &= (oi_chg >= oi_gate)
    if basis is not None and len(basis) > 0:
        b = basis.reindex(df.index).ffill()
        # Confirmation: require OI gate OR basis flip aligned
        basis_sign = (b > 0).astype(int)
        basis_flip_up = basis_sign.diff().fillna(0) > 0  # negative->positive
        basis_flip_dn = basis_sign.diff().fillna(0) < 0  # positive->negative
        conf_up |= basis_flip_up
        conf_dn |= basis_flip_dn

    # Optional retest entry within 2 bars after breakout close
    long_raw = brk_up & conf_up
    short_raw = brk_dn & conf_dn
    long_retest = long_raw.shift(1).fillna(False) & (df[close_col] <= hi20.shift(1) * 1.005)
    short_retest = short_raw.shift(1).fillna(False) & (df[close_col] >= lo20.shift(1) * 0.995)
    long_entry = long_raw | long_retest
    short_entry = short_raw | short_retest

    sig = pd.Series(0, index=df.index, dtype="int8")
    sig[long_entry] = 1
    sig[short_entry] = -1
    return sig
