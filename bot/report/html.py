import base64
import io
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


def _png_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    return buf.getvalue()


def _embed_png(b: bytes) -> str:
    return f'<img src="data:image/png;base64,{base64.b64encode(b).decode()}" />'


def monthly_returns(equity: pd.Series) -> pd.DataFrame:
    r = equity.resample('M').last().pct_change().dropna()
    r.index = r.index.strftime("%Y-%m")
    return r.to_frame('ret')


def draw_equity(equity: pd.Series) -> str:
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot equity curve with better styling
    ax.plot(equity.index, equity.values, linewidth=2, color='#2E86AB', alpha=0.9)
    ax.fill_between(equity.index, 1.0, equity.values, alpha=0.3, color='#2E86AB')
    
    # Formatting
    ax.set_title("Equity Curve", fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Equity", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Format dates on x-axis
    if len(equity) > 50:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(equity)//10)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    else:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    
    # Rotate date labels to prevent overlap
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Better y-axis formatting
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.3f}'))
    
    # Tight layout to prevent label cutoff
    plt.tight_layout()
    
    return _embed_png(_png_bytes(fig))


def draw_drawdown(equity: pd.Series) -> str:
    peak = equity.cummax()
    dd = (equity / peak - 1.0)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot drawdown with better styling
    ax.plot(dd.index, dd.values, linewidth=2, color='#C73E1D', alpha=0.9)
    ax.fill_between(dd.index, 0, dd.values, alpha=0.3, color='#C73E1D')
    
    # Formatting
    ax.set_title("Drawdown", fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Drawdown", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Format dates on x-axis
    if len(dd) > 50:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dd)//10)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    else:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    
    # Rotate date labels to prevent overlap
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Better y-axis formatting (as percentage)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*100:.1f}%'))
    
    # Set y-axis limits to show drawdown properly
    ax.set_ylim(dd.min() * 1.1, 0.01)
    
    # Tight layout to prevent label cutoff
    plt.tight_layout()
    
    return _embed_png(_png_bytes(fig))


def build_report(equity: pd.Series, comps: dict[str, pd.Series], out_html: str) -> None:
    eq_img = draw_equity(equity)
    dd_img = draw_drawdown(equity)
    m = monthly_returns(equity)
    table = m.to_html(float_format=lambda x: f"{x*100:.2f}%")
    pnl_sum = {k: float(v.sum()) for k, v in comps.items()}
    
    # Format PnL components nicely
    pnl_formatted = "<table class='pnl-table'>\n"
    for k, v in pnl_sum.items():
        if k in ['gross', 'carry', 'net']:
            formatted_val = f"{v*100:.2f}%"
        else:
            formatted_val = f"{v:.4f}"
        pnl_formatted += f"  <tr><td class='label'>{k.title()}:</td><td class='value'>{formatted_val}</td></tr>\n"
    pnl_formatted += "</table>"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>BTC Trading Bot - Backtest Report</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
                color: #333;
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-bottom: 30px;
            }}
            h2 {{
                color: #34495e;
                border-left: 4px solid #3498db;
                padding-left: 15px;
                margin-top: 40px;
                margin-bottom: 20px;
            }}
            .chart-container {{
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .chart-container img {{
                max-width: 100%;
                height: auto;
                border-radius: 4px;
            }}
            table {{
                background: white;
                border-radius: 8px;
                width: 100%;
                border-collapse: collapse;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin: 20px 0;
            }}
            table th, table td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
            }}
            table th {{
                background-color: #3498db;
                color: white;
                font-weight: 600;
            }}
            table tbody tr:hover {{
                background-color: #f8f9fa;
            }}
            .pnl-table {{
                max-width: 400px;
                font-family: 'Monaco', 'Menlo', monospace;
            }}
            .pnl-table .label {{
                font-weight: 600;
                color: #2c3e50;
                width: 120px;
            }}
            .pnl-table .value {{
                font-weight: 700;
                color: #27ae60;
                text-align: right;
            }}
            .summary {{
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .metric-card {{
                background: white;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: 700;
                color: #27ae60;
                margin-bottom: 8px;
            }}
            .metric-label {{
                font-size: 14px;
                color: #7f8c8d;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
        </style>
    </head>
    <body>
        <h1>🤖 BTC Trading Bot - Backtest Report</h1>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{((equity.iloc[-1] - 1) * 100):.2f}%</div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{len(equity)} bars</div>
                <div class="metric-label">Period</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{equity.index[0].strftime('%Y-%m-%d')}</div>
                <div class="metric-label">Start Date</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{equity.index[-1].strftime('%Y-%m-%d')}</div>
                <div class="metric-label">End Date</div>
            </div>
        </div>

        <h2>📈 Equity Curve</h2>
        <div class="chart-container">
            {eq_img}
        </div>

        <h2>📉 Drawdown</h2>
        <div class="chart-container">
            {dd_img}
        </div>

        <h2>📅 Monthly Returns</h2>
        <div class="chart-container">
            {table}
        </div>

        <h2>💰 PnL Breakdown</h2>
        <div class="summary">
            {pnl_formatted}
        </div>
    </body>
    </html>
    """
    Path(out_html).parent.mkdir(parents=True, exist_ok=True)
    Path(out_html).write_text(html, encoding="utf-8")


