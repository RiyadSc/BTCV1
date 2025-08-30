"""
FGI Strategy Reporting and Visualization
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FGIReporter:
    """Generate reports and visualizations for FGI strategy."""
    
    def __init__(self, results: Dict[str, Any]):
        self.results = results
        self.equity_curve = results.get('equity_curve', pd.DataFrame())
        self.trades = results.get('trades', pd.DataFrame())
    
    def generate_summary_report(self) -> str:
        """Generate text summary of backtest results."""
        r = self.results
        
        report = f"""
=== FEAR AND GREED INDEX STRATEGY BACKTEST REPORT ===

Strategy Parameters:
- Entry Threshold: FGI ≤ 20 (Extreme Fear)
- Exit Threshold: FGI ≥ 80 (Extreme Greed)
- Position Size: 25% of equity per trade
- Entry/Exit Interval: Every 2 days while in zone

Performance Summary:
- Initial Capital: ${r.get('initial_equity', 0):,.2f}
- Final Equity: ${r.get('final_equity', 0):,.2f}
- Total Return: {r.get('total_return', 0):.2%}
- Annualized Return: {r.get('annual_return', 0):.2%}
- Buy & Hold Return: {r.get('buy_hold_return', 0):.2%}
- Excess Return: {r.get('excess_return', 0):.2%}

Risk Metrics:
- Volatility: {r.get('volatility', 0):.2%}
- Sharpe Ratio: {r.get('sharpe_ratio', 0):.2f}
- Maximum Drawdown: {r.get('max_drawdown', 0):.2%}

Trading Activity:
- Total Trades: {r.get('num_trades', 0)}
- Win Rate: {r.get('win_rate', 0):.2%}
- Final Position: {r.get('final_position_shares', 0):.4f} BTC
- Final Cash: ${r.get('final_cash', 0):,.2f}

"""
        
        # Add trade summary if available
        if not self.trades.empty:
            buy_trades = self.trades[self.trades['type'] == 'BUY']
            sell_trades = self.trades[self.trades['type'] == 'SELL']
            
            report += f"""
