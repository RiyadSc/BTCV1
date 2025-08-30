from __future__ import annotations
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Dict, Any, List, Tuple, Callable
from pathlib import Path
from itertools import product

from bot.strategies.cat import signals_cat
from bot.strategies.vsb import signals_vsb
from bot.backtest.engine import Backtester, SizingRules
from bot.indicators.core import ema, atr, realized_vol


def modified_cat_strategy(
    df: pd.DataFrame, 
    fast_ema: int = 50, 
    slow_ema: int = 200,
    funding: Optional[pd.Series] = None, 
    basis: Optional[pd.Series] = None
) -> pd.Series:
    """CAT strategy with configurable EMA parameters."""
    
    f = funding.reindex(df.index).ffill().fillna(0) if funding is not None else pd.Series(0.0, index=df.index)
    b = basis.reindex(df.index).fillna(0) if basis is not None else pd.Series(0.0, index=df.index)

    close_col = "close" if "close" in df.columns else "c"
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"
    
    fast = ema(df[close_col], fast_ema)
    slow = ema(df[close_col], slow_ema)
    trend_up = fast > slow
    trend_dn = fast < slow

    long_ok = trend_up & ((f <= 0) | (b <= 0))
    short_ok = trend_dn & (f >= 0.0001)

    hi20 = df[high_col].rolling(20).max()
    lo20 = df[low_col].rolling(20).min()

    trend_up_persist = trend_up & trend_up.shift(1).fillna(False)
    trend_dn_persist = trend_dn & trend_dn.shift(1).fillna(False)

    long_entry = trend_up_persist & long_ok & (df[close_col] > hi20.shift(1))
    short_entry = trend_dn_persist & short_ok & (df[close_col] < lo20.shift(1))

    sig = pd.Series(0, index=df.index, dtype="int8")
    sig[long_entry] = 1
    sig[short_entry] = -1
    return sig


def modified_vsb_strategy(
    df: pd.DataFrame, 
    rv_percentile: float = 0.35,
    atr_percentile: float = 0.45, 
    oi_threshold: float = 0.01,
    window: int = 180,
    oi: Optional[pd.Series] = None, 
    basis: Optional[pd.Series] = None
) -> pd.Series:
    """VSB strategy with configurable percentile and OI threshold parameters."""
    
    close_col = "close" if "close" in df.columns else "c"
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"
    
    # compression with configurable percentiles
    rv10 = realized_vol(df[close_col], 10)
    atrn = atr(df, 14) / df[close_col]
    rv_thresh = rv10.rolling(window, min_periods=20).quantile(rv_percentile)
    atr_thresh = atrn.rolling(window, min_periods=20).quantile(atr_percentile)
    compressed = (rv10 <= rv_thresh) & (atrn <= atr_thresh)

    # breakout
    hi20 = df[high_col].rolling(20).max().shift(1)
    lo20 = df[low_col].rolling(20).min().shift(1)
    brk_up = compressed & (df[close_col] > hi20)
    brk_dn = compressed & (df[close_col] < lo20)

    # confirmation with configurable OI threshold
    conf_up = pd.Series(True, index=df.index)
    conf_dn = pd.Series(True, index=df.index)
    if oi is not None and len(oi) > 0:
        oi_al = oi.reindex(df.index).ffill()
        oi_chg = oi_al.pct_change(1).fillna(0)
        conf_up &= (oi_chg >= oi_threshold)
        conf_dn &= (oi_chg >= oi_threshold)
    if basis is not None and len(basis) > 0:
        b = basis.reindex(df.index).ffill()
        conf_up &= b.diff().where(df[close_col].diff() > 0, other=0) >= 0
        conf_dn &= b.diff().where(df[close_col].diff() < 0, other=0) >= 0

    long_entry = brk_up & conf_up
    short_entry = brk_dn & conf_dn

    sig = pd.Series(0, index=df.index, dtype="int8")
    sig[long_entry] = 1
    sig[short_entry] = -1
    return sig


