#!/usr/bin/env python3
"""
Fetch historical BTC price data to extend our dataset back to 2018
"""
import sys
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from bot.data.native.coinbase import klines_paginated
from bot.utils.io import write_parquet


def fetch_coinbase_historical(symbol: str = "BTC-USD", start_date: str = "2018-02-01") -> pd.DataFrame:
    """Fetch historical data from Coinbase going back to start_date."""
    
    # Convert start_date to milliseconds
    start_dt = pd.to_datetime(start_date, utc=True)
    start_ms = int(start_dt.timestamp() * 1000)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Fetching {symbol} data from {start_date}...")
    
    try:
        # Use the existing klines_paginated function for daily data
        df = klines_paginated(symbol, "1d", start_ms)
        
        if df.empty:
            logger.error("No data returned from Coinbase")
            return df
            
        logger.info(f"Fetched {len(df)} records from {df.index.min()} to {df.index.max()}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching from Coinbase: {e}")
        return pd.DataFrame()


def fetch_binance_historical(symbol: str = "BTCUSD", start_date: str = "2018-02-01") -> pd.DataFrame:
    """Fetch historical data from Binance as backup."""
    
    start_dt = pd.to_datetime(start_date, utc=True)
    start_ms = int(start_dt.timestamp() * 1000)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Fetching {symbol} data from Binance...")
    
    base_url = "https://api.binance.com/api/v3/klines"
    
    all_data = []
    current_start = start_ms
    
    while True:
        params = {
            'symbol': symbol,
            'interval': '1d',
            'startTime': current_start,
            'limit': 1000  # Max limit
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            all_data.extend(data)
            
            # Update start time for next batch
            last_timestamp = data[-1][0]
            current_start = last_timestamp + 86400000  # +1 day in ms
            
            # Check if we've reached current time
            if current_start > int(time.time() * 1000):
                break
                
            # Rate limiting
            time.sleep(0.1)
            
            logger.info(f"Fetched batch ending at {pd.to_datetime(last_timestamp, unit='ms', utc=True)}")
            
        except Exception as e:
            logger.error(f"Error fetching from Binance: {e}")
            break
    
    if not all_data:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'count', 'taker_buy_volume', 
        'taker_buy_quote_volume', 'ignore'
    ])
    
    # Convert timestamp and set as index
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df = df.set_index('timestamp').sort_index()
    
    # Keep only OHLCV columns and rename to match existing format
    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    df = df.rename(columns={'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v'})
    
    logger.info(f"Processed {len(df)} records from {df.index.min()} to {df.index.max()}")
    return df


def combine_and_save_data(historical_df: pd.DataFrame, existing_path: str = "storage/spot_1d.parquet") -> None:
    """Combine historical data with existing data and save."""
    
    logger = logging.getLogger(__name__)
    
    # Load existing data
    try:
        existing_df = pd.read_parquet(existing_path)
        logger.info(f"Loaded existing data: {len(existing_df)} records from {existing_df.index.min()} to {existing_df.index.max()}")
    except FileNotFoundError:
        logger.warning(f"No existing data found at {existing_path}")
        existing_df = pd.DataFrame()
    
    if existing_df.empty:
        combined_df = historical_df
    else:
        # Combine datasets, remove duplicates, sort by date
        combined_df = pd.concat([historical_df, existing_df])
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        combined_df = combined_df.sort_index()
    
    # Save combined data
    backup_path = existing_path.replace('.parquet', '_backup.parquet')
    if Path(existing_path).exists():
        # Create backup
        existing_df.to_parquet(backup_path)
        logger.info(f"Created backup at {backup_path}")
    
    write_parquet(combined_df, existing_path)
    
    logger.info(f"Saved combined data: {len(combined_df)} records from {combined_df.index.min()} to {combined_df.index.max()}")
    
    return combined_df


def main():
    """Fetch missing historical BTC data."""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=== Fetching Historical BTC Data ===")
    
    # Try Coinbase first (matches existing data source)
    logger.info("Attempting to fetch from Coinbase...")
    historical_df = fetch_coinbase_historical("BTC-USD", "2018-02-01")
    
    if historical_df.empty:
        logger.info("Coinbase failed, trying Binance...")
        historical_df = fetch_binance_historical("BTCUSDT", "2018-02-01")
    
    if historical_df.empty:
        logger.error("Failed to fetch historical data from all sources")
        return
    
    # Combine and save
    logger.info("Combining with existing data...")
    combined_df = combine_and_save_data(historical_df)
    
    print(f"\n=== SUCCESS ===")
    print(f"Extended BTC dataset: {len(combined_df)} records")
    print(f"Date range: {combined_df.index.min()} to {combined_df.index.max()}")
    print(f"Price range: ${combined_df['c'].min():,.2f} to ${combined_df['c'].max():,.2f}")
    
    # Verify we now have data for FGI period
    fgi_df = pd.read_parquet('fgi_strategy/data/fgi_historical_real.parquet')
    fgi_start = fgi_df.index.min()
    
    if combined_df.index.min() <= fgi_start:
        overlap_days = len(combined_df[combined_df.index >= fgi_start])
        print(f"Overlap with FGI data: {overlap_days} days")
        print("✅ Ready for complete historical backtest!")
    else:
        missing_days = (combined_df.index.min() - fgi_start).days
        print(f"⚠️  Still missing {missing_days} days of overlap")


if __name__ == "__main__":
    main()
