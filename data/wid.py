"""World Inequality Database (WID) data loader.

Uses WID bulk CSV data or per-country downloads. Since WID has no official
Python package, this module handles downloading and parsing the data files.

For the bulk download approach, WID provides country-level CSV files at:
https://wid.world/bulk_download/WID_data_{country_code}.csv

This module downloads per-country files for our focus countries rather than
the full 500MB+ bulk archive.
"""

import io
from pathlib import Path

import pandas as pd
import requests

from data.cache import cached
from data.config import (
    RAW_DATA_DIR, FOCUS_COUNTRIES, EXTENDED_COUNTRIES,
    WID_VARIABLES, WID_PERCENTILES,
    DEFAULT_START_YEAR, DEFAULT_END_YEAR,
)

_WID_BASE_URL = "https://wid.world/bulk_download/WID_data_{code}.csv"


def _download_country(country_code: str) -> pd.DataFrame:
    """Download WID data for a single country."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    local_path = RAW_DATA_DIR / f"WID_data_{country_code}.csv"

    if not local_path.exists():
        url = _WID_BASE_URL.format(code=country_code)
        print(f"Downloading WID data for {country_code}...")
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        local_path.write_bytes(resp.content)

    # WID CSVs use semicolons as separators
    df = pd.read_csv(local_path, sep=";", low_memory=False)
    df["country"] = country_code
    return df


def load_country(country_code: str) -> pd.DataFrame:
    """Load WID data for a single country (cached)."""
    return cached(
        f"wid_country_{country_code}",
        lambda: _download_country(country_code),
        max_age_days=30,
    )


def _extract_variable(df: pd.DataFrame, var_prefix: str,
                       percentiles: list[str] | None = None,
                       age_group: str = "992",
                       pop_unit: str = "j") -> pd.DataFrame:
    """Extract a specific variable from WID raw data.

    WID variable names follow the pattern: {indicator}{age}{pop}
    e.g., sptinc992j = share of pre-tax income, age 20+, equal-split
    """
    var_code = f"{var_prefix}{pop_unit}{age_group}"

    mask = df["variable"].str.startswith(var_code) if "variable" in df.columns else pd.Series(False, index=df.index)
    subset = df[mask].copy()

    if subset.empty:
        return pd.DataFrame(columns=["country", "year", "percentile", "value"])

    result = subset[["country", "year", "percentile", "value"]].copy()
    result["year"] = pd.to_numeric(result["year"], errors="coerce")
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    result = result.dropna(subset=["year", "value"])
    result["year"] = result["year"].astype(int)

    if percentiles is not None:
        result = result[result["percentile"].isin(percentiles)]

    return result.reset_index(drop=True)


def get_income_shares(countries=None, income_concept="pretax",
                      percentiles=None, start_year=None, end_year=None):
    """Get income shares by percentile group.

    Parameters
    ----------
    countries : list of str, optional
        ISO-2 country codes. Defaults to FOCUS_COUNTRIES.
    income_concept : str
        "pretax" for pre-tax national income, "posttax" for post-tax disposable,
        "factor" for factor income.
    percentiles : list of str, optional
        WID percentile codes (e.g., ["p0p50", "p90p100"]). Defaults to all main groups.
    start_year, end_year : int, optional

    Returns
    -------
    pd.DataFrame with columns: country, year, percentile, value
    """
    countries = countries or FOCUS_COUNTRIES
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    concept_map = {
        "pretax": "sptinc",
        "posttax": "sdiinc",
        "factor": "sfainc",
    }
    var_prefix = concept_map.get(income_concept)
    if var_prefix is None:
        raise ValueError(f"Unknown income_concept '{income_concept}'")

    if percentiles is None:
        percentiles = list(WID_PERCENTILES.values())

    frames = []
    for cc in countries:
        raw = load_country(cc)
        extracted = _extract_variable(raw, var_prefix, percentiles=percentiles)
        extracted = extracted[
            (extracted["year"] >= start_year) & (extracted["year"] <= end_year)
        ]
        frames.append(extracted)

    if not frames:
        return pd.DataFrame(columns=["country", "year", "percentile", "value"])

    return pd.concat(frames, ignore_index=True)


def get_average_income(countries=None, income_concept="pretax",
                       percentiles=None, start_year=None, end_year=None):
    """Get average income at specific percentiles (for absolute comparisons).

    Parameters
    ----------
    countries : list of str, optional
    income_concept : str
        "pretax" or "posttax"
    percentiles : list of str, optional
        WID percentile codes. Defaults to main groups.
    start_year, end_year : int, optional

    Returns
    -------
    pd.DataFrame with columns: country, year, percentile, value
    """
    countries = countries or FOCUS_COUNTRIES
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    concept_map = {
        "pretax": "aptinc",
        "posttax": "adiinc",
        "factor": "afainc",
    }
    var_prefix = concept_map.get(income_concept)
    if var_prefix is None:
        raise ValueError(f"Unknown income_concept '{income_concept}'")

    if percentiles is None:
        percentiles = list(WID_PERCENTILES.values())

    frames = []
    for cc in countries:
        raw = load_country(cc)
        extracted = _extract_variable(raw, var_prefix, percentiles=percentiles)
        extracted = extracted[
            (extracted["year"] >= start_year) & (extracted["year"] <= end_year)
        ]
        frames.append(extracted)

    if not frames:
        return pd.DataFrame(columns=["country", "year", "percentile", "value"])

    return pd.concat(frames, ignore_index=True)


def get_wealth_shares(countries=None, percentiles=None,
                      start_year=None, end_year=None):
    """Get wealth shares by percentile group.

    Returns
    -------
    pd.DataFrame with columns: country, year, percentile, value
    """
    countries = countries or FOCUS_COUNTRIES
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    if percentiles is None:
        percentiles = list(WID_PERCENTILES.values())

    frames = []
    for cc in countries:
        raw = load_country(cc)
        extracted = _extract_variable(raw, "shweal", percentiles=percentiles)
        extracted = extracted[
            (extracted["year"] >= start_year) & (extracted["year"] <= end_year)
        ]
        frames.append(extracted)

    if not frames:
        return pd.DataFrame(columns=["country", "year", "percentile", "value"])

    return pd.concat(frames, ignore_index=True)


def get_top_shares_timeseries(countries=None, percentile="p99p100",
                               concept="pretax", start_year=None, end_year=None):
    """Convenience function: get a single percentile share over time.

    Useful for plotting top 1% or top 10% share time series.

    Returns
    -------
    pd.DataFrame with columns: country, year, value
    """
    if concept == "wealth":
        df = get_wealth_shares(countries, percentiles=[percentile],
                               start_year=start_year, end_year=end_year)
    else:
        df = get_income_shares(countries, income_concept=concept,
                               percentiles=[percentile],
                               start_year=start_year, end_year=end_year)
    return df


def get_ppp_exchange_rates(countries=None, year: int = 2019):
    """Get PPP exchange rates (LCU per USD) from WID.

    The variable xlcuspi999 gives the PPP conversion factor
    from local currency units to international (US) dollars.

    Parameters
    ----------
    countries : list of str, optional
        ISO-2 country codes. Defaults to FOCUS_COUNTRIES.
    year : int
        Target year. Uses closest available year.

    Returns
    -------
    dict mapping country code (ISO-2) to PPP exchange rate (float).
        Divide WID local-currency values by this to get PPP USD.
    """
    countries = countries or FOCUS_COUNTRIES

    rates = {}
    for cc in countries:
        raw = load_country(cc)
        mask = raw["variable"] == "xlcuspi999"
        sub = raw[mask].copy()
        if sub.empty:
            continue
        sub["year"] = pd.to_numeric(sub["year"], errors="coerce")
        sub["value"] = pd.to_numeric(sub["value"], errors="coerce")
        sub = sub.dropna(subset=["year", "value"])
        sub["year_diff"] = abs(sub["year"] - year)
        closest = sub.sort_values("year_diff").iloc[0]
        rates[cc] = float(closest["value"])

    return rates