def run_parameter_grid(
    df: pd.DataFrame,
    strategy_func: Callable,
    param_grid: Dict[str, List],
    funding: Optional[pd.Series] = None,
    oi: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    timeframe: str = "1h"
) -> pd.DataFrame:
    """
    Run strategy across parameter grid and return results.
    
    Returns DataFrame with parameters and performance metrics.
    """
    
    results = []
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    
    total_combinations = np.prod([len(vals) for vals in param_values])
    print(f"Testing {total_combinations} parameter combinations...")
    
    for i, param_combo in enumerate(product(*param_values)):
        if i % 10 == 0:
            print(f"  Progress: {i}/{total_combinations} ({i/total_combinations*100:.1f}%)")
        
        # Create parameter dict
        params = dict(zip(param_names, param_combo))
        
        try:
            # Generate signals with these parameters
            # Only pass parameters that the strategy function accepts
            if 'fast_ema' in params:  # CAT strategy
                signals = strategy_func(df, **params, funding=funding, basis=basis)
            else:  # VSB strategy  
                signals = strategy_func(df, **params, oi=oi, basis=basis)
            
            if (signals != 0).sum() < 5:  # Skip if too few signals
                results.append({
                    **params,
                    'total_return': 0,
                    'sharpe': 0,
                    'max_drawdown': 0,
                    'num_signals': 0,
                    'error': 'insufficient_signals'
                })
                continue
            
            # Run backtest
            if 'fast_ema' in params:  # CAT strategy
                bt = Backtester(
                    df, signals, funding_series=funding,
                    time_stop_bars=7*24 if timeframe=="1h" else 7*6 if timeframe=="4h" else 7,
                    trail_atr_k=2.5
                )
            else:  # VSB strategy
                bt = Backtester(
                    df, signals, funding_series=funding,
                    time_stop_bars=8*24 if timeframe=="1h" else 8*6 if timeframe=="4h" else 8,
                    trail_atr_k=2.0
                )
            
            result = bt.run(SizingRules())
            
            if len(result) == 0:
                results.append({
                    **params,
                    'total_return': 0,
                    'sharpe': 0,
                    'max_drawdown': 0,
                    'num_signals': (signals != 0).sum(),
                    'error': 'backtest_failed'
                })
                continue
            
            # Calculate metrics
            equity = result['equity']
            returns = result['net'].fillna(0)
            
            total_return = equity.iloc[-1] - 1.0 if len(equity) > 0 else 0
            
            # Annualized metrics
            periods_per_year = 365 * 24 if timeframe == "1h" else 365 * 6 if timeframe == "4h" else 365
            ann_return = returns.mean() * periods_per_year
            vol = returns.std() * np.sqrt(periods_per_year)
            sharpe = ann_return / vol if vol > 0 else 0
            
            # Drawdown
            running_max = equity.expanding().max()
            drawdown = (equity - running_max) / running_max
            max_drawdown = drawdown.min()
            
            results.append({
                **params,
                'total_return': total_return,
                'annualized_return': ann_return,
                'volatility': vol,
                'sharpe': sharpe,
                'max_drawdown': max_drawdown,
                'num_signals': (signals != 0).sum(),
                'error': None
            })
            
        except Exception as e:
            results.append({
                **params,
                'total_return': 0,
                'sharpe': 0,
                'max_drawdown': 0,
                'num_signals': 0,
                'error': str(e)
            })
    
    print(f"Completed {len(results)} parameter combinations")
    return pd.DataFrame(results)


def create_heatmap(
    results_df: pd.DataFrame,
    x_param: str,
    y_param: str,
    metric: str = 'sharpe',
    title: str = None,
    save_path: str = None
) -> plt.Figure:
    """Create heatmap visualization of parameter grid results."""
    
    # Filter out error cases
    clean_results = results_df[results_df['error'].isna()].copy()
    
    if len(clean_results) == 0:
        print("No valid results to plot")
        return None
    
    # Create pivot table
    pivot = clean_results.pivot_table(
        values=metric, 
        index=y_param, 
        columns=x_param, 
        aggfunc='mean'
    )
    
    # Create heatmap
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        pivot, 
        annot=True, 
        fmt='.3f', 
        cmap='RdYlBu_r',
        center=0 if metric == 'sharpe' else None,
        cbar_kws={'label': metric.replace('_', ' ').title()}
    )
    
    plt.title(title or f'{metric.replace("_", " ").title()} Heatmap')
    plt.xlabel(x_param.replace('_', ' ').title())
    plt.ylabel(y_param.replace('_', ' ').title())
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Heatmap saved to {save_path}")
    
    return plt.gcf()


def analyze_parameter_stability(
    results_df: pd.DataFrame,
    metric: str = 'sharpe',
    stability_threshold: float = 0.1
) -> Dict[str, Any]:
    """Analyze parameter stability and identify robust regions."""
    
    clean_results = results_df[results_df['error'].isna()].copy()
    
    if len(clean_results) == 0:
        print(f"No valid results found. Total results: {len(results_df)}")
        if len(results_df) > 0:
            print(f"Error summary: {results_df['error'].value_counts()}")
        return {'error': 'No valid results', 'total_results': len(results_df)}
    
    # Find best performance
    best_idx = clean_results[metric].idxmax()
    best_params = clean_results.loc[best_idx]
    
    # Find performance statistics
    metric_values = clean_results[metric]
    
    analysis = {
        'best_performance': {
            'value': best_params[metric],
            'parameters': {k: v for k, v in best_params.items() if k not in ['total_return', 'annualized_return', 'volatility', 'sharpe', 'max_drawdown', 'num_signals', 'error']}
        },
        'performance_stats': {
            'mean': metric_values.mean(),
            'std': metric_values.std(),
            'min': metric_values.min(),
            'max': metric_values.max(),
            'q25': metric_values.quantile(0.25),
            'q75': metric_values.quantile(0.75)
        },
        'stability_analysis': {
            'coefficient_of_variation': metric_values.std() / metric_values.mean() if metric_values.mean() != 0 else np.inf,
            'robust_performance_threshold': metric_values.quantile(0.75),
            'stable_parameter_count': len(clean_results[metric_values > (best_params[metric] - stability_threshold)])
        }
    }
    
    # Identify robust parameter regions (within threshold of best)
    robust_mask = metric_values > (best_params[metric] - stability_threshold)
    robust_results = clean_results[robust_mask]
    
    if len(robust_results) > 1:
        # Find parameter ranges for robust region
        param_cols = [col for col in robust_results.columns if col not in ['total_return', 'annualized_return', 'volatility', 'sharpe', 'max_drawdown', 'num_signals', 'error']]
        robust_ranges = {}
        for param in param_cols:
            robust_ranges[param] = {
                'min': robust_results[param].min(),
                'max': robust_results[param].max(),
                'range': robust_results[param].max() - robust_results[param].min()
            }
        analysis['robust_parameter_ranges'] = robust_ranges
    
    return analysis


