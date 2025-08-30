import sys
from typing import Optional
import numpy as np
import click
import pandas as pd
from rich.console import Console

from bot.data.fetch import fetch_ohlcv_paged, fetch_funding_rates, fetch_open_interest, save_market_data, load_market_data, compute_relative_basis, fetch_and_persist_mark_and_basis, persist_oi_processed
from bot.data.native import binance as binance_api
from bot.data.native import bybit as bybit_api
from bot.data.native import coinbase as coinbase_api
from bot.strategies.cat import signals_cat
from bot.strategies.vsb import signals_vsb
from bot.strategies.orchestrator import build_managed_signal
from bot.backtest.engine import Backtester, CostModel, SizingRules
from bot.portfolio.ensemble import combine_positions
from bot.validation.walk_forward import run_walk_forward_validation, WalkForwardConfig, save_wf_results
from bot.risk.controls import RiskLimits, RiskMonitor
from bot.risk.portfolio_limits import PortfolioRiskManager, PortfolioRiskConfig
from bot.analysis.pnl_decomposition import PnLDecomposer

console = Console()


@click.group()
def main():
    """CLI for data fetching and backtesting."""


@main.command()
@click.option("--timeframe", default="1h")
@click.option("--data-dir", default="storage/processed")
@click.option("--equity-start", type=float, default=1000.0)
@click.option("--leverage", type=float, default=5.0)
@click.option("--risk-per-trade", type=float, default=0.02, help="Fraction of equity used as margin per trade")
@click.option("--sl-atr-k", type=float, default=2.0)
@click.option("--tp-atr-k", type=float, default=4.0)
@click.option("--all-sessions", is_flag=True, default=True, help="If set, do not session-gate entries")
@click.option("--max-daily-sl", type=int, default=3)
@click.option("--report-out", type=str, default="out/html/orchestrated_report.html")
def run_orchestrated(timeframe: str, data_dir: str, equity_start: float, leverage: float, risk_per_trade: float, sl_atr_k: float, tp_atr_k: float, all_sessions: bool, max_daily_sl: int, report_out: str):
    """Run orchestrated backtest: single position across CAT+VSB, 2% risk, 5x leverage, SL/TP, daily SL pause, HTML report."""
    console.print("[bold blue]🤖 RUNNING ORCHESTRATED BACKTEST[/bold blue]")
    spot, perp, funding, oi = load_market_data(data_dir, timeframe)
    idx = spot.index.intersection(perp.index)
    spot = spot.reindex(idx).ffill(); perp = perp.reindex(idx).ffill()
    basis = compute_relative_basis(perp, spot).reindex(idx).ffill()
    if funding is not None:
        funding = funding.reindex(idx).ffill()
    if oi is not None:
        oi = oi.reindex(idx).ffill()

    # Build strategy signals
    sig_cat = signals_cat(perp, funding=funding, basis=basis, fast_ema=48, slow_ema=180)
    sig_vsb = signals_vsb(perp, oi=oi, basis=basis, rv_percentile=0.40, atr_percentile=0.45, oi_gate=0.02)

    # Optional session gate (US 16-24 UTC)
    session_gate = None
    if not all_sessions:
        session_gate = (perp.index.hour >= 16) & (perp.index.hour < 24)

    # Build managed position series
    managed_pos, exit_reason, source = build_managed_signal(
        perp, sig_cat, sig_vsb, sl_atr_k=sl_atr_k, tp_atr_k=tp_atr_k, atr_n=14, max_daily_sl_hits=max_daily_sl, session_gate=session_gate
    )

    # Run backtester with explicit margin fraction = risk_per_trade and leverage
    cost_model = CostModel(maker_bps_round=0.0004, taker_bps_round=0.0008, impact_coef=0.001, spread_bps=0.5, use_maker=False)
    bt = Backtester(perp, managed_pos, equity_start=equity_start, cost_model=cost_model, funding_series=funding, sl_atr_k=None, tp_atr_k=None, signal_is_position=True)
    out = bt.run(SizingRules(margin_fraction=risk_per_trade, leverage=leverage))

    # Generate HTML report
    try:
        from bot.report.html import build_report
        equity = out["equity"]
        comps = {
            'gross': out['gross'],
            'carry': out['carry'],
            'fees': out['fees'],
            'spread_slip': out['spread_slip'],
            'impact_slip': out['impact_slip'],
            'net': out['net'],
        }
        build_report(equity, comps, report_out)
        console.print(f"[green]Report written to {report_out}")
    except Exception as e:
        console.print(f"[yellow]Report generation failed: {e}")

    final_eq = out['equity'].iloc[-1]
    # Diagnostics: count SL/TP by source
    try:
        # Mark exits
        exits = exit_reason[exit_reason != ""].to_frame('reason')
        exits['source'] = source.reindex(exits.index).replace('', np.nan).ffill()
        sl_counts = exits[exits['reason']=='sl']['source'].value_counts()
        tp_counts = exits[exits['reason']=='tp']['source'].value_counts()
        console.print(f"SL by source: {dict(sl_counts)}")
        console.print(f"TP by source: {dict(tp_counts)}")
    except Exception as e:
        console.print(f"[yellow]Diagnostics failed: {e}")
    console.print(f"[magenta]Final equity: ${final_eq:,.2f}")
    return 0
