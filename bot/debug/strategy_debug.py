from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from bot.strategies.cat import signals_cat
from bot.strategies.vsb import signals_vsb
from bot.indicators.core import realized_vol, atr, ema


def analyze_signal_generation(
    df: pd.DataFrame,
    funding: Optional[pd.Series] = None,
    oi: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    window_start: Optional[pd.Timestamp] = None,
    window_end: Optional[pd.Timestamp] = None
) -> Dict[str, Any]:
    """Analyze signal generation for both strategies in a given window."""
    
    if window_start and window_end:
        mask = (df.index >= window_start) & (df.index < window_end)
        df_window = df[mask].copy()
        if funding is not None:
            funding = funding[funding.index.isin(df_window.index)]
        if oi is not None:
            oi = oi[oi.index.isin(df_window.index)]
        if basis is not None:
            basis = basis[basis.index.isin(df_window.index)]
    else:
        df_window = df.copy()
    
    results = {}
    
    # CAT Analysis
    try:
        cat_signals = signals_cat(df, funding=funding, basis=basis)
        if window_start and window_end:
            cat_signals = cat_signals[(cat_signals.index >= window_start) & (cat_signals.index < window_end)]
        
        results['cat'] = {
            'total_signals': len(cat_signals),
            'long_signals': (cat_signals == 1).sum(),
            'short_signals': (cat_signals == -1).sum(),
            'flat_signals': (cat_signals == 0).sum(),
            'signal_changes': (cat_signals.diff() != 0).sum(),
            'first_signal': cat_signals.iloc[0] if len(cat_signals) > 0 else 0,
            'last_signal': cat_signals.iloc[-1] if len(cat_signals) > 0 else 0,
            'signal_frequency': (cat_signals != 0).mean(),
        }
    except Exception as e:
        results['cat'] = {'error': str(e)}
    
    # VSB Analysis
    try:
        vsb_signals = signals_vsb(df, oi=oi, basis=basis)
        if window_start and window_end:
            vsb_signals = vsb_signals[(vsb_signals.index >= window_start) & (vsb_signals.index < window_end)]
        
        results['vsb'] = {
            'total_signals': len(vsb_signals),
            'long_signals': (vsb_signals == 1).sum(),
            'short_signals': (vsb_signals == -1).sum(),
            'flat_signals': (vsb_signals == 0).sum(),
            'signal_changes': (vsb_signals.diff() != 0).sum(),
            'first_signal': vsb_signals.iloc[0] if len(vsb_signals) > 0 else 0,
            'last_signal': vsb_signals.iloc[-1] if len(vsb_signals) > 0 else 0,
            'signal_frequency': (vsb_signals != 0).mean(),
        }
    except Exception as e:
        results['vsb'] = {'error': str(e)}
    
    return results


def debug_vsb_components(
    df: pd.DataFrame,
    oi: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    window: int = 180
) -> Dict[str, Any]:
    """Debug VSB strategy components step by step."""
    
    close_col = "close" if "close" in df.columns else "c"
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"
    
    # Step 1: Basic indicators
    rv10 = realized_vol(df[close_col], 10)
    atrn = atr(df, 14) / df[close_col]
    
    # Step 2: Rolling percentiles (potential look-ahead issue)
    rv_thresh = rv10.rolling(window).quantile(0.2)
    atr_thresh = atrn.rolling(window).quantile(0.3)
    
    # Step 3: Compression detection
    compressed = (rv10 <= rv_thresh) & (atrn <= atr_thresh)
    
    # Step 4: Breakout detection
    hi20 = df[high_col].rolling(20).max().shift(1)
    lo20 = df[low_col].rolling(20).min().shift(1)
    brk_up = compressed & (df[close_col] > hi20)
    brk_dn = compressed & (df[close_col] < lo20)
    
    # Step 5: OI confirmation
    oi_conf_up = pd.Series(True, index=df.index)
    oi_conf_dn = pd.Series(True, index=df.index)
    
    if oi is not None and len(oi) > 0:
        oi_aligned = oi.reindex(df.index).ffill()
        oi_chg = oi_aligned.pct_change().fillna(0)
        oi_conf_up = oi_chg >= 0.02
        oi_conf_dn = oi_chg >= 0.02
    
    # Step 6: Basis confirmation
    basis_conf_up = pd.Series(True, index=df.index)
    basis_conf_dn = pd.Series(True, index=df.index)
    
    if basis is not None and len(basis) > 0:
        b = basis.reindex(df.index).ffill()
        basis_conf_up = b.diff().where(df[close_col].diff() > 0, other=0) >= 0
        basis_conf_dn = b.diff().where(df[close_col].diff() < 0, other=0) >= 0
    
    # Final confirmations
    conf_up = oi_conf_up & basis_conf_up
    conf_dn = oi_conf_dn & basis_conf_dn
    
    # Final signals
    signal_up = brk_up & conf_up
    signal_dn = brk_dn & conf_dn
    
    return {
        'total_bars': len(df),
        'rv10_valid': rv10.notna().sum(),
        'atrn_valid': atrn.notna().sum(),
        'rv_thresh_valid': rv_thresh.notna().sum(),
        'atr_thresh_valid': atr_thresh.notna().sum(),
        'compressed_count': compressed.sum(),
        'compressed_pct': compressed.mean(),
        'brk_up_count': brk_up.sum(),
        'brk_dn_count': brk_dn.sum(),
        'oi_conf_up_count': oi_conf_up.sum() if oi is not None else 0,
        'oi_conf_dn_count': oi_conf_dn.sum() if oi is not None else 0,
        'basis_conf_up_count': basis_conf_up.sum() if basis is not None else 0,
        'basis_conf_dn_count': basis_conf_dn.sum() if basis is not None else 0,
        'final_long_signals': signal_up.sum(),
        'final_short_signals': signal_dn.sum(),
        'oi_available': oi is not None and len(oi) > 0,
        'basis_available': basis is not None and len(basis) > 0,
    }


