"""
Enhanced FGI Backtest Engine with Advanced Features and Winner Tracking
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnhancedFGIConfig:
    """Enhanced configuration for FGI strategy."""
    ultra_fear_threshold: float = 15.0
    fear_threshold: float = 25.0
    greed_threshold: float = 75.0
    ultra_greed_threshold: float = 85.0
    ultra_fear_size: float = 0.15
    fear_size: float = 0.10
    light_fear_size: float = 0.05
    greed_sell_size: float = 0.10
    ultra_greed_sell_size: float = 0.15
    max_btc_exposure: float = 0.80
    min_cash_reserve: float = 0.20
    drawdown_threshold: float = 0.50
    volatility_lookback: int = 30
    momentum_lookback: int = 30
    min_momentum_buy: float = -0.30
    recovery_momentum: float = -0.15
    trend_confirmation: int = 7
    initial_capital: float = 100000.0
    transaction_cost_pct: float = 0.001
    fgi_smoothing_days: int = 3


@dataclass
class EnhancedPosition:
    """Enhanced position tracking with average cost basis."""
    shares: float = 0.0
    avg_price: float = 0.0
    total_cost: float = 0.0
    
    def add_shares(self, shares: float, price: float) -> None:
        """Add shares to position."""
        if self.shares == 0:
            self.avg_price = price
            self.total_cost = shares * price
        else:
            total_value = self.total_cost + (shares * price)
            self.total_cost = total_value
            self.avg_price = total_value / (self.shares + shares)
        self.shares += shares
    
    def remove_shares(self, shares: float) -> float:
        """Remove shares from position. Returns cost basis of removed shares."""
        if shares > self.shares:
            shares = self.shares
        
        proceeds = shares * self.avg_price
        self.shares -= shares
        self.total_cost -= proceeds
        
        if self.shares <= 0:
            self.shares = 0.0
            self.avg_price = 0.0
            self.total_cost = 0.0
            
        return proceeds
    
    def market_value(self, current_price: float) -> float:
        """Current market value of position."""
        return self.shares * current_price
    
    def unrealized_pnl(self, current_price: float) -> float:
        """Unrealized P&L."""
        return self.market_value(current_price) - self.total_cost


class EnhancedFGIBacktester:
    """Enhanced backtester with winner tracking."""
    
    def __init__(self, config: EnhancedFGIConfig):
        self.config = config
        self.reset()
    
    def reset(self) -> None:
        """Reset backtest state."""
        self.cash = self.config.initial_capital
        self.position = EnhancedPosition()
        self.equity_history = []
        self.trades = []
        self.last_entry_date = None
        self.last_exit_date = None
    
    def run_backtest(self, price_data: pd.DataFrame, fgi_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run enhanced FGI backtest.
        
        Args:
            price_data: DataFrame with daily BTC prices
            fgi_data: DataFrame with FGI values
            
        Returns:
            Dictionary with backtest results
        """
        logger.info("Starting Enhanced FGI backtest")
        self.reset()
        
        # Align data
        aligned_data = self._align_data(price_data, fgi_data)
        if aligned_data.empty:
            logger.error("No aligned data for backtest")
            return {}
        
        # Add smoothed FGI
        aligned_data['fgi_smooth'] = aligned_data['fgi_value'].rolling(
            window=self.config.fgi_smoothing_days, min_periods=1
        ).mean()
        
        # Add momentum
        aligned_data['momentum'] = aligned_data['close'].pct_change(self.config.momentum_lookback)
        
        logger.info(f"Backtesting from {aligned_data.index[0]} to {aligned_data.index[-1]}")
        logger.info(f"Total trading days: {len(aligned_data)}")
        
        # Run day-by-day simulation
        for date, row in aligned_data.iterrows():
            self._process_day(date, row, aligned_data)
        
        # Calculate final metrics
        results = self._calculate_metrics(aligned_data)
        
        logger.info(f"Backtest completed. Final equity: ${results['final_equity']:,.2f}")
        logger.info(f"Total return: {results['total_return']:.2%}")
        logger.info(f"Number of trades: {len(self.trades)}")
        
        return results
    
    def _align_data(self, price_data: pd.DataFrame, fgi_data: pd.DataFrame) -> pd.DataFrame:
        """Align price and FGI data."""
        price_idx = pd.to_datetime(price_data.index).normalize()
        fgi_idx = pd.to_datetime(fgi_data.index).normalize()
        
        common_dates = price_idx.intersection(fgi_idx)
        
        if len(common_dates) == 0:
            logger.error("No common dates between price and FGI data")
            return pd.DataFrame()
        
        price_aligned = price_data.reindex(price_idx).loc[common_dates]
        fgi_aligned = fgi_data.reindex(fgi_idx).loc[common_dates]
        
        aligned = pd.DataFrame(index=common_dates)
        aligned['close'] = price_aligned['c'].values
        aligned['fgi_value'] = fgi_aligned['fgi_value'].values
        
        aligned = aligned.ffill().dropna()
        
        logger.info(f"Aligned data: {len(aligned)} days from {aligned.index[0]} to {aligned.index[-1]}")
        return aligned
    
    def _process_day(self, date: pd.Timestamp, row: pd.Series, full_data: pd.DataFrame) -> None:
        """Process a single trading day with enhanced logic."""
        price = row['close']
        fgi = row['fgi_smooth']
        momentum = row['momentum'] if not pd.isna(row['momentum']) else 0
        
        # Dynamic position sizing based on FGI
        if fgi <= self.config.ultra_fear_threshold:
            buy_size = self.config.ultra_fear_size
        elif fgi <= self.config.fear_threshold:
            buy_size = self.config.fear_size
        else:
            buy_size = 0
        
        # Entry logic with momentum filter
        if buy_size > 0 and momentum >= self.config.min_momentum_buy:
            self._execute_entry(date, price, buy_size)
        
        # Exit logic
        if self.position.shares > 0:
            if fgi >= self.config.ultra_greed_threshold:
                self._execute_exit(date, price, self.config.ultra_greed_sell_size)
            elif fgi >= self.config.greed_threshold:
                self._execute_exit(date, price, self.config.greed_sell_size)
        
        # Record daily equity
        total_equity = self.cash + self.position.market_value(price)
        self.equity_history.append({
            'date': date,
            'equity': total_equity,
            'cash': self.cash,
            'position_value': self.position.market_value(price),
            'price': price,
            'fgi': row['fgi_value'],
            'shares': self.position.shares
        })
    
    def _execute_entry(self, date: pd.Timestamp, price: float, size_pct: float) -> None:
        """Execute entry trade."""
        total_equity = self.cash + self.position.market_value(price)
        trade_amount = total_equity * size_pct
        
        if trade_amount > self.cash:
            trade_amount = self.cash
        
        if trade_amount < 1.0:
            return
        
        transaction_cost = trade_amount * self.config.transaction_cost_pct
        net_amount = trade_amount - transaction_cost
        shares_to_buy = net_amount / price
        
        self.cash -= trade_amount
        self.position.add_shares(shares_to_buy, price)
        
        trade = {
            'date': date,
            'type': 'BUY',
            'shares': shares_to_buy,
            'price': price,
            'amount': trade_amount,
            'cost': transaction_cost,
            'cash_after': self.cash,
            'total_shares': self.position.shares,
            'avg_price': self.position.avg_price
        }
        self.trades.append(trade)
        
        logger.debug(f"{date.date()}: BUY {shares_to_buy:.4f} shares at ${price:.2f}")
    
    def _execute_exit(self, date: pd.Timestamp, price: float, size_pct: float) -> None:
        """Execute exit trade with P&L tracking."""
        if self.position.shares <= 0:
            return
        
        shares_to_sell = self.position.shares * size_pct
        if shares_to_sell > self.position.shares:
            shares_to_sell = self.position.shares
        
        gross_proceeds = shares_to_sell * price
        if gross_proceeds < 1.0:
            return
        
        transaction_cost = gross_proceeds * self.config.transaction_cost_pct
        net_proceeds = gross_proceeds - transaction_cost
        
        # Track P&L before removing shares
        avg_price_before = self.position.avg_price
        realized_pnl = (price - avg_price_before) * shares_to_sell - transaction_cost
        is_winner = realized_pnl > 0
        
        self.position.remove_shares(shares_to_sell)
        self.cash += net_proceeds
        
        trade = {
            'date': date,
            'type': 'SELL',
            'shares': shares_to_sell,
            'price': price,
            'amount': gross_proceeds,
            'cost': transaction_cost,
            'avg_price': avg_price_before,
            'realized_pnl': realized_pnl,
            'pnl_pct': (price / avg_price_before - 1) if avg_price_before > 0 else 0,
            'win': is_winner,
            'cash_after': self.cash,
            'total_shares': self.position.shares
        }
        self.trades.append(trade)
        
        logger.debug(f"{date.date()}: SELL {shares_to_sell:.4f} shares at ${price:.2f}, "
                    f"PnL: ${realized_pnl:.2f} ({'WIN' if is_winner else 'LOSS'})")
    
    def _calculate_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate backtest performance metrics."""
        if not self.equity_history:
            return {}
        
        equity_df = pd.DataFrame(self.equity_history).set_index('date')
        
        initial_equity = self.config.initial_capital
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity / initial_equity) - 1
        
        # Buy and hold
        initial_price = data['close'].iloc[0]
        final_price = data['close'].iloc[-1]
        bh_return = (final_price / initial_price) - 1
        
        # Daily returns
        equity_df['returns'] = equity_df['equity'].pct_change()
        
        # Risk metrics
        annual_return = (1 + total_return) ** (365.25 / len(data)) - 1
        volatility = equity_df['returns'].std() * np.sqrt(365.25)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        # Drawdown
        rolling_max = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] / rolling_max) - 1
        max_drawdown = drawdown.min()
        
        # Win rate from SELL trades with realized P&L
        trade_df = pd.DataFrame(self.trades)
        win_rate = 0
        if not trade_df.empty:
            sell_trades = trade_df[trade_df['type'] == 'SELL']
            if not sell_trades.empty and 'win' in sell_trades.columns:
                win_rate = sell_trades['win'].sum() / len(sell_trades)
        
        return {
            'initial_equity': initial_equity,
            'final_equity': final_equity,
            'total_return': total_return,
            'annual_return': annual_return,
            'buy_hold_return': bh_return,
            'excess_return': total_return - bh_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': len(self.trades),
            'equity_curve': equity_df,
            'trades': trade_df,
            'final_position_shares': self.position.shares,
            'final_cash': self.cash
        }