Trade Breakdown:
- Buy Trades: {len(buy_trades)}
- Sell Trades: {len(sell_trades)}
- Average Buy Amount: ${buy_trades['amount'].mean():,.2f}
- Average Sell Amount: ${sell_trades['amount'].mean():,.2f}
- Total Transaction Costs: ${self.trades['cost'].sum():,.2f}
"""
        
        return report
    
    def plot_equity_curve(self, save_path: Optional[str] = None, show_trades: bool = True) -> None:
        """Plot equity curve with FGI zones and trades."""
        if self.equity_curve.empty:
            logger.warning("No equity curve data to plot")
            return
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12), sharex=True)
        
        # Plot 1: Equity curve vs BTC price
        ax1_twin = ax1.twinx()
        
        ax1.plot(self.equity_curve.index, self.equity_curve['equity'], 
                label='FGI Strategy', color='blue', linewidth=2)
        
        # Calculate buy & hold for comparison
        initial_price = self.equity_curve['price'].iloc[0]
        initial_equity = self.results.get('initial_equity', 100000)
        shares_bh = initial_equity / initial_price
        bh_value = shares_bh * self.equity_curve['price']
        
        ax1.plot(self.equity_curve.index, bh_value, 
                label='Buy & Hold', color='gray', linestyle='--', alpha=0.7)
        
        ax1_twin.plot(self.equity_curve.index, self.equity_curve['price'], 
                     color='orange', alpha=0.5, label='BTC Price')
        
        ax1.set_ylabel('Portfolio Value ($)', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        ax1_twin.set_ylabel('BTC Price ($)', color='orange')
        ax1_twin.tick_params(axis='y', labelcolor='orange')
        ax1.legend(loc='upper left')
        ax1_twin.legend(loc='upper right')
        ax1.set_title('FGI Strategy Performance vs Buy & Hold')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Fear and Greed Index with zones
        ax2.plot(self.equity_curve.index, self.equity_curve['fgi'], 
                color='purple', linewidth=1.5, label='Fear & Greed Index')
        
        # Highlight entry and exit zones
        ax2.axhline(y=20, color='red', linestyle='--', alpha=0.7, label='Entry Zone (≤20)')
        ax2.axhline(y=80, color='green', linestyle='--', alpha=0.7, label='Exit Zone (≥80)')
        ax2.fill_between(self.equity_curve.index, 0, 20, alpha=0.2, color='red', label='Extreme Fear')
        ax2.fill_between(self.equity_curve.index, 80, 100, alpha=0.2, color='green', label='Extreme Greed')
        
        ax2.set_ylabel('FGI Value')
        ax2.set_ylim(0, 100)
        ax2.legend()
        ax2.set_title('Fear and Greed Index Over Time')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Position size over time
        ax3.plot(self.equity_curve.index, self.equity_curve['shares'], 
                color='brown', linewidth=1.5, label='BTC Position Size')
        ax3.set_ylabel('BTC Holdings')
        ax3.set_xlabel('Date')
        ax3.legend()
        ax3.set_title('Position Size Over Time')
        ax3.grid(True, alpha=0.3)
        
        # Add trade markers if requested
        if show_trades and not self.trades.empty:
            for _, trade in self.trades.iterrows():
                trade_date = trade['date']
                if trade['type'] == 'BUY':
                    ax1.scatter(trade_date, self.equity_curve.loc[trade_date, 'equity'], 
                              color='green', marker='^', s=50, alpha=0.8, zorder=5)
                    ax3.scatter(trade_date, trade['total_shares'], 
                              color='green', marker='^', s=50, alpha=0.8, zorder=5)
                else:  # SELL
                    ax1.scatter(trade_date, self.equity_curve.loc[trade_date, 'equity'], 
                              color='red', marker='v', s=50, alpha=0.8, zorder=5)
                    ax3.scatter(trade_date, trade['total_shares'], 
                              color='red', marker='v', s=50, alpha=0.8, zorder=5)
        
        # Format x-axis
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved equity curve plot to {save_path}")
        
        plt.show()
    
    def plot_drawdown_analysis(self, save_path: Optional[str] = None) -> None:
        """Plot drawdown analysis."""
        if self.equity_curve.empty:
            logger.warning("No equity curve data for drawdown analysis")
            return
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
        
        # Calculate rolling maximum and drawdown
        equity = self.equity_curve['equity']
        rolling_max = equity.expanding().max()
        drawdown = (equity / rolling_max) - 1
        
        # Plot 1: Equity vs Rolling High
        ax1.plot(equity.index, equity, label='Portfolio Value', color='blue', linewidth=2)
        ax1.plot(rolling_max.index, rolling_max, label='Rolling High', color='red', linestyle='--', alpha=0.7)
        ax1.fill_between(equity.index, equity, rolling_max, alpha=0.3, color='red')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.legend()
        ax1.set_title('Portfolio Value vs Rolling High')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Drawdown
        ax2.fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red', label='Drawdown')
        ax2.plot(drawdown.index, drawdown, color='red', linewidth=1)
        ax2.axhline(y=self.results.get('max_drawdown', 0), color='darkred', 
                   linestyle='--', alpha=0.8, label=f"Max DD: {self.results.get('max_drawdown', 0):.2%}")
        ax2.set_ylabel('Drawdown (%)')
        ax2.set_xlabel('Date')
        ax2.legend()
        ax2.set_title('Portfolio Drawdown Over Time')
        ax2.grid(True, alpha=0.3)
        
        # Format as percentage
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
        
        # Format x-axis
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved drawdown analysis to {save_path}")
        
        plt.show()
    
    def generate_html_report(self, output_path: str) -> None:
        """Generate comprehensive HTML report."""
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>FGI Strategy Backtest Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; border-left: 4px solid #3498db; padding-left: 10px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-box {{ background: #ecf0f1; padding: 15px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ font-size: 14px; color: #7f8c8d; margin-top: 5px; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .trade-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .trade-table th, .trade-table td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        .trade-table th {{ background-color: #3498db; color: white; }}
        .buy {{ background-color: #d5f4e6; }}
        .sell {{ background-color: #fce4ec; }}
        pre {{ background: #2c3e50; color: white; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Fear and Greed Index Strategy Backtest Report</h1>
        
        <h2>Strategy Overview</h2>
        <p><strong>Entry Signal:</strong> Fear and Greed Index ≤ 20 (Extreme Fear)</p>
        <p><strong>Exit Signal:</strong> Fear and Greed Index ≥ 80 (Extreme Greed)</p>
        <p><strong>Position Sizing:</strong> 25% of equity per trade, every 2 days while in zone</p>
        
        <h2>Performance Metrics</h2>
        <div class="metrics">
            <div class="metric-box">
                <div class="metric-value {'positive' if self.results.get('total_return', 0) > 0 else 'negative'}">{self.results.get('total_return', 0):.2%}</div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric-box">
                <div class="metric-value {'positive' if self.results.get('excess_return', 0) > 0 else 'negative'}">{self.results.get('excess_return', 0):.2%}</div>
                <div class="metric-label">Excess Return vs B&H</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{self.results.get('sharpe_ratio', 0):.2f}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric-box">
                <div class="metric-value negative">{self.results.get('max_drawdown', 0):.2%}</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{self.results.get('num_trades', 0)}</div>
                <div class="metric-label">Total Trades</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{self.results.get('win_rate', 0):.1%}</div>
                <div class="metric-label">Win Rate</div>
            </div>
        </div>
        
        <h2>Detailed Summary</h2>
        <pre>{self.generate_summary_report()}</pre>
"""
        
        # Add trade table if available
        if not self.trades.empty:
            html_content += """
        <h2>Trade History</h2>
        <table class="trade-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Type</th>
                    <th>Shares</th>
                    <th>Price</th>
                    <th>Amount</th>
                    <th>Cost</th>
                    <th>Total Shares</th>
                </tr>
            </thead>
            <tbody>
"""
            
            for _, trade in self.trades.head(50).iterrows():  # Show first 50 trades
                row_class = 'buy' if trade['type'] == 'BUY' else 'sell'
                html_content += f"""
                <tr class="{row_class}">
                    <td>{trade['date'].strftime('%Y-%m-%d')}</td>
                    <td>{trade['type']}</td>
                    <td>{trade['shares']:.4f}</td>
                    <td>${trade['price']:,.2f}</td>
                    <td>${trade['amount']:,.2f}</td>
                    <td>${trade['cost']:.2f}</td>
                    <td>{trade['total_shares']:.4f}</td>
                </tr>
"""
            
            if len(self.trades) > 50:
                html_content += f"<tr><td colspan='7'><em>... and {len(self.trades) - 50} more trades</em></td></tr>"
            
            html_content += """
            </tbody>
        </table>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        # Save HTML file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Generated HTML report: {output_path}")
    
    def save_results_to_csv(self, output_dir: str) -> None:
        """Save equity curve and trades to CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save equity curve
        if not self.equity_curve.empty:
            equity_path = output_path / "fgi_equity_curve.csv"
            self.equity_curve.to_csv(equity_path)
            logger.info(f"Saved equity curve to {equity_path}")
        
        # Save trades
        if not self.trades.empty:
            trades_path = output_path / "fgi_trades.csv"
            self.trades.to_csv(trades_path, index=False)
            logger.info(f"Saved trades to {trades_path}")
        
        # Save summary metrics
        summary_path = output_path / "fgi_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(self.generate_summary_report())
        logger.info(f"Saved summary to {summary_path}")


