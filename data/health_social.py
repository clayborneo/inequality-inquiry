"""Health and social outcome data for the Spirit Level analysis.

Aggregates inequality and outcome data from OECD and other sources
into a single analysis-ready DataFrame for cross-country comparisons.
"""

import pandas as pd
import requests

from data.cache import cached
from data.config import (
    ISO2_TO_ISO3, ISO3_TO_ISO2, COUNTRY_NAMES,
    WELLBEING_COUNTRIES, RAW_DATA_DIR,
)
from data import swiid


def _fetch_world_bank_indicator(indicator_code: str, countries: list[str],
                                 start_year: int = 2015,
                                 end_year: int = 2023) -> pd.DataFrame:
    """Fetch a World Bank indicator via their REST API.

    Parameters
    ----------
    indicator_code : str
        e.g., "SP.DYN.LE00.IN" for life expectancy
    countries : list of str
        ISO-3 country codes
    """
    country_str = ";".join(countries)
    url = (
        f"https://api.worldbank.org/v2/country/{country_str}/indicator/"
        f"{indicator_code}?date={start_year}:{end_year}&format=json&per_page=1000"
    )

    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if len(data) < 2 or data[1] is None:
        return pd.DataFrame(columns=["country_iso3", "year", "value"])

    rows = []
    for entry in data[1]:
        if entry["value"] is not None:
            rows.append({
                "country_iso3": entry["countryiso3code"],
                "year": int(entry["date"]),
                "value": float(entry["value"]),
            })

    return pd.DataFrame(rows)


# World Bank indicator codes for Spirit Level analysis
_WB_INDICATORS = {
    "life_expectancy": "SP.DYN.LE00.IN",        # Life expectancy at birth
    "infant_mortality": "SP.DYN.IMRT.IN",        # Infant mortality per 1000
    "homicide_rate": "VC.IHR.PSRC.P5",           # Intentional homicides per 100k
    "gdp_per_capita_ppp": "NY.GDP.PCAP.PP.CD",   # GDP per capita, PPP
}


def get_spirit_level_data(countries=None, year: int = 2019):
    """Build a cross-country dataset for Spirit Level analysis.

    Merges inequality (SWIID Gini) with health and social outcome
    variables from the World Bank.

    Parameters
    ----------
    countries : list of str, optional
        ISO-2 codes. Defaults to a broad set of OECD countries.
    year : int
        Target year. Uses closest available year within +/-3 years.

    Returns
    -------
    pd.DataFrame with one row per country and columns for each indicator.
    """
    if countries is None:
        countries = [
            "US", "GB", "FR", "DE", "SE", "DK", "NO", "FI", "NL",
            "IT", "ES", "PT", "IE", "AT", "BE", "CH", "AU", "CA",
            "NZ", "JP", "CZ", "PL",
        ]

    iso3_codes = [ISO2_TO_ISO3[c] for c in countries if c in ISO2_TO_ISO3]

    def _load():
        # Get SWIID Gini (disposable income)
        gini_df = swiid.get_gini(countries, gini_type="disp",
                                  start_year=year - 3, end_year=year + 3)
        # Take the year closest to target for each country
        if not gini_df.empty:
            gini_df["year_diff"] = abs(gini_df["year"] - year)
            gini_df = (gini_df.sort_values("year_diff")
                       .groupby("country_code")
                       .first()
                       .reset_index())
            gini_df = gini_df[["country_code", "gini"]].rename(
                columns={"gini": "gini_disp"})
        else:
            gini_df = pd.DataFrame(columns=["country_code", "gini_disp"])

        # Get market Gini too
        gini_mkt = swiid.get_gini(countries, gini_type="mkt",
                                   start_year=year - 3, end_year=year + 3)
        if not gini_mkt.empty:
            gini_mkt["year_diff"] = abs(gini_mkt["year"] - year)
            gini_mkt = (gini_mkt.sort_values("year_diff")
                        .groupby("country_code")
                        .first()
                        .reset_index())
            gini_mkt = gini_mkt[["country_code", "gini"]].rename(
                columns={"gini": "gini_mkt"})
        else:
            gini_mkt = pd.DataFrame(columns=["country_code", "gini_mkt"])

        # Get World Bank indicators
        result = gini_df.copy()
        if not gini_mkt.empty:
            result = result.merge(gini_mkt, on="country_code", how="outer")

        for indicator_name, wb_code in _WB_INDICATORS.items():
            wb_df = _fetch_world_bank_indicator(
                wb_code, iso3_codes,
                start_year=year - 3, end_year=year + 3,
            )
            if not wb_df.empty:
                wb_df["year_diff"] = abs(wb_df["year"] - year)
                wb_df = (wb_df.sort_values("year_diff")
                         .groupby("country_iso3")
                         .first()
                         .reset_index())
                wb_df["country_code"] = wb_df["country_iso3"].map(ISO3_TO_ISO2)
                wb_df = wb_df[["country_code", "value"]].rename(
                    columns={"value": indicator_name})
                result = result.merge(wb_df, on="country_code", how="outer")

        # Add country names
        result["country_name"] = result["country_code"].map(COUNTRY_NAMES)
        result = result.dropna(subset=["country_code"])

        return result

    return cached(f"spirit_level_data_{year}", _load, max_age_days=30)