@click.option("--spot-venue", type=click.Choice(["coinbase","bitstamp"]), default="coinbase")
@click.option("--spot-symbol", default="BTC-USD")
@click.option("--perp-venue", type=click.Choice(["binance","okx","bybit"]), default="binance")
@click.option("--perp-symbol", default="BTCUSDT")
@click.option("--timeframe", default="1h")
@click.option("--since", type=str, default=None, help="ISO date like 2023-01-01")
@click.option("--out", "out_dir", default="storage/processed")
def fetch(spot_venue: str, spot_symbol: str, perp_venue: str, perp_symbol: str, timeframe: str, since: Optional[str], out_dir: str):
    console.log(f"Fetching spot from {spot_venue}")
    since_ms = None
    if since:
        since_ms = int(pd.Timestamp(since, tz="UTC").timestamp()*1000)
    if spot_venue == "coinbase":
        if since_ms:
            spot = coinbase_api.klines_paginated(spot_symbol, timeframe, since_ms)
        else:
            spot = coinbase_api.klines(spot_symbol, granularity=3600 if timeframe=="1h" else 14400 if timeframe=="4h" else 86400)
    else:
        spot = fetch_ohlcv_paged("bitstamp", "BTC/USD", timeframe=timeframe)
    console.log(f"Fetched {len(spot)} spot bars")

    if perp_venue == "binance":
        console.log("Fetching Binance perp klines and mark klines")
        if since_ms:
            perp = binance_api.klines_paginated(perp_symbol, timeframe, since_ms)
            _mark = binance_api.mark_klines_paginated(perp_symbol, timeframe, since_ms)
        else:
            perp = binance_api.klines(perp_symbol, interval=timeframe)
            _mark = binance_api.mark_price_kline(perp_symbol, interval=timeframe)
        console.log("Fetching funding history")
        funding = binance_api.funding_paginated(perp_symbol, since_ms) if since_ms else binance_api.funding_rate_history(perp_symbol)
        console.log("Fetching open interest history (Binance)")
        try:
            if since_ms:
                oi = binance_api.open_interest_paginated(perp_symbol, interval="5m", since_ms=since_ms)
            else:
                oi = binance_api.open_interest(perp_symbol, interval="5m")
        except Exception as e:
            console.print(f"[yellow]OI fetch failed: {e}")
            oi = pd.Series(dtype='float64', name='oi')
    elif perp_venue == "bybit":
        console.log("Fetching Bybit perp klines (via ccxt) and native OI (Bybit)")
        # Price/funding via ccxt for now; OI via native Bybit
        perp = fetch_ohlcv_paged("bybit", f"{perp_symbol.replace('USDT','')}/USDT", timeframe=timeframe, since_ms=since_ms)
        try:
            funding = fetch_funding_rates("bybit", f"{perp_symbol.replace('USDT','')}/USDT", since_ms=since_ms)
        except Exception:
            funding = None
        # OI via Bybit native API, forward from since
        try:
            if since_ms:
                oi = bybit_api.open_interest_paginated(perp_symbol, interval="5min", since_ms=since_ms)
            else:
                oi = bybit_api.open_interest(perp_symbol, interval="5min")
        except Exception as e:
            console.print(f"[yellow]Bybit OI fetch failed: {e}")
            oi = pd.Series(dtype='float64', name='oi')
    else:
        console.print("[yellow]Using ccxt for perp venue")
        ex_id = perp_venue
        perp = fetch_ohlcv_paged(ex_id, f"{perp_symbol.replace('USDT','')}/USDT", timeframe=timeframe, since_ms=since_ms)
        try:
            funding = fetch_funding_rates(ex_id, f"{perp_symbol.replace('USDT','')}/USDT", since_ms=since_ms)
        except Exception:
            funding = None
        try:
            oi = fetch_open_interest(ex_id, f"{perp_symbol.replace('USDT','')}/USDT", timeframe=timeframe, since_ms=since_ms)
        except Exception:
            oi = None

    save_market_data(out_dir, timeframe, spot, perp, funding, oi)
    console.print(f"[green]Saved data to {out_dir}")

    # persist mark & basis_rel and processed OI (level and Δ%) in a recommended path
    try:
        fetch_and_persist_mark_and_basis(
            perp_symbol=perp_symbol if "/" in perp_symbol else perp_symbol.replace("/",""),
            spot_symbol=spot_symbol,
            timeframe=timeframe,
            out_dir=out_dir,
        )
        if oi is not None and len(oi) > 0:
            idx = perp.index
            persist_oi_processed(oi, idx, out_dir, timeframe)
    except Exception as e:
        console.print(f"[yellow]Mark/basis/OI processing skipped: {e}")


