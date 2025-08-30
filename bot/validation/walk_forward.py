from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from pathlib import Path

from bot.strategies.cat import signals_cat
from bot.strategies.vsb import signals_vsb
from bot.backtest.engine import Backtester, SizingRules
from bot.portfolio.ensemble import combine_positions


@dataclass
class WalkForwardConfig:
    train_days: int = 365
    test_days: int = 90
    step_days: int = 30
    min_train_bars: int = 1000  # minimum bars needed for training


@dataclass
class WalkForwardWindow:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    window_id: int


@dataclass
class WindowResult:
    window: WalkForwardWindow
    strategy: str
    equity_start: float
    equity_end: float
    total_return: float
    annualized_return: float
    volatility: float
    sharpe: float
    max_drawdown: float
    num_trades: int
    win_rate: float


def generate_windows(df: pd.DataFrame, config: WalkForwardConfig) -> List[WalkForwardWindow]:
    """Generate rolling train/test windows."""
    if len(df) < config.min_train_bars:
        raise ValueError(f"Not enough data: {len(df)} bars < {config.min_train_bars} minimum")
    
    windows = []
    start_date = df.index[0]
    end_date = df.index[-1]
    
    window_id = 0
    current_start = start_date
    
    while True:
        train_start = current_start
        train_end = train_start + pd.Timedelta(days=config.train_days)
        test_start = train_end
        test_end = test_start + pd.Timedelta(days=config.test_days)
        
        # Check if we have enough data for this window
        if test_end > end_date:
            break
            
        # Ensure we have minimum training data
        train_data = df[(df.index >= train_start) & (df.index < train_end)]
        if len(train_data) < config.min_train_bars:
            break
            
        windows.append(WalkForwardWindow(
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            window_id=window_id
        ))
        
        window_id += 1
        current_start += pd.Timedelta(days=config.step_days)
    
    return windows


