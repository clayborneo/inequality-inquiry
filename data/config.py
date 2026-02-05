"""Centralized configuration: country codes, WID variables, colors, paths."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / ".cache"
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
FIGURES_DIR = PROJECT_ROOT / "figures"

# ---------------------------------------------------------------------------
# Country lists
# ---------------------------------------------------------------------------
FOCUS_COUNTRIES = ["US", "GB", "FR", "DE", "SE", "DK", "NO"]
EXTENDED_COUNTRIES = FOCUS_COUNTRIES + [
    "IT", "ES", "NL", "FI", "PL", "CZ", "IE",
]

WELLBEING_COUNTRIES = FOCUS_COUNTRIES + [
    "JP", "AU", "CL",                            # Additional high-income
    "CN", "BR", "MX", "ZA", "TR", "RU",          # Upper-middle
    "IN", "ID", "PH", "EG", "NG",                # Lower-middle
    "ET", "BD",                                   # Low-income
]

# Display names
COUNTRY_NAMES = {
    "US": "United States",
    "GB": "United Kingdom",
    "FR": "France",
    "DE": "Germany",
    "SE": "Sweden",
    "DK": "Denmark",
    "NO": "Norway",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "FI": "Finland",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "IE": "Ireland",
    "AT": "Austria",
    "BE": "Belgium",
    "PT": "Portugal",
    "CH": "Switzerland",
    "JP": "Japan",
    "CA": "Canada",
    "AU": "Australia",
    "NZ": "New Zealand",
    # Wellbeing analysis additions
    "CL": "Chile",
    "CN": "China",
    "BR": "Brazil",
    "MX": "Mexico",
    "ZA": "South Africa",
    "TR": "Turkey",
    "RU": "Russia",
    "IN": "India",
    "ID": "Indonesia",
    "PH": "Philippines",
    "EG": "Egypt",
    "NG": "Nigeria",
    "ET": "Ethiopia",
    "BD": "Bangladesh",
}

# ISO-2 to ISO-3 mapping (for OECD queries)
ISO2_TO_ISO3 = {
    "US": "USA", "GB": "GBR", "FR": "FRA", "DE": "DEU",
    "SE": "SWE", "DK": "DNK", "NO": "NOR", "IT": "ITA",
    "ES": "ESP", "NL": "NLD", "FI": "FIN", "PL": "POL",
    "CZ": "CZE", "IE": "IRL", "AT": "AUT", "BE": "BEL",
    "PT": "PRT", "CH": "CHE", "JP": "JPN", "CA": "CAN",
    "AU": "AUS", "NZ": "NZL",
    # Wellbeing analysis additions
    "CL": "CHL", "CN": "CHN", "BR": "BRA", "MX": "MEX",
    "ZA": "ZAF", "TR": "TUR", "RU": "RUS", "IN": "IND",
    "ID": "IDN", "PH": "PHL", "EG": "EGY", "NG": "NGA",
    "ET": "ETH", "BD": "BGD",
}

ISO3_TO_ISO2 = {v: k for k, v in ISO2_TO_ISO3.items()}

# Eurostat uses ISO-2 but "UK" for GB
ISO2_TO_EUROSTAT = {k: k for k in COUNTRY_NAMES}
ISO2_TO_EUROSTAT["GB"] = "UK"

# ---------------------------------------------------------------------------
# Consistent color palette (one color per country)
# ---------------------------------------------------------------------------
COUNTRY_COLORS = {
    "US": "#1f77b4",  # blue
    "GB": "#ff7f0e",  # orange
    "FR": "#2ca02c",  # green
    "DE": "#d62728",  # red
    "SE": "#9467bd",  # purple
    "DK": "#8c564b",  # brown
    "NO": "#e377c2",  # pink
    "IT": "#7f7f7f",  # gray
    "ES": "#bcbd22",  # olive
    "NL": "#17becf",  # cyan
    "FI": "#aec7e8",  # light blue
    "PL": "#ffbb78",  # light orange
    "CZ": "#98df8a",  # light green
    "IE": "#ff9896",  # light red
    # High-income (blues)
    "JP": "#4292c6",
    "AU": "#6baed6",
    "CL": "#9ecae1",
    # Upper-middle income (greens)
    "CN": "#238b45",
    "BR": "#41ab5d",
    "MX": "#74c476",
    "ZA": "#a1d99b",
    "TR": "#c7e9c0",
    "RU": "#006d2c",
    # Lower-middle income (oranges)
    "IN": "#e6550d",
    "ID": "#fd8d3c",
    "PH": "#fdae6b",
    "EG": "#fdd0a2",
    "NG": "#d94701",
    # Low-income (reds)
    "ET": "#cb181d",
    "BD": "#fb6a4a",
}

# ---------------------------------------------------------------------------
# WID variable codes (DINA methodology)
# ---------------------------------------------------------------------------
WID_VARIABLES = {
    # Income shares
    "pretax_income_share": "sptinc",    # pre-tax national income share
    "posttax_income_share": "sdiinc",   # post-tax disposable income share
    "factor_income_share": "sfainc",    # pre-tax factor income share

    # Average income
    "pretax_income_avg": "aptinc",      # pre-tax national income average
    "posttax_income_avg": "adiinc",     # post-tax disposable income average
    "factor_income_avg": "afainc",      # pre-tax factor income average

    # Wealth
    "wealth_share": "shweal",           # net personal wealth share
    "wealth_avg": "ahweal",            # net personal wealth average
}

# WID percentile groups
WID_PERCENTILES = {
    "bottom_50": "p0p50",
    "middle_40": "p50p90",
    "top_10": "p90p100",
    "top_1": "p99p100",
    "top_0.1": "p99.9p100",
}

# ---------------------------------------------------------------------------
# SWIID column mappings
# ---------------------------------------------------------------------------
SWIID_URL = "https://dataverse.harvard.edu/api/access/datafile/:persistentId?persistentId=doi:10.7910/DVN/LM4OWF/GASZEZ"

# ---------------------------------------------------------------------------
# Default time range
# ---------------------------------------------------------------------------
DEFAULT_START_YEAR = 1980
DEFAULT_END_YEAR = 2023
