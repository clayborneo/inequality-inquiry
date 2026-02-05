"""SWIID (Standardized World Income Inequality Database) loader.

Downloads the SWIID summary CSV from Harvard Dataverse and provides
filtered access to market and disposable income Gini coefficients.
"""

import io

import pandas as pd
import requests

from data.cache import cached
from data.config import (
    RAW_DATA_DIR, ISO2_TO_ISO3, ISO3_TO_ISO2, COUNTRY_NAMES,
    DEFAULT_START_YEAR, DEFAULT_END_YEAR,
)

# Direct download URL for swiid_summary.csv from Harvard Dataverse
_SWIID_SUMMARY_URL = (
    "https://raw.githubusercontent.com/fsolt/swiid/master/data/swiid_summary.csv"
)


def _download_swiid() -> pd.DataFrame:
    """Download and parse the SWIID summary CSV."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    local_path = RAW_DATA_DIR / "swiid_summary.csv"

    if not local_path.exists():
        resp = requests.get(_SWIID_SUMMARY_URL, timeout=60)
        resp.raise_for_status()
        local_path.write_bytes(resp.content)

    df = pd.read_csv(local_path)
    return df


def load_swiid() -> pd.DataFrame:
    """Load the full SWIID summary dataset (cached).

    Returns a DataFrame with columns including:
    country, year, gini_disp, gini_disp_se, gini_mkt, gini_mkt_se,
    abs_red, abs_red_se, rel_red, rel_red_se
    """
    return cached("swiid_summary_v2", _download_swiid, max_age_days=30)


def get_gini(countries=None, gini_type="disp", start_year=None, end_year=None):
    """Get Gini coefficients for selected countries and years.

    Parameters
    ----------
    countries : list of str, optional
        ISO-2 country codes. If None, returns all countries.
    gini_type : str
        "disp" for disposable income, "mkt" for market income.
    start_year, end_year : int, optional

    Returns
    -------
    pd.DataFrame with columns: country_code, country_name, year, gini, gini_se
    """
    df = load_swiid()
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    col = f"gini_{gini_type}"
    se_col = f"gini_{gini_type}_se"

    if col not in df.columns:
        raise ValueError(f"Unknown gini_type '{gini_type}'. Use 'disp' or 'mkt'.")

    df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()

    if countries is not None:
        # SWIID uses full country names, so we need to match
        name_set = {COUNTRY_NAMES.get(c, c) for c in countries}
        df = df[df["country"].isin(name_set)]

    result = df[["country", "year", col, se_col]].copy()
    result.columns = ["country_name", "year", "gini", "gini_se"]

    # Add ISO-2 codes where possible
    name_to_iso2 = {v: k for k, v in COUNTRY_NAMES.items()}
    result["country_code"] = result["country_name"].map(name_to_iso2).fillna("")

    return result.reset_index(drop=True)


def get_redistribution(countries=None, start_year=None, end_year=None):
    """Get market Gini, disposable Gini, and redistribution measures.

    Returns
    -------
    pd.DataFrame with columns: country_name, country_code, year,
        gini_mkt, gini_disp, abs_red, rel_red
    """
    df = load_swiid()
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()

    if countries is not None:
        name_set = {COUNTRY_NAMES.get(c, c) for c in countries}
        df = df[df["country"].isin(name_set)]

    cols = ["country", "year", "gini_mkt", "gini_disp", "abs_red", "rel_red"]
    available_cols = [c for c in cols if c in df.columns]
    result = df[available_cols].copy()
    result = result.rename(columns={"country": "country_name"})

    # Compute redistribution if not in the data
    if "abs_red" not in result.columns and "gini_mkt" in result.columns:
        result["abs_red"] = result["gini_mkt"] - result["gini_disp"]
    if "rel_red" not in result.columns and "gini_mkt" in result.columns:
        result["rel_red"] = (
            (result["gini_mkt"] - result["gini_disp"]) / result["gini_mkt"]
        )

    name_to_iso2 = {v: k for k, v in COUNTRY_NAMES.items()}
    result["country_code"] = result["country_name"].map(name_to_iso2).fillna("")

    return result.reset_index(drop=True)
