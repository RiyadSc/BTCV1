from __future__ import annotations
from typing import Optional, Tuple
import pandas as pd
import numpy as np

from bot.indicators.core import atr
from bot.indicators.core import ema


def build_managed_signal(
    df: pd.DataFrame,
    sig_cat: pd.Series,
    sig_vsb: pd.Series,
    sl_atr_k_cat: float = 2.0,
    tp_atr_k_cat: float = 4.0,
    sl_atr_k_vsb: float = 2.0,
    tp_atr_k_vsb: float = 4.0,
    atr_n: int = 14,
    max_daily_sl_hits: int = 2,
    max_daily_entries: int = 10,
    cooldown_bars: int = 4,
    time_stop_bars_cat: Optional[int] = None,
    time_stop_bars_vsb: Optional[int] = None,
    trail_atr_k_cat: Optional[float] = None,
    min_hold_bars: int = 2,
    session_gate: Optional[pd.Series] = None,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Compose a single, managed position signal from CAT and VSB signals.

    Rules:
    - Only one trade at a time
    - Entry preference: VSB if non-zero, else CAT
    - Exit only via SL/TP (no signal-based flip exits)
    - After 3 SL hits in a UTC day, pause entries for the rest of that day
    - Optional session gating mask can zero-out entries

    Returns:
    - managed_pos: pd.Series of {-1,0,1} representing active trade direction over time
    - exit_reason: pd.Series of strings {'', 'tp', 'sl'} marking bars where exit occurs
    - source: pd.Series of strings {'', 'cat', 'vsb'} marking which strategy opened the trade
    """
    # Handle price columns
    close_col = "close" if "close" in df.columns else "c"
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"

    prices = df[close_col]
    highs = df[high_col]
    lows = df[low_col]
    bar_atr = atr(df, atr_n).reindex(df.index).ffill()

    # Remove MTF gating to increase opportunities
    allow_long = pd.Series(True, index=df.index)
    allow_short = pd.Series(True, index=df.index)

    # Align signals
    sig_cat = sig_cat.reindex(df.index).fillna(0).astype(int)
    sig_vsb = sig_vsb.reindex(df.index).fillna(0).astype(int)

    # Normalize session_gate to Series if provided
    if session_gate is not None and not isinstance(session_gate, pd.Series):
        session_gate = pd.Series(session_gate, index=df.index)

    managed = pd.Series(0, index=df.index, dtype="int8")
    exit_reason = pd.Series("", index=df.index, dtype="object")
    source = pd.Series("", index=df.index, dtype="object")

    in_pos = 0  # -1 short, 1 long, 0 flat
    entry_px = None
    sl_px = None
    tp_px = None
    entry_bar = -1
    current_source = ""
    current_day = None
    daily_sl_hits = {}
    daily_entries = {}
    # Per-strategy cooldowns
    cooldown_active = {"cat": 0, "vsb": 0}
    trail_activated = False

    for i, ts in enumerate(df.index):
        day = ts.date()
        if day not in daily_sl_hits:
            daily_sl_hits[day] = 0
            daily_entries[day] = 0
        
        # Decrement cooldowns
        for strat in cooldown_active:
            if cooldown_active[strat] > 0:
                cooldown_active[strat] -= 1

        if in_pos == 0:
            # Check if daily SL limit hit
            if daily_sl_hits[day] >= max_daily_sl_hits:
                managed.iloc[i] = 0
                continue

            # Check if max daily entries hit
            if daily_entries[day] >= max_daily_entries:
                managed.iloc[i] = 0
                continue

            # Consider new entry only if session gate allows
            if session_gate is not None and not bool(session_gate.iloc[i]):
                managed.iloc[i] = 0
                continue

            # Pick strategy: prefer VSB when available
            desired = 0
            opened_by = ""
            if sig_vsb.iloc[i] != 0 and cooldown_active["vsb"] == 0:
                desired = int(sig_vsb.iloc[i])
                opened_by = "vsb"
            elif sig_cat.iloc[i] != 0 and cooldown_active["cat"] == 0:
                desired = int(sig_cat.iloc[i])
                opened_by = "cat"
            
            # Enforce MTF directional gating
            if desired > 0 and not bool(allow_long.iloc[i]):
                desired = 0
            if desired < 0 and not bool(allow_short.iloc[i]):
                desired = 0

            if desired != 0 and not np.isnan(bar_atr.iloc[i]) and bar_atr.iloc[i] > 0:
                in_pos = desired
                entry_px = prices.iloc[i]
                entry_bar = i
                current_source = opened_by
                trail_activated = False
                
                # Use per-strategy SL/TP
                if opened_by == "cat":
                    sl_k, tp_k = sl_atr_k_cat, tp_atr_k_cat
                else:
                    sl_k, tp_k = sl_atr_k_vsb, tp_atr_k_vsb
                    
                if in_pos > 0:
                    sl_px = entry_px - sl_k * bar_atr.iloc[i]
                    tp_px = entry_px + tp_k * bar_atr.iloc[i]
                else:
                    sl_px = entry_px + sl_k * bar_atr.iloc[i]
                    tp_px = entry_px - tp_k * bar_atr.iloc[i]
                    
                managed.iloc[i] = in_pos
                source.iloc[i] = opened_by
                daily_entries[day] += 1
            else:
                managed.iloc[i] = 0
        else:
            # Manage open position via bar extremes against SL/TP
            hit_sl = False
            hit_tp = False
            if in_pos > 0:
                # Long: SL if low <= sl_px; TP if high >= tp_px
                if not np.isnan(lows.iloc[i]) and sl_px is not None and lows.iloc[i] <= sl_px:
                    hit_sl = True
                if not np.isnan(highs.iloc[i]) and tp_px is not None and highs.iloc[i] >= tp_px:
                    hit_tp = True
            else:
                # Short: SL if high >= sl_px; TP if low <= tp_px
                if not np.isnan(highs.iloc[i]) and sl_px is not None and highs.iloc[i] >= sl_px:
                    hit_sl = True
                if not np.isnan(lows.iloc[i]) and tp_px is not None and lows.iloc[i] <= tp_px:
                    hit_tp = True

            # CAT trailing stop activation after 2x SL favorable move
            if not hit_tp and not hit_sl and entry_px is not None and current_source == "cat" and trail_atr_k_cat is not None:
                if in_pos > 0:
                    sl_dist = entry_px - sl_px if sl_px is not None else None
                    if sl_dist and (prices.iloc[i] - entry_px) >= 2.0 * sl_dist:
                        sl_px = max(sl_px or -np.inf, prices.iloc[i] - trail_atr_k_cat * bar_atr.iloc[i])
                        trail_activated = True
                elif in_pos < 0:
                    sl_dist = sl_px - entry_px if sl_px is not None else None
                    if sl_dist and (entry_px - prices.iloc[i]) >= 2.0 * sl_dist:
                        sl_px = min(sl_px or np.inf, prices.iloc[i] + trail_atr_k_cat * bar_atr.iloc[i])
                        trail_activated = True

            # Check time stops
            time_stop_hit = False
            if entry_bar != -1:
                bars_held = i - entry_bar
                if current_source == "cat" and time_stop_bars_cat is not None and bars_held >= time_stop_bars_cat:
                    time_stop_hit = True
                elif current_source == "vsb" and time_stop_bars_vsb is not None and bars_held >= time_stop_bars_vsb:
                    time_stop_hit = True

            if hit_tp or hit_sl or time_stop_hit:
                # Preserve source at exit bar for diagnostics
                source.iloc[i] = current_source
                managed.iloc[i] = 0
                
                if hit_tp:
                    exit_reason.iloc[i] = "tp"
                elif hit_sl:
                    exit_reason.iloc[i] = "sl"
                    daily_sl_hits[day] += 1
                    # Set cooldown for strategy that lost
                    cooldown_active[current_source] = cooldown_bars
                elif time_stop_hit:
                    exit_reason.iloc[i] = "time"
                
                # Flat after exit
                in_pos = 0
                entry_px = sl_px = tp_px = None
                entry_bar = -1
                current_source = ""
                trail_activated = False
            else:
                # Remain in position
                managed.iloc[i] = in_pos
                # propagate source while in position
                source.iloc[i] = current_source
                
                # Opposite signal exit after minimum hold
                if entry_bar != -1 and (i - entry_bar) >= min_hold_bars:
                    if in_pos == 1 and (sig_cat.iloc[i] == -1 or sig_vsb.iloc[i] == -1):
                        managed.iloc[i] = 0
                        exit_reason.iloc[i] = "opposite_signal"
                        source.iloc[i] = current_source
                        in_pos = 0
                        entry_px = sl_px = tp_px = None
                        entry_bar = -1
                        current_source = ""
                        trail_activated = False
                    elif in_pos == -1 and (sig_cat.iloc[i] == 1 or sig_vsb.iloc[i] == 1):
                        managed.iloc[i] = 0
                        exit_reason.iloc[i] = "opposite_signal"
                        source.iloc[i] = current_source
                        in_pos = 0
                        entry_px = sl_px = tp_px = None
                        entry_bar = -1
                        current_source = ""
                        trail_activated = False

    return managed, exit_reason, source


def build_concurrent_signals(
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    sig_cat_1h: pd.Series,
    sig_vsb_4h: pd.Series,
    sl_atr_k_cat: float = 1.5,
    tp_atr_k_cat: float = 6.0,
    sl_atr_k_vsb: float = 1.8,
    tp_atr_k_vsb: float = 5.5,
    time_stop_bars_cat: int = 168,  # 7 days on 1h
    time_stop_bars_vsb: int = 30,   # 5 days on 4h
    trail_atr_k_cat: float = 1.5,
    max_exposure: float = 1.25,
    funding_1h: Optional[pd.Series] = None,
    enable_regime_scaling: bool = True,
    enable_quality_filter: bool = True,
    min_quality_threshold: float = 0.6,
    enable_adaptive_sizing: bool = True,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Build concurrent CAT (1h) + VSB (4h) positions with exposure cap.
    
    Returns:
    - combined_pos: Combined position series on 1h index  
    - combined_exit_reason: Exit reasons on 1h index
    - combined_source: Source attribution on 1h index
    """
    from bot.portfolio.ensemble import combine_positions
    
    # Apply regime-based scaling if enabled
    if enable_regime_scaling:
        from bot.indicators.regime import (
            trend_strength, volatility_regime, market_regime, 
            funding_sentiment, regime_multipliers
        )
        
        # Calculate regime indicators
        trend_str = trend_strength(df_1h, lookback=60)
        vol_regime = volatility_regime(df_1h, lookback=180)
        mkt_regime = market_regime(df_1h, short_ema=21, long_ema=100)
        fund_sentiment = funding_sentiment(funding_1h, lookback=168) if funding_1h is not None else pd.Series(0, index=df_1h.index)
        
        # Get regime multipliers
        multipliers = regime_multipliers(trend_str, vol_regime, mkt_regime, fund_sentiment)
        
        # Apply multipliers to SL/TP
        sl_mult = multipliers['sl_multiplier']
        tp_mult = multipliers['tp_multiplier']
        
        # Dynamic SL/TP for each strategy
        sl_atr_k_cat_adj = sl_atr_k_cat * sl_mult
        tp_atr_k_cat_adj = tp_atr_k_cat * tp_mult
        sl_atr_k_vsb_adj = sl_atr_k_vsb * sl_mult.reindex(df_4h.index, method='ffill').fillna(1.0)
        tp_atr_k_vsb_adj = tp_atr_k_vsb * tp_mult.reindex(df_4h.index, method='ffill').fillna(1.0)
    else:
        sl_atr_k_cat_adj = sl_atr_k_cat
        tp_atr_k_cat_adj = tp_atr_k_cat  
        sl_atr_k_vsb_adj = sl_atr_k_vsb
        tp_atr_k_vsb_adj = tp_atr_k_vsb
    
    # Apply quality filters to signals
    if enable_quality_filter:
        from bot.indicators.quality import high_quality_filter
        sig_cat_1h_filtered = high_quality_filter(df_1h, sig_cat_1h, funding_1h, min_quality_threshold)
        sig_vsb_4h_filtered = high_quality_filter(df_4h, sig_vsb_4h, None, min_quality_threshold)
    else:
        sig_cat_1h_filtered = sig_cat_1h
        sig_vsb_4h_filtered = sig_vsb_4h
    
    # Build individual managed signals
    cat_pos, cat_exit, cat_source = build_managed_signal(
        df_1h, sig_cat_1h_filtered, pd.Series(0, index=df_1h.index),  # No VSB on 1h
        sl_atr_k_cat=sl_atr_k_cat_adj if not enable_regime_scaling else sl_atr_k_cat_adj.mean(),
        tp_atr_k_cat=tp_atr_k_cat_adj if not enable_regime_scaling else tp_atr_k_cat_adj.mean(),
        sl_atr_k_vsb=sl_atr_k_vsb, tp_atr_k_vsb=tp_atr_k_vsb,
        time_stop_bars_cat=time_stop_bars_cat,
        trail_atr_k_cat=trail_atr_k_cat,
        max_daily_sl_hits=2, cooldown_bars=4
    )
    
    vsb_pos, vsb_exit, vsb_source = build_managed_signal(
        df_4h, pd.Series(0, index=df_4h.index), sig_vsb_4h_filtered,  # No CAT on 4h
        sl_atr_k_cat=sl_atr_k_cat, tp_atr_k_cat=tp_atr_k_cat,
        sl_atr_k_vsb=sl_atr_k_vsb_adj if not enable_regime_scaling else sl_atr_k_vsb_adj.mean(),
        tp_atr_k_vsb=tp_atr_k_vsb_adj if not enable_regime_scaling else tp_atr_k_vsb_adj.mean(),
        time_stop_bars_vsb=time_stop_bars_vsb,
        max_daily_sl_hits=2, cooldown_bars=1  # 4h bars
    )
    
    # Resample VSB 4h signals to 1h
    vsb_pos_1h = vsb_pos.reindex(df_1h.index, method='ffill').fillna(0)
    vsb_exit_1h = vsb_exit.reindex(df_1h.index, method='ffill').fillna('')
    vsb_source_1h = vsb_source.reindex(df_1h.index, method='ffill').fillna('')
    
    # Combine positions with exposure cap
    pos_map = {"cat": cat_pos, "vsb": vsb_pos_1h}
    combined_pos = combine_positions(pos_map, max_exposure=max_exposure)
    
    # Combine exit reasons and sources (prioritize non-empty)
    combined_exit_reason = pd.Series('', index=df_1h.index)
    combined_source = pd.Series('', index=df_1h.index)
    
    for i in range(len(df_1h.index)):
        # Exit reason: use first non-empty
        if cat_exit.iloc[i] != '':
            combined_exit_reason.iloc[i] = f"cat_{cat_exit.iloc[i]}"
        elif vsb_exit_1h.iloc[i] != '':
            combined_exit_reason.iloc[i] = f"vsb_{vsb_exit_1h.iloc[i]}"
            
        # Source: combine active sources
        sources = []
        if cat_source.iloc[i] != '':
            sources.append("cat")
        if vsb_source_1h.iloc[i] != '':
            sources.append("vsb")
        combined_source.iloc[i] = "+".join(sources)
    
    return combined_pos, combined_exit_reason, combined_source


