from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd


def combine_positions(pos_map: Dict[str, pd.Series], max_exposure: float = 1.25) -> pd.Series:
    # Align all positions
    idx = None
    for s in pos_map.values():
        idx = s.index if idx is None else idx.union(s.index)
    aligned = {k: v.reindex(idx).ffill().fillna(0.0) for k, v in pos_map.items()}

    names = list(aligned.keys())
    a = aligned[names[0]] if names else pd.Series(0.0, index=idx)
    b = aligned[names[1]] if len(names) > 1 else pd.Series(0.0, index=idx)

    # Correlation rule: if both long or both short, scale each to 70%
    same_sign = (np.sign(a) == np.sign(b)) & (np.sign(a) != 0)
    a_adj = a.copy(); b_adj = b.copy()
    a_adj[same_sign] = a[same_sign] * 0.7
    b_adj[same_sign] = b[same_sign] * 0.7

    combined = a_adj + b_adj

    # Cap exposure to max_exposure notional
    over = combined.abs() > max_exposure
    if over.any():
        scale = max_exposure / combined.abs()
        scale[~over] = 1.0
        combined = combined * scale

    return combined
