import pandas as pd
import numpy as np


def assert_hourly_utc(idx: pd.DatetimeIndex) -> None:
    assert idx.tz is not None and str(idx.tz) == 'UTC'
    assert (idx.minute == 0).all() and (idx.second == 0).all() and (idx.microsecond == 0).all()


def missing_ratio(idx: pd.DatetimeIndex) -> float:
    exp = pd.date_range(idx.min(), idx.max(), freq='1h', tz='UTC')
    return 1 - (len(idx.intersection(exp)) / len(exp))


def funding_cuts_ok(funding_series: pd.Series) -> bool:
    cuts = funding_series.replace(0, np.nan).dropna()
    if cuts.empty:
        return False
    per_day = cuts.groupby(cuts.index.date).size().median()
    return per_day >= 3


def corr_spot_mark_ok(spot_close: pd.Series, mark_close: pd.Series) -> bool:
    common = spot_close.dropna().index.intersection(mark_close.dropna().index)
    c = spot_close.reindex(common).corr(mark_close.reindex(common))
    return c > 0.999


def basis_stats(basis_rel: pd.Series) -> tuple[float, float]:
    return float(basis_rel.median()), float(basis_rel.std())


