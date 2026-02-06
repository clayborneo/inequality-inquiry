"""Labor market data: working hours and labor force participation.

Working hours sourced from Our World in Data (Huberman & Minns + Penn World
Table). Labor force participation from the World Bank (ILO modeled estimates).
"""

import numpy as np
import pandas as pd
import requests

from data.cache import cached
from data.config import (
    ISO2_TO_ISO3, ISO3_TO_ISO2, WELLBEING_COUNTRIES,
)
# Reuse the World Bank fetcher from health_social
from data.health_social import _fetch_world_bank_indicator


# OWID indicator: annual working hours per worker
# Combines Huberman & Minns (1870-1938) + PWT (1950-2023)
_OWID_HOURS_DATA_URL = (
    "https://api.ourworldindata.org/v1/indicators/1103669.data.json"
)
_OWID_HOURS_META_URL = (
    "https://api.ourworldindata.org/v1/indicators/1103669.metadata.json"
)

# World Bank labor force participation indicators (ILO modeled, ages 15+)
_WB_LFP_INDICATORS = {
    "total": "SL.TLF.CACT.ZS",
    "female": "SL.TLF.CACT.FE.ZS",
    "male": "SL.TLF.CACT.MA.ZS",
}


def get_working_hours_timeseries(countries=None, start_year: int = 1950,
                                  end_year: int = 2023) -> pd.DataFrame:
    """Fetch annual working hours per worker from Our World in Data.

    Combines Huberman & Minns (1870-1938) and Penn World Table (1950-2023).

    Parameters
    ----------
    countries : list of str, optional
        ISO-2 codes. If None, returns all available countries.
    start_year, end_year : int
        Year range to include.

    Returns
    -------
    pd.DataFrame with columns: country_code, year, hours_per_worker
    """
    def _load():
        try:
            data_resp = requests.get(_OWID_HOURS_DATA_URL, timeout=60)
            data_resp.raise_for_status()
            meta_resp = requests.get(_OWID_HOURS_META_URL, timeout=60)
            meta_resp.raise_for_status()
        except Exception:
            return pd.DataFrame(columns=["country_code", "year",
                                         "hours_per_worker"])

        data = data_resp.json()
        meta = meta_resp.json()

        entity_map = {}
        if "dimensions" in meta and "entities" in meta["dimensions"]:
            for ent in meta["dimensions"]["entities"].get("values", []):
                if ent.get("code"):
                    entity_map[ent["id"]] = ent["code"]

        df = pd.DataFrame({
            "entity_id": data["entities"],
            "year": data["years"],
            "hours_per_worker": data["values"],
        })

        df["country_iso3"] = df["entity_id"].map(entity_map)
        df = df.dropna(subset=["country_iso3"])
        df["country_code"] = df["country_iso3"].map(ISO3_TO_ISO2)
        df = df.dropna(subset=["country_code"])

        df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()

        return df[["country_code", "year",
                    "hours_per_worker"]].reset_index(drop=True)

    df = cached(f"working_hours_ts_{start_year}_{end_year}", _load,
                max_age_days=30)

    if countries is not None and not df.empty:
        df = df[df["country_code"].isin(countries)].reset_index(drop=True)

    return df


def get_working_hours_historical(countries=None, start_year: int = 1870,
                                  end_year: int = 2023) -> pd.DataFrame:
    """Fetch long-run working hours including Huberman & Minns data (1870+).

    Convenience wrapper for get_working_hours_timeseries with 1870 start.
    Historical data (1870-1938) covers ~15 countries only.
    """
    return get_working_hours_timeseries(
        countries=countries, start_year=start_year, end_year=end_year)


