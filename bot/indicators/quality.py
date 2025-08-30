"""
High-quality entry filters to reduce SL rate.
"""
import pandas as pd
import numpy as np
from bot.indicators.core import ema, atr


def volume_breakout_confirmation(df: pd.DataFrame, volume_multiplier: float = 2.0, lookback: int = 20) -> pd.Series:
    """Confirm breakouts with above-average volume."""
    vol_col = "volume" if "volume" in df.columns else "v"
    if vol_col not in df.columns or df[vol_col].isna().all():
        return pd.Series(True, index=df.index)  # Default to confirmed if no volume
    
    volume = df[vol_col]
    vol_ma = volume.rolling(lookback).mean()
    volume_confirmed = volume >= (vol_ma * volume_multiplier)
    
    return volume_confirmed


def multi_timeframe_alignment(df: pd.DataFrame, fast: int = 21, slow: int = 50) -> pd.Series:
    """Check if multiple timeframes are aligned."""
    close_col = "close" if "close" in df.columns else "c"
    close = df[close_col]
    
    # Current timeframe trend
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    trend_1tf = ema_fast > ema_slow
    
    # Higher timeframe trend (4x resolution)
    close_4tf = close.resample('4h').last().dropna()
    ema_fast_4tf = ema(close_4tf, max(1, fast//4))
    ema_slow_4tf = ema(close_4tf, max(1, slow//4))
    trend_4tf = (ema_fast_4tf > ema_slow_4tf).reindex(df.index, method='ffill').fillna(False)
    
    # Even higher timeframe (daily)
    close_1d = close.resample('1D').last().dropna()
    ema_fast_1d = ema(close_1d, max(1, fast//6))  # More reasonable for daily
    ema_slow_1d = ema(close_1d, max(1, slow//6))
    trend_1d = (ema_fast_1d > ema_slow_1d).reindex(df.index, method='ffill').fillna(False)
    
    # All timeframes must align
    bullish_alignment = trend_1tf & trend_4tf & trend_1d
    bearish_alignment = (~trend_1tf) & (~trend_4tf) & (~trend_1d)
    
    # Return: +1 bullish aligned, -1 bearish aligned, 0 mixed
    alignment = pd.Series(0, index=df.index)
    alignment[bullish_alignment] = 1
    alignment[bearish_alignment] = -1
    
    return alignment


def rsi_filter(df: pd.DataFrame, period: int = 14, overbought: float = 70, oversold: float = 30) -> pd.Series:
    """Filter out overbought/oversold conditions."""
    close_col = "close" if "close" in df.columns else "c"
    close = df[close_col]
    
    # Calculate RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Allow trades only in middle range
    rsi_ok = (rsi > oversold) & (rsi < overbought)
    
    return rsi_ok


def volatility_expansion(df: pd.DataFrame, atr_period: int = 14, expansion_threshold: float = 1.2) -> pd.Series:
    """Detect recent volatility expansion."""
    current_atr = atr(df, atr_period)
    atr_ma = current_atr.rolling(atr_period * 2).mean()
    
    # ATR should be expanding (recent volatility pickup)
    atr_expanding = current_atr >= (atr_ma * expansion_threshold)
    
    return atr_expanding


def momentum_persistence(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    """Check if momentum has persisted over recent bars."""
    close_col = "close" if "close" in df.columns else "c"
    close = df[close_col]
    
    # Price direction consistency
    returns = close.pct_change()
    
    # For longs: require majority of recent returns to be positive
    recent_returns = returns.rolling(lookback)
    positive_ratio = (recent_returns.apply(lambda x: (x > 0).sum()) / lookback)
    
    # Strong momentum = 60%+ of recent moves in same direction
    momentum_up = positive_ratio >= 0.6
    momentum_dn = positive_ratio <= 0.4
    
    # Return: +1 up momentum, -1 down momentum, 0 mixed
    momentum = pd.Series(0, index=df.index)
    momentum[momentum_up] = 1
    momentum[momentum_dn] = -1
    
    return momentum


def support_resistance_filter(df: pd.DataFrame, lookback: int = 50) -> pd.Series:
    """Avoid entries near obvious support/resistance levels."""
    close_col = "close" if "close" in df.columns else "c"
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"
    
    close = df[close_col]
    high = df[high_col]
    low = df[low_col]
    
    # Recent highs and lows
    recent_high = high.rolling(lookback).max()
    recent_low = low.rolling(lookback).min()
    
    # Distance from S/R levels
    dist_from_high = (recent_high - close) / close
    dist_from_low = (close - recent_low) / close
    
    # Avoid trades too close to S/R (within 1% of recent extremes)
    too_close_to_resistance = dist_from_high < 0.01
    too_close_to_support = dist_from_low < 0.01
    
    # Clear of S/R levels
    clear_levels = ~(too_close_to_resistance | too_close_to_support)
    
    return clear_levels


def entry_quality_score(
    df: pd.DataFrame,
    funding: pd.Series = None,
    volume_mult: float = 2.0,
    require_mtf_alignment: bool = True,
    require_rsi_filter: bool = True,
    require_vol_expansion: bool = True,
) -> pd.Series:
    """
    Calculate overall entry quality score (0-1).
    
    Higher score = higher quality entry = lower SL probability.
    """
    
    # Individual filters
    vol_conf = volume_breakout_confirmation(df, volume_mult).astype(float)
    mtf_align = multi_timeframe_alignment(df)
    rsi_ok = rsi_filter(df).astype(float) if require_rsi_filter else pd.Series(1.0, index=df.index)
    vol_exp = volatility_expansion(df).astype(float) if require_vol_expansion else pd.Series(1.0, index=df.index)
    momentum = momentum_persistence(df)
    sr_clear = support_resistance_filter(df).astype(float)
    
    # Confluence score
    base_score = (vol_conf * 0.2 + rsi_ok * 0.2 + vol_exp * 0.2 + sr_clear * 0.2)
    
    # MTF alignment bonus/penalty
    if require_mtf_alignment:
        mtf_bonus = mtf_align * 0.2  # +20% for alignment, -20% for misalignment
        base_score += mtf_bonus
    
    # Momentum persistence bonus
    momentum_bonus = momentum * 0.1  # +10% for persistent momentum
    base_score += momentum_bonus
    
    # Bound score to [0, 1]
    quality_score = np.clip(base_score, 0, 1)
    
    return quality_score


def high_quality_filter(
    df: pd.DataFrame,
    signal: pd.Series,
    funding: pd.Series = None,
    min_quality_threshold: float = 0.6,
) -> pd.Series:
    """
    Filter signals to only allow high-quality entries.
    
    This should significantly reduce SL rate by being more selective.
    """
    
    quality = entry_quality_score(df, funding)
    
    # Only allow entries above quality threshold
    high_quality_long = (signal == 1) & (quality >= min_quality_threshold)
    high_quality_short = (signal == -1) & (quality >= min_quality_threshold)
    
    filtered_signal = pd.Series(0, index=df.index, dtype="int8")
    filtered_signal[high_quality_long] = 1
    filtered_signal[high_quality_short] = -1
    
    return filtered_signal