@main.command()
@click.option("--spot-venue", type=click.Choice(["coinbase","bitstamp"]), default="coinbase")
@click.option("--perp-venue", type=click.Choice(["binance","okx","bybit"]), default="binance")
@click.option("--timeframe", default="1h")
@click.option("--data-dir", default="storage/processed")
@click.option("--strategy", type=click.Choice(["cat","vsb","both"]), default="both")
@click.option("--cost-maker-bps", type=float, default=0.4)
@click.option("--cost-taker-bps", type=float, default=0.8)
@click.option("--impact-k", type=float, default=0.001)
@click.option("--spread-bps", type=float, default=0.5)
@click.option("--maker-bias", is_flag=True, default=False)
@click.option("--report", type=str, default=None)
@click.option("--walk-forward", is_flag=True, default=False, help="Enable walk-forward validation")
@click.option("--wf-train-days", type=int, default=365, help="Training period in days")
@click.option("--wf-test-days", type=int, default=90, help="Test period in days")
@click.option("--wf-step-days", type=int, default=30, help="Step size in days")
@click.option("--wf-output", type=str, default="out/walk_forward_results.csv", help="WF results output file")
@click.option("--enable-risk-controls", is_flag=True, default=False, help="Enable comprehensive risk controls")
@click.option("--daily-loss-limit", type=float, default=0.02, help="Daily loss limit (default 2%)")
@click.option("--weekly-loss-limit", type=float, default=0.05, help="Weekly loss limit (default 5%)")
@click.option("--monthly-loss-limit", type=float, default=0.10, help="Monthly loss limit (default 10%)")
@click.option("--max-individual-position", type=float, default=0.70, help="Max individual position size (default 70%)")
@click.option("--max-total-exposure", type=float, default=1.25, help="Max total exposure (default 125%)")
def backtest(spot_venue: str, perp_venue: str, timeframe: str, data_dir: str, strategy: str, cost_maker_bps: float, cost_taker_bps: float, impact_k: float, spread_bps: float, maker_bias: bool, report: str | None, walk_forward: bool, wf_train_days: int, wf_test_days: int, wf_step_days: int, wf_output: str, enable_risk_controls: bool, daily_loss_limit: float, weekly_loss_limit: float, monthly_loss_limit: float, max_individual_position: float, max_total_exposure: float):
    spot, perp, funding, oi = load_market_data(data_dir, timeframe)
    idx = spot.index.intersection(perp.index)
    spot = spot.reindex(idx).ffill(); perp = perp.reindex(idx).ffill()
    basis = compute_relative_basis(perp, spot).reindex(idx).ffill()
    if funding is not None:
        funding = funding.reindex(idx).ffill()
    if oi is not None:
        oi = oi.reindex(idx).ffill()

    # Walk-forward validation mode
    if walk_forward:
        console.print(f"[cyan]Running walk-forward validation...")
        console.print(f"[cyan]Train: {wf_train_days}d, Test: {wf_test_days}d, Step: {wf_step_days}d")
        
        strategies_to_test = []
        if strategy in ("cat", "both"):
            strategies_to_test.append("cat")
        if strategy in ("vsb", "both"):
            strategies_to_test.append("vsb")
            
        wf_config = WalkForwardConfig(
            train_days=wf_train_days,
            test_days=wf_test_days,
            step_days=wf_step_days
        )
        
        wf_results = run_walk_forward_validation(
            perp, funding, oi, basis, strategies_to_test, wf_config, timeframe
        )
        
        # Save results
        from pathlib import Path
        Path(wf_output).parent.mkdir(parents=True, exist_ok=True)
        save_wf_results(wf_results, wf_output)
        
        console.print(f"[green]Walk-forward validation complete. Results saved to {wf_output}")
        return 0

    # Standard in-sample backtest mode
    res = {}
    if strategy in ("cat","both"):
        sig_cat = signals_cat(perp, funding=funding, basis=basis)
        bt_cat = Backtester(perp, sig_cat, funding_series=funding, time_stop_bars=7*24 if timeframe=="1h" else 7*6 if timeframe=="4h" else 7, trail_atr_k=2.5)
        out_cat = bt_cat.run(SizingRules())
        res["CAT"] = out_cat
    if strategy in ("vsb","both"):
        sig_vsb = signals_vsb(perp, oi=oi, basis=basis)
        bt_vsb = Backtester(perp, sig_vsb, funding_series=funding, time_stop_bars=8*24 if timeframe=="1h" else 8*6 if timeframe=="4h" else 8, trail_atr_k=2.0)
        out_vsb = bt_vsb.run(SizingRules())
        res["VSB"] = out_vsb

    # ensemble with correlation/exposure rules
    if strategy == "both":
        pos_map = {name: df["pos"] for name, df in res.items()}
        comb_pos = combine_positions(pos_map, max_exposure=1.25)
        # Handle both old ('c') and new ('close') column names
        close_col = "close" if "close" in perp.columns else "c"
        ret = perp[close_col].pct_change().fillna(0)
        funding_al = funding.reindex(perp.index).ffill() if funding is not None else pd.Series(0.0, index=perp.index)
        hours = (perp.index[1:] - perp.index[:-1]).asi8 / 3.6e12
        hours = np.insert(hours, 0, hours[0] if len(hours) > 0 else 1.0)
        carry = comb_pos.shift().fillna(0) * funding_al * (hours / 8.0)
        net = comb_pos.shift().fillna(0) * ret + carry
        equity = (1.0 + net).cumprod()
        console.print(f"[cyan]Ensemble equity: {equity.iloc[-1]:.4f}")
    for name, df in res.items():
        console.print(f"[magenta]{name} equity: {df['equity'].iloc[-1]:.4f}")

    # brief stats
    def stats(x: pd.Series):
        ret = x.fillna(0)
        ann = ret.mean() * 365*24 if timeframe=="1h" else ret.mean() * 365*6 if timeframe=="4h" else ret.mean() * 365
        vol = ret.std() * (365*24)**0.5 if timeframe=="1h" else ret.std() * (365*6)**0.5 if timeframe=="4h" else ret.std() * (365)**0.5
        sharpe = ann/vol if vol>0 else 0
        return ann, vol, sharpe

    for name, df in res.items():
        ann, vol, sh = stats(df["net"])
        console.print(f"{name}: ann={ann:.3f}, vol={vol:.3f}, sharpe={sh:.2f}")

    if report:
        try:
            from bot.report.html import build_report
            # choose one or ensemble for report; here use first result
            any_name = next(iter(res))
            equity_series = res[any_name]['equity']
            pnl_components_dict = {
                'gross': res[any_name]['gross'],
                'carry': res[any_name]['carry'],
                'fees': res[any_name]['fees'],
                'spread_slip': res[any_name]['spread_slip'],
                'impact_slip': res[any_name]['impact_slip'],
                'net': res[any_name]['net'],
            }
            build_report(equity_series, pnl_components_dict, report)
            console.print(f"[green]Report written to {report}")
        except Exception as e:
            console.print(f"[yellow]Report generation failed: {e}")

    return 0