def debug_cat_components(
    df: pd.DataFrame,
    funding: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None
) -> Dict[str, Any]:
    """Debug CAT strategy components step by step."""
    
    close_col = "close" if "close" in df.columns else "c"
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"
    
    # Trend detection
    fast = ema(df[close_col], 50)
    slow = ema(df[close_col], 200)
    trend_up = fast > slow
    trend_dn = fast < slow
    
    # Carry filters
    f = pd.Series(0.0, index=df.index)
    b = pd.Series(0.0, index=df.index)
    
    if funding is not None and len(funding) > 0:
        f = funding.reindex(df.index).ffill().fillna(0)
    if basis is not None and len(basis) > 0:
        b = basis.reindex(df.index).ffill().fillna(0)
    
    long_ok = trend_up & ((f <= 0) | (b <= 0))
    short_ok = trend_dn & (f >= 0.0004)
    
    # Breakout confirmation
    hi20 = df[high_col].rolling(20).max()
    lo20 = df[low_col].rolling(20).min()
    
    # Persistence requirements
    trend_up_persist = trend_up & trend_up.shift(1).fillna(False)
    trend_dn_persist = trend_dn & trend_dn.shift(1).fillna(False)
    
    # Entry signals
    long_entry = trend_up_persist & long_ok & (df[close_col] > hi20.shift(1))
    short_entry = trend_dn_persist & short_ok & (df[close_col] < lo20.shift(1))
    
    return {
        'total_bars': len(df),
        'trend_up_count': trend_up.sum(),
        'trend_dn_count': trend_dn.sum(),
        'trend_up_pct': trend_up.mean(),
        'trend_dn_pct': trend_dn.mean(),
        'funding_available': funding is not None and len(funding) > 0,
        'basis_available': basis is not None and len(basis) > 0,
        'funding_avg': f.mean() if funding is not None else 0,
        'basis_avg': b.mean() if basis is not None else 0,
        'long_ok_count': long_ok.sum(),
        'short_ok_count': short_ok.sum(),
        'long_ok_pct': long_ok.mean(),
        'short_ok_pct': short_ok.mean(),
        'trend_up_persist_count': trend_up_persist.sum(),
        'trend_dn_persist_count': trend_dn_persist.sum(),
        'long_entry_count': long_entry.sum(),
        'short_entry_count': short_entry.sum(),
    }


def test_look_ahead_bias(
    df: pd.DataFrame,
    funding: Optional[pd.Series] = None,
    oi: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    shift_bars: int = 1
) -> Dict[str, float]:
    """Test for look-ahead bias by shifting inputs and measuring signal degradation."""
    
    # Original signals
    orig_cat = signals_cat(df, funding=funding, basis=basis)
    orig_vsb = signals_vsb(df, oi=oi, basis=basis)
    
    # Shifted signals (simulating look-ahead)
    shifted_cat = signals_cat(df.shift(shift_bars), funding=funding.shift(shift_bars) if funding is not None else None, basis=basis.shift(shift_bars) if basis is not None else None)
    shifted_vsb = signals_vsb(df.shift(shift_bars), oi=oi.shift(shift_bars) if oi is not None else None, basis=basis.shift(shift_bars) if basis is not None else None)
    
    # Calculate correlation (high correlation suggests look-ahead bias)
    cat_corr = orig_cat.corr(shifted_cat.shift(-shift_bars)) if len(orig_cat.dropna()) > 10 else 0
    vsb_corr = orig_vsb.corr(shifted_vsb.shift(-shift_bars)) if len(orig_vsb.dropna()) > 10 else 0
    
    return {
        'cat_lookahead_correlation': cat_corr,
        'vsb_lookahead_correlation': vsb_corr,
        'cat_signal_count_orig': (orig_cat != 0).sum(),
        'cat_signal_count_shifted': (shifted_cat != 0).sum(),
        'vsb_signal_count_orig': (orig_vsb != 0).sum(),
        'vsb_signal_count_shifted': (shifted_vsb != 0).sum(),
    }


def run_comprehensive_debug(
    df: pd.DataFrame,
    funding: Optional[pd.Series] = None,
    oi: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    window_start: Optional[pd.Timestamp] = None,
    window_end: Optional[pd.Timestamp] = None
) -> Dict[str, Any]:
    """Run comprehensive debugging analysis."""
    
    print(f"Running comprehensive debug for window: {window_start} to {window_end}")
    
    # Overall signal analysis
    signal_analysis = analyze_signal_generation(df, funding, oi, basis, window_start, window_end)
    
    # VSB component debugging
    vsb_debug = debug_vsb_components(df, oi, basis)
    
    # CAT component debugging  
    cat_debug = debug_cat_components(df, funding, basis)
    
    # Look-ahead bias test
    lookahead_test = test_look_ahead_bias(df, funding, oi, basis)
    
    return {
        'signal_analysis': signal_analysis,
        'vsb_debug': vsb_debug,
        'cat_debug': cat_debug,
        'lookahead_test': lookahead_test,
        'data_summary': {
            'total_bars': len(df),
            'date_range': f"{df.index[0]} to {df.index[-1]}",
            'funding_coverage': funding.notna().mean() if funding is not None else 0,
            'oi_coverage': oi.notna().mean() if oi is not None else 0,
            'basis_coverage': basis.notna().mean() if basis is not None else 0,
        }
    }