# ---------------------------------------------------------------------------
# Wellbeing analysis indicators (broader global coverage)
# ---------------------------------------------------------------------------
_WB_WELLBEING_INDICATORS = {
    # Health
    "life_expectancy": "SP.DYN.LE00.IN",
    "infant_mortality": "SP.DYN.IMRT.IN",
    "under5_mortality": "SH.DYN.MORT",
    "hospital_beds": "SH.MED.BEDS.ZS",
    "health_expenditure_pct_gdp": "SH.XPD.CHEX.GD.ZS",
    # Material living standards
    "gdp_per_capita_ppp": "NY.GDP.PCAP.PP.CD",
    "poverty_215": "SI.POV.DDAY",
    "electricity_access": "EG.ELC.ACCS.ZS",
    # Education
    "literacy_rate": "SE.ADT.LITR.ZS",
    "secondary_enrollment": "SE.SEC.ENRR",
    "tertiary_enrollment": "SE.TER.ENRR",
}


def get_wellbeing_data(countries=None, year: int = 2019):
    """Build a cross-country dataset for wellbeing analysis.

    Fetches health, education, material, and inequality indicators
    from the World Bank for a broad set of countries spanning all
    income tiers.

    Parameters
    ----------
    countries : list of str, optional
        ISO-2 codes. Defaults to WELLBEING_COUNTRIES.
    year : int
        Target year. Uses closest available year within +/-5 years.

    Returns
    -------
    pd.DataFrame with one row per country.
    """
    if countries is None:
        countries = WELLBEING_COUNTRIES

    iso3_codes = [ISO2_TO_ISO3[c] for c in countries if c in ISO2_TO_ISO3]

    def _load():
        # Get SWIID Gini (disposable income)
        gini_df = swiid.get_gini(countries, gini_type="disp",
                                  start_year=year - 5, end_year=year + 5)
        if not gini_df.empty:
            gini_df["year_diff"] = abs(gini_df["year"] - year)
            gini_df = (gini_df.sort_values("year_diff")
                       .groupby("country_code")
                       .first()
                       .reset_index())
            gini_df = gini_df[["country_code", "gini"]].rename(
                columns={"gini": "gini_disp"})
        else:
            gini_df = pd.DataFrame(columns=["country_code", "gini_disp"])

        result = gini_df.copy()

        for indicator_name, wb_code in _WB_WELLBEING_INDICATORS.items():
            wb_df = _fetch_world_bank_indicator(
                wb_code, iso3_codes,
                start_year=year - 5, end_year=year + 5,
            )
            if not wb_df.empty:
                wb_df["year_diff"] = abs(wb_df["year"] - year)
                wb_df = (wb_df.sort_values("year_diff")
                         .groupby("country_iso3")
                         .first()
                         .reset_index())
                wb_df["country_code"] = wb_df["country_iso3"].map(ISO3_TO_ISO2)
                wb_df = wb_df[["country_code", "value"]].rename(
                    columns={"value": indicator_name})
                result = result.merge(wb_df, on="country_code", how="outer")

        result["country_name"] = result["country_code"].map(COUNTRY_NAMES)
        result = result.dropna(subset=["country_code"])

        return result

    return cached(f"wellbeing_data_{year}", _load, max_age_days=30)


def get_happiness_scores(year: int = 2019):
    """Fetch Cantril Ladder (happiness) scores from Our World in Data API.

    Uses the OWID indicator API (indicator 1025227) which provides
    Cantril Ladder scores with entity metadata including ISO-3 codes.

    Parameters
    ----------
    year : int
        Target year. Falls back to closest available year within +/-3.

    Returns
    -------
    pd.DataFrame with columns: country_code, happiness_score
    """
    data_url = "https://api.ourworldindata.org/v1/indicators/1025227.data.json"
    meta_url = "https://api.ourworldindata.org/v1/indicators/1025227.metadata.json"

    def _load():
        try:
            data_resp = requests.get(data_url, timeout=60)
            data_resp.raise_for_status()
            meta_resp = requests.get(meta_url, timeout=60)
            meta_resp.raise_for_status()
        except Exception:
            return pd.DataFrame(columns=["country_code", "happiness_score"])

        data = data_resp.json()
        meta = meta_resp.json()

        # Build entity ID → ISO-3 code mapping
        entity_map = {}
        if "dimensions" in meta and "entities" in meta["dimensions"]:
            for ent in meta["dimensions"]["entities"].get("values", []):
                if ent.get("code"):
                    entity_map[ent["id"]] = ent["code"]

        # Build DataFrame from API arrays
        df = pd.DataFrame({
            "entity_id": data["entities"],
            "year": data["years"],
            "happiness_score": data["values"],
        })

        df["country_iso3"] = df["entity_id"].map(entity_map)
        df = df.dropna(subset=["country_iso3"])
        df["country_code"] = df["country_iso3"].map(ISO3_TO_ISO2)
        df = df.dropna(subset=["country_code"])

        # Filter to target year window
        df = df[(df["year"] >= year - 3) & (df["year"] <= year + 3)].copy()
        df["year_diff"] = abs(df["year"] - year)
        df = (df.sort_values("year_diff")
               .groupby("country_code")
               .first()
               .reset_index())

        return df[["country_code", "happiness_score"]]

    return cached(f"happiness_scores_{year}", _load, max_age_days=30)