def get_working_hours_snapshot(countries=None,
                                year: int = 2019) -> pd.DataFrame:
    """Get working hours for a single year (closest within +/-3 years).

    Returns
    -------
    pd.DataFrame with columns: country_code, hours_per_worker
    """
    ts = get_working_hours_timeseries(
        countries=countries, start_year=year - 3, end_year=year + 3)

    if ts.empty:
        return pd.DataFrame(columns=["country_code", "hours_per_worker"])

    # For each country, pick the year closest to target
    ts["year_diff"] = (ts["year"] - year).abs()
    idx = ts.groupby("country_code")["year_diff"].idxmin()
    result = ts.loc[idx, ["country_code", "hours_per_worker"]].copy()

    return result.reset_index(drop=True)


def get_labor_force_participation_timeseries(
    countries=None, start_year: int = 1990, end_year: int = 2024,
    gender: str = "total",
) -> pd.DataFrame:
    """Fetch labor force participation rate time series from World Bank.

    Parameters
    ----------
    countries : list of str, optional
        ISO-2 codes. Defaults to WELLBEING_COUNTRIES.
    start_year, end_year : int
    gender : str
        "total", "female", or "male"

    Returns
    -------
    pd.DataFrame with columns: country_code, year, lfp_rate
    """
    if gender not in _WB_LFP_INDICATORS:
        raise ValueError(f"gender must be one of {list(_WB_LFP_INDICATORS)}")

    if countries is None:
        countries = WELLBEING_COUNTRIES

    iso3_codes = [ISO2_TO_ISO3[c] for c in countries if c in ISO2_TO_ISO3]
    indicator = _WB_LFP_INDICATORS[gender]

    def _load():
        # Batch countries to avoid World Bank API URL-length limits
        batch_size = 10
        parts = []
        for i in range(0, len(iso3_codes), batch_size):
            batch = iso3_codes[i:i + batch_size]
            try:
                chunk = _fetch_world_bank_indicator(
                    indicator, batch,
                    start_year=start_year, end_year=end_year,
                )
                if not chunk.empty:
                    parts.append(chunk)
            except Exception:
                continue  # skip failed batches gracefully

        if not parts:
            return pd.DataFrame(columns=["country_code", "year", "lfp_rate"])

        wb_df = pd.concat(parts, ignore_index=True)
        wb_df["country_code"] = wb_df["country_iso3"].map(ISO3_TO_ISO2)
        wb_df = wb_df.dropna(subset=["country_code"])
        wb_df = wb_df.rename(columns={"value": "lfp_rate"})

        return wb_df[["country_code", "year",
                       "lfp_rate"]].reset_index(drop=True)

    key_countries = "_".join(sorted(countries))
    return cached(
        f"lfp_{gender}_ts_{start_year}_{end_year}_{key_countries}",
        _load, max_age_days=30)


def get_labor_force_participation_snapshot(
    countries=None, year: int = 2019,
) -> pd.DataFrame:
    """Fetch LFP for a single year: total, female, male, and gender gap.

    Returns
    -------
    pd.DataFrame with columns: country_code, lfp_total, lfp_female,
                                lfp_male, gender_gap
    """
    if countries is None:
        countries = WELLBEING_COUNTRIES

    dfs = {}
    for gender in ("total", "female", "male"):
        ts = get_labor_force_participation_timeseries(
            countries=countries, start_year=year - 3, end_year=year + 3,
            gender=gender)
        if ts.empty:
            continue
        # Pick closest year per country
        ts["year_diff"] = (ts["year"] - year).abs()
        idx = ts.groupby("country_code")["year_diff"].idxmin()
        dfs[gender] = ts.loc[idx, ["country_code", "lfp_rate"]].copy()
        dfs[gender] = dfs[gender].rename(
            columns={"lfp_rate": f"lfp_{gender}"})

    if not dfs:
        return pd.DataFrame(columns=["country_code", "lfp_total",
                                      "lfp_female", "lfp_male",
                                      "gender_gap"])

    result = dfs["total"]
    for gender in ("female", "male"):
        if gender in dfs:
            result = result.merge(dfs[gender], on="country_code", how="outer")

    if "lfp_male" in result.columns and "lfp_female" in result.columns:
        result["gender_gap"] = result["lfp_male"] - result["lfp_female"]

    return result.reset_index(drop=True)
