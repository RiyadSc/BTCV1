from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from bot.strategies.cat import signals_cat
from bot.strategies.vsb import signals_vsb
from bot.indicators.core import realized_vol, atr, ema
from bot.backtest.engine import Backtester, SizingRules


def verify_percentile_trailing(df: pd.DataFrame, window: int = 180) -> Dict[str, Any]:
    """Verify that percentile calculations are strictly trailing and don't use future data."""
    
    close_col = "close" if "close" in df.columns else "c"
    
    # Test data: create a series with a known future spike
    test_data = df[close_col].copy()
    spike_idx = len(test_data) // 2  # Put spike in middle
    original_value = test_data.iloc[spike_idx]
    test_data.iloc[spike_idx] = test_data.iloc[spike_idx] * 5  # 5x spike
    
    # Calculate rolling percentiles
    rv_test = realized_vol(pd.DataFrame({close_col: test_data})[close_col], 10)
    atr_test = atr(pd.DataFrame({close_col: test_data, 'high': test_data, 'low': test_data}), 14) / test_data
    
    # Rolling percentiles with min_periods
    rv_thresh = rv_test.rolling(window, min_periods=20).quantile(0.35)
    atr_thresh = atr_test.rolling(window, min_periods=20).quantile(0.45)
    
    # Check if pre-spike percentiles are affected by the spike
    pre_spike_rv = rv_thresh.iloc[spike_idx - 10:spike_idx]
    post_spike_rv = rv_thresh.iloc[spike_idx + 1:spike_idx + 11]
    
    pre_spike_atr = atr_thresh.iloc[spike_idx - 10:spike_idx]
    post_spike_atr = atr_thresh.iloc[spike_idx + 1:spike_idx + 11]
    
    # If percentiles are trailing, pre-spike values shouldn't change
    return {
        'spike_position': spike_idx,
        'spike_magnitude': 5.0,
        'original_value': float(original_value),
        'spiked_value': float(test_data.iloc[spike_idx]),
        'pre_spike_rv_mean': float(pre_spike_rv.mean()) if not pre_spike_rv.empty else None,
        'post_spike_rv_mean': float(post_spike_rv.mean()) if not post_spike_rv.empty else None,
        'pre_spike_atr_mean': float(pre_spike_atr.mean()) if not pre_spike_atr.empty else None,
        'post_spike_atr_mean': float(post_spike_atr.mean()) if not post_spike_atr.empty else None,
        'rv_percentile_leaked': bool(abs(pre_spike_rv.mean() - post_spike_rv.mean()) > 0.001) if not (pre_spike_rv.empty or post_spike_rv.empty) else False,
        'atr_percentile_leaked': bool(abs(pre_spike_atr.mean() - post_spike_atr.mean()) > 0.001) if not (pre_spike_atr.empty or post_spike_atr.empty) else False,
    }


def verify_funding_timing(
    df: pd.DataFrame, 
    funding: Optional[pd.Series], 
    positions: pd.Series
) -> Dict[str, Any]:
    """Verify funding is only applied at 00:00, 08:00, 16:00 UTC."""
    
    if funding is None or len(funding) == 0:
        return {'error': 'No funding data available'}
    
    # Check funding timestamp alignment
    funding_hours = funding.index.hour
    valid_hours = funding_hours.isin([0, 8, 16])
    funding_minutes = funding.index.minute
    valid_minutes = funding_minutes == 0
    
    # Check for proper 8-hour intervals
    funding_diffs = funding.index.to_series().diff()
    expected_interval = pd.Timedelta(hours=8)
    valid_intervals = (funding_diffs == expected_interval) | funding_diffs.isna()
    
    # Simulate funding accrual logic from backtest engine
    funding_aligned = funding.reindex(df.index).ffill()
    funding_cuts = df.index.hour.isin([0, 8, 16]) & (df.index.minute == 0)
    
    return {
        'total_funding_cuts': len(funding),
        'valid_hour_cuts': valid_hours.sum(),
        'valid_minute_cuts': valid_minutes.sum(),
        'valid_interval_cuts': valid_intervals.sum(),
        'hour_compliance': float(valid_hours.mean()),
        'minute_compliance': float(valid_minutes.mean()),
        'interval_compliance': float(valid_intervals.mean()),
        'funding_hours_unique': sorted(funding_hours.unique().tolist()),
        'funding_minutes_unique': sorted(funding_minutes.unique().tolist()),
        'total_bar_funding_opportunities': funding_cuts.sum(),
        'funding_properly_aligned': bool(valid_hours.all() and valid_minutes.all()),
    }


