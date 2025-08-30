from typing import Tuple
import numpy as np
import pandas as pd


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    # Handle both old ('h','l','c') and new ('high','low','close') column names
    high_col = "high" if "high" in df.columns else "h"
    low_col = "low" if "low" in df.columns else "l"
    close_col = "close" if "close" in df.columns else "c"
    
    high = df[high_col]
    low = df[low_col]
    close = df[close_col].shift()
    tr = np.maximum.reduce([
        (high - low).values,
        (high - close).abs().values,
        (low - close).abs().values,
    ])
    tr_series = pd.Series(tr, index=df.index)
    return tr_series.ewm(alpha=1 / n, adjust=False).mean()


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def realized_vol(series: pd.Series, n: int = 10) -> pd.Series:
    log_ret = np.log(series).diff()
    rv = log_ret.rolling(n).std() * np.sqrt(365 * 24)  # annualized on 1h bars
    return rv


def rolling_percentile(series: pd.Series, window: int, pct: float) -> pd.Series:
    def _percentile(x: np.ndarray) -> float:
        return float(np.nanpercentile(x, pct))

    return series.rolling(window).apply(_percentile, raw=True)


def donchian(df: pd.DataFrame, n: int) -> Tuple[pd.Series, pd.Series]:
    return df["h"].rolling(n).max(), df["l"].rolling(n).min()