def generate_full_report(results: Dict[str, Any], output_dir: str, show_plots: bool = True) -> None:
    """
    Generate a complete report with all outputs.
    
    Args:
        results: Backtest results dictionary
        output_dir: Directory to save outputs
        show_plots: Whether to display plots
    """
    reporter = FGIReporter(results)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate all outputs
    reporter.save_results_to_csv(output_dir)
    reporter.generate_html_report(str(output_path / "fgi_report.html"))
    
    if show_plots:
        reporter.plot_equity_curve(str(output_path / "fgi_equity_curve.png"))
        reporter.plot_drawdown_analysis(str(output_path / "fgi_drawdown.png"))
    
    # Print summary to console
    print(reporter.generate_summary_report())


if __name__ == "__main__":
    # Test with sample results
    import datetime
    
    sample_results = {
        'initial_equity': 100000,
        'final_equity': 150000,
        'total_return': 0.5,
        'annual_return': 0.2,
        'buy_hold_return': 0.3,
        'excess_return': 0.2,
        'volatility': 0.4,
        'sharpe_ratio': 0.5,
        'max_drawdown': -0.15,
        'win_rate': 0.65,
        'num_trades': 20,
        'final_position_shares': 2.5,
        'final_cash': 25000
    }
    
    reporter = FGIReporter(sample_results)
    print(reporter.generate_summary_report())