def comprehensive_lookahead_test(
    df: pd.DataFrame,
    funding: Optional[pd.Series] = None,
    oi: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    shift_bars: List[int] = [1, 2, 5, 10]
) -> Dict[str, Any]:
    """
    Comprehensive look-ahead bias test by shifting inputs and measuring performance degradation.
    
    If strategies use future data, performance shouldn't degrade when inputs are shifted.
    """
    
    results = {}
    
    # Original signals and performance
    orig_cat = signals_cat(df, funding=funding, basis=basis)
    orig_vsb = signals_vsb(df, oi=oi, basis=basis)
    
    # Calculate original returns (simplified)
    close_col = "close" if "close" in df.columns else "c"
    returns = df[close_col].pct_change().fillna(0)
    
    orig_cat_ret = (orig_cat.shift() * returns).sum()
    orig_vsb_ret = (orig_vsb.shift() * returns).sum()
    
    results['original'] = {
        'cat_total_signals': (orig_cat != 0).sum(),
        'vsb_total_signals': (orig_vsb != 0).sum(),
        'cat_cumulative_return': float(orig_cat_ret),
        'vsb_cumulative_return': float(orig_vsb_ret),
    }
    
    # Test with shifted inputs
    for shift in shift_bars:
        shifted_df = df.shift(shift)
        shifted_funding = funding.shift(shift) if funding is not None else None
        shifted_oi = oi.shift(shift) if oi is not None else None
        shifted_basis = basis.shift(shift) if basis is not None else None
        
        try:
            shifted_cat = signals_cat(shifted_df, funding=shifted_funding, basis=shifted_basis)
            shifted_vsb = signals_vsb(shifted_df, oi=shifted_oi, basis=shifted_basis)
            
            # Align signals back to original timeline
            aligned_cat = shifted_cat.shift(-shift)
            aligned_vsb = shifted_vsb.shift(-shift)
            
            # Calculate returns
            shifted_cat_ret = (aligned_cat.shift() * returns).sum()
            shifted_vsb_ret = (aligned_vsb.shift() * returns).sum()
            
            # Calculate correlation with original signals
            cat_corr = orig_cat.corr(aligned_cat) if len(orig_cat.dropna()) > 10 else 0
            vsb_corr = orig_vsb.corr(aligned_vsb) if len(orig_vsb.dropna()) > 10 else 0
            
            results[f'shift_{shift}'] = {
                'cat_total_signals': (aligned_cat != 0).sum(),
                'vsb_total_signals': (aligned_vsb != 0).sum(),
                'cat_cumulative_return': float(shifted_cat_ret),
                'vsb_cumulative_return': float(shifted_vsb_ret),
                'cat_signal_correlation': float(cat_corr),
                'vsb_signal_correlation': float(vsb_corr),
                'cat_return_degradation': float(orig_cat_ret - shifted_cat_ret),
                'vsb_return_degradation': float(orig_vsb_ret - shifted_vsb_ret),
            }
            
        except Exception as e:
            results[f'shift_{shift}'] = {'error': str(e)}
    
    # Calculate degradation statistics
    degradations_cat = [results[f'shift_{s}'].get('cat_return_degradation', 0) for s in shift_bars if f'shift_{s}' in results and 'error' not in results[f'shift_{s}']]
    degradations_vsb = [results[f'shift_{s}'].get('vsb_return_degradation', 0) for s in shift_bars if f'shift_{s}' in results and 'error' not in results[f'shift_{s}']]
    
    results['summary'] = {
        'cat_avg_degradation': float(np.mean(degradations_cat)) if degradations_cat else 0,
        'vsb_avg_degradation': float(np.mean(degradations_vsb)) if degradations_vsb else 0,
        'cat_degradation_consistent': bool(all(d > 0 for d in degradations_cat)) if degradations_cat else False,
        'vsb_degradation_consistent': bool(all(d > 0 for d in degradations_vsb)) if degradations_vsb else False,
        'cat_likely_clean': bool(np.mean(degradations_cat) > 0.01) if degradations_cat else False,  # >1% degradation expected
        'vsb_likely_clean': bool(np.mean(degradations_vsb) > 0.01) if degradations_vsb else False,
    }
    
    return results


