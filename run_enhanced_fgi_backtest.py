#!/usr/bin/env python3
"""
Enhanced FGI Strategy Backtest Runner
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fgi_strategy.enhanced_backtest_engine import EnhancedFGIBacktester, EnhancedFGIConfig
from fgi_strategy.data_fetcher import fetch_and_cache_fgi_data
from fgi_strategy.enhanced_reporter import generate_enhanced_fgi_report
from utils import ensure_dir
import pandas as pd
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_btc_daily_data() -> pd.DataFrame:
    """Load BTC daily OHLCV data."""
    try:
        # Try to load from storage
        btc_data = pd.read_parquet("storage/spot_1d.parquet")
        if not btc_data.empty:
            logger.info(f"Loaded BTC data: {len(btc_data)} records from {btc_data.index[0]} to {btc_data.index[-1]}")
            return btc_data
    except Exception as e:
        logger.warning(f"Could not load BTC data from storage: {e}")
    
    # Fallback: create minimal data for testing
    logger.warning("Creating minimal BTC data for testing")
    dates = pd.date_range('2018-01-01', '2025-08-18', freq='D')
    btc_data = pd.DataFrame({
        'open': [1000] * len(dates),
        'high': [1100] * len(dates),
        'low': [900] * len(dates),
        'close': [1050] * len(dates),
        'volume': [1000000] * len(dates)
    }, index=dates)
    
    return btc_data

def main():
    """Run enhanced FGI strategy backtest."""
    logger.info("Starting Enhanced FGI Strategy Backtest")
    
    # Load data
    logger.info("Loading BTC price data...")
    btc_data = load_btc_daily_data()
    
    logger.info("Fetching FGI data...")
    fgi_data = fetch_and_cache_fgi_data(
        cache_path="fgi_strategy/data/fgi_historical_real.parquet",
        api_key=None,  # Using free alternative.me API
        force_refresh=True  # Force fresh real data
    )
    
    # Fix timezone issues - make both timezone-naive
    if btc_data.index.tz is not None:
        btc_data.index = btc_data.index.tz_localize(None)
    if fgi_data.index.tz is not None:
        fgi_data.index = fgi_data.index.tz_localize(None)
    
    # Merge data
    logger.info("Merging BTC and FGI data...")
    merged_data = btc_data.merge(fgi_data, left_index=True, right_index=True, how='inner')
    merged_data = merged_data.sort_index()
    
    logger.info(f"Merged data: {len(merged_data)} records from {merged_data.index[0]} to {merged_data.index[-1]}")
    
    # Configure enhanced strategy using the proper config class
    config = EnhancedFGIConfig(
        ultra_fear_threshold=15.0,      # Ultra fear - 15% allocation
        fear_threshold=25.0,            # Fear zone - 10% allocation
        greed_threshold=75.0,           # Greed zone - 10% sell
        ultra_greed_threshold=85.0,     # Ultra greed - 15% sell
        ultra_fear_size=0.15,           # 15% on ultra fear
        fear_size=0.10,                 # 10% on fear
        light_fear_size=0.05,           # 5% on light fear
        greed_sell_size=0.10,           # 10% sell on greed
        ultra_greed_sell_size=0.15,     # 15% sell on ultra greed
        max_btc_exposure=0.80,          # Max 80% in BTC
        min_cash_reserve=0.20,          # Min 20% cash
        drawdown_threshold=0.50,        # Reduce size if >50% DD
        volatility_lookback=30,         # Days for volatility calc
        momentum_lookback=30,           # Days for momentum
        min_momentum_buy=-0.30,         # Don't buy if momentum < -30%
        recovery_momentum=-0.15,        # Enhanced buy if recovering
        trend_confirmation=7,           # Days for trend confirmation
        initial_capital=1000.0,         # $1k starting capital
        transaction_cost_pct=0.001,     # 0.1% transaction costs
        fgi_smoothing_days=3            # 3-day FGI smoothing
    )
    
    # Run enhanced backtest
    logger.info("Running enhanced backtest...")
    engine = EnhancedFGIBacktester(config)
    results = engine.run_backtest(btc_data, fgi_data)
    
    # Generate enhanced report
    logger.info("Generating enhanced report...")
    output_dir = f"out/enhanced_fgi_strategy_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    ensure_dir(output_dir)
    
    # Prepare results for enhanced reporter
    enhanced_results = {
        'initial_equity': results['initial_equity'],
        'final_equity': results['final_equity'],
        'total_return': results['total_return'],
        'annual_return': results['annual_return'],
        'buy_hold_return': results['buy_hold_return'],
        'excess_return': results['excess_return'],
        'volatility': results['volatility'],
        'sharpe_ratio': results['sharpe_ratio'],
        'max_drawdown': results['max_drawdown'],
        'win_rate': results['win_rate'],
        'num_trades': results['num_trades'],
        'final_position_shares': results['final_position_shares'],
        'final_cash': results['final_cash'],
        'equity_curve': results['equity_curve'],
        'trades': results['trades']
    }
    
    generate_enhanced_fgi_report(enhanced_results, output_dir)
    
    # Also save CSV files
    results['trades'].to_csv(f"{output_dir}/trades.csv")
    results['equity_curve'].to_csv(f"{output_dir}/equity_curve.csv")
    
    logger.info(f"Enhanced backtest completed. Results saved to: {output_dir}")
    logger.info(f"Total Return: {results['total_return']:.2%}")
    logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    logger.info(f"Max Drawdown: {results['max_drawdown']:.2%}")
    logger.info(f"Total Trades: {results['num_trades']}")

if __name__ == "__main__":
    main()
