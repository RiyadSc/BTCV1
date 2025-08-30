"""
Kelly criterion and adaptive position sizing.
"""
import pandas as pd
import numpy as np


def estimate_win_probability(
    quality_score: pd.Series,
    baseline_win_rate: float = 0.45,
    quality_sensitivity: float = 0.3
) -> pd.Series:
    """
    Estimate win probability based on entry quality.
    
    Higher quality entries should have higher win rates.
    """
    
    # Linear relationship: quality 0 = baseline - sensitivity, quality 1 = baseline + sensitivity
    win_prob = baseline_win_rate + (quality_score - 0.5) * quality_sensitivity
    
    # Bound probabilities to reasonable range [0.2, 0.8]
    win_prob = np.clip(win_prob, 0.2, 0.8)
    
    return win_prob


def kelly_fraction(
    win_probability: pd.Series,
    avg_win: float = 0.04,  # 4% average win
    avg_loss: float = 0.02,  # 2% average loss  
    max_kelly: float = 0.25  # Cap at 25% of capital
) -> pd.Series:
    """
    Calculate Kelly fraction for position sizing.
    
    Kelly = (bp - q) / b
    where:
    - b = ratio of win amount to loss amount (avg_win / avg_loss)
    - p = win probability
    - q = loss probability (1 - p)
    """
    
    b = avg_win / avg_loss  # Win/loss ratio
    p = win_probability
    q = 1 - p
    
    kelly = (b * p - q) / b
    
    # Apply safety margin (use 25% of full Kelly) and cap
    safe_kelly = kelly * 0.25
    safe_kelly = np.clip(safe_kelly, 0.005, max_kelly)  # Min 0.5%, max 25%
    
    return safe_kelly


def adaptive_stop_loss(
    entry_price: float,
    current_price: float,
    atr_value: float,
    position_direction: int,  # 1 for long, -1 for short
    initial_sl_atr: float = 1.5,
    trail_trigger_atr: float = 2.0,
    trail_distance_atr: float = 1.0,
) -> float:
    """
    Calculate adaptive stop loss that trails after initial profit.
    
    Logic:
    1. Start with initial SL at entry ± initial_sl_atr * ATR
    2. Once profit reaches trail_trigger_atr * ATR, start trailing
    3. Trail at trail_distance_atr * ATR behind highest/lowest price
    """
    
    if position_direction == 1:  # Long position
        initial_sl = entry_price - (initial_sl_atr * atr_value)
        profit = current_price - entry_price
        
        if profit >= (trail_trigger_atr * atr_value):
            # Start trailing: SL = current_price - trail_distance * ATR
            trailing_sl = current_price - (trail_distance_atr * atr_value)
            return max(initial_sl, trailing_sl)
        else:
            return initial_sl
            
    else:  # Short position
        initial_sl = entry_price + (initial_sl_atr * atr_value)
        profit = entry_price - current_price
        
        if profit >= (trail_trigger_atr * atr_value):
            # Start trailing: SL = current_price + trail_distance * ATR
            trailing_sl = current_price + (trail_distance_atr * atr_value)
            return min(initial_sl, trailing_sl)
        else:
            return initial_sl


def adaptive_take_profit(
    entry_price: float,
    current_price: float,
    atr_value: float,
    position_direction: int,
    quality_score: float,
    base_tp_atr: float = 4.0,
    quality_multiplier: float = 2.0,
) -> float:
    """
    Calculate adaptive take profit based on entry quality.
    
    Higher quality entries get wider profit targets.
    """
    
    # Adjust TP based on quality: low quality = tighter TP, high quality = wider TP
    tp_multiplier = 1.0 + (quality_score - 0.5) * quality_multiplier
    adjusted_tp_atr = base_tp_atr * tp_multiplier
    
    if position_direction == 1:  # Long position
        tp_price = entry_price + (adjusted_tp_atr * atr_value)
    else:  # Short position
        tp_price = entry_price - (adjusted_tp_atr * atr_value)
    
    return tp_price


def regime_leverage_multiplier(
    market_regime: str,  # 'bull', 'bear', 'sideways'
    volatility_regime: int,  # 0=low, 1=medium, 2=high
    trend_strength: float,  # 0-1 scale
    base_leverage: float = 5.0,
    max_leverage: float = 10.0,
) -> float:
    """
    Calculate regime-based leverage multiplier.
    
    Higher leverage in:
    - Strong trending markets
    - Low volatility periods
    - Clear bull/bear regimes
    """
    
    leverage = base_leverage
    
    # Regime adjustments
    if market_regime == "bull":
        leverage *= 1.2
    elif market_regime == "bear":
        leverage *= 1.1  # Slightly more conservative in bear
    else:  # sideways
        leverage *= 0.8
    
    # Volatility adjustments
    if volatility_regime == 0:  # Low vol
        leverage *= 1.3
    elif volatility_regime == 2:  # High vol
        leverage *= 0.7
    
    # Trend strength adjustments
    leverage *= (0.8 + 0.4 * trend_strength)  # 0.8x to 1.2x based on trend strength
    
    # Cap leverage
    leverage = min(leverage, max_leverage)
    
    return leverage


def dynamic_position_sizing(
    equity: float,
    quality_score: float,
    market_regime: str,
    volatility_regime: int,
    trend_strength: float,
    base_risk_per_trade: float = 0.02,
    base_leverage: float = 5.0,
) -> dict:
    """
    Calculate dynamic position size based on multiple factors.
    
    Returns dict with:
    - risk_amount: Dollar amount to risk
    - leverage: Leverage to use
    - position_fraction: Fraction of equity for margin
    """
    
    # Kelly-based risk sizing
    win_prob = estimate_win_probability(pd.Series([quality_score]))[0]
    kelly_frac = kelly_fraction(pd.Series([win_prob]))[0]
    
    # Use Kelly fraction but cap it
    risk_fraction = min(kelly_frac, base_risk_per_trade * 3)  # Max 3x base risk
    risk_fraction = max(risk_fraction, base_risk_per_trade * 0.5)  # Min 0.5x base risk
    
    # Regime-based leverage
    leverage = regime_leverage_multiplier(
        market_regime, volatility_regime, trend_strength, base_leverage
    )
    
    # Calculate position metrics
    risk_amount = equity * risk_fraction
    margin_fraction = risk_fraction  # Use risk fraction as margin fraction
    
    return {
        'risk_amount': risk_amount,
        'leverage': leverage,
        'margin_fraction': margin_fraction,
        'win_probability': win_prob,
        'kelly_fraction': kelly_frac,
    }
