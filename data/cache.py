"""Disk-based caching layer using parquet files."""

import hashlib
import time
from pathlib import Path
from typing import Callable

import pandas as pd

from data.config import CACHE_DIR


def _cache_path(key: str) -> Path:
    """Return the parquet file path for a given cache key."""
    safe_key = hashlib.md5(key.encode()).hexdigest()
    return CACHE_DIR / f"{safe_key}.parquet"


def _meta_path(key: str) -> Path:
    """Return the metadata file path for a given cache key."""
    safe_key = hashlib.md5(key.encode()).hexdigest()
    return CACHE_DIR / f"{safe_key}.meta"


def cached(key: str, loader_fn: Callable[[], pd.DataFrame],
           max_age_days: int = 7) -> pd.DataFrame:
    """Load data from cache or call loader_fn and cache the result.

    Parameters
    ----------
    key : str
        A unique string identifying this data query.
    loader_fn : callable
        A function that returns a DataFrame when called.
    max_age_days : int
        Maximum age of cached data in days before refreshing.

    Returns
    -------
    pd.DataFrame
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(key)
    meta = _meta_path(key)

    # Check if cached data exists and is fresh
    if path.exists() and meta.exists():
        cached_time = float(meta.read_text().strip())
        age_days = (time.time() - cached_time) / 86400
        if age_days < max_age_days:
            return pd.read_parquet(path)

    # Load fresh data
    df = loader_fn()
    df.to_parquet(path, index=False)
    meta.write_text(str(time.time()))
    return df


def clear_cache():
    """Remove all cached files."""
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.parquet"):
            f.unlink()
        for f in CACHE_DIR.glob("*.meta"):
            f.unlink()
