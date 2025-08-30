from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
from enum import Enum


class RiskState(Enum):
    """Risk control states."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY_STOP = "emergency_stop"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class RiskLimits:
    """Risk control limits configuration."""
    
    # Loss stops (as fractions of equity)
    daily_loss_limit: float = 0.02    # 2% daily loss stop
    weekly_loss_limit: float = 0.05   # 5% weekly loss stop
    monthly_loss_limit: float = 0.10  # 10% monthly loss stop
    
    # Position limits
    max_individual_position: float = 0.70  # Max 70% of target vol per strategy
    max_total_exposure: float = 1.25       # Max 125% total notional exposure
    max_concentration: float = 0.50        # Max 50% in single direction
    
    # Market condition kill-switches
    max_slippage_multiplier: float = 2.0   # Kill if slippage > 2x model
    max_spread_multiplier: float = 1.5     # Kill if spread > 1.5x 30D median
    slippage_breach_count: int = 2         # Consecutive breaches before kill
    
    # Volatility controls
    max_vol_target_multiplier: float = 3.0  # Max 3x target volatility
    vol_lookback_days: int = 30             # Volatility calculation window
    
    # Drawdown controls
    max_peak_to_trough: float = 0.15       # 15% max drawdown from peak
    drawdown_pause_days: int = 3           # Days to pause after max DD


@dataclass
class RiskAlert:
    """Risk alert data structure."""
    timestamp: datetime
    level: AlertLevel
    source: str
    message: str
    current_value: float
    limit_value: float
    action_taken: str


class RiskMonitor:
    """
    Real-time risk monitoring and control system.
    
    Tracks portfolio PnL, positions, market conditions and enforces
    risk limits with automatic position flattening when necessary.
    """
    
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.state = RiskState.NORMAL
        self.alerts: List[RiskAlert] = []
        
        # Track breach counts for kill-switches
        self.slippage_breach_count = 0
        self.last_slippage_breach = None
        
        # Track historical values for monitoring
        self.equity_high_water_mark = None
        self.daily_start_equity = None
        self.weekly_start_equity = None
        self.monthly_start_equity = None
        
        # Emergency stop flags
        self.emergency_stop_active = False
        self.stop_reason = None
        self.stop_timestamp = None
        
        # Market condition tracking
        self.recent_spreads: List[float] = []
        self.spread_median_30d = None
        
    def reset_day(self, current_equity: float):
        """Reset daily tracking at market open."""
        self.daily_start_equity = current_equity
        if self.equity_high_water_mark is None:
            self.equity_high_water_mark = current_equity
            
    def reset_week(self, current_equity: float):
        """Reset weekly tracking."""
        self.weekly_start_equity = current_equity
        
    def reset_month(self, current_equity: float):
        """Reset monthly tracking."""
        self.monthly_start_equity = current_equity
        
    def update_high_water_mark(self, current_equity: float):
        """Update equity high water mark."""
        if self.equity_high_water_mark is None or current_equity > self.equity_high_water_mark:
            self.equity_high_water_mark = current_equity
    
    def check_loss_stops(self, current_equity: float, timestamp: datetime) -> bool:
        """
        Check daily/weekly/monthly loss limits.
        Returns True if any limit is breached.
        """
        breached = False
        
        # Daily loss check
        if self.daily_start_equity and current_equity < self.daily_start_equity * (1 - self.limits.daily_loss_limit):
            daily_loss = (self.daily_start_equity - current_equity) / self.daily_start_equity
            self._create_alert(
                AlertLevel.CRITICAL, "daily_loss_stop",
                f"Daily loss limit breached: {daily_loss:.2%} > {self.limits.daily_loss_limit:.2%}",
                daily_loss, self.limits.daily_loss_limit,
                "FLATTEN ALL POSITIONS", timestamp
            )
            breached = True
            
        # Weekly loss check
        if self.weekly_start_equity and current_equity < self.weekly_start_equity * (1 - self.limits.weekly_loss_limit):
            weekly_loss = (self.weekly_start_equity - current_equity) / self.weekly_start_equity
            self._create_alert(
                AlertLevel.CRITICAL, "weekly_loss_stop",
                f"Weekly loss limit breached: {weekly_loss:.2%} > {self.limits.weekly_loss_limit:.2%}",
                weekly_loss, self.limits.weekly_loss_limit,
                "FLATTEN ALL POSITIONS", timestamp
            )
            breached = True
            
        # Monthly loss check
        if self.monthly_start_equity and current_equity < self.monthly_start_equity * (1 - self.limits.monthly_loss_limit):
            monthly_loss = (self.monthly_start_equity - current_equity) / self.monthly_start_equity
            self._create_alert(
                AlertLevel.CRITICAL, "monthly_loss_stop",
                f"Monthly loss limit breached: {monthly_loss:.2%} > {self.limits.monthly_loss_limit:.2%}",
                monthly_loss, self.limits.monthly_loss_limit,
                "FLATTEN ALL POSITIONS", timestamp
            )
            breached = True
            
        return breached
    
    def check_drawdown_limits(self, current_equity: float, timestamp: datetime) -> bool:
        """Check peak-to-trough drawdown limits."""
        if not self.equity_high_water_mark:
            return False
            
        drawdown = (self.equity_high_water_mark - current_equity) / self.equity_high_water_mark
        
        if drawdown > self.limits.max_peak_to_trough:
            self._create_alert(
                AlertLevel.CRITICAL, "max_drawdown",
                f"Maximum drawdown breached: {drawdown:.2%} > {self.limits.max_peak_to_trough:.2%}",
                drawdown, self.limits.max_peak_to_trough,
                f"FLATTEN ALL POSITIONS - PAUSE {self.limits.drawdown_pause_days} DAYS", timestamp
            )
            return True
            
        return False
    
    def check_position_limits(self, positions: Dict[str, float], target_vol: float, timestamp: datetime) -> Tuple[bool, Dict[str, float]]:
        """
        Check position size and exposure limits.
        Returns (is_breached, adjusted_positions).
        """
        adjusted = positions.copy()
        breached = False
        
        # Check individual position limits
        for strategy, pos in positions.items():
            abs_pos = abs(pos)
            if abs_pos > self.limits.max_individual_position * target_vol:
                old_pos = pos
                adjusted[strategy] = np.sign(pos) * self.limits.max_individual_position * target_vol
                self._create_alert(
                    AlertLevel.WARNING, "position_limit",
                    f"{strategy} position capped: {abs_pos:.3f} -> {abs(adjusted[strategy]):.3f}",
                    abs_pos, self.limits.max_individual_position * target_vol,
                    "POSITION_CAPPED", timestamp
                )
                breached = True
        
        # Check total exposure
        total_exposure = sum(abs(pos) for pos in adjusted.values())
        max_total = self.limits.max_total_exposure * target_vol
        
        if total_exposure > max_total:
            # Scale down all positions proportionally
            scale_factor = max_total / total_exposure
            for strategy in adjusted:
                adjusted[strategy] *= scale_factor
            
            self._create_alert(
                AlertLevel.WARNING, "total_exposure",
                f"Total exposure scaled down: {total_exposure:.3f} -> {max_total:.3f}",
                total_exposure, max_total,
                f"ALL_POSITIONS_SCALED_{scale_factor:.3f}", timestamp
            )
            breached = True
            
        # Check concentration limits
        long_exposure = sum(max(0, pos) for pos in adjusted.values())
        short_exposure = abs(sum(min(0, pos) for pos in adjusted.values()))
        total_gross = long_exposure + short_exposure
        
        if total_gross > 0:
            long_concentration = long_exposure / total_gross
            short_concentration = short_exposure / total_gross
            
            if long_concentration > self.limits.max_concentration:
                self._create_alert(
                    AlertLevel.WARNING, "long_concentration",
                    f"Long concentration too high: {long_concentration:.2%} > {self.limits.max_concentration:.2%}",
                    long_concentration, self.limits.max_concentration,
                    "CONCENTRATION_WARNING", timestamp
                )
                breached = True
                
            if short_concentration > self.limits.max_concentration:
                self._create_alert(
                    AlertLevel.WARNING, "short_concentration", 
                    f"Short concentration too high: {short_concentration:.2%} > {self.limits.max_concentration:.2%}",
                    short_concentration, self.limits.max_concentration,
                    "CONCENTRATION_WARNING", timestamp
                )
                breached = True
        
        return breached, adjusted
    
    def check_market_conditions(self, realized_slippage: float, model_slippage: float, 
                              current_spread: float, timestamp: datetime) -> bool:
        """
        Check market condition kill-switches.
        Returns True if emergency stop should be triggered.
        """
        emergency_stop = False
        
        # Slippage kill-switch
        max_allowed_slippage = model_slippage * self.limits.max_slippage_multiplier
        if realized_slippage > max_allowed_slippage:
            self.slippage_breach_count += 1
            self.last_slippage_breach = timestamp
            
            self._create_alert(
                AlertLevel.CRITICAL, "high_slippage",
                f"Slippage breach #{self.slippage_breach_count}: {realized_slippage:.4f} > {max_allowed_slippage:.4f}",
                realized_slippage, max_allowed_slippage,
                f"SLIPPAGE_BREACH_{self.slippage_breach_count}", timestamp
            )
            
            if self.slippage_breach_count >= self.limits.slippage_breach_count:
                emergency_stop = True
                self._trigger_emergency_stop("CONSECUTIVE_SLIPPAGE_BREACHES", timestamp)
        else:
            # Reset count if no breach
            if self.last_slippage_breach and (timestamp - self.last_slippage_breach).total_seconds() > 3600:
                self.slippage_breach_count = 0
        
        # Spread kill-switch
        self.recent_spreads.append(current_spread)
        if len(self.recent_spreads) > 30 * 24:  # Keep 30 days of hourly data
            self.recent_spreads.pop(0)
            
        if len(self.recent_spreads) >= 30:  # Need minimum data
            self.spread_median_30d = np.median(self.recent_spreads[:-1])  # Exclude current
            max_allowed_spread = self.spread_median_30d * self.limits.max_spread_multiplier
            
            if current_spread > max_allowed_spread:
                self._create_alert(
                    AlertLevel.CRITICAL, "high_spread",
                    f"Spread too high: {current_spread:.4f} > {max_allowed_spread:.4f}",
                    current_spread, max_allowed_spread,
                    "SPREAD_KILL_SWITCH", timestamp
                )
                emergency_stop = True
                self._trigger_emergency_stop("HIGH_SPREAD", timestamp)
        
        return emergency_stop
    
    def check_volatility_limits(self, current_vol: float, target_vol: float, timestamp: datetime) -> bool:
        """Check if realized volatility exceeds limits."""
        max_vol = target_vol * self.limits.max_vol_target_multiplier
        
        if current_vol > max_vol:
            self._create_alert(
                AlertLevel.WARNING, "high_volatility",
                f"Volatility too high: {current_vol:.3f} > {max_vol:.3f}",
                current_vol, max_vol,
                "VOLATILITY_WARNING", timestamp
            )
            return True
            
        return False
    
    def _create_alert(self, level: AlertLevel, source: str, message: str,
                     current_value: float, limit_value: float, action: str, timestamp: datetime):
        """Create and store risk alert."""
        alert = RiskAlert(
            timestamp=timestamp,
            level=level,
            source=source,
            message=message,
            current_value=current_value,
            limit_value=limit_value,
            action_taken=action
        )
        self.alerts.append(alert)
        
        # Update state based on alert level
        if level == AlertLevel.CRITICAL or level == AlertLevel.EMERGENCY:
            self.state = RiskState.CRITICAL
        elif level == AlertLevel.WARNING and self.state == RiskState.NORMAL:
            self.state = RiskState.WARNING
    
    def _trigger_emergency_stop(self, reason: str, timestamp: datetime):
        """Trigger emergency stop."""
        self.emergency_stop_active = True
        self.stop_reason = reason
        self.stop_timestamp = timestamp
        self.state = RiskState.EMERGENCY_STOP
        
        self._create_alert(
            AlertLevel.EMERGENCY, "emergency_stop",
            f"EMERGENCY STOP TRIGGERED: {reason}",
            1.0, 0.0,
            "EMERGENCY_FLATTEN_ALL", timestamp
        )
    
    def should_allow_new_positions(self) -> bool:
        """Check if new positions should be allowed."""
        return not self.emergency_stop_active and self.state != RiskState.EMERGENCY_STOP
    
    def should_flatten_all_positions(self) -> bool:
        """Check if all positions should be flattened immediately."""
        return self.emergency_stop_active or self.state == RiskState.EMERGENCY_STOP
    
    def get_recent_alerts(self, hours: int = 24) -> List[RiskAlert]:
        """Get alerts from last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alerts if alert.timestamp >= cutoff]
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get current risk status summary."""
        recent_alerts = self.get_recent_alerts(24)
        
        return {
            'state': self.state.value,
            'emergency_stop_active': self.emergency_stop_active,
            'stop_reason': self.stop_reason,
            'equity_hwm': self.equity_high_water_mark,
            'recent_alerts_24h': len(recent_alerts),
            'critical_alerts_24h': len([a for a in recent_alerts if a.level == AlertLevel.CRITICAL]),
            'slippage_breach_count': self.slippage_breach_count,
            'last_alert': self.alerts[-1] if self.alerts else None,
            'limits': {
                'daily_loss': f"{self.limits.daily_loss_limit:.1%}",
                'weekly_loss': f"{self.limits.weekly_loss_limit:.1%}",
                'monthly_loss': f"{self.limits.monthly_loss_limit:.1%}",
                'max_individual_pos': f"{self.limits.max_individual_position:.1%}",
                'max_total_exposure': f"{self.limits.max_total_exposure:.1%}"
            }
        }


def apply_risk_controls(
    positions: Dict[str, float],
    current_equity: float,
    target_vol: float,
    risk_monitor: RiskMonitor,
    realized_slippage: float = 0.0,
    model_slippage: float = 0.001,
    current_spread: float = 0.0,
    current_vol: float = None,
    timestamp: datetime = None
) -> Tuple[Dict[str, float], List[str]]:
    """
    Apply comprehensive risk controls to positions.
    
    Returns:
        (adjusted_positions, risk_actions)
    """
    if timestamp is None:
        timestamp = datetime.now()
        
    actions = []
    adjusted_positions = positions.copy()
    
    # Update high water mark
    risk_monitor.update_high_water_mark(current_equity)
    
    # Check loss stops
    if risk_monitor.check_loss_stops(current_equity, timestamp):
        adjusted_positions = {k: 0.0 for k in positions.keys()}
        actions.append("LOSS_STOP_TRIGGERED")
        return adjusted_positions, actions
    
    # Check drawdown limits
    if risk_monitor.check_drawdown_limits(current_equity, timestamp):
        adjusted_positions = {k: 0.0 for k in positions.keys()}
        actions.append("DRAWDOWN_STOP_TRIGGERED")
        return adjusted_positions, actions
    
    # Check market conditions (kill-switches)
    if risk_monitor.check_market_conditions(realized_slippage, model_slippage, current_spread, timestamp):
        adjusted_positions = {k: 0.0 for k in positions.keys()}
        actions.append("MARKET_CONDITIONS_KILL_SWITCH")
        return adjusted_positions, actions
    
    # Check if emergency stop is active
    if risk_monitor.should_flatten_all_positions():
        adjusted_positions = {k: 0.0 for k in positions.keys()}
        actions.append("EMERGENCY_STOP_ACTIVE")
        return adjusted_positions, actions
    
    # Check position limits
    pos_breached, adjusted_positions = risk_monitor.check_position_limits(adjusted_positions, target_vol, timestamp)
    if pos_breached:
        actions.append("POSITION_LIMITS_APPLIED")
    
    # Check volatility limits
    if current_vol and risk_monitor.check_volatility_limits(current_vol, target_vol, timestamp):
        actions.append("VOLATILITY_WARNING")
    
    # Prevent new positions if not allowed
    if not risk_monitor.should_allow_new_positions():
        # Only allow position reductions, not increases
        for strategy in adjusted_positions:
            original_abs = abs(positions.get(strategy, 0))
            adjusted_abs = abs(adjusted_positions[strategy])
            if adjusted_abs > original_abs:
                adjusted_positions[strategy] = positions.get(strategy, 0)
        actions.append("NEW_POSITIONS_BLOCKED")
    
    return adjusted_positions, actions
