from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

from bot.risk.controls import RiskMonitor, RiskLimits, apply_risk_controls


@dataclass
class PortfolioRiskConfig:
    """Enhanced portfolio risk configuration."""
    
    # Base risk config
    base_risk_limits: RiskLimits
    
    # Strategy-specific limits
    strategy_max_weights: Dict[str, float]  # Max weight per strategy
    strategy_vol_targets: Dict[str, float]  # Vol target per strategy
    
    # Correlation-based risk
    max_correlation_exposure: float = 0.8   # Reduce size if strategies highly correlated
    correlation_threshold: float = 0.7      # Threshold for correlation adjustment
    
    # Time-based risk
    session_risk_multipliers: Dict[str, float] = None  # Risk multiplier by session
    day_of_week_multipliers: Dict[int, float] = None   # Risk multiplier by day (0=Monday)
    
    # Regime-based risk
    high_vol_regime_multiplier: float = 0.7  # Reduce size in high vol regimes
    trend_regime_multiplier: float = 1.0     # Normal size in trend regimes
    chop_regime_multiplier: float = 0.8      # Reduce size in choppy regimes


class PortfolioRiskManager:
    """
    Enhanced portfolio-level risk management.
    
    Combines individual strategy risk controls with portfolio-level
    correlation, regime, and time-based adjustments.
    """
    
    def __init__(self, config: PortfolioRiskConfig):
        self.config = config
        self.risk_monitor = RiskMonitor(config.base_risk_limits)
        
        # Track strategy correlations over time
        self.strategy_returns_history: Dict[str, list] = {}
        self.max_correlation_lookback = 252  # 1 year of daily returns
        
        # Track regime state
        self.current_regime = "normal"
        self.regime_vol_multiplier = 1.0
        
    def calculate_portfolio_risk_budget(
        self, 
        strategy_signals: Dict[str, float],
        current_equity: float,
        market_data: Dict[str, Any],
        timestamp: datetime = None
    ) -> Tuple[Dict[str, float], Dict[str, Any]]:
        """
        Calculate risk-adjusted position sizes for the portfolio.
        
        Args:
            strategy_signals: Raw strategy signals (-1, 0, 1)
            current_equity: Current portfolio equity
            market_data: Market condition data (volatility, regime, etc.)
            timestamp: Current timestamp
            
        Returns:
            (risk_adjusted_positions, risk_metrics)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        risk_metrics = {}
        
        # 1. Calculate base position sizes from strategy vol targets
        base_positions = self._calculate_base_positions(
            strategy_signals, current_equity, market_data
        )
        risk_metrics['base_positions'] = base_positions
        
        # 2. Apply correlation adjustments
        correlation_adjusted = self._apply_correlation_adjustments(
            base_positions, timestamp
        )
        risk_metrics['correlation_adjustment'] = {
            k: correlation_adjusted[k] / base_positions[k] if base_positions[k] != 0 else 1.0
            for k in base_positions.keys()
        }
        
        # 3. Apply regime adjustments
        regime_adjusted = self._apply_regime_adjustments(
            correlation_adjusted, market_data
        )
        risk_metrics['regime_adjustment'] = self.regime_vol_multiplier
        
        # 4. Apply time-based adjustments
        time_adjusted = self._apply_time_adjustments(
            regime_adjusted, timestamp
        )
        risk_metrics['time_adjustments'] = self._get_time_multipliers(timestamp)
        
        # 5. Apply core risk controls (loss stops, position limits, kill switches)
        final_positions, risk_actions = apply_risk_controls(
            time_adjusted,
            current_equity,
            sum(abs(pos) for pos in time_adjusted.values()),  # Total target vol
            self.risk_monitor,
            realized_slippage=market_data.get('realized_slippage', 0.0),
            model_slippage=market_data.get('model_slippage', 0.001),
            current_spread=market_data.get('current_spread', 0.0),
            current_vol=market_data.get('realized_vol'),
            timestamp=timestamp
        )
        
        risk_metrics['risk_actions'] = risk_actions
        risk_metrics['final_adjustment'] = {
            k: final_positions[k] / time_adjusted[k] if time_adjusted[k] != 0 else 1.0
            for k in time_adjusted.keys()
        }
        
        # 6. Calculate portfolio-level metrics
        risk_metrics.update(self._calculate_portfolio_metrics(
            final_positions, current_equity, market_data
        ))
        
        return final_positions, risk_metrics
    
    def _calculate_base_positions(
        self, 
        signals: Dict[str, float], 
        equity: float, 
        market_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate base position sizes from vol targeting."""
        positions = {}
        
        for strategy, signal in signals.items():
            if signal == 0:
                positions[strategy] = 0.0
                continue
                
            # Get strategy vol target
            vol_target = self.config.strategy_vol_targets.get(strategy, 0.15)  # Default 15%
            
            # Calculate position size: (target_vol * equity) / strategy_vol
            # For simplicity, assume strategy vol = 20% annually
            strategy_vol = market_data.get(f'{strategy}_vol', 0.20)
            
            base_size = (vol_target * equity) / strategy_vol
            positions[strategy] = signal * base_size
            
        return positions
    
    def _apply_correlation_adjustments(
        self, 
        positions: Dict[str, float], 
        timestamp: datetime
    ) -> Dict[str, float]:
        """Adjust positions based on strategy correlations."""
        adjusted = positions.copy()
        
        # Skip if we don't have enough correlation history
        if len(self.strategy_returns_history) < 2:
            return adjusted
            
        # Calculate recent correlations
        strategies = list(positions.keys())
        correlations = self._calculate_strategy_correlations(strategies)
        
        # Calculate total correlation-weighted exposure
        total_exposure = 0
        correlation_factors = {}
        
        for strategy in strategies:
            # Calculate average correlation with other active strategies
            other_strategies = [s for s in strategies if s != strategy and positions[s] != 0]
            if not other_strategies:
                correlation_factors[strategy] = 1.0
                continue
                
            avg_correlation = np.mean([
                abs(correlations.get((strategy, other), 0.0)) 
                for other in other_strategies
            ])
            
            # Apply correlation penalty if above threshold
            if avg_correlation > self.config.correlation_threshold:
                penalty = 1.0 - (avg_correlation - self.config.correlation_threshold) / (1.0 - self.config.correlation_threshold)
                correlation_factors[strategy] = max(penalty, self.config.max_correlation_exposure)
            else:
                correlation_factors[strategy] = 1.0
                
            adjusted[strategy] = positions[strategy] * correlation_factors[strategy]
        
        return adjusted
    
    def _calculate_strategy_correlations(self, strategies: List[str]) -> Dict[Tuple[str, str], float]:
        """Calculate pairwise strategy correlations."""
        correlations = {}
        
        for i, strat1 in enumerate(strategies):
            for j, strat2 in enumerate(strategies[i+1:], i+1):
                returns1 = self.strategy_returns_history.get(strat1, [])
                returns2 = self.strategy_returns_history.get(strat2, [])
                
                if len(returns1) >= 30 and len(returns2) >= 30:
                    # Use last N observations for correlation
                    n = min(len(returns1), len(returns2), self.max_correlation_lookback)
                    corr = np.corrcoef(returns1[-n:], returns2[-n:])[0, 1]
                    correlations[(strat1, strat2)] = corr
                    correlations[(strat2, strat1)] = corr
                    
        return correlations
    
    def _apply_regime_adjustments(
        self, 
        positions: Dict[str, float], 
        market_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Adjust positions based on market regime."""
        # Detect current regime from market data
        current_vol = market_data.get('realized_vol', 0.20)
        trend_strength = market_data.get('trend_strength', 0.0)
        
        # Simple regime classification
        high_vol_threshold = 0.30  # 30% annualized vol
        trend_threshold = 0.5
        
        if current_vol > high_vol_threshold:
            self.current_regime = "high_vol"
            self.regime_vol_multiplier = self.config.high_vol_regime_multiplier
        elif abs(trend_strength) > trend_threshold:
            self.current_regime = "trend"
            self.regime_vol_multiplier = self.config.trend_regime_multiplier
        else:
            self.current_regime = "chop"
            self.regime_vol_multiplier = self.config.chop_regime_multiplier
            
        # Apply regime multiplier
        return {k: v * self.regime_vol_multiplier for k, v in positions.items()}
    
    def _apply_time_adjustments(
        self, 
        positions: Dict[str, float], 
        timestamp: datetime
    ) -> Dict[str, float]:
        """Apply time-based risk adjustments."""
        multipliers = self._get_time_multipliers(timestamp)
        total_multiplier = multipliers['session'] * multipliers['day_of_week']
        
        return {k: v * total_multiplier for k, v in positions.items()}
    
    def _get_time_multipliers(self, timestamp: datetime) -> Dict[str, float]:
        """Get time-based risk multipliers."""
        multipliers = {'session': 1.0, 'day_of_week': 1.0}
        
        # Session-based (UTC hours)
        if self.config.session_risk_multipliers:
            hour = timestamp.hour
            if 0 <= hour < 8:  # Asia session
                multipliers['session'] = self.config.session_risk_multipliers.get('asia', 1.0)
            elif 8 <= hour < 16:  # Europe session
                multipliers['session'] = self.config.session_risk_multipliers.get('europe', 1.0)
            else:  # US session
                multipliers['session'] = self.config.session_risk_multipliers.get('us', 1.0)
        
        # Day of week
        if self.config.day_of_week_multipliers:
            day_of_week = timestamp.weekday()  # 0=Monday
            multipliers['day_of_week'] = self.config.day_of_week_multipliers.get(day_of_week, 1.0)
            
        return multipliers
    
    def _calculate_portfolio_metrics(
        self, 
        positions: Dict[str, float], 
        equity: float, 
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate portfolio-level risk metrics."""
        total_gross = sum(abs(pos) for pos in positions.values())
        total_net = sum(positions.values())
        
        long_exposure = sum(max(0, pos) for pos in positions.values())
        short_exposure = abs(sum(min(0, pos) for pos in positions.values()))
        
        return {
            'total_gross_exposure': total_gross,
            'total_net_exposure': total_net,
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'gross_leverage': total_gross / equity if equity > 0 else 0,
            'net_leverage': abs(total_net) / equity if equity > 0 else 0,
            'long_short_ratio': long_exposure / short_exposure if short_exposure > 0 else float('inf'),
            'portfolio_beta': total_net / equity if equity > 0 else 0,
            'regime': self.current_regime,
            'regime_multiplier': self.regime_vol_multiplier,
            'active_strategies': len([k for k, v in positions.items() if v != 0]),
        }
    
    def update_strategy_returns(self, strategy_returns: Dict[str, float]):
        """Update strategy return history for correlation tracking."""
        for strategy, ret in strategy_returns.items():
            if strategy not in self.strategy_returns_history:
                self.strategy_returns_history[strategy] = []
            
            self.strategy_returns_history[strategy].append(ret)
            
            # Keep only recent history
            if len(self.strategy_returns_history[strategy]) > self.max_correlation_lookback:
                self.strategy_returns_history[strategy].pop(0)
    
    def reset_daily_tracking(self, equity: float):
        """Reset daily risk tracking."""
        self.risk_monitor.reset_day(equity)
        
    def reset_weekly_tracking(self, equity: float):
        """Reset weekly risk tracking.""" 
        self.risk_monitor.reset_week(equity)
        
    def reset_monthly_tracking(self, equity: float):
        """Reset monthly risk tracking."""
        self.risk_monitor.reset_month(equity)
        
    def get_risk_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive risk dashboard data."""
        base_summary = self.risk_monitor.get_risk_summary()
        
        # Add portfolio-specific metrics
        portfolio_metrics = {
            'current_regime': self.current_regime,
            'regime_multiplier': self.regime_vol_multiplier,
            'strategy_count': len(self.strategy_returns_history),
            'correlation_lookback_days': len(list(self.strategy_returns_history.values())[0]) if self.strategy_returns_history else 0,
        }
        
        return {**base_summary, **portfolio_metrics}
