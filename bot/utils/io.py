import os
from typing import Optional
import pandas as pd


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_parquet(df: pd.DataFrame, path: str) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    df.to_parquet(path, engine="pyarrow")


def read_parquet(path: str) -> pd.DataFrame:
    return pd.read_parquet(path, engine="pyarrow")


def ohlcv_resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    agg = {
        "o": "first",
        "h": "max",
        "l": "min",
        "c": "last",
        "v": "sum",
    }
    rs = df.resample(timeframe).agg(agg).dropna(how="any")
    return rs


def align_and_ffill(series: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    return series.reindex(index).ffill()
