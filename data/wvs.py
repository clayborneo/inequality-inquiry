"""World Values Survey / European Values Study data loader.

Loads life satisfaction data from locally downloaded WVS/EVS files.
Data must be downloaded from https://www.worldvaluessurvey.org/
(requires free registration).

Download instructions:
    1. Register at https://www.worldvaluessurvey.org/WVSDocumentation.jsp
    2. Download the WVS Time-Series (1981-2022) in CSV format
    3. Place the CSV file at: raw_data/wvs_timeseries.csv

Key variable: A170 (life satisfaction, 1-10 scale)
"""

import pandas as pd
import numpy as np

from data.cache import cached
from data.config import RAW_DATA_DIR


_WVS_FILE = RAW_DATA_DIR / "wvs_timeseries.csv"

_DOWNLOAD_MSG = (
    "WVS data file not found at raw_data/wvs_timeseries.csv.\n"
    "To download:\n"
    "  1. Register at https://www.worldvaluessurvey.org/WVSDocumentation.jsp\n"
    "  2. Download the WVS Time-Series (1981-2022) in CSV format\n"
    "  3. Place the CSV file at: raw_data/wvs_timeseries.csv\n"
    "\n"
    "The file should contain at minimum: S002VS (wave), S003 (country code),\n"
    "S020 (year), A170 (life satisfaction 1-10), S017 (weight)."
)

# WVS uses ISO 3166-1 numeric country codes
WVS_NUMERIC_TO_ISO2 = {
    8: "AL",     12: "DZ",    32: "AR",    36: "AU",    50: "BD",
    51: "AM",    31: "AZ",    48: "BH",    112: "BY",   76: "BR",
    100: "BG",   124: "CA",   152: "CL",   156: "CN",   170: "CO",
    191: "HR",   196: "CY",   203: "CZ",   208: "DK",   218: "EC",
    818: "EG",   233: "EE",   231: "ET",   246: "FI",   250: "FR",
    268: "GE",   276: "DE",   288: "GH",   300: "GR",   320: "GT",
    344: "HK",   348: "HU",   356: "IN",   360: "ID",   364: "IR",
    368: "IQ",   376: "IL",   380: "IT",   392: "JP",   400: "JO",
    398: "KZ",   404: "KE",   410: "KR",   414: "KW",   417: "KG",
    422: "LB",   428: "LV",   434: "LY",   440: "LT",   458: "MY",
    466: "ML",   484: "MX",   498: "MD",   504: "MA",   528: "NL",
    554: "NZ",   566: "NG",   578: "NO",   586: "PK",   604: "PE",
    608: "PH",   616: "PL",   620: "PT",   630: "PR",   634: "QA",
    642: "RO",   643: "RU",   646: "RW",   682: "SA",   688: "RS",
    702: "SG",   703: "SK",   705: "SI",   710: "ZA",   724: "ES",
    752: "SE",   756: "CH",   158: "TW",   762: "TJ",   764: "TH",
    780: "TT",   788: "TN",   792: "TR",   804: "UA",   826: "GB",
    840: "US",   858: "UY",   860: "UZ",   704: "VN",   887: "YE",
    894: "ZM",   716: "ZW",
}


def load_wvs() -> pd.DataFrame:
    """Load WVS/EVS time-series data.

    Returns
    -------
    pd.DataFrame
        Columns: country_code (ISO-2), wave, year, life_satisfaction (1-10),
                 weight
    """
    if not _WVS_FILE.exists():
        raise FileNotFoundError(_DOWNLOAD_MSG)

    # Read with low_memory=False since WVS files have mixed types
    df = pd.read_csv(_WVS_FILE, low_memory=False)

    # Normalize column names (may vary between download formats)
    col_upper = {c: c.upper().strip() for c in df.columns}
    df = df.rename(columns=col_upper)

    # Identify required columns (try common variants)
    col_map = {}
    for target, candidates in {
        "wave": ["S002VS", "S002"],
        "country_num": ["S003"],
        "year": ["S020"],
        "satisfaction": ["A170"],
        "weight": ["S017", "S017B"],
    }.items():
        for c in candidates:
            if c in df.columns:
                col_map[target] = c
                break

    missing = {"wave", "country_num", "year", "satisfaction"} - set(col_map)
    if missing:
        raise ValueError(
            f"Could not find required WVS columns for: {missing}. "
            f"Available columns: {sorted(df.columns)[:30]}..."
        )

    result = pd.DataFrame()
    result["wave"] = pd.to_numeric(df[col_map["wave"]], errors="coerce")
    result["country_num"] = pd.to_numeric(df[col_map["country_num"]],
                                           errors="coerce")
    result["year"] = pd.to_numeric(df[col_map["year"]], errors="coerce")
    result["life_satisfaction"] = pd.to_numeric(df[col_map["satisfaction"]],
                                                 errors="coerce")

    if "weight" in col_map:
        result["weight"] = pd.to_numeric(df[col_map["weight"]],
                                          errors="coerce").fillna(1.0)
    else:
        result["weight"] = 1.0

    # Map numeric country codes to ISO-2
    result["country_code"] = (result["country_num"]
                               .astype("Int64")
                               .map(WVS_NUMERIC_TO_ISO2))

    # Filter to valid responses (satisfaction 1-10, positive weights)
    result = result.dropna(subset=["country_code", "life_satisfaction", "year"])
    result = result[
        (result["life_satisfaction"] >= 1)
        & (result["life_satisfaction"] <= 10)
        & (result["weight"] > 0)
    ].copy()

    result["wave"] = result["wave"].astype(int)
    result["year"] = result["year"].astype(int)

    return result[["country_code", "wave", "year", "life_satisfaction",
                    "weight"]].reset_index(drop=True)


def get_wvs_satisfaction_trend(min_waves: int = 3) -> pd.DataFrame:
    """Compute weighted mean life satisfaction by country-wave from WVS.

    Parameters
    ----------
    min_waves : int
        Minimum number of waves a country must appear in to be included.

    Returns
    -------
    pd.DataFrame
        Columns: country_code, wave, year_midpoint, mean_satisfaction,
                 se_satisfaction, n_respondents
    """
    df = load_wvs()

    results = []
    for (cc, wave), group in df.groupby(["country_code", "wave"]):
        w = group["weight"].values
        s = group["life_satisfaction"].values
        total_w = w.sum()
        n = len(group)

        if total_w == 0 or n < 50:
            continue

        mean_s = np.average(s, weights=w)
        # Weighted standard error
        var_s = np.average((s - mean_s) ** 2, weights=w)
        se_s = np.sqrt(var_s / n)

        results.append({
            "country_code": cc,
            "wave": int(wave),
            "year_midpoint": int(round(group["year"].median())),
            "mean_satisfaction": mean_s,
            "se_satisfaction": se_s,
            "n_respondents": n,
        })

    result = pd.DataFrame(results)
    if result.empty:
        return result

    # Filter to countries with enough waves
    wave_counts = result.groupby("country_code")["wave"].nunique()
    keep = wave_counts[wave_counts >= min_waves].index
    result = result[result["country_code"].isin(keep)].copy()

    return result.sort_values(["country_code", "wave"]).reset_index(drop=True)
