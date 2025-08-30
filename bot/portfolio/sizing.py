from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from bot.indicators.core import atr


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.0075
    atr_n: int = 14
    atr_k: float = 2.0


def compute_unit_size(df: pd.DataFrame, cfg: RiskConfig) -> pd.Series:
    bar_atr = atr(df, cfg.atr_n)
    unit = cfg.atr_k * bar_atr
    size = (cfg.risk_per_trade / unit).replace([pd.NA, float("inf")], 0.0).fillna(0.0)
    return size
