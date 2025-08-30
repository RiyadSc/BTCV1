from dataclasses import dataclass, asdict
import pandas as pd


@dataclass
class Fill:
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    side: int  # +1 long, -1 short
    qty: float
    entry_px: float
    sl_px: float
    tp_px: float
    exit_px: float
    gross_ret: float
    fees: float
    spread_slip: float
    impact_slip: float
    funding_pnl: float
    net_ret: float


def build_ledger(
    bars: pd.DataFrame,
    pos_series: pd.Series,
    fees_bps: float,
    spread_bps: float,
    impact_series: pd.Series,
    funding_series: pd.Series,
    atr_series: pd.Series | None = None,
    sl_atr_k: float | None = None,
    tp_atr_k: float | None = None,
) -> pd.DataFrame:
    led: list[Fill] = []
    prev_pos = 0.0
    entry_ts = None
    entry_px = None
    entry_sl = None
    entry_tp = None
    qty = 0.0
    side = 0
    running_costs = {"fees": 0.0, "spread": 0.0, "impact": 0.0, "funding": 0.0}
    for t, pos in pos_series.items():
        px = float(bars.loc[t, 'c']) if 'c' in bars.columns else float(bars.loc[t, 'close'])
        # accumulate per-bar costs
        if pos != prev_pos:
            order_frac = abs(pos - prev_pos)
            running_costs["fees"] += order_frac * (fees_bps * 1e-4)
            running_costs["spread"] += order_frac * (spread_bps * 1e-4)
            running_costs["impact"] += float(impact_series.reindex([t]).fillna(0).iloc[0])
        running_costs["funding"] += float(funding_series.reindex([t]).fillna(0).iloc[0])

        if prev_pos == 0 and pos != 0:
            entry_ts = t
            entry_px = px
            qty = abs(pos)
            side = 1 if pos > 0 else -1
            if atr_series is not None and (sl_atr_k is not None or tp_atr_k is not None):
                atr_now = float(atr_series.reindex([t]).fillna(method='ffill').iloc[0])
                if side > 0:
                    entry_sl = entry_px - (sl_atr_k or 0.0) * atr_now
                    entry_tp = entry_px + (tp_atr_k or 0.0) * atr_now
                else:
                    entry_sl = entry_px + (sl_atr_k or 0.0) * atr_now
                    entry_tp = entry_px - (tp_atr_k or 0.0) * atr_now
        elif prev_pos != 0 and pos == 0:
            exit_ts = t
            exit_px = px
            gross_ret = side * (exit_px / entry_px - 1.0) * qty
            fees = running_costs["fees"]
            spr = running_costs["spread"]
            imp = running_costs["impact"]
            fund = running_costs["funding"]
            net = gross_ret - fees - spr - imp + fund
            led.append(Fill(entry_ts, exit_ts, side, qty, entry_px, entry_sl or float('nan'), entry_tp or float('nan'), exit_px, gross_ret, fees, spr, imp, fund, net))
            running_costs = {"fees": 0.0, "spread": 0.0, "impact": 0.0, "funding": 0.0}
            entry_ts = entry_px = qty = None
            entry_sl = entry_tp = None
            side = 0
        prev_pos = pos
    return pd.DataFrame([asdict(f) for f in led])


