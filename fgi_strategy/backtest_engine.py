"""
Fear and Greed Index Backtest Engine
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FGIConfig:
    """Configuration for FGI strategy."""
    entry_threshold: float = 20.0  # Enter when FGI <= 20
    exit_threshold: float = 80.0   # Exit when FGI >= 80
    position_size_pct: float = 0.10  # 10% of equity per entry/exit
    entry_interval_days: int = 1     # Enter every day while FGI <= 20
    exit_interval_days: int = 1      # Exit every day while FGI >= 80
    initial_capital: float = 100000.0  # Starting capital
    transaction_cost_pct: float = 0.001  # 0.1% transaction costs


@dataclass
class Position:
    """Represents a trading position."""
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
        """Remove shares from position. Returns proceeds."""
        if shares > self.shares:
            shares = self.shares
        
        proceeds = shares * self.avg_price  # Use avg price for consistent tracking
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


class FGIBacktester:
    """Backtester for Fear and Greed Index strategy."""
    
    def __init__(self, config: FGIConfig):
        self.config = config
        self.reset()
    
    def reset(self) -> None:
        """Reset backtest state."""
        self.cash = self.config.initial_capital
        self.position = Position()
        self.equity_history = []
        self.trades = []
        self.last_entry_date = None
        self.last_exit_date = None
        self.in_entry_zone = False
        self.in_exit_zone = False
    
    def run_backtest(self, price_data: pd.DataFrame, fgi_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run the FGI backtest.
        
        Args:
            price_data: DataFrame with daily BTC prices (columns: o,h,l,c,v)
            fgi_data: DataFrame with FGI values (column: fgi_value)
            
        Returns:
            Dictionary with backtest results and metrics
        """
        logger.info("Starting FGI backtest")
        self.reset()
        
        # Align data
        aligned_data = self._align_data(price_data, fgi_data)
        if aligned_data.empty:
            logger.error("No aligned data for backtest")
            return {}
        
        logger.info(f"Backtesting from {aligned_data.index[0]} to {aligned_data.index[-1]}")
        logger.info(f"Total trading days: {len(aligned_data)}")
        
        # Run day-by-day simulation
        for date, row in aligned_data.iterrows():
            self._process_day(date, row)
        
        # Calculate final metrics
        results = self._calculate_metrics(aligned_data)
        
        logger.info(f"Backtest completed. Final equity: ${results['final_equity']:,.2f}")
        logger.info(f"Total return: {results['total_return']:.2%}")
        logger.info(f"Number of trades: {len(self.trades)}")
        
        return results
    
    def _align_data(self, price_data: pd.DataFrame, fgi_data: pd.DataFrame) -> pd.DataFrame:
        """Align price and FGI data on the same dates."""
        # Ensure both have datetime index
        price_idx = pd.to_datetime(price_data.index).normalize()
        fgi_idx = pd.to_datetime(fgi_data.index).normalize()
        
        # Create aligned DataFrame
        common_dates = price_idx.intersection(fgi_idx)
        
        if len(common_dates) == 0:
            logger.error("No common dates between price and FGI data")
            return pd.DataFrame()
        
        # Reindex both to common dates
        price_aligned = price_data.reindex(price_idx).loc[common_dates]
        fgi_aligned = fgi_data.reindex(fgi_idx).loc[common_dates]
        
        # Combine into single DataFrame
        aligned = pd.DataFrame(index=common_dates)
        aligned['close'] = price_aligned['c'].values
        aligned['fgi_value'] = fgi_aligned['fgi_value'].values
        
        # Forward fill any missing values
        aligned = aligned.ffill().dropna()
        
        logger.info(f"Aligned data: {len(aligned)} days from {aligned.index[0]} to {aligned.index[-1]}")
        return aligned
    
    def _process_day(self, date: pd.Timestamp, row: pd.Series) -> None:
        """Process a single trading day."""
        price = row['close']
        fgi = row['fgi_value']
        
        # Check entry conditions - buy 10% of total equity daily when FGI <= 20
        if fgi <= self.config.entry_threshold:
            if not self.in_entry_zone:
                self.in_entry_zone = True
                self.last_entry_date = None  # Reset to allow immediate entry
            
            # Check if enough time has passed since last entry (daily)
            if (self.last_entry_date is None or 
                (date - self.last_entry_date).days >= self.config.entry_interval_days):
                self._execute_entry(date, price)
                self.last_entry_date = date
        else:
            self.in_entry_zone = False
        
        # Check exit conditions - sell 10% of position daily when FGI >= 80
        if self.position.shares > 0 and fgi >= self.config.exit_threshold:
            if not self.in_exit_zone:
                self.in_exit_zone = True
                self.last_exit_date = None  # Reset to allow immediate exit
            
            # Check if enough time has passed since last exit (daily)
            if (self.last_exit_date is None or 
                (date - self.last_exit_date).days >= self.config.exit_interval_days):
                self._execute_exit(date, price)
                self.last_exit_date = date
        else:
            if fgi < self.config.exit_threshold:
                self.in_exit_zone = False
        
        # Record daily equity
        total_equity = self.cash + self.position.market_value(price)
        self.equity_history.append({
            'date': date,
            'equity': total_equity,
            'cash': self.cash,
            'position_value': self.position.market_value(price),
            'price': price,
            'fgi': fgi,
            'shares': self.position.shares
        })
    
    def _execute_entry(self, date: pd.Timestamp, price: float) -> None:
        """Execute entry trade."""
        total_equity = self.cash + self.position.market_value(price)
        trade_amount = total_equity * self.config.position_size_pct
        
        if trade_amount > self.cash:
            trade_amount = self.cash  # Use available cash
        
        if trade_amount < 1.0:  # Minimum trade size
            return
        
        # Calculate transaction costs
        transaction_cost = trade_amount * self.config.transaction_cost_pct
        net_amount = trade_amount - transaction_cost
        
        shares_to_buy = net_amount / price
        
        # Execute trade
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
            'total_shares': self.position.shares
        }
        self.trades.append(trade)
        
        logger.debug(f"{date.date()}: BUY {shares_to_buy:.4f} shares at ${price:.2f} "
                    f"(${trade_amount:.2f}, cost: ${transaction_cost:.2f})")
    
    def _execute_exit(self, date: pd.Timestamp, price: float) -> None:
        """Execute exit trade - sell 10% of current position value."""
        if self.position.shares <= 0:
            return
        
        # Sell 10% of current position shares (not 10% of total equity)
        shares_to_sell = self.position.shares * self.config.position_size_pct
        if shares_to_sell > self.position.shares:
            shares_to_sell = self.position.shares
        
        # Minimum trade size check
        gross_proceeds = shares_to_sell * price
        if gross_proceeds < 1.0:  # Skip tiny trades
            return
        
        # Calculate proceeds
        transaction_cost = gross_proceeds * self.config.transaction_cost_pct
        net_proceeds = gross_proceeds - transaction_cost
        
        # Execute trade
        self.position.remove_shares(shares_to_sell)
        self.cash += net_proceeds
        
        trade = {
            'date': date,
            'type': 'SELL',
            'shares': shares_to_sell,
            'price': price,
            'amount': gross_proceeds,
            'cost': transaction_cost,
            'cash_after': self.cash,
            'total_shares': self.position.shares
        }
        self.trades.append(trade)
        
        logger.debug(f"{date.date()}: SELL {shares_to_sell:.4f} shares at ${price:.2f} "
                    f"(${gross_proceeds:.2f}, cost: ${transaction_cost:.2f})")
    
    def _calculate_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate backtest performance metrics."""
        if not self.equity_history:
            return {}
        
        equity_df = pd.DataFrame(self.equity_history).set_index('date')
        
        # Basic metrics
        initial_equity = self.config.initial_capital
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity / initial_equity) - 1
        
        # Buy and hold comparison
        initial_price = data['close'].iloc[0]
        final_price = data['close'].iloc[-1]
        bh_return = (final_price / initial_price) - 1
        
        # Calculate daily returns
        equity_df['returns'] = equity_df['equity'].pct_change()
        data_returns = data['close'].pct_change()
        
        # Risk metrics
        annual_return = (1 + total_return) ** (365.25 / len(data)) - 1
        volatility = equity_df['returns'].std() * np.sqrt(365.25)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        # Drawdown analysis
        rolling_max = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] / rolling_max) - 1
        max_drawdown = drawdown.min()
        
        # Win rate (profitable trades)
        trade_df = pd.DataFrame(self.trades)
        if not trade_df.empty:
            sell_trades = trade_df[trade_df['type'] == 'SELL']
            if not sell_trades.empty:
                # This is simplified - more complex P&L calculation would track individual position performance
                profitable_trades = len(sell_trades[sell_trades['price'] > sell_trades['price'].shift(1)])
                win_rate = profitable_trades / len(sell_trades) if len(sell_trades) > 0 else 0
            else:
                win_rate = 0
        else:
            win_rate = 0
        
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


def run_fgi_backtest(price_data: pd.DataFrame, 
                    fgi_data: pd.DataFrame, 
                    config: Optional[FGIConfig] = None) -> Dict[str, Any]:
    """
    Convenience function to run FGI backtest.
    
    Args:
        price_data: Daily BTC price data
        fgi_data: Fear and Greed Index data
        config: Strategy configuration (uses default if None)
        
    Returns:
        Backtest results dictionary
    """
    if config is None:
        config = FGIConfig()
    
    backtester = FGIBacktester(config)
    return backtester.run_backtest(price_data, fgi_data)


if __name__ == "__main__":
    # Test with sample data
    logging.basicConfig(level=logging.INFO)
    
    # Create sample data for testing
    dates = pd.date_range('2023-01-01', '2024-01-01', freq='D')
    
    # Sample price data (trending upward with volatility)
    np.random.seed(42)
    prices = 30000 * np.exp(np.cumsum(np.random.normal(0.001, 0.03, len(dates))))
    price_data = pd.DataFrame({
        'o': prices,
        'h': prices * 1.02,
        'l': prices * 0.98,
        'c': prices,
        'v': np.random.uniform(1000, 5000, len(dates))
    }, index=dates)
    
    # Sample FGI data with cycles
    fgi_values = 50 + 30 * np.sin(np.linspace(0, 4 * np.pi, len(dates))) + np.random.normal(0, 5, len(dates))
    fgi_values = np.clip(fgi_values, 0, 100)
    fgi_data = pd.DataFrame({'fgi_value': fgi_values}, index=dates)
    
    # Run backtest
    results = run_fgi_backtest(price_data, fgi_data)
    
    print("=== FGI Strategy Backtest Results ===")
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Buy & Hold Return: {results['buy_hold_return']:.2%}")
    print(f"Excess Return: {results['excess_return']:.2%}")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2%}")
    print(f"Number of Trades: {results['num_trades']}")
