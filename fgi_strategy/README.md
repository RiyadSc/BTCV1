# Fear and Greed Index (FGI) Trading Strategy

## Overview

This is a systematic Bitcoin trading strategy based on the CoinMarketCap Fear and Greed Index. The strategy exploits market psychology by buying during periods of extreme fear and selling during periods of extreme greed.

## Strategy Logic

### Entry Rules
- **Signal**: Enter when Fear and Greed Index ≤ 20 (Extreme Fear)
- **Position Size**: 25% of current equity per entry
- **Frequency**: Execute entries every 2 days while FGI remains ≤ 20
- **Rationale**: Buy when market is in extreme fear and potentially oversold

### Exit Rules
- **Signal**: Exit when Fear and Greed Index ≥ 80 (Extreme Greed)
- **Position Size**: Sell 25% of holdings per exit
- **Frequency**: Execute exits every 2 days while FGI remains ≥ 80
- **Rationale**: Sell when market is in extreme greed and potentially overbought

### Key Features
- **Gradual Scaling**: Builds positions gradually during fear periods
- **Risk Management**: Limits exposure with position sizing and interval controls
- **Market Psychology**: Leverages contrarian psychology indicators
- **Transaction Costs**: Accounts for 0.1% transaction costs per trade

## Implementation

### Data Sources
1. **Price Data**: Daily BTC price data from existing storage (`storage/spot_1d.parquet`)
2. **FGI Data**: CoinMarketCap Fear and Greed Index via API
   - Primary: CMC Pro API endpoint
   - Fallback: Mock data generator for testing/development

### Module Structure
```
fgi_strategy/
├── __init__.py              # Package initialization
├── data_fetcher.py          # FGI data collection and caching
├── backtest_engine.py       # Strategy logic and backtesting
├── reporter.py              # Results analysis and reporting
└── data/                    # Cached FGI data
    └── fgi_historical.parquet
```

## Usage

### Basic Backtest
```bash
python3 run_fgi_backtest.py
```

### Programmatic Usage
```python
from fgi_strategy.data_fetcher import fetch_and_cache_fgi_data
from fgi_strategy.backtest_engine import run_fgi_backtest, FGIConfig
from fgi_strategy.reporter import generate_full_report
import pandas as pd

# Load data
btc_data = pd.read_parquet("storage/spot_1d.parquet")
fgi_data = fetch_and_cache_fgi_data()

# Configure strategy
config = FGIConfig(
    entry_threshold=20.0,
    exit_threshold=80.0,
    position_size_pct=0.25,
    entry_interval_days=2,
    exit_interval_days=2,
    initial_capital=100000.0
)

# Run backtest
results = run_fgi_backtest(btc_data, fgi_data, config)

# Generate reports
generate_full_report(results, "output_directory")
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `entry_threshold` | 20.0 | FGI level to trigger entries (≤ value) |
| `exit_threshold` | 80.0 | FGI level to trigger exits (≥ value) |
| `position_size_pct` | 0.25 | Percentage of equity per trade (25%) |
| `entry_interval_days` | 2 | Days between entries while in fear zone |
| `exit_interval_days` | 2 | Days between exits while in greed zone |
| `initial_capital` | 100000.0 | Starting capital ($100k) |
| `transaction_cost_pct` | 0.001 | Transaction costs (0.1%) |

## Sample Results

Based on backtesting from 2023-01-01 to 2025-08-17:

### Performance Metrics
- **Total Return**: 151.81%
- **Annualized Return**: 42.10%
- **Sharpe Ratio**: 1.49
- **Maximum Drawdown**: -19.56%
- **Win Rate**: 55.5%

### Trading Activity
- **Total Trades**: 139 (29 buys, 110 sells)
- **Average Buy Size**: $35,826
- **Average Sell Size**: $9,564
- **Transaction Costs**: $2,091

### Comparison vs Buy & Hold
- **Buy & Hold Return**: 608.71%
- **Strategy Excess Return**: -456.90%

*Note: While the strategy had positive returns, it underperformed buy-and-hold during this specific period of strong Bitcoin performance.*

## Output Files

Running the backtest generates:
- `fgi_equity_curve.csv` - Daily portfolio values and positions
- `fgi_trades.csv` - Complete trade history
- `fgi_summary.txt` - Text summary of results
- `fgi_report.html` - Interactive HTML report
- `fgi_equity_curve.png` - Equity curve visualization
- `fgi_drawdown.png` - Drawdown analysis

## API Configuration

### Using CoinMarketCap Pro API
```python
from fgi_strategy.data_fetcher import fetch_and_cache_fgi_data

# With API key
fgi_data = fetch_and_cache_fgi_data(
    api_key="your_cmc_pro_api_key",
    force_refresh=True
)
```

### Mock Data (Development)
When no API key is provided or API fails, the system automatically generates realistic mock FGI data for testing and development.

## Strategy Considerations

### Strengths
1. **Contrarian Approach**: Exploits market psychology extremes
2. **Risk Management**: Gradual position building/unwinding
3. **Clear Rules**: Objective entry/exit criteria
4. **Backtesting Framework**: Comprehensive testing and analysis

### Limitations
1. **Market Regime Dependency**: May underperform in strong trending markets
2. **Fear/Greed Persistence**: Extended periods in extreme zones can be costly
3. **Transaction Costs**: Frequent trading increases cost burden
4. **FGI Lag**: Index may lag actual market conditions

### Potential Improvements
1. **Dynamic Thresholds**: Adjust entry/exit levels based on market conditions
2. **Position Sizing**: Variable position sizes based on FGI intensity
3. **Risk Controls**: Maximum position limits or stop-losses
4. **Multi-Asset**: Extend to other cryptocurrencies
5. **Market Filters**: Combine with trend or momentum filters

## Dependencies

- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `matplotlib` - Plotting and visualization
- `requests` - API data fetching
- `pathlib` - File system operations

## License

This strategy implementation is part of the TradeBOT experimental framework.
