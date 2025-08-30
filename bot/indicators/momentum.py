"""
Momentum confirmation indicators.
"""
import pandas as pd
import numpy as np
from bot.indicators.core import ema


def momentum_score(df: pd.DataFrame, short: int = 12, long: int = 26) -> pd.Series:
    """Calculate momentum score using multiple timeframes."""
    close_col = "close" if "close" in df.columns else "c"
    close = df[close_col]
    
    # Price momentum (rate of change)
    roc_fast = close.pct_change(short)
    roc_slow = close.pct_change(long)
    
    # EMA momentum
    ema_short = ema(close, short)
    ema_long = ema(close, long)
    ema_momentum = (ema_short - ema_long) / ema_long
    
    # Volume-weighted momentum (if volume available)
    vol_col = "volume" if "volume" in df.columns else "v"
    if vol_col in df.columns and not df[vol_col].isna().all():
        volume = df[vol_col]
        vwap = (close * volume).rolling(short).sum() / volume.rolling(short).sum()
        vwap_momentum = (close - vwap) / vwap
    else:
        vwap_momentum = pd.Series(0, index=close.index)
    
    # Combine momentum signals
    momentum = (roc_fast + roc_slow + ema_momentum + vwap_momentum) / 4
    
    # Smooth and normalize
    momentum_smoothed = momentum.rolling(5).mean()
    return momentum_smoothed.fillna(0)


def volume_confirmation(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Volume confirmation - higher volume on breakouts."""
    vol_col = "volume" if "volume" in df.columns else "v"
    if vol_col not in df.columns or df[vol_col].isna().all():
        return pd.Series(1, index=df.index)  # Default to confirmed if no volume data
    
    volume = df[vol_col]
    vol_ma = volume.rolling(lookback).mean()
    vol_ratio = volume / vol_ma
    
    # Strong volume = above 1.5x average
    vol_confirmed = vol_ratio >= 1.5
    return vol_confirmed.astype(float)


def rsi_divergence(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Detect RSI divergence for momentum confirmation."""
    close_col = "close" if "close" in df.columns else "c"
    close = df[close_col]
    
    # Calculate RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Look for bullish divergence: price lower low, RSI higher low
    price_lows = close.rolling(period).min()
    rsi_lows = rsi.rolling(period).min()
    
    price_lower_low = (close <= price_lows.shift(1)) & (close.shift(period) > price_lows.shift(1))
    rsi_higher_low = (rsi >= rsi_lows.shift(1)) & (rsi.shift(period) < rsi_lows.shift(1))
    
    bullish_div = price_lower_low & rsi_higher_low
    
    # Look for bearish divergence: price higher high, RSI lower high
    price_highs = close.rolling(period).max()
    rsi_highs = rsi.rolling(period).max()
    
    price_higher_high = (close >= price_highs.shift(1)) & (close.shift(period) < price_highs.shift(1))
    rsi_lower_high = (rsi <= rsi_highs.shift(1)) & (rsi.shift(period) > rsi_highs.shift(1))
    
    bearish_div = price_higher_high & rsi_lower_high
    
    # Return divergence signal: +1 bullish, -1 bearish, 0 none
    div_signal = pd.Series(0, index=close.index)
    div_signal[bullish_div] = 1
    div_signal[bearish_div] = -1
    
    return div_signal


def microstructure_filter(df: pd.DataFrame) -> pd.Series:
    """Simple microstructure filter based on recent price action."""
    close_col = "close" if "close" in df.columns else "c"
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"
    
    close = df[close_col]
    high = df[high_col]
    low = df[low_col]
    
    # Recent strength: close near high of recent bars
    recent_high = high.rolling(3).max()
    recent_low = low.rolling(3).min()
    close_position = (close - recent_low) / (recent_high - recent_low + 1e-8)
    
    # Strong = close in top 20% of recent range
    strength = close_position >= 0.8
    weakness = close_position <= 0.2
    
    # Return strength signal: +1 strong, -1 weak, 0 neutral
    signal = pd.Series(0, index=close.index)
    signal[strength] = 1
    signal[weakness] = -1
    
    return signal


def confluence_score(df: pd.DataFrame, funding: pd.Series = None) -> pd.Series:
    """Calculate confluence score combining multiple momentum indicators."""
    
    momentum = momentum_score(df)
    vol_conf = volume_confirmation(df)
    rsi_div = rsi_divergence(df)
    micro = microstructure_filter(df)
    
    # Normalize momentum to -1, +1 range
    momentum_norm = np.tanh(momentum * 10)  # Scale and bound
    
    # Combine signals with weights
    confluence = (
        momentum_norm * 0.4 +      # Main momentum
        vol_conf * 0.2 +           # Volume confirmation
        rsi_div * 0.2 +            # Divergence
        micro * 0.2                # Microstructure
    )
    
    # Add funding sentiment if available
    if funding is not None and len(funding) > 0:
        funding_norm = np.tanh(funding * 1000)  # Normalize funding rates
        confluence += funding_norm * 0.1
    
    return confluence