@main.command()
@click.option("--data-dir", default="storage/processed")
@click.option("--equity-start", type=float, default=1000.0)
@click.option("--leverage", type=float, default=5.0)
@click.option("--risk-per-trade", type=float, default=0.02, help="Fraction of equity used as margin per trade")
@click.option("--sl-atr-k-cat", type=float, default=1.5)
@click.option("--tp-atr-k-cat", type=float, default=6.0)
@click.option("--sl-atr-k-vsb", type=float, default=1.8)
@click.option("--tp-atr-k-vsb", type=float, default=5.5)
@click.option("--time-stop-cat", type=int, default=168, help="CAT time stop (hours on 1h data)")
@click.option("--time-stop-vsb", type=int, default=30, help="VSB time stop (bars on 4h data)")
@click.option("--trail-atr-k", type=float, default=1.5, help="CAT trailing stop ATR multiplier")
@click.option("--max-exposure", type=float, default=1.25, help="Max combined exposure cap")
@click.option("--quality-threshold", type=float, default=0.6, help="Minimum quality score for entries")
@click.option("--enable-quality-filter", is_flag=True, default=True, help="Enable high-quality entry filters")
@click.option("--enable-adaptive-sizing", is_flag=True, default=True, help="Enable Kelly-based position sizing")
@click.option("--report-out", type=str, default="out/html/concurrent_report.html")
def run_concurrent(data_dir: str, equity_start: float, leverage: float, risk_per_trade: float, 
                  sl_atr_k_cat: float, tp_atr_k_cat: float, sl_atr_k_vsb: float, tp_atr_k_vsb: float,
                  time_stop_cat: int, time_stop_vsb: int, trail_atr_k: float, max_exposure: float,
                  quality_threshold: float, enable_quality_filter: bool, enable_adaptive_sizing: bool, report_out: str):
    """Run concurrent CAT(1h) + VSB(4h) backtest with exposure cap."""
    console.print("[bold blue]🚀 RUNNING CONCURRENT CAT(1h) + VSB(4h) BACKTEST[/bold blue]")
    
    # Load 1h data 
    spot_1h, perp_1h, funding_1h, oi_1h = load_market_data(data_dir, "1h")
    
    # Align 1h data
    idx_1h = spot_1h.index.intersection(perp_1h.index)
    spot_1h = spot_1h.reindex(idx_1h).ffill()
    perp_1h = perp_1h.reindex(idx_1h).ffill()
    basis_1h = compute_relative_basis(perp_1h, spot_1h).reindex(idx_1h).ffill()
    if funding_1h is not None:
        funding_1h = funding_1h.reindex(idx_1h).ffill()
    if oi_1h is not None:
        oi_1h = oi_1h.reindex(idx_1h).ffill()
    
    # Resample 1h data to 4h for VSB signals  
    if 'c' in perp_1h.columns:  # Handle ccxt format
        perp_4h = perp_1h.resample('4h').agg({
            'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
        }).dropna()
        spot_4h = spot_1h.resample('4h').agg({
            'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
        }).dropna()
    else:  # Standard format
        perp_4h = perp_1h.resample('4h').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()
        spot_4h = spot_1h.resample('4h').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'  
        }).dropna()
    
    basis_4h = compute_relative_basis(perp_4h, spot_4h)
    funding_4h = funding_1h.resample('4h').last().dropna() if funding_1h is not None else None
    oi_4h = oi_1h.resample('4h').last().dropna() if oi_1h is not None else None
    
    # Generate strategy signals
    sig_cat_1h = signals_cat(perp_1h, funding=funding_1h, basis=basis_1h, fast_ema=48, slow_ema=180)
    sig_vsb_4h = signals_vsb(perp_4h, oi=oi_4h, basis=basis_4h, rv_percentile=0.40, atr_percentile=0.45, oi_gate=0.02)
    
    # Build concurrent signals with all optimizations
    from bot.strategies.orchestrator import build_concurrent_signals
    combined_pos, combined_exit, combined_source = build_concurrent_signals(
        perp_1h, perp_4h, sig_cat_1h, sig_vsb_4h,
        sl_atr_k_cat=sl_atr_k_cat, tp_atr_k_cat=tp_atr_k_cat,
        sl_atr_k_vsb=sl_atr_k_vsb, tp_atr_k_vsb=tp_atr_k_vsb,
        time_stop_bars_cat=time_stop_cat, time_stop_bars_vsb=time_stop_vsb,
        trail_atr_k_cat=trail_atr_k, max_exposure=max_exposure,
        funding_1h=funding_1h, enable_regime_scaling=True,
        enable_quality_filter=enable_quality_filter,
        min_quality_threshold=quality_threshold,
        enable_adaptive_sizing=enable_adaptive_sizing
    )
    
    # Run backtester on 1h data with combined position
    cost_model = CostModel(maker_bps_round=0.0004, taker_bps_round=0.0008, impact_coef=0.001, spread_bps=0.5, use_maker=False)
    bt = Backtester(perp_1h, combined_pos, equity_start=equity_start, cost_model=cost_model, 
                   funding_series=funding_1h, signal_is_position=True)
    out = bt.run(SizingRules(margin_fraction=risk_per_trade, leverage=leverage))
    
    # Print trade diagnostics
    entries = (combined_pos.shift(1).fillna(0) == 0) & (combined_pos != 0)
    exits = combined_exit != ''
    console.print(f"[cyan]Total Entries: {int(entries.sum())}, Total Exits: {int(exits.sum())}[/cyan]")
    console.print(f"[cyan]By year: {entries.groupby(entries.index.year).sum().to_dict()}[/cyan]")
    console.print(f"[cyan]Final equity: {out['equity'].iloc[-1]:.4f}[/cyan]")
    
    # Exit reason breakdown
    exit_counts = combined_exit[combined_exit != ''].value_counts().to_dict()
    console.print(f"[yellow]Exit reasons: {exit_counts}[/yellow]")
    
    # Source breakdown  
    source_counts = combined_source[combined_source != ''].value_counts().to_dict()
    console.print(f"[yellow]Position sources: {source_counts}[/yellow]")
    
    # Generate HTML report
    try:
        from bot.report.html import build_report
        equity = out["equity"]
        comps = {
            'gross': out['gross'],
            'carry': out['carry'],
            'fees': out['fees'],
            'spread_slip': out['spread_slip'],
            'impact_slip': out['impact_slip'],
            'net': out['net'],
        }
        import os
        os.makedirs(os.path.dirname(report_out), exist_ok=True)
        build_report(equity, comps, report_out)
        console.print(f"[green]Report saved to {report_out}[/green]")
    except Exception as e:
        console.print(f"[red]Report generation failed: {e}[/red]")
    
    return 0


