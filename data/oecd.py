"""OECD data loader using the new SDMX REST API (sdmx.oecd.org).

The OECD migrated from stats.oecd.org to sdmx.oecd.org. This module
queries the new CSV endpoint directly, which is more reliable than
pandasdmx for the new API.

Key datasets:
- DSD_WISE_IDD@DF_IDD: Income Distribution Database (Gini, decile shares, poverty)
"""

import io

import pandas as pd
import requests

from data.cache import cached
from data.config import (
    ISO2_TO_ISO3, ISO3_TO_ISO2,
    DEFAULT_START_YEAR, DEFAULT_END_YEAR,
)

_BASE_URL = "https://sdmx.oecd.org/public/rest/data"
_AGENCY = "OECD.WISE.INE"
_DATAFLOW = "DSD_WISE_IDD@DF_IDD"


def _fetch_idd_csv(iso3_codes: list[str], measures: list[str],
                    start_year: int, end_year: int) -> pd.DataFrame:
    """Fetch IDD data from the OECD SDMX REST API as CSV.

    The IDD dataflow has 9 key dimensions:
    REF_AREA.FREQ.MEASURE.STATISTICAL_OPERATION.UNIT_MEASURE.AGE.METHODOLOGY.DEFINITION.POVERTY_LINE

    Parameters
    ----------
    iso3_codes : list of str
        ISO-3 country codes (e.g., ["USA", "FRA"])
    measures : list of str
        OECD measure codes (e.g., ["INC_DISP_GINI", "INC_MRKT_GINI"])
    """
    ref_area = "+".join(iso3_codes)
    measure = "+".join(measures)
    # Dimensions: REF_AREA.FREQ.MEASURE.STAT_OP.UNIT.AGE.METHOD.DEFINITION.POVERTY_LINE
    key = f"{ref_area}.A.{measure}..._T.METH2012.."
    url = f"{_BASE_URL}/{_AGENCY},{_DATAFLOW},/{key}"

    resp = requests.get(
        url,
        params={"startPeriod": str(start_year), "endPeriod": str(end_year),
                "format": "csv"},
        timeout=120,
    )
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text))
    return df