def run_cat_parameter_stability(
    df: pd.DataFrame,
    funding: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    timeframe: str = "1h",
    output_dir: str = "out/parameter_stability"
) -> Dict[str, Any]:
    """Run CAT parameter stability analysis."""
    
    print("🔬 Running CAT parameter stability analysis...")
    
    # Define parameter grid
    param_grid = {
        'fast_ema': list(range(40, 81, 5)),  # 40, 45, 50, ..., 80
        'slow_ema': list(range(150, 251, 10))  # 150, 160, 170, ..., 250
    }
    
    # Run grid search
    results = run_parameter_grid(
        df, modified_cat_strategy, param_grid,
        funding=funding, basis=basis, timeframe=timeframe
    )
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Save results
    results.to_csv(f"{output_dir}/cat_parameter_results.csv", index=False)
    
    # Create heatmaps
    heatmap_sharpe = create_heatmap(
        results, 'fast_ema', 'slow_ema', 'sharpe',
        title='CAT Strategy: Sharpe Ratio by EMA Parameters',
        save_path=f"{output_dir}/cat_sharpe_heatmap.png"
    )
    
    heatmap_return = create_heatmap(
        results, 'fast_ema', 'slow_ema', 'total_return',
        title='CAT Strategy: Total Return by EMA Parameters',
        save_path=f"{output_dir}/cat_return_heatmap.png"
    )
    
    # Analyze stability
    stability_analysis = analyze_parameter_stability(results, 'sharpe')
    
    print(f"✅ CAT analysis complete:")
    print(f"   Best Sharpe: {stability_analysis['best_performance']['value']:.3f}")
    print(f"   Best params: {stability_analysis['best_performance']['parameters']}")
    print(f"   Stability CV: {stability_analysis['stability_analysis']['coefficient_of_variation']:.3f}")
    
    return {
        'results': results,
        'stability_analysis': stability_analysis,
        'param_grid': param_grid
    }


def run_vsb_parameter_stability(
    df: pd.DataFrame,
    oi: Optional[pd.Series] = None,
    basis: Optional[pd.Series] = None,
    timeframe: str = "1h",
    output_dir: str = "out/parameter_stability"
) -> Dict[str, Any]:
    """Run VSB parameter stability analysis."""
    
    print("🔬 Running VSB parameter stability analysis...")
    
    # Define parameter grid
    param_grid = {
        'rv_percentile': [0.15, 0.20, 0.25, 0.30, 0.35, 0.40],  # 15% to 40%
        'oi_threshold': [0.005, 0.01, 0.015, 0.02, 0.03, 0.05]  # 0.5% to 5%
    }
    
    # Run grid search
    results = run_parameter_grid(
        df, modified_vsb_strategy, param_grid,
        oi=oi, basis=basis, timeframe=timeframe
    )
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Save results
    results.to_csv(f"{output_dir}/vsb_parameter_results.csv", index=False)
    
    # Create heatmaps
    heatmap_sharpe = create_heatmap(
        results, 'oi_threshold', 'rv_percentile', 'sharpe',
        title='VSB Strategy: Sharpe Ratio by Threshold Parameters',
        save_path=f"{output_dir}/vsb_sharpe_heatmap.png"
    )
    
    heatmap_return = create_heatmap(
        results, 'oi_threshold', 'rv_percentile', 'total_return',
        title='VSB Strategy: Total Return by Threshold Parameters', 
        save_path=f"{output_dir}/vsb_return_heatmap.png"
    )
    
    # Analyze stability
    stability_analysis = analyze_parameter_stability(results, 'sharpe')
    
    print(f"✅ VSB analysis complete:")
    print(f"   Best Sharpe: {stability_analysis['best_performance']['value']:.3f}")
    print(f"   Best params: {stability_analysis['best_performance']['parameters']}")
    print(f"   Stability CV: {stability_analysis['stability_analysis']['coefficient_of_variation']:.3f}")
    
    return {
        'results': results,
        'stability_analysis': stability_analysis,
        'param_grid': param_grid
    }
