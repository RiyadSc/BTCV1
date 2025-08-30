#!/usr/bin/env python3
"""
FGI Trading Signal Bot
Returns trading signals based on Fear & Greed Index analysis
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
import logging
from dataclasses import dataclass
import time
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass  
class TradingSignal:
    """Trading signal with actionable recommendations."""
    action: str  # "BUY", "SELL", "HOLD"
    position_size: float  # Recommended position size (%)
    current_fgi: float
    fgi_classification: str





class FGISignalBot:
    """FGI trading signal bot that returns only the signal and allocation."""
    
    def __init__(self):
        self._last_historical_fetch = 0
        self._historical_cache = None
        self._cache_duration = 86400  # 24 hours
        
    def get_current_fgi(self) -> Tuple[float, str]:
        """Fetch current Fear & Greed Index from alternative.me."""
        try:
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            current_fgi = float(data['data'][0]['value'])
            fgi_classification = data['data'][0]['value_classification'].upper()
            
            logger.info(f"Current FGI: {current_fgi} ({fgi_classification})")
            return current_fgi, fgi_classification
            
        except Exception as e:
            logger.error(f"Failed to fetch FGI data: {e}")
            raise
    
    def get_current_btc_price(self) -> float:
        """Fetch current BTC price from Binance API."""
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'price' in data:
                price = float(data['price'])
                logger.info(f"Current BTC price: ${price:,.2f}")
                return price
            else:
                raise ValueError("Invalid response from Binance")
            
        except Exception as e:
            logger.error(f"Failed to fetch BTC price: {e}")
            raise
    
    def get_historical_prices(self, days: int = 220) -> pd.DataFrame:
        """Get recent BTC price history for technical analysis."""
        if not self._should_fetch_historical() and self._historical_cache is not None:
            if len(self._historical_cache) >= days:
                logger.info("Using cached historical price data.")
                return self._historical_cache.tail(days)

        try:
            url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit={days + 5}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            df = pd.DataFrame(data, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
            
            df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close'] = df['close'].astype(float)
            df.set_index('timestamp', inplace=True)
            
            df = df.tail(days)
            
            logger.info(f"Fetched {len(df)} days of historical data")
            self._historical_cache = df[['close']]
            self._last_historical_fetch = time.time()
            return df[['close']]
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            raise
    
    def _should_fetch_historical(self) -> bool:
        """Check if we should fetch new historical data based on cache duration."""
        current_time = time.time()
        return current_time - self._last_historical_fetch > self._cache_duration
    
    def calculate_market_regime(self, price_data: pd.DataFrame, current_price: float) -> str:
        """Calculate market regime (bull/bear) based on 200-day moving average."""
        try:
            if len(price_data) < 200:
                return "BEAR"  # Default to bear if insufficient data
            
            price_data = price_data.copy()
            price_data.loc[datetime.now()] = current_price
            price_data = price_data.sort_index()
            
            ma_200 = price_data['close'].rolling(200, min_periods=1).mean().iloc[-1]
            
            return "BULL" if current_price >= ma_200 else "BEAR"
            
        except Exception as e:
            logger.error(f"Error calculating market regime: {e}")
            return "BEAR"
    
    def generate_signal(self, btc_exposure: float = 0.0, portfolio_dd: float = 0.0) -> TradingSignal:
        """Generate trading signal based on current market conditions."""
        try:
            # Get current data
            fgi_value, fgi_classification = self.get_current_fgi()
            current_price = self.get_current_btc_price()
            
            # Get market regime
            price_history = self.get_historical_prices(days=220)
            regime = self.calculate_market_regime(price_history, current_price)
            
            # Determine action and position size based on FGI and regime
            action, position_size = self._calculate_signal(fgi_value, regime, btc_exposure, portfolio_dd)
            
            return TradingSignal(
                action=action,
                position_size=position_size,
                current_fgi=fgi_value,
                fgi_classification=fgi_classification
            )
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return TradingSignal(
                action="HOLD",
                position_size=0.0,
                current_fgi=50.0,
                fgi_classification="NEUTRAL"
            )
    
    def _calculate_signal(self, fgi_value: float, regime: str, btc_exposure: float, portfolio_dd: float) -> Tuple[str, float]:
        """Calculate trading signal based on FGI thresholds and market regime."""
        # Buy signals
        if fgi_value <= 15:  # Ultra Fear
            if btc_exposure < 0.80:  # Check max exposure
                return "BUY", 0.15  # Buy 15% of equity
        elif fgi_value <= 25:  # Fear
            if btc_exposure < 0.80:  # Check max exposure
                return "BUY", 0.10  # Buy 10% of equity
        elif fgi_value <= 35:  # Light Fear
            if btc_exposure < 0.80:  # Check max exposure
                return "BUY", 0.05  # Buy 5% of equity
        
        # Sell signals
        if fgi_value >= 85:  # Ultra Greed
            if btc_exposure > 0:  # Check if we have position to sell
                return "SELL", 0.20  # Sell 20% of position
        elif fgi_value >= 75:  # Greed
            if btc_exposure > 0:  # Check if we have position to sell
                return "SELL", 0.15  # Sell 15% of position
        
        # Portfolio protection
        if portfolio_dd < -0.30 and btc_exposure > 0:
            return "SELL", 0.20  # Sell 20% for protection
        
        # No clear signal
        return "HOLD", 0.0


def format_signal_output(signal: TradingSignal) -> str:
    """Format trading signal for user display."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    action_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
    
    output = f"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                                🤖 FGI TRADING SIGNAL BOT 🤖                           ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

