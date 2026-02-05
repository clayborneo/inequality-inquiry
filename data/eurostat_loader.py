"""Eurostat EU-SILC data loader using the `eurostat` Python package.

Named eurostat_loader.py (not eurostat.py) to avoid shadowing the
pip-installed `eurostat` package.
"""

import pandas as pd

from data.cache import cached
from data.config import (
    ISO2_TO_EUROSTAT, DEFAULT_START_YEAR, DEFAULT_END_YEAR,
)


def _fetch_eurostat_table(table_code: str) -> pd.DataFrame:
    """Download a Eurostat table using the eurostat package."""
    import eurostat as est
    df = est.get_data_df(table_code)
    return df


def get_gini(countries=None, start_year=None, end_year=None):
    """Gini coefficient of equivalised disposable income (ilc_di12).

    Parameters
    ----------
    countries : list of str, optional
        ISO-2 country codes. If None, returns all available countries.
    start_year, end_year : int, optional

    Returns
    -------
    pd.DataFrame with columns: country, year, gini
    """
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    def _load():
        return _fetch_eurostat_table("ilc_di12")

    df = cached("eurostat_gini_ilc_di12", _load, max_age_days=30)

    if df.empty:
        return pd.DataFrame(columns=["country", "year", "gini"])

    # Eurostat tables have country codes in a 'geo' or 'geo\\TIME_PERIOD' column
    # The format varies; we need to melt the wide-format table
    try:
        # Try to identify the geo column and time columns
        geo_col = [c for c in df.columns if "geo" in c.lower()]
        if geo_col:
            geo_col = geo_col[0]
        else:
            geo_col = df.columns[0]

        # Melt year columns
        id_vars = [c for c in df.columns if not str(c).startswith(("19", "20"))]
        time_cols = [c for c in df.columns if str(c).startswith(("19", "20"))]

        if time_cols:
            melted = df.melt(id_vars=id_vars, value_vars=time_cols,
                             var_name="year", value_name="gini")
            melted["year"] = pd.to_numeric(melted["year"], errors="coerce")
            melted["gini"] = pd.to_numeric(melted["gini"], errors="coerce")
            melted = melted.dropna(subset=["year", "gini"])
            melted["year"] = melted["year"].astype(int)

            result = melted[[geo_col, "year", "gini"]].copy()
            result = result.rename(columns={geo_col: "country"})
        else:
            result = df.copy()
            result.columns = ["country", "year", "gini"]
    except Exception:
        return df  # Return raw if parsing fails

    result = result[
        (result["year"] >= start_year) & (result["year"] <= end_year)
    ]

    if countries is not None:
        eurostat_codes = [ISO2_TO_EUROSTAT.get(c, c) for c in countries]
        result = result[result["country"].isin(eurostat_codes)]

    return result.reset_index(drop=True)


def get_s80_s20(countries=None, start_year=None, end_year=None):
    """Income quintile share ratio S80/S20 (ilc_di11).

    Returns
    -------
    pd.DataFrame with columns: country, year, s80_s20
    """
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    def _load():
        return _fetch_eurostat_table("ilc_di11")

    df = cached("eurostat_s80s20_ilc_di11", _load, max_age_days=30)

    if df.empty:
        return pd.DataFrame(columns=["country", "year", "s80_s20"])

    # Similar parsing as get_gini
    try:
        geo_col = [c for c in df.columns if "geo" in c.lower()]
        geo_col = geo_col[0] if geo_col else df.columns[0]

        id_vars = [c for c in df.columns if not str(c).startswith(("19", "20"))]
        time_cols = [c for c in df.columns if str(c).startswith(("19", "20"))]

        if time_cols:
            melted = df.melt(id_vars=id_vars, value_vars=time_cols,
                             var_name="year", value_name="s80_s20")
            melted["year"] = pd.to_numeric(melted["year"], errors="coerce")
            melted["s80_s20"] = pd.to_numeric(melted["s80_s20"], errors="coerce")
            melted = melted.dropna(subset=["year", "s80_s20"])
            melted["year"] = melted["year"].astype(int)

            result = melted[[geo_col, "year", "s80_s20"]].copy()
            result = result.rename(columns={geo_col: "country"})
        else:
            result = df.copy()
    except Exception:
        return df

    result = result[
        (result["year"] >= start_year) & (result["year"] <= end_year)
    ]

    if countries is not None:
        eurostat_codes = [ISO2_TO_EUROSTAT.get(c, c) for c in countries]
        result = result[result["country"].isin(eurostat_codes)]

    return result.reset_index(drop=True)


def get_poverty_rate(countries=None, start_year=None, end_year=None):
    """At-risk-of-poverty rate after social transfers (ilc_li02).

    Returns
    -------
    pd.DataFrame with columns: country, year, poverty_rate
    """
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    def _load():
        return _fetch_eurostat_table("ilc_li02")

    df = cached("eurostat_poverty_ilc_li02", _load, max_age_days=30)

    if df.empty:
        return pd.DataFrame(columns=["country", "year", "poverty_rate"])

    try:
        geo_col = [c for c in df.columns if "geo" in c.lower()]
        geo_col = geo_col[0] if geo_col else df.columns[0]

        id_vars = [c for c in df.columns if not str(c).startswith(("19", "20"))]
        time_cols = [c for c in df.columns if str(c).startswith(("19", "20"))]

        if time_cols:
            melted = df.melt(id_vars=id_vars, value_vars=time_cols,
                             var_name="year", value_name="poverty_rate")
            melted["year"] = pd.to_numeric(melted["year"], errors="coerce")
            melted["poverty_rate"] = pd.to_numeric(melted["poverty_rate"], errors="coerce")
            melted = melted.dropna(subset=["year", "poverty_rate"])
            melted["year"] = melted["year"].astype(int)

            result = melted[[geo_col, "year", "poverty_rate"]].copy()
            result = result.rename(columns={geo_col: "country"})
        else:
            result = df.copy()
    except Exception:
        return df

    result = result[
        (result["year"] >= start_year) & (result["year"] <= end_year)
    ]

    if countries is not None:
        eurostat_codes = [ISO2_TO_EUROSTAT.get(c, c) for c in countries]
        result = result[result["country"].isin(eurostat_codes)]

    return result.reset_index(drop=True)
