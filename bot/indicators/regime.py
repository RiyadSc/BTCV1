"""
Regime detection indicators for dynamic strategy adaptation.
"""
import pandas as pd
import numpy as np
from bot.indicators.core import ema, atr


def trend_strength(df: pd.DataFrame, lookback: int = 60) -> pd.Series:
    """Measure trend strength using price vs EMA and slope consistency."""
    close_col = "close" if "close" in df.columns else "c"
    close = df[close_col]
    
    # Long-term trend direction
    ema_long = ema(close, lookback)
    
    # Trend strength = how far price is from EMA + slope consistency
    price_deviation = (close - ema_long) / ema_long
    slope = ema_long.diff(lookback//4) / ema_long.shift(lookback//4)
    slope_consistency = slope.rolling(lookback//2).std()
    
    # Strong trend = large deviation + consistent slope
    strength = price_deviation.abs() / (slope_consistency + 0.001)
    return strength.rolling(20).mean().fillna(0)


def volatility_regime(df: pd.DataFrame, lookback: int = 180) -> pd.Series:
    """Detect high/low volatility regimes using percentile ranking."""
    close_col = "close" if "close" in df.columns else "c"
    
    # Use ATR for volatility measure
    vol = atr(df, 14) / df[close_col]
    vol_percentile = vol.rolling(lookback).rank(pct=True)
    
    # Regime: 0=low vol, 1=medium vol, 2=high vol
    regime = pd.Series(1, index=df.index)  # Default medium
    regime[vol_percentile <= 0.3] = 0      # Low vol
    regime[vol_percentile >= 0.7] = 2      # High vol
    
    return regime


def market_regime(df: pd.DataFrame, short_ema: int = 21, long_ema: int = 100) -> pd.Series:
    """Detect bull/bear/sideways regimes."""
    close_col = "close" if "close" in df.columns else "c"
    close = df[close_col]
    
    ema_short = ema(close, short_ema)
    ema_long = ema(close, long_ema)
    
    # Trend direction
    trend_up = ema_short > ema_long
    trend_dn = ema_short < ema_long
    
    # Trend strength (price vs EMAs)
    price_vs_short = (close - ema_short) / ema_short
    price_vs_long = (close - ema_long) / ema_long
    
    # Strong trend thresholds
    strong_threshold = 0.02  # 2%
    
    regime = pd.Series("sideways", index=df.index)
    
    # Bull regime: uptrend + price well above EMAs
    bull_condition = trend_up & (price_vs_short > 0.005) & (price_vs_long > strong_threshold)
    regime[bull_condition] = "bull"
    
    # Bear regime: downtrend + price well below EMAs  
    bear_condition = trend_dn & (price_vs_short < -0.005) & (price_vs_long < -strong_threshold)
    regime[bear_condition] = "bear"
    
    return regime


def funding_sentiment(funding: pd.Series, lookback: int = 168) -> pd.Series:
    """Detect extreme funding sentiment for contrarian signals."""
    if funding is None or len(funding) == 0:
        return pd.Series(0, index=funding.index if funding is not None else [])
    
    # Rolling percentiles of funding rates
    funding_percentile = funding.rolling(lookback).rank(pct=True)
    
    sentiment = pd.Series(0, index=funding.index)  # Neutral
    sentiment[funding_percentile >= 0.9] = 1      # Extreme greed (contrarian bearish)
    sentiment[funding_percentile <= 0.1] = -1     # Extreme fear (contrarian bullish)
    
    return sentiment


def regime_multipliers(
    trend_strength: pd.Series,
    vol_regime: pd.Series, 
    market_regime: pd.Series,
    funding_sentiment: pd.Series
) -> dict:
    """Calculate regime-based multipliers for position sizing and SL/TP."""
    
    # Base multipliers
    size_mult = pd.Series(1.0, index=trend_strength.index)
    sl_mult = pd.Series(1.0, index=trend_strength.index)
    tp_mult = pd.Series(1.0, index=trend_strength.index)
    
    # High trend strength → larger positions, wider stops
    high_trend = trend_strength > trend_strength.quantile(0.7)
    size_mult[high_trend] = 1.5
    sl_mult[high_trend] = 1.2
    tp_mult[high_trend] = 1.3
    
    # Low volatility → larger positions, tighter stops
    low_vol = vol_regime == 0
    size_mult[low_vol] *= 1.3
    sl_mult[low_vol] *= 0.8
    tp_mult[low_vol] *= 0.9
    
    # High volatility → smaller positions, wider stops
    high_vol = vol_regime == 2
    size_mult[high_vol] *= 0.7
    sl_mult[high_vol] *= 1.4
    tp_mult[high_vol] *= 1.2
    
    # Bull regime → bias toward longs, asymmetric TP
    bull = market_regime == "bull"
    tp_mult[bull] *= 1.2
    
    # Bear regime → bias toward shorts, tighter stops
    bear = market_regime == "bear"
    sl_mult[bear] *= 0.9
    
    # Extreme funding → contrarian bias
    extreme_funding = funding_sentiment.abs() == 1
    size_mult[extreme_funding] *= 1.2  # Size up on extreme sentiment
    
    return {
        'size_multiplier': size_mult,
        'sl_multiplier': sl_mult, 
        'tp_multiplier': tp_mult
    }
