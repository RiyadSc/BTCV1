#!/usr/bin/env python3
"""
Fear and Greed Index Strategy Backtest Runner
"""
import sys
import logging
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from fgi_strategy.backtest_engine import run_fgi_backtest, FGIConfig
from fgi_strategy.reporter import generate_full_report


def load_btc_daily_data(storage_path: str = "storage/spot_1d.parquet") -> pd.DataFrame:
    """Load daily BTC price data."""
    try:
        df = pd.read_parquet(storage_path)
        logging.info(f"Loaded BTC daily data: {len(df)} records from {df.index[0]} to {df.index[-1]}")
        return df
    except FileNotFoundError:
        logging.error(f"BTC data file not found: {storage_path}")
        raise
    except Exception as e:
        logging.error(f"Error loading BTC data: {e}")
        raise


def main():
    """Run the complete FGI strategy backtest."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/fgi_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=== Starting Fear and Greed Index Strategy Backtest ===")
    
    try:
        # 1. Load BTC daily price data
        logger.info("Loading BTC daily price data...")
        btc_data = load_btc_daily_data()
        
        # 2. Load FGI data from cached parquet
        logger.info("Loading Fear and Greed Index data from parquet...")
        fgi_parquet = Path("fgi_strategy/data/fgi_historical_real.parquet")
        if not fgi_parquet.exists():
            # fallback to historical parquet if real not present
            fgi_parquet = Path("fgi_strategy/data/fgi_historical.parquet")
        fgi_data = pd.read_parquet(fgi_parquet)
        
        if fgi_data.empty:
            logger.error("No FGI data available")
            return
        
        # 3. Configure strategy
        config = FGIConfig(
            entry_threshold=20.0,      # Enter when FGI <= 20
            exit_threshold=80.0,       # Exit when FGI >= 80
            position_size_pct=0.10,    # 10% of equity per trade (daily)
            entry_interval_days=1,     # Enter every day while FGI <= 20
            exit_interval_days=1,      # Exit every day while FGI >= 80
            initial_capital=1000.0,    # $1k starting capital
            transaction_cost_pct=0.001 # 0.1% transaction costs
        )
        
        logger.info(f"Strategy config: Entry≤{config.entry_threshold}, Exit≥{config.exit_threshold}, "
                   f"Position Size: {config.position_size_pct:.0%}, Intervals: {config.entry_interval_days}d, "
                   f"Starting Capital: ${config.initial_capital:,.0f}")
        logger.info(f"Loaded FGI data: {len(fgi_data)} records from {fgi_data.index.min()} to {fgi_data.index.max()}")
        
        # 4. Run backtest
        logger.info("Running backtest...")
        results = run_fgi_backtest(btc_data, fgi_data, config)
        
        if not results:
            logger.error("Backtest failed - no results")
            return
        
        # 5. Generate reports
        output_dir = f"out/fgi_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Generating reports in {output_dir}...")
        
        generate_full_report(
            results=results,
            output_dir=output_dir,
            show_plots=True
        )
        
        # 5b. Export trades (including realized PnL flags)
        trades = results.get('trades')
        if trades is not None and not trades.empty:
            trades_csv = Path(output_dir) / 'trades.csv'
            trades.to_csv(trades_csv)
            logger.info(f"Exported trades to {trades_csv}")
        
        # 6. Print key results
        print("\n" + "="*60)
        print("FGI STRATEGY BACKTEST COMPLETED")
        print("="*60)
        print(f"Total Return: {results['total_return']:.2%}")
        print(f"Buy & Hold Return: {results['buy_hold_return']:.2%}")
        print(f"Excess Return: {results['excess_return']:.2%}")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.2%}")
        print(f"Number of Trades: {results['num_trades']}")
        print(f"Win Rate: {results['win_rate']:.1%}")
        if trades is not None and not trades.empty:
            num_buy = len(trades[trades['type']=='BUY'])
            num_sell = len(trades[trades['type']=='SELL'])
            num_sell_wins = int(trades[(trades['type']=='SELL') & (trades.get('win', False))].shape[0]) if 'win' in trades.columns else 'n/a'
            print(f"BUY trades: {num_buy}, SELL trades: {num_sell}, SELL winners: {num_sell_wins}")
        print(f"\nReports saved to: {output_dir}")
        print("="*60)
        
        logger.info("Backtest completed successfully")
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