📅 Timestamp: {timestamp}

{action_emoji[signal.action]} ACTION: {signal.action}
📊 Position Size: {signal.position_size:.1%} of portfolio

📈 MARKET DATA:
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ 😱 Fear & Greed: {signal.current_fgi:.0f}/100 ({signal.fgi_classification})                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘
"""

    if signal.action == "BUY":
        output += f"""
🎯 RECOMMENDED ACTION:
• BUY Bitcoin with {signal.position_size:.1%} of your portfolio
• Current Fear & Greed Index suggests market fear - good buying opportunity
"""
    elif signal.action == "SELL":
        output += f"""
🎯 RECOMMENDED ACTION:
• SELL {signal.position_size:.1%} of your Bitcoin holdings
• Current Fear & Greed Index suggests market greed - good selling opportunity
"""
    else:
        output += f"""
🎯 RECOMMENDED ACTION:
• HOLD your current positions
• Market conditions don't present a clear trading opportunity
• Wait for more extreme Fear & Greed levels
"""

    output += f"""
⚠️  RISK WARNING:
• This is algorithmic analysis - not financial advice
• Always do your own research and risk management
• Never invest more than you can afford to lose
• Consider your personal financial situation

═══════════════════════════════════════════════════════════════════════════════════════
"""
    
    return output


def main():
    """Main function to run the signal bot."""
    print("🤖 FGI Trading Signal Bot Starting...")
    
    try:
        # Initialize bot
        bot = FGISignalBot()
        
        # Get user's current position (optional)
        print("\n📊 Optional: Enter your current portfolio details for better analysis")
        try:
            btc_exposure_input = input("Current BTC exposure (0-100%, press Enter for 0%): ").strip()
            btc_exposure = float(btc_exposure_input) / 100 if btc_exposure_input else 0.0
        except ValueError:
            btc_exposure = 0.0
        
        try:
            portfolio_dd_input = input("Current portfolio drawdown (%, press Enter for 0%): ").strip()
            portfolio_dd = -abs(float(portfolio_dd_input)) / 100 if portfolio_dd_input else 0.0
        except ValueError:
            portfolio_dd = 0.0
        
        # Generate signal
        print("\n🔍 Analyzing market conditions...")
        signal = bot.generate_signal(btc_exposure, portfolio_dd)
        
        # Display results
        print(format_signal_output(signal))
        
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"\n❌ Error: {e}")
        print("Please check your internet connection and try again.")


if __name__ == "__main__":
    main()