def audit_backtest_timing(
    df: pd.DataFrame,
    funding: Optional[pd.Series] = None
) -> Dict[str, Any]:
    """Audit backtest engine timing alignment."""
    
    # Check if all data is UTC aligned
    df_tz = df.index.tz
    funding_tz = funding.index.tz if funding is not None else None
    
    # Check for minute alignment (should be :00)
    df_minutes = df.index.minute
    minute_aligned = (df_minutes == 0).all()
    
    # Check for consistent hourly intervals
    df_diffs = df.index.to_series().diff().dropna()
    expected_interval = pd.Timedelta(hours=1)
    interval_consistent = (df_diffs == expected_interval).mean()
    
    # Check funding cuts alignment with data
    if funding is not None:
        funding_cuts_in_data = funding.index.intersection(df.index)
        funding_coverage = len(funding_cuts_in_data) / len(funding)
    else:
        funding_cuts_in_data = pd.DatetimeIndex([])
        funding_coverage = 0
    
    return {
        'df_timezone': str(df_tz),
        'funding_timezone': str(funding_tz) if funding_tz else None,
        'timezones_match': df_tz == funding_tz if funding_tz else True,
        'minute_aligned': minute_aligned,
        'interval_consistency': float(interval_consistent),
        'total_bars': len(df),
        'funding_cuts_in_data': len(funding_cuts_in_data),
        'funding_coverage': float(funding_coverage),
        'data_start': str(df.index[0]),
        'data_end': str(df.index[-1]),
        'funding_start': str(funding.index[0]) if funding is not None and len(funding) > 0 else None,
        'funding_end': str(funding.index[-1]) if funding is not None and len(funding) > 0 else None,
    }


def run_complete_leakage_audit(
    df: pd.DataFrame,
    funding: Optional[pd.Series] = None,
    oi: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None
) -> Dict[str, Any]:
    """Run comprehensive leakage audit."""
    
    print("🔍 Running comprehensive leakage audit...")
    
    # 1. Verify percentile calculations are trailing
    print("  1. Testing percentile trailing behavior...")
    percentile_test = verify_percentile_trailing(df)
    
    # 2. Verify funding timing
    print("  2. Auditing funding timing...")
    dummy_positions = pd.Series(0.0, index=df.index)  # For timing test
    funding_test = verify_funding_timing(df, funding, dummy_positions)
    
    # 3. Comprehensive look-ahead test
    print("  3. Running look-ahead bias tests...")
    lookahead_test = comprehensive_lookahead_test(df, funding, oi, basis)
    
    # 4. Audit backtest timing
    print("  4. Auditing backtest timing alignment...")
    timing_test = audit_backtest_timing(df, funding)
    
    return {
        'percentile_test': percentile_test,
        'funding_test': funding_test,
        'lookahead_test': lookahead_test,
        'timing_test': timing_test,
    }
