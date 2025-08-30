from __future__ import annotations
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from bot.indicators.core import ema, realized_vol


@dataclass
class PnLComponents:
    """PnL decomposition by source."""
    price_pnl: pd.Series
    funding_pnl: pd.Series  
    fees_pnl: pd.Series
    spread_slippage_pnl: pd.Series
    impact_slippage_pnl: pd.Series
    net_pnl: pd.Series
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame for analysis."""
        return pd.DataFrame({
            'price_pnl': self.price_pnl,
            'funding_pnl': self.funding_pnl,
            'fees_pnl': self.fees_pnl,
            'spread_slippage_pnl': self.spread_slippage_pnl,
            'impact_slippage_pnl': self.impact_slippage_pnl,
            'net_pnl': self.net_pnl
        })


@dataclass  
class RegimeClassification:
    """Market regime classification."""
    trend_regime: pd.Series  # trend/chop
    vol_regime: pd.Series    # high/normal/low vol
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame."""
        return pd.DataFrame({
            'trend_regime': self.trend_regime,
            'vol_regime': self.vol_regime
        })


@dataclass
class SessionClassification:
    """Trading session classification."""
    session: pd.Series  # asia/europe/us
    day_of_week: pd.Series
    hour_of_day: pd.Series
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame."""
        return pd.DataFrame({
            'session': self.session,
            'day_of_week': self.day_of_week,
            'hour_of_day': self.hour_of_day
        })


@dataclass
class TradeAnalysis:
    """Individual trade analysis."""
    trade_returns: pd.Series
    trade_durations: pd.Series
    max_adverse_excursion: pd.Series  # MAE
    max_favorable_excursion: pd.Series  # MFE
    win_loss_flag: pd.Series
    trade_size: pd.Series
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame."""
        return pd.DataFrame({
            'trade_returns': self.trade_returns,
            'trade_durations': self.trade_durations,
            'mae': self.max_adverse_excursion,
            'mfe': self.max_favorable_excursion,
            'win_loss': self.win_loss_flag,
            'trade_size': self.trade_size
        })