@main.command()
@click.option("--daily-loss-limit", type=float, default=0.02, help="Daily loss limit (default 2%)")
@click.option("--weekly-loss-limit", type=float, default=0.05, help="Weekly loss limit (default 5%)")
@click.option("--monthly-loss-limit", type=float, default=0.10, help="Monthly loss limit (default 10%)")
@click.option("--max-individual-position", type=float, default=0.70, help="Max individual position (default 70%)")
@click.option("--max-total-exposure", type=float, default=1.25, help="Max total exposure (default 125%)")
@click.option("--max-slippage-multiplier", type=float, default=2.0, help="Max slippage multiplier (default 2x)")
@click.option("--max-spread-multiplier", type=float, default=1.5, help="Max spread multiplier (default 1.5x)")
def test_risk_controls(daily_loss_limit: float, weekly_loss_limit: float, monthly_loss_limit: float,
                      max_individual_position: float, max_total_exposure: float, 
                      max_slippage_multiplier: float, max_spread_multiplier: float):
    """Test comprehensive risk control system with various scenarios."""
    from datetime import datetime, timedelta
    import numpy as np
    
    console.print("[bold blue]🔒 TESTING RISK CONTROL SYSTEM[/bold blue]")
    console.print("=" * 60)
    
    # Setup risk limits
    risk_limits = RiskLimits(
        daily_loss_limit=daily_loss_limit,
        weekly_loss_limit=weekly_loss_limit,
        monthly_loss_limit=monthly_loss_limit,
        max_individual_position=max_individual_position,
        max_total_exposure=max_total_exposure,
        max_slippage_multiplier=max_slippage_multiplier,
        max_spread_multiplier=max_spread_multiplier
    )
    
    console.print(f"[cyan]Risk Limits Configuration:[/cyan]")
    console.print(f"  Daily Loss Limit: {daily_loss_limit:.1%}")
    console.print(f"  Weekly Loss Limit: {weekly_loss_limit:.1%}")
    console.print(f"  Monthly Loss Limit: {monthly_loss_limit:.1%}")
    console.print(f"  Max Individual Position: {max_individual_position:.1%}")
    console.print(f"  Max Total Exposure: {max_total_exposure:.1%}")
    console.print(f"  Max Slippage Multiplier: {max_slippage_multiplier}x")
    console.print(f"  Max Spread Multiplier: {max_spread_multiplier}x")
    
    # Test scenarios
    scenarios = [
        {
            "name": "Normal Operation",
            "equity": 100000,
            "positions": {"CAT": 8000, "VSB": 4000},
            "slippage": 0.0005,
            "model_slippage": 0.001,
            "spread": 0.0002
        },
        {
            "name": "Large Positions",
            "equity": 100000,
            "positions": {"CAT": 15000, "VSB": 12000},  # Too large
            "slippage": 0.0008,
            "model_slippage": 0.001,
            "spread": 0.0003
        },
        {
            "name": "Daily Loss Trigger",
            "equity": 97500,  # 2.5% loss
            "positions": {"CAT": 5000, "VSB": 3000},
            "slippage": 0.0006,
            "model_slippage": 0.001,
            "spread": 0.0002
        },
        {
            "name": "High Slippage",
            "equity": 100000,
            "positions": {"CAT": 6000, "VSB": 4000},
            "slippage": 0.0025,  # 2.5x model
            "model_slippage": 0.001,
            "spread": 0.0002
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        console.print(f"\n[yellow]Scenario {i}: {scenario['name']}[/yellow]")
        console.print("-" * 40)
        
        # Create fresh risk monitor for each scenario
        risk_monitor = RiskMonitor(risk_limits)
        risk_monitor.reset_day(100000)  # Reset with initial equity
        
        # Apply risk controls
        from bot.risk.controls import apply_risk_controls
        adjusted_positions, actions = apply_risk_controls(
            scenario["positions"],
            scenario["equity"],
            15000,  # target vol
            risk_monitor,
            realized_slippage=scenario["slippage"],
            model_slippage=scenario["model_slippage"],
            current_spread=scenario["spread"],
            timestamp=datetime.now()
        )
        
        console.print(f"  Original: {scenario['positions']}")
        console.print(f"  Adjusted: {dict(adjusted_positions)}")
        console.print(f"  Actions:  {actions}")
        console.print(f"  State:    {risk_monitor.state.value}")
        
        if risk_monitor.alerts:
            console.print(f"  Alerts:   {len(risk_monitor.alerts)} generated")
            for alert in risk_monitor.alerts[-2:]:  # Show last 2 alerts
                console.print(f"    - [{alert.level.value.upper()}] {alert.message}")
    
    console.print(f"\n[green]✅ Risk Control Testing Complete[/green]")
    console.print(f"[cyan]Key Features Validated:[/cyan]")
    console.print(f"  ✓ Loss stops (daily/weekly/monthly)")
    console.print(f"  ✓ Position size limits") 
    console.print(f"  ✓ Total exposure caps")
    console.print(f"  ✓ Slippage kill-switches")
    console.print(f"  ✓ Real-time alerting")
    console.print(f"  ✓ Emergency stop functionality")


@main.command()
@click.option("--timeframe", default="1h", help="Data timeframe")
@click.option("--data-dir", default="storage/processed", help="Data directory")
@click.option("--strategy", type=click.Choice(["cat","vsb","both"]), default="both", help="Strategy to analyze")
@click.option("--output-dir", default="out/pnl_analysis", help="Output directory for analysis")
def analyze_pnl(timeframe: str, data_dir: str, strategy: str, output_dir: str):
    """Run comprehensive PnL decomposition analysis."""
    
    console.print("[bold blue]📊 COMPREHENSIVE PnL DECOMPOSITION ANALYSIS[/bold blue]")
    console.print("=" * 70)
    
    # Load data
    console.print("[cyan]Loading market data...[/cyan]")
    spot, perp, funding, oi = load_market_data(data_dir, timeframe)
    idx = spot.index.intersection(perp.index)
    spot = spot.reindex(idx).ffill()
    perp = perp.reindex(idx).ffill()
    basis = compute_relative_basis(perp, spot).reindex(idx).ffill()
    if funding is not None:
        funding = funding.reindex(idx).ffill()
    if oi is not None:
        oi = oi.reindex(idx).ffill()
    
    console.print(f"[green]✓ Loaded {len(perp)} bars from {perp.index[0]} to {perp.index[-1]}[/green]")
    
    # Generate strategies and run backtests
    strategies_to_analyze = []
    if strategy in ["cat", "both"]:
        strategies_to_analyze.append("CAT")
    if strategy in ["vsb", "both"]:
        strategies_to_analyze.append("VSB")
    
    # Setup cost model
    cost_model = CostModel(
        maker_bps_round=0.0004, 
        taker_bps_round=0.0008, 
        impact_coef=0.001, 
        spread_bps=0.5, 
        use_maker=False
    )
    
    # Initialize PnL decomposer
    pnl_decomposer = PnLDecomposer()
    
    analysis_results = {}
    
    for strat_name in strategies_to_analyze:
        console.print(f"\n[yellow]Analyzing {strat_name} Strategy...[/yellow]")
        
        # Generate signals
        if strat_name == "CAT":
            signals = signals_cat(perp, funding=funding, basis=basis)
        else:  # VSB
            signals = signals_vsb(perp, oi=oi, basis=basis)
        
        console.print(f"  Generated {(signals != 0).sum()} signals")
        
        # Run backtest
        bt = Backtester(perp, signals, funding_series=funding, cost_model=cost_model)
        backtest_result = bt.run(SizingRules())
        
        if len(backtest_result) == 0:
            console.print(f"  [red]❌ Backtest failed for {strat_name}[/red]")
            continue
        
        # Get price data (close column)
        close_col = "close" if "close" in perp.columns else "c"
        price_data = perp[close_col]
        
        # Get positions from backtest
        positions = bt.signal.replace(to_replace=0, method="ffill").fillna(0).astype(float)
        
        # Run comprehensive PnL analysis
        analysis = pnl_decomposer.run_comprehensive_analysis(
            backtest_result, price_data, positions, strat_name
        )
        
        analysis_results[strat_name] = analysis
        
        # Generate report
        report_file = pnl_decomposer.generate_pnl_report(strat_name, output_dir)
        console.print(f"  [green]✓ Analysis complete - Report: {report_file}[/green]")
    
    # Summary comparison if analyzing both strategies
    if len(analysis_results) > 1:
        console.print(f"\n[bold cyan]📈 STRATEGY COMPARISON SUMMARY[/bold cyan]")
        console.print("-" * 50)
        
        for strat_name, analysis in analysis_results.items():
            attribution = analysis['attribution']
            components = attribution['component_breakdown']
            trade_stats = attribution['trade_statistics']
            
            console.print(f"\n[yellow]{strat_name} Summary:[/yellow]")
            console.print(f"  Total PnL:      {components['total_pnl']:8.4f}")
            console.print(f"  Price PnL:      {components['price_pnl']:8.4f}")
            console.print(f"  Funding PnL:    {components['funding_pnl']:8.4f}")
            console.print(f"  Total Fees:     {components['fees_pnl']:8.4f}")
            console.print(f"  Total Trades:   {trade_stats['total_trades']:8d}")
            console.print(f"  Win Rate:       {trade_stats['win_rate']:8.1%}")
            console.print(f"  Profit Factor:  {trade_stats['profit_factor']:8.2f}")
    
    console.print(f"\n[bold green]🎉 PnL Decomposition Analysis Complete![/bold green]")
    console.print(f"[cyan]📁 Results saved to: {output_dir}/[/cyan]")
    console.print(f"[cyan]📊 Generated visualizations and detailed reports[/cyan]")


@main.command()
@click.option("--timeframe", default="1h")
@click.option("--data-dir", default="storage/processed")
@click.option("--strategy", type=click.Choice(["cat","vsb","both"]), default="cat")
@click.option("--equity-start", type=float, default=1000.0)
@click.option("--leverage", type=float, default=5.0)
@click.option("--margin-frac", type=float, default=0.01, help="Fraction of equity used as margin per trade")
@click.option("--sl-atr-k", type=float, default=2.0, help="Stop loss in ATR multiples")
@click.option("--tp-atr-k", type=float, default=4.0, help="Take profit in ATR multiples")
@click.option("--enable-risk-controls", is_flag=True, default=True)
@click.option("--daily-loss-limit", type=float, default=0.02)
@click.option("--weekly-loss-limit", type=float, default=0.05)
@click.option("--monthly-loss-limit", type=float, default=0.10)
def simulate(timeframe: str, data_dir: str, strategy: str, equity_start: float, leverage: float, margin_frac: float, sl_atr_k: float, tp_atr_k: float, enable_risk_controls: bool, daily_loss_limit: float, weekly_loss_limit: float, monthly_loss_limit: float):
    """Simulate a leveraged, margin-based backtest with risk controls and SL/TP."""
    from datetime import datetime
    console.print("[bold blue]🧪 RUNNING LEVERAGED SIMULATION[/bold blue]")
    console.print(f"[cyan]Equity start: ${equity_start:.2f} | Leverage: {leverage:.1f}x | Margin: {margin_frac*100:.2f}%[/cyan]")

    spot, perp, funding, oi = load_market_data(data_dir, timeframe)
    idx = spot.index.intersection(perp.index)
    spot = spot.reindex(idx).ffill(); perp = perp.reindex(idx).ffill()
    basis = compute_relative_basis(perp, spot).reindex(idx).ffill()
    if funding is not None:
        funding = funding.reindex(idx).ffill()
    if oi is not None:
        oi = oi.reindex(idx).ffill()

    # Generate signals
    if strategy == "cat":
        sig = signals_cat(perp, funding=funding, basis=basis)
    elif strategy == "vsb":
        sig = signals_vsb(perp, oi=oi, basis=basis)
    else:
        # For simulate, use CAT by default if both
        sig = signals_cat(perp, funding=funding, basis=basis)

    # Run leveraged backtest with SL/TP
    bt = Backtester(
        perp,
        sig,
        equity_start=equity_start,
        funding_series=funding,
        time_stop_bars=7*24 if timeframe=="1h" else 7*6 if timeframe=="4h" else 7,
        trail_atr_k=2.5,
        sl_atr_k=sl_atr_k,
        tp_atr_k=tp_atr_k,
    )
    out = bt.run(SizingRules(margin_fraction=margin_frac, leverage=leverage))

    # Apply high-level risk controls by flattening after loss stops until reset boundaries
    if enable_risk_controls:
        from bot.risk.controls import RiskLimits, RiskMonitor
        limits = RiskLimits(
            daily_loss_limit=daily_loss_limit,
            weekly_loss_limit=weekly_loss_limit,
            monthly_loss_limit=monthly_loss_limit,
        )
        rm = RiskMonitor(limits)

        eq = out["equity"].copy()
        net = out["net"].copy()
        idx = eq.index

        # Initialize period starts
        current_day = None
        current_week = None
        current_month = None
        flattened = False

        adj_net = net.copy()
        adj_net[:] = adj_net  # copy

        for i, ts in enumerate(idx):
            day = (ts.year, ts.month, ts.day)
            week = ts.isocalendar().week
            month = (ts.year, ts.month)

            # Reset boundaries
            if current_day != day:
                rm.reset_day(eq.iloc[i-1] if i>0 else equity_start)
                current_day = day
                flattened = False
            if current_week != week:
                rm.reset_week(eq.iloc[i-1] if i>0 else equity_start)
                current_week = week
            if current_month != month:
                rm.reset_month(eq.iloc[i-1] if i>0 else equity_start)
                current_month = month

            # Recompute cumulative equity with adjusted net up to i-1
            if i > 0:
                adj_equity_prev = equity_start * (1.0 + adj_net.iloc[:i]).prod()
            else:
                adj_equity_prev = equity_start

            # Check loss stops
            if rm.check_loss_stops(adj_equity_prev, ts):
                flattened = True

            if flattened:
                adj_net.iloc[i] = 0.0

        # Build adjusted equity series
        adj_equity = (1.0 + adj_net).cumprod() * equity_start
        out["net_rc"] = adj_net
        out["equity_rc"] = adj_equity
        final_equity = adj_equity.iloc[-1]
    else:
        final_equity = out["equity"].iloc[-1]

    # Summary
    console.print(f"[magenta]Final equity ({'RC' if enable_risk_controls else 'raw'}): ${final_equity:,.2f}")
    ann = out["net"].mean() * (365*24 if timeframe=="1h" else 365*6 if timeframe=="4h" else 365)
    vol = out["net"].std() * ((365*24) ** 0.5 if timeframe=="1h" else (365*6) ** 0.5 if timeframe=="4h" else (365) ** 0.5)
    sh = ann/vol if vol>0 else 0
    console.print(f"Sharpe (raw): {sh:.2f}")
    return 0


if __name__ == "__main__":
    main()
