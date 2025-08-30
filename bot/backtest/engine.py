from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, Dict
import numpy as np
import pandas as pd
from bot.indicators.core import atr


@dataclass
class CostModel:
    taker_bps_round: float = 0.0008  # 8 bps round-trip
    maker_bps_round: float = 0.0004  # 4 bps round-trip
    use_maker: bool = False
    impact_coef: float = 0.001  # scales with sqrt(order_notional / bar_notional)
    spread_bps: float = 0.5  # median spread per side in bps (configurable)


@dataclass
class SizingRules:
    risk_per_trade: float = 0.0075
    atr_n: int = 14
    atr_k: float = 2.0
    # New: explicit margin fraction and leverage for cross
    # If provided, position fraction = sign(signal) * leverage * margin_fraction
    margin_fraction: float = 0.0
    leverage: float = 1.0


class Backtester:
    def __init__(
        self,
        df: pd.DataFrame,
        signal_series: pd.Series,
        equity_start: float = 1.0,
        cost_model: Optional[CostModel] = None,
        funding_series: Optional[pd.Series] = None,
        time_stop_bars: Optional[int] = None,
        trail_atr_k: Optional[float] = None,
        # New: fixed ATR-based stop loss / take profit
        sl_atr_k: Optional[float] = None,
        tp_atr_k: Optional[float] = None,
        # New: if True, interpret signal_series as the actual position series
        signal_is_position: bool = False,
        enable_adaptive_sizing: bool = False,
        regime_data: Optional[dict] = None,
    ):
        self.df = df
        self.signal = signal_series.reindex(df.index).fillna(0)
        self.equity_start = equity_start
        self.cost_model = cost_model or CostModel()
        self.funding = funding_series.reindex(df.index).fillna(0) if funding_series is not None else pd.Series(0.0, index=df.index)
        self.time_stop_bars = time_stop_bars
        self.trail_atr_k = trail_atr_k
        self.sl_atr_k = sl_atr_k
        self.tp_atr_k = tp_atr_k
        self.signal_is_position = signal_is_position
        self.enable_adaptive_sizing = enable_adaptive_sizing
        self.regime_data = regime_data or {}

    def run(self, sizing: SizingRules) -> pd.DataFrame:
        # Handle both old ('c') and new ('close') column names
        close_col = "close" if "close" in self.df.columns else "c"
        prices = self.df[close_col]
        bar_atr = atr(self.df, sizing.atr_n)
        unit = sizing.atr_k * bar_atr
        # desired direction (-1, 0, 1)
        if self.signal_is_position:
            # Use provided series as-is (already represents held position over time)
            desired_dir = self.signal.astype(float)
        else:
            # Legacy behavior: hold last non-zero signal until flip
            desired_dir = self.signal.replace(to_replace=0, method="ffill").fillna(0).astype(float)

        # Position fraction of equity: either legacy ATR-based risk sizing or explicit margin/leverage
        if sizing.margin_fraction > 0:
            desired_pos = desired_dir * (sizing.leverage * sizing.margin_fraction)
        else:
            # Legacy: approximate fraction based on ATR (kept for backward compatibility)
            size = np.where(unit > 0, sizing.risk_per_trade / unit, 0.0)
            desired_pos = desired_dir * size

        # optional trailing/time stop and fixed SL/TP stops
        if self.trail_atr_k is not None:
            trail_stop = prices.copy() * 0.0
            active_dir = 0
            last_flip_idx = 0
            entry_price = None
            for i, ts in enumerate(prices.index):
                s = self.signal.iloc[i]
                if s != 0 and (i == 0 or self.signal.iloc[i-1] == 0):
                    active_dir = int(s)
                    last_flip_idx = i
                    entry_price = prices.iloc[i]
                    if active_dir > 0:
                        trail_stop.iloc[i] = prices.iloc[i] - self.trail_atr_k * bar_atr.iloc[i]
                    else:
                        trail_stop.iloc[i] = prices.iloc[i] + self.trail_atr_k * bar_atr.iloc[i]
                else:
                    if active_dir > 0:
                        trail_stop.iloc[i] = max(trail_stop.iloc[i-1], prices.iloc[i] - self.trail_atr_k * bar_atr.iloc[i])
                        if prices.iloc[i] < trail_stop.iloc[i]:
                            desired_pos.iloc[i] = 0
                            active_dir = 0
                            entry_price = None
                    elif active_dir < 0:
                        trail_stop.iloc[i] = min(trail_stop.iloc[i-1], prices.iloc[i] + self.trail_atr_k * bar_atr.iloc[i])
                        if prices.iloc[i] > trail_stop.iloc[i]:
                            desired_pos.iloc[i] = 0
                            active_dir = 0
                            entry_price = None
                    else:
                        trail_stop.iloc[i] = trail_stop.iloc[i-1] if i > 0 else 0
                if self.time_stop_bars is not None and active_dir != 0 and (i - last_flip_idx) >= self.time_stop_bars:
                    desired_pos.iloc[i] = 0
                    active_dir = 0
                    entry_price = None

                # Apply fixed SL/TP based on ATR from entry
                if active_dir != 0 and entry_price is not None and (self.sl_atr_k is not None or self.tp_atr_k is not None):
                    atr_now = bar_atr.iloc[i]
                    if active_dir > 0:
                        sl_price = entry_price - (self.sl_atr_k or 0) * atr_now
                        tp_price = entry_price + (self.tp_atr_k or 1e9) * atr_now
                        if prices.iloc[i] <= sl_price or prices.iloc[i] >= tp_price:
                            desired_pos.iloc[i] = 0
                            active_dir = 0
                            entry_price = None
                    else:
                        sl_price = entry_price + (self.sl_atr_k or 0) * atr_now
                        tp_price = entry_price - (self.tp_atr_k or 1e9) * atr_now
                        if prices.iloc[i] >= sl_price or prices.iloc[i] <= tp_price:
                            desired_pos.iloc[i] = 0
                            active_dir = 0
                            entry_price = None

        pos = desired_pos
        ret = prices.pct_change().fillna(0)
        gross = pos.shift().fillna(0) * ret

        # funding accrual: pay only on 00:00, 08:00, 16:00 UTC cuts, using held notional at prior bar close
        # self.funding contains sparse rates at exact cut timestamps; zero elsewhere
        fr = self.funding.reindex(self.df.index).fillna(0.0)
        carry = (pos.shift().fillna(0) * fr)

        turns = (pos != pos.shift()).astype(int)
        # Fraction of notional traded this bar (position change)
        order_frac = np.abs(pos - pos.shift().fillna(0))
        spread_cost_rt = (self.cost_model.maker_bps_round if self.cost_model.use_maker else self.cost_model.taker_bps_round)
        # Fees scale with traded notional fraction
        fees = order_frac * spread_cost_rt
        # slippage: spread per side + impact
        # quote notional volume proxy
        # Handle both old ('v') and new ('volume') column names
        volume_col = "volume" if "volume" in self.df.columns else "v"
        bar_quote_notional = self.df.get("qv") if "qv" in self.df.columns else (self.df[volume_col] * prices)
        bar_quote_notional = bar_quote_notional.replace(0, np.nan)
        # Approximate impact using position fraction as proxy for order size fraction
        order_frac = np.abs(pos - pos.shift().fillna(0))
        impact = np.sqrt(np.maximum(order_frac / (1.0 + (bar_quote_notional / bar_quote_notional.median()).fillna(1.0)), 0)).fillna(0) * self.cost_model.impact_coef * turns
        # Spread slippage also scales with order size fraction
        spread_slip = (self.cost_model.spread_bps * 1e-4) * order_frac

        net = gross + carry - fees - (impact + spread_slip)
        equity = (1.0 + net).cumprod() * self.equity_start
        out = pd.DataFrame({
            "pos": pos,
            "gross": gross,
            "carry": carry,
            "fees": fees,
            "spread_slip": spread_slip,
            "impact_slip": impact,
            "net": net,
            "equity": equity,
        }, index=self.df.index)
        return out
