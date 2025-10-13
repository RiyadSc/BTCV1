"""
FGI Data Fetcher Module
"""
import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def fetch_and_cache_fgi_data(
    cache_path: str = "fgi_strategy/data/fgi_historical_real.parquet",
    api_key: str | None = None,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Fetch FGI data from cache or API.
    
    Args:
        cache_path: Path to cached parquet file
        api_key: API key (not used, kept for compatibility)
        force_refresh: Force API refresh (not used, kept for compatibility)
        
    Returns:
        DataFrame with FGI data
    """
    cache_file = Path(cache_path)
    
    if cache_file.exists():
        logger.info(f"Loading FGI data from cache: {cache_path}")
        fgi_data = pd.read_parquet(cache_path)
        logger.info(f"Loaded {len(fgi_data)} FGI records from {fgi_data.index.min()} to {fgi_data.index.max()}")
        return fgi_data
    
    # Try fallback cache
    fallback_path = "fgi_strategy/data/fgi_historical.parquet"
    if Path(fallback_path).exists():
        logger.warning(f"Cache not found at {cache_path}, using fallback: {fallback_path}")
        fgi_data = pd.read_parquet(fallback_path)
        logger.info(f"Loaded {len(fgi_data)} FGI records from fallback")
        return fgi_data
    
    logger.error(f"No FGI data found at {cache_path} or fallback")
    return pd.DataFrame()