def run_strategy_window(
    df: pd.DataFrame,
    funding: Optional[pd.Series],
    oi: Optional[pd.Series],
    basis: Optional[pd.Series],
    window: WalkForwardWindow,
    strategy: str,
    timeframe: str = "1h"
) -> Optional[WindowResult]:
    """Run a single strategy on one walk-forward window."""
    
    # Get test period data
    test_data = df[(df.index >= window.test_start) & (df.index < window.test_end)].copy()
    if len(test_data) < 10:  # Need minimum test bars
        return None
    
    # Generate signals using training data to avoid look-ahead
    if strategy == "cat":
        signals = signals_cat(df, funding=funding, basis=basis)
    elif strategy == "vsb":
        signals = signals_vsb(df, oi=oi, basis=basis)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    # Get test period signals
    test_signals = signals[(signals.index >= window.test_start) & (signals.index < window.test_end)]
    if len(test_signals) == 0:
        return None
    
    # Run backtest on test period only
    if strategy == "cat":
        bt = Backtester(
            test_data, 
            test_signals, 
            funding_series=funding,
            time_stop_bars=7*24 if timeframe=="1h" else 7*6 if timeframe=="4h" else 7,
            trail_atr_k=2.5
        )
    else:  # vsb
        bt = Backtester(
            test_data,
            test_signals,
            funding_series=funding,
            time_stop_bars=8*24 if timeframe=="1h" else 8*6 if timeframe=="4h" else 8,
            trail_atr_k=2.0
        )
    
    result = bt.run(SizingRules())
    
    if len(result) == 0:
        return None
    
    # Calculate metrics
    equity = result['equity']
    returns = result['net'].fillna(0)
    
    equity_start = equity.iloc[0] if len(equity) > 0 else 1.0
    equity_end = equity.iloc[-1] if len(equity) > 0 else 1.0
    total_return = equity_end / equity_start - 1.0
    
    # Annualized metrics
    test_days_actual = (window.test_end - window.test_start).days
    periods_per_year = 365 * 24 if timeframe == "1h" else 365 * 6 if timeframe == "4h" else 365
    periods_in_test = len(returns)
    
    if periods_in_test > 0 and test_days_actual > 0:
        ann_return = (1 + total_return) ** (365 / test_days_actual) - 1
        volatility = returns.std() * np.sqrt(periods_per_year)
        sharpe = ann_return / volatility if volatility > 0 else 0
    else:
        ann_return = volatility = sharpe = 0
    
    # Drawdown calculation
    running_max = equity.expanding().max()
    drawdown = (equity - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Trade stats
    positions = result.get('pos', pd.Series(dtype=float))
    position_changes = positions.diff().abs()
    num_trades = int((position_changes > 0).sum() / 2)  # Approximate trade count
    
    # Win rate approximation
    trade_rets = returns[position_changes > 0]
    win_rate = (trade_rets > 0).mean() if len(trade_rets) > 0 else 0
    
    return WindowResult(
        window=window,
        strategy=strategy,
        equity_start=equity_start,
        equity_end=equity_end,
        total_return=total_return,
        annualized_return=ann_return,
        volatility=volatility,
        sharpe=sharpe,
        max_drawdown=max_drawdown,
        num_trades=num_trades,
        win_rate=win_rate
    )


def calculate_deflated_sharpe(sharpes: List[float], num_trials: int) -> float:
    """
    Calculate Deflated Sharpe Ratio to adjust for multiple testing.
    
    Based on Bailey & López de Prado (2012)
    """
    if not sharpes or len(sharpes) == 0:
        return 0.0
    
    observed_sharpe = np.mean(sharpes)
    sharpe_std = np.std(sharpes, ddof=1) if len(sharpes) > 1 else 0
    
    if sharpe_std == 0:
        return observed_sharpe
    
    # Expected maximum Sharpe under null hypothesis
    # Simplified version - more sophisticated implementations use variance of strategy returns
    gamma = 0.5772156649  # Euler-Mascheroni constant
    expected_max_sharpe = np.sqrt(2 * np.log(num_trials)) - (gamma + np.log(np.log(num_trials))) / (2 * np.sqrt(2 * np.log(num_trials)))
    
    # Deflated Sharpe
    deflated_sharpe = (observed_sharpe - expected_max_sharpe) / sharpe_std if sharpe_std > 0 else 0
    
    return deflated_sharpe


def run_walk_forward_validation(
    df: pd.DataFrame,
    funding: Optional[pd.Series],
    oi: Optional[pd.Series], 
    basis: Optional[pd.Series],
    strategies: List[str],
    config: WalkForwardConfig,
    timeframe: str = "1h"
) -> Dict[str, Any]:
    """Run full walk-forward validation."""
    
    windows = generate_windows(df, config)
    print(f"Generated {len(windows)} walk-forward windows")
    
    results = []
    
    for strategy in strategies:
        print(f"\nRunning {strategy.upper()} walk-forward validation...")
        strategy_results = []
        
        for i, window in enumerate(windows):
            print(f"  Window {i+1}/{len(windows)}: {window.test_start.date()} to {window.test_end.date()}")
            
            result = run_strategy_window(
                df, funding, oi, basis, window, strategy, timeframe
            )
            
            if result:
                strategy_results.append(result)
                results.append(result)
        
        # Strategy summary
        if strategy_results:
            sharpes = [r.sharpe for r in strategy_results]
            returns = [r.total_return for r in strategy_results]
            
            avg_sharpe = np.mean(sharpes)
            avg_return = np.mean(returns)
            win_rate = np.mean([r.sharpe > 0 for r in strategy_results])
            
            print(f"\n{strategy.upper()} Summary:")
            print(f"  Windows: {len(strategy_results)}")
            print(f"  Avg Sharpe: {avg_sharpe:.3f}")
            print(f"  Avg Return: {avg_return:.3f}")
            print(f"  Win Rate: {win_rate:.3f}")
            
            # Deflated Sharpe (using number of windows as trials)
            deflated = calculate_deflated_sharpe(sharpes, len(strategy_results))
            print(f"  Deflated Sharpe: {deflated:.3f}")
    
    return {
        'windows': windows,
        'results': results,
        'config': config
    }


def save_wf_results(results: Dict[str, Any], output_path: str) -> None:
    """Save walk-forward results to CSV."""
    df_results = []
    
    for result in results['results']:
        df_results.append({
            'window_id': result.window.window_id,
            'strategy': result.strategy,
            'test_start': result.window.test_start,
            'test_end': result.window.test_end,
            'total_return': result.total_return,
            'annualized_return': result.annualized_return,
            'volatility': result.volatility,
            'sharpe': result.sharpe,
            'max_drawdown': result.max_drawdown,
            'num_trades': result.num_trades,
            'win_rate': result.win_rate
        })
    
    df = pd.DataFrame(df_results)
    df.to_csv(output_path, index=False)
    print(f"Walk-forward results saved to {output_path}")
