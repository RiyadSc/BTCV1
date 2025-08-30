"""
Utility functions for the FGI strategy backtesting
"""
import os
from pathlib import Path

def ensure_dir(directory: str) -> None:
    """Ensure a directory exists, create if it doesn't."""
    Path(directory).mkdir(parents=True, exist_ok=True)