class PnLDecomposer:
    """
    Comprehensive PnL decomposition and attribution analysis.
    
    Breaks down trading returns by:
    1. Source: Price PnL vs Funding vs Costs
    2. Regime: Trend/Chop, High/Low Vol
    3. Session: Asia/Europe/US, Day of Week
    4. Trade: Win/Loss distribution, MAE/MFE, Duration
    """
    
    def __init__(self):
        self.results = {}
        
    def decompose_pnl_components(
        self, 
        backtest_result: Dict[str, pd.Series]
    ) -> PnLComponents:
        """Decompose PnL into constituent components."""
        
        # Extract component series from backtest result
        price_pnl = backtest_result['gross'].fillna(0)
        funding_pnl = backtest_result['carry'].fillna(0)
        fees_pnl = -backtest_result['fees'].fillna(0)  # Fees are costs
        spread_slip_pnl = -backtest_result['spread_slip'].fillna(0)  # Slippage is cost
        impact_slip_pnl = -backtest_result['impact_slip'].fillna(0)  # Impact is cost
        net_pnl = backtest_result['net'].fillna(0)
        
        return PnLComponents(
            price_pnl=price_pnl,
            funding_pnl=funding_pnl,
            fees_pnl=fees_pnl,
            spread_slippage_pnl=spread_slip_pnl,
            impact_slippage_pnl=impact_slip_pnl,
            net_pnl=net_pnl
        )
    
    def classify_regimes(
        self, 
        price_data: pd.Series, 
        lookback_days: int = 60
    ) -> RegimeClassification:
        """Classify market regimes for attribution."""
        
        # Trend regime: EMA50 vs EMA200
        ema50 = ema(price_data, 50)
        ema200 = ema(price_data, 200)
        trend_regime = pd.Series('chop', index=price_data.index)
        trend_regime[ema50 > ema200] = 'trend_up'
        trend_regime[ema50 < ema200] = 'trend_down'
        
        # Volatility regime: realized vol vs quantiles
        vol_lookback_bars = lookback_days * 24  # Assuming hourly data
        rv = realized_vol(price_data, 24)  # 24-hour realized vol
        vol_q25 = rv.rolling(vol_lookback_bars, min_periods=30).quantile(0.25)
        vol_q75 = rv.rolling(vol_lookback_bars, min_periods=30).quantile(0.75)
        
        vol_regime = pd.Series('normal', index=price_data.index)
        vol_regime[rv > vol_q75] = 'high'
        vol_regime[rv < vol_q25] = 'low'
        
        return RegimeClassification(
            trend_regime=trend_regime,
            vol_regime=vol_regime
        )
    
    def classify_sessions(self, index: pd.DatetimeIndex) -> SessionClassification:
        """Classify trading sessions for attribution."""
        
        # Session classification based on UTC hours
        hours = index.hour
        session = pd.Series('unknown', index=index)
        
        # Asia: 00:00-08:00 UTC
        session[(hours >= 0) & (hours < 8)] = 'asia'
        # Europe: 08:00-16:00 UTC  
        session[(hours >= 8) & (hours < 16)] = 'europe'
        # US: 16:00-24:00 UTC
        session[(hours >= 16) & (hours < 24)] = 'us'
        
        # Day of week (0=Monday, 6=Sunday)
        day_of_week = index.dayofweek
        hour_of_day = hours
        
        return SessionClassification(
            session=session,
            day_of_week=day_of_week,
            hour_of_day=hour_of_day
        )
    
    def analyze_trades(
        self, 
        positions: pd.Series,
        prices: pd.Series,
        returns: pd.Series
    ) -> TradeAnalysis:
        """Analyze individual trade characteristics."""
        
        # Identify trade entry/exit points
        position_changes = positions.diff().fillna(0)
        trade_entries = position_changes != 0
        
        if not trade_entries.any():
            # No trades, return empty analysis
            empty_series = pd.Series([], dtype=float)
            return TradeAnalysis(
                trade_returns=empty_series,
                trade_durations=empty_series,
                max_adverse_excursion=empty_series,
                max_favorable_excursion=empty_series,
                win_loss_flag=empty_series,
                trade_size=empty_series
            )
        
        # Build trade-level data
        trade_data = []
        current_position = 0
        entry_price = None
        entry_time = None
        running_pnl = 0
        max_favorable = 0
        max_adverse = 0
        
        for i, (timestamp, pos) in enumerate(positions.items()):
            if i >= len(returns):
                break
                
            period_return = returns.iloc[i]
            running_pnl += current_position * period_return
            
            # Track MAE/MFE during the trade
            if current_position != 0:
                max_favorable = max(max_favorable, running_pnl)
                max_adverse = min(max_adverse, running_pnl)
            
            # Check for position change
            if pos != current_position:
                # Close existing trade if any
                if current_position != 0 and entry_time is not None:
                    duration = i - entry_time
                    trade_data.append({
                        'exit_time': timestamp,
                        'trade_return': running_pnl,
                        'duration': duration,
                        'mae': max_adverse,
                        'mfe': max_favorable,
                        'win_loss': 1 if running_pnl > 0 else 0,
                        'trade_size': abs(current_position)
                    })
                
                # Start new trade
                if pos != 0:
                    entry_time = i
                    entry_price = prices.iloc[i] if i < len(prices) else None
                    running_pnl = 0
                    max_favorable = 0
                    max_adverse = 0
                
                current_position = pos
        
        # Convert to series
        if trade_data:
            trade_df = pd.DataFrame(trade_data)
            trade_df = trade_df.set_index('exit_time')
            
            return TradeAnalysis(
                trade_returns=trade_df['trade_return'],
                trade_durations=trade_df['duration'],
                max_adverse_excursion=trade_df['mae'],
                max_favorable_excursion=trade_df['mfe'],
                win_loss_flag=trade_df['win_loss'],
                trade_size=trade_df['trade_size']
            )
        else:
            # No completed trades
            empty_series = pd.Series([], dtype=float)
            return TradeAnalysis(
                trade_returns=empty_series,
                trade_durations=empty_series,
                max_adverse_excursion=empty_series,
                max_favorable_excursion=empty_series,
                win_loss_flag=empty_series,
                trade_size=empty_series
            )
    
    def run_comprehensive_analysis(
        self,
        backtest_result: Dict[str, pd.Series],
        price_data: pd.Series,
        positions: pd.Series,
        strategy_name: str = "Strategy"
    ) -> Dict[str, Any]:
        """Run comprehensive PnL decomposition analysis."""
        
        print(f"🔍 Running comprehensive PnL analysis for {strategy_name}...")
        
        # 1. PnL Component Decomposition
        pnl_components = self.decompose_pnl_components(backtest_result)
        
        # 2. Regime Classification
        regimes = self.classify_regimes(price_data)
        
        # 3. Session Classification
        sessions = self.classify_sessions(price_data.index)
        
        # 4. Trade Analysis
        returns = backtest_result['net'].fillna(0)
        trades = self.analyze_trades(positions, price_data, returns)
        
        # 5. Attribution Analysis
        attribution = self._calculate_attribution(
            pnl_components, regimes, sessions, trades
        )
        
        # Store results
        analysis_result = {
            'strategy_name': strategy_name,
            'pnl_components': pnl_components,
            'regimes': regimes,
            'sessions': sessions,
            'trades': trades,
            'attribution': attribution
        }
        
        self.results[strategy_name] = analysis_result
        return analysis_result
    
    def _calculate_attribution(
        self,
        pnl_components: PnLComponents,
        regimes: RegimeClassification,
        sessions: SessionClassification,
        trades: TradeAnalysis
    ) -> Dict[str, Any]:
        """Calculate attribution statistics."""
        
        # Combine data for analysis
        pnl_df = pnl_components.to_dataframe()
        regime_df = regimes.to_dataframe()
        session_df = sessions.to_dataframe()
        
        # Align indices
        common_index = pnl_df.index.intersection(regime_df.index).intersection(session_df.index)
        pnl_aligned = pnl_df.reindex(common_index)
        regime_aligned = regime_df.reindex(common_index)
        session_aligned = session_df.reindex(common_index)
        
        attribution = {}
        
        # 1. Component Attribution
        total_return = pnl_aligned['net_pnl'].sum()
        attribution['component_breakdown'] = {
            'price_pnl': pnl_aligned['price_pnl'].sum(),
            'funding_pnl': pnl_aligned['funding_pnl'].sum(),
            'fees_pnl': pnl_aligned['fees_pnl'].sum(),
            'spread_slippage_pnl': pnl_aligned['spread_slippage_pnl'].sum(),
            'impact_slippage_pnl': pnl_aligned['impact_slippage_pnl'].sum(),
            'total_pnl': total_return
        }
        
        # 2. Regime Attribution
        regime_attribution = {}
        for regime_type in ['trend_up', 'trend_down', 'chop']:
            mask = regime_aligned['trend_regime'] == regime_type
            regime_attribution[f'trend_{regime_type}'] = {
                'pnl': pnl_aligned[mask]['net_pnl'].sum(),
                'count': mask.sum(),
                'pnl_per_period': pnl_aligned[mask]['net_pnl'].mean() if mask.sum() > 0 else 0
            }
        
        for vol_type in ['high', 'normal', 'low']:
            mask = regime_aligned['vol_regime'] == vol_type
            regime_attribution[f'vol_{vol_type}'] = {
                'pnl': pnl_aligned[mask]['net_pnl'].sum(),
                'count': mask.sum(),
                'pnl_per_period': pnl_aligned[mask]['net_pnl'].mean() if mask.sum() > 0 else 0
            }
        
        attribution['regime_attribution'] = regime_attribution
        
        # 3. Session Attribution
        session_attribution = {}
        for session_type in ['asia', 'europe', 'us']:
            mask = session_aligned['session'] == session_type
            session_attribution[session_type] = {
                'pnl': pnl_aligned[mask]['net_pnl'].sum(),
                'count': mask.sum(),
                'pnl_per_period': pnl_aligned[mask]['net_pnl'].mean() if mask.sum() > 0 else 0
            }
        
        # Day of week attribution
        dow_attribution = {}
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day_num, day_name in enumerate(day_names):
            mask = session_aligned['day_of_week'] == day_num
            dow_attribution[day_name] = {
                'pnl': pnl_aligned[mask]['net_pnl'].sum(),
                'count': mask.sum(),
                'pnl_per_period': pnl_aligned[mask]['net_pnl'].mean() if mask.sum() > 0 else 0
            }
        
        attribution['session_attribution'] = session_attribution
        attribution['day_of_week_attribution'] = dow_attribution
        
        # 4. Trade Statistics
        if len(trades.trade_returns) > 0:
            trade_stats = {
                'total_trades': len(trades.trade_returns),
                'win_rate': trades.win_loss_flag.mean(),
                'avg_win': trades.trade_returns[trades.win_loss_flag == 1].mean() if (trades.win_loss_flag == 1).any() else 0,
                'avg_loss': trades.trade_returns[trades.win_loss_flag == 0].mean() if (trades.win_loss_flag == 0).any() else 0,
                'win_loss_ratio': (trades.trade_returns[trades.win_loss_flag == 1].mean() / 
                                 abs(trades.trade_returns[trades.win_loss_flag == 0].mean()) 
                                 if (trades.win_loss_flag == 0).any() and trades.trade_returns[trades.win_loss_flag == 0].mean() != 0 else float('inf')),
                'avg_duration': trades.trade_durations.mean(),
                'max_duration': trades.trade_durations.max(),
                'avg_mae': trades.max_adverse_excursion.mean(),
                'avg_mfe': trades.max_favorable_excursion.mean(),
                'profit_factor': (trades.trade_returns[trades.win_loss_flag == 1].sum() / 
                                abs(trades.trade_returns[trades.win_loss_flag == 0].sum()) 
                                if (trades.win_loss_flag == 0).any() and trades.trade_returns[trades.win_loss_flag == 0].sum() != 0 else float('inf'))
            }
        else:
            trade_stats = {
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'win_loss_ratio': 0,
                'avg_duration': 0,
                'max_duration': 0,
                'avg_mae': 0,
                'avg_mfe': 0,
                'profit_factor': 0
            }
        
        attribution['trade_statistics'] = trade_stats
        
        return attribution
    
    def generate_pnl_report(
        self, 
        strategy_name: str,
        output_dir: str = "out/pnl_analysis"
    ) -> str:
        """Generate comprehensive PnL analysis report."""
        
        if strategy_name not in self.results:
            raise ValueError(f"No analysis results found for {strategy_name}")
        
        results = self.results[strategy_name]
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate visualizations
        self._create_pnl_visualizations(results, output_path)
        
        # Generate text report
        report_file = output_path / f"{strategy_name}_pnl_analysis.txt"
        with open(report_file, 'w') as f:
            f.write(self._generate_text_report(results))
        
        print(f"📊 PnL analysis report saved to {report_file}")
        return str(report_file)
    
    def _create_pnl_visualizations(self, results: Dict[str, Any], output_path: Path):
        """Create PnL analysis visualizations."""
        
        strategy_name = results['strategy_name']
        
        # Set style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # 1. Component Breakdown Pie Chart
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        component_data = results['attribution']['component_breakdown']
        # Only show meaningful components
        components = {k: v for k, v in component_data.items() if k != 'total_pnl' and abs(v) > 0.001}
        
        if components:
            labels = [k.replace('_', ' ').title() for k in components.keys()]
            values = list(components.values())
            colors = ['green' if v > 0 else 'red' for v in values]
            
            ax1.pie(np.abs(values), labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
            ax1.set_title(f'{strategy_name}: PnL Component Breakdown')
        else:
            ax1.text(0.5, 0.5, 'No PnL Components', ha='center', va='center', transform=ax1.transAxes)
            ax1.set_title(f'{strategy_name}: PnL Component Breakdown')
        
        # 2. Regime Attribution
        regime_data = results['attribution']['regime_attribution']
        regime_labels = []
        regime_values = []
        
        for key, data in regime_data.items():
            if data['count'] > 0:
                regime_labels.append(key.replace('_', ' ').title())
                regime_values.append(data['pnl'])
        
        if regime_values:
            colors = ['green' if v > 0 else 'red' for v in regime_values]
            bars = ax2.bar(regime_labels, regime_values, color=colors, alpha=0.7)
            ax2.set_title(f'{strategy_name}: Regime Attribution')
            ax2.set_ylabel('PnL')
            ax2.tick_params(axis='x', rotation=45)
            
            # Add value labels on bars
            for bar, value in zip(bars, regime_values):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value:.3f}', ha='center', va='bottom' if height > 0 else 'top')
        else:
            ax2.text(0.5, 0.5, 'No Regime Data', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title(f'{strategy_name}: Regime Attribution')
        
        # 3. Session Attribution
        session_data = results['attribution']['session_attribution']
        session_labels = list(session_data.keys())
        session_values = [data['pnl'] for data in session_data.values()]
        
        if any(v != 0 for v in session_values):
            colors = ['green' if v > 0 else 'red' for v in session_values]
            bars = ax3.bar(session_labels, session_values, color=colors, alpha=0.7)
            ax3.set_title(f'{strategy_name}: Session Attribution')
            ax3.set_ylabel('PnL')
            
            # Add value labels
            for bar, value in zip(bars, session_values):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value:.3f}', ha='center', va='bottom' if height > 0 else 'top')
        else:
            ax3.text(0.5, 0.5, 'No Session Data', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title(f'{strategy_name}: Session Attribution')
        
        # 4. Trade Distribution
        trades = results['trades']
        if len(trades.trade_returns) > 0:
            ax4.hist(trades.trade_returns, bins=20, alpha=0.7, color='blue', edgecolor='black')
            ax4.axvline(trades.trade_returns.mean(), color='red', linestyle='--', 
                       label=f'Mean: {trades.trade_returns.mean():.4f}')
            ax4.set_title(f'{strategy_name}: Trade Return Distribution')
            ax4.set_xlabel('Trade Return')
            ax4.set_ylabel('Frequency')
            ax4.legend()
        else:
            ax4.text(0.5, 0.5, 'No Trade Data', ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title(f'{strategy_name}: Trade Return Distribution')
        
        plt.tight_layout()
        plt.savefig(output_path / f"{strategy_name}_pnl_analysis.png", dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📈 PnL visualization saved to {output_path / f'{strategy_name}_pnl_analysis.png'}")
    
    def _generate_text_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive text report."""
        
        strategy_name = results['strategy_name']
        attribution = results['attribution']
        
        report = []
        report.append("=" * 80)
        report.append(f"COMPREHENSIVE PnL ANALYSIS: {strategy_name.upper()}")
        report.append("=" * 80)
        
        # Component Breakdown
        report.append("\n📊 PnL COMPONENT BREAKDOWN")
        report.append("-" * 40)
        
        components = attribution['component_breakdown']
        total_pnl = components['total_pnl']
        
        for component, value in components.items():
            if component != 'total_pnl':
                pct = (value / total_pnl * 100) if total_pnl != 0 else 0
                report.append(f"  {component.replace('_', ' ').title():20s}: {value:8.4f} ({pct:5.1f}%)")
        
        report.append(f"  {'Total PnL':20s}: {total_pnl:8.4f}")
        
        # Regime Attribution
        report.append("\n🌊 REGIME ATTRIBUTION")
        report.append("-" * 40)
        
        regime_data = attribution['regime_attribution']
        for regime, data in regime_data.items():
            if data['count'] > 0:
                avg_pnl = data['pnl_per_period']
                report.append(f"  {regime.replace('_', ' ').title():15s}: "
                             f"PnL={data['pnl']:7.4f}, Count={data['count']:4d}, "
                             f"Avg={avg_pnl:7.4f}")
        
        # Session Attribution
        report.append("\n🕐 SESSION ATTRIBUTION")
        report.append("-" * 40)
        
        session_data = attribution['session_attribution']
        for session, data in session_data.items():
            if data['count'] > 0:
                avg_pnl = data['pnl_per_period']
                report.append(f"  {session.title():10s}: "
                             f"PnL={data['pnl']:7.4f}, Count={data['count']:4d}, "
                             f"Avg={avg_pnl:7.4f}")
        
        # Day of Week Attribution
        report.append("\n📅 DAY OF WEEK ATTRIBUTION")
        report.append("-" * 40)
        
        dow_data = attribution['day_of_week_attribution']
        for day, data in dow_data.items():
            if data['count'] > 0:
                avg_pnl = data['pnl_per_period']
                report.append(f"  {day:10s}: "
                             f"PnL={data['pnl']:7.4f}, Count={data['count']:4d}, "
                             f"Avg={avg_pnl:7.4f}")
        
        # Trade Statistics
        report.append("\n📈 TRADE STATISTICS")
        report.append("-" * 40)
        
        trade_stats = attribution['trade_statistics']
        report.append(f"  Total Trades:     {trade_stats['total_trades']:6d}")
        report.append(f"  Win Rate:         {trade_stats['win_rate']:6.1%}")
        report.append(f"  Average Win:      {trade_stats['avg_win']:8.4f}")
        report.append(f"  Average Loss:     {trade_stats['avg_loss']:8.4f}")
        report.append(f"  Win/Loss Ratio:   {trade_stats['win_loss_ratio']:8.2f}")
        report.append(f"  Profit Factor:    {trade_stats['profit_factor']:8.2f}")
        report.append(f"  Avg Duration:     {trade_stats['avg_duration']:8.1f} periods")
        report.append(f"  Max Duration:     {trade_stats['max_duration']:8.0f} periods")
        report.append(f"  Avg MAE:          {trade_stats['avg_mae']:8.4f}")
        report.append(f"  Avg MFE:          {trade_stats['avg_mfe']:8.4f}")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)