def _parse_idd_gini(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse raw OECD IDD CSV into a tidy Gini DataFrame."""
    if raw.empty:
        return pd.DataFrame(columns=["country_code", "year", "gini_mkt", "gini_disp"])

    # Keep only current-definition rows (D_CUR) where available
    if "DEFINITION" in raw.columns:
        cur = raw[raw["DEFINITION"] == "D_CUR"]
        if not cur.empty:
            raw = cur

    cols = {
        "REF_AREA": "country_iso3",
        "MEASURE": "measure",
        "TIME_PERIOD": "year",
        "OBS_VALUE": "value",
    }
    df = raw[list(cols.keys())].rename(columns=cols).copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["year", "value"])

    # Map ISO-3 to ISO-2
    df["country_code"] = df["country_iso3"].map(ISO3_TO_ISO2)
    df = df.dropna(subset=["country_code"])

    # Pivot measures into columns
    disp = df[df["measure"] == "INC_DISP_GINI"][["country_code", "year", "value"]].rename(
        columns={"value": "gini_disp"})
    mkt = df[df["measure"] == "INC_MRKT_GINI"][["country_code", "year", "value"]].rename(
        columns={"value": "gini_mkt"})

    if disp.empty and mkt.empty:
        return pd.DataFrame(columns=["country_code", "year", "gini_mkt", "gini_disp"])

    if not disp.empty and not mkt.empty:
        result = disp.merge(mkt, on=["country_code", "year"], how="outer")
    elif not disp.empty:
        result = disp
        result["gini_mkt"] = pd.NA
    else:
        result = mkt
        result["gini_disp"] = pd.NA

    return result.sort_values(["country_code", "year"]).reset_index(drop=True)


def get_idd_gini(countries=None, start_year=None, end_year=None):
    """Fetch Gini coefficients (market and disposable) from OECD IDD.

    Returns
    -------
    pd.DataFrame with columns: country_code, year, gini_mkt, gini_disp
        Gini values are on a 0-1 scale.
    """
    countries = countries or list(ISO2_TO_ISO3.keys())
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    iso3_codes = [ISO2_TO_ISO3[c] for c in countries if c in ISO2_TO_ISO3]

    def _load():
        try:
            raw = _fetch_idd_csv(
                iso3_codes,
                measures=["INC_DISP_GINI", "INC_MRKT_GINI"],
                start_year=start_year,
                end_year=end_year,
            )
            return _parse_idd_gini(raw)
        except Exception as e:
            print(f"OECD IDD query failed: {e}")
            return pd.DataFrame(
                columns=["country_code", "year", "gini_mkt", "gini_disp"])

    return cached(
        f"oecd_idd_gini_{'_'.join(sorted(iso3_codes))}_{start_year}_{end_year}",
        _load,
        max_age_days=30,
    )


def get_idd_decile_shares(countries=None, start_year=None, end_year=None):
    """Fetch income shares by decile from OECD IDD.

    Returns
    -------
    pd.DataFrame with columns: country_code, year, measure, value
    """
    countries = countries or list(ISO2_TO_ISO3.keys())
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    iso3_codes = [ISO2_TO_ISO3[c] for c in countries if c in ISO2_TO_ISO3]

    # Decile share measure codes
    decile_measures = [f"INC_DISP_SHR_D{i}" for i in range(1, 11)]

    def _load():
        try:
            raw = _fetch_idd_csv(
                iso3_codes,
                measures=decile_measures,
                start_year=start_year,
                end_year=end_year,
            )
            if raw.empty:
                return pd.DataFrame()

            cols = {
                "REF_AREA": "country_iso3",
                "MEASURE": "measure",
                "TIME_PERIOD": "year",
                "OBS_VALUE": "value",
            }
            df = raw[list(cols.keys())].rename(columns=cols)
            df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df["country_code"] = df["country_iso3"].map(ISO3_TO_ISO2)
            return df.dropna(subset=["country_code", "year", "value"]).reset_index(drop=True)
        except Exception as e:
            print(f"OECD decile shares query failed: {e}")
            return pd.DataFrame()

    return cached(
        f"oecd_idd_deciles_{'_'.join(sorted(iso3_codes))}_{start_year}_{end_year}",
        _load,
        max_age_days=30,
    )


def get_health_data(countries=None, start_year=None, end_year=None):
    """Fetch OECD health indicators.

    Note: Health data uses a different OECD dataflow. This function uses the
    World Bank API via health_social.py as the primary source; this is a
    secondary option if needed.

    Returns
    -------
    pd.DataFrame
    """
    countries = countries or list(ISO2_TO_ISO3.keys())
    start_year = start_year or DEFAULT_START_YEAR
    end_year = end_year or DEFAULT_END_YEAR

    iso3_codes = [ISO2_TO_ISO3[c] for c in countries if c in ISO2_TO_ISO3]

    def _load():
        try:
            ref_area = "+".join(iso3_codes)
            # OECD Health Status dataset
            url = (f"{_BASE_URL}/OECD.ELS.HD,DSD_HEALTH_STAT@DF_HEALTH_STAT,/"
                   f"{ref_area}.A.MATIMORTA+LIFEEXP._T._T._T..")
            resp = requests.get(
                url,
                params={"startPeriod": str(start_year),
                        "endPeriod": str(end_year),
                        "format": "csv"},
                timeout=120,
            )
            resp.raise_for_status()
            raw = pd.read_csv(io.StringIO(resp.text))

            if raw.empty:
                return pd.DataFrame()

            cols = {
                "REF_AREA": "country_iso3",
                "MEASURE": "measure",
                "TIME_PERIOD": "year",
                "OBS_VALUE": "value",
            }
            df = raw[list(cols.keys())].rename(columns=cols)
            df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df["country_code"] = df["country_iso3"].map(ISO3_TO_ISO2)
            return df.dropna(subset=["country_code", "year", "value"]).reset_index(drop=True)
        except Exception as e:
            print(f"OECD health data query failed: {e}")
            return pd.DataFrame()

    return cached(
        f"oecd_health_{'_'.join(sorted(iso3_codes))}_{start_year}_{end_year}",
        _load,
        max_age_days=30,
    )
