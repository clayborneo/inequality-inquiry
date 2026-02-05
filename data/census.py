"""US Census Bureau CPS historical income inequality data loader.

Downloads historical income tables from the Census Bureau website.
These are static Excel files covering 1967-present.
"""

import io

import pandas as pd
import requests

from data.cache import cached
from data.config import RAW_DATA_DIR, DEFAULT_START_YEAR, DEFAULT_END_YEAR

# Census historical income inequality tables
_GINI_TABLE_URL = (
    "https://www2.census.gov/programs-surveys/cps/tables/time-series/"
    "historical-income-inequality/h4.xlsx"
)

_INCOME_BY_QUINTILE_URL = (
    "https://www2.census.gov/programs-surveys/cps/tables/time-series/"
    "historical-income-households/h3ar.xlsx"
)


def _download_excel(url: str, filename: str) -> pd.DataFrame:
    """Download an Excel file from Census and return raw DataFrame."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    local_path = RAW_DATA_DIR / filename

    if not local_path.exists():
        print(f"Downloading Census table: {filename}...")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        local_path.write_bytes(resp.content)

    return pd.read_excel(local_path, engine="openpyxl")


def get_us_gini_timeseries(start_year=None, end_year=None):
    """US Gini index of household income from CPS ASEC, 1967-present.

    Returns
    -------
    pd.DataFrame with columns: year, gini
    """
    start_year = start_year or 1967
    end_year = end_year or DEFAULT_END_YEAR

    def _load():
        df = _download_excel(_GINI_TABLE_URL, "census_h4_gini.xlsx")

        # Census Excel tables have complex headers; extract year and Gini columns
        # The structure varies by year but typically has Year in column 0 and
        # Gini in one of the other columns
        # Try to find the data programmatically
        result_rows = []
        for _, row in df.iterrows():
            vals = row.values
            # Look for rows where first value looks like a year
            try:
                year_val = int(float(str(vals[0]).strip().split()[0]))
                if 1900 < year_val < 2100:
                    # Look for a Gini-like value (between 0 and 1, or 0 and 100)
                    for v in vals[1:]:
                        try:
                            gini_val = float(str(v).strip())
                            if 0 < gini_val < 1:
                                result_rows.append({"year": year_val, "gini": gini_val})
                                break
                            elif 0 < gini_val < 100:
                                result_rows.append({"year": year_val, "gini": gini_val / 100})
                                break
                        except (ValueError, TypeError):
                            continue
            except (ValueError, TypeError):
                continue

        return pd.DataFrame(result_rows)

    df = cached("census_us_gini_ts", _load, max_age_days=30)
    df = df[(df["year"] >= start_year) & (df["year"] <= end_year)]
    return df.sort_values("year").reset_index(drop=True)


def get_us_income_by_quintile(start_year=None, end_year=None):
    """Mean household income by quintile, US, 1967-present.

    Returns
    -------
    pd.DataFrame with columns: year, q1, q2, q3, q4, q5, top5
    (q1 = bottom 20%, q5 = top 20%, top5 = top 5%)
    """
    start_year = start_year or 1967
    end_year = end_year or DEFAULT_END_YEAR

    def _load():
        df = _download_excel(_INCOME_BY_QUINTILE_URL, "census_h3ar_quintiles.xlsx")

        # Parse the complex Census Excel structure
        result_rows = []
        for _, row in df.iterrows():
            vals = row.values
            try:
                year_val = int(float(str(vals[0]).strip().split()[0]))
                if 1900 < year_val < 2100:
                    # Extract numeric values from remaining columns
                    nums = []
                    for v in vals[1:]:
                        try:
                            nums.append(float(str(v).replace(",", "").strip()))
                        except (ValueError, TypeError):
                            continue
                    if len(nums) >= 5:
                        entry = {"year": year_val}
                        entry["q1"] = nums[0]
                        entry["q2"] = nums[1]
                        entry["q3"] = nums[2]
                        entry["q4"] = nums[3]
                        entry["q5"] = nums[4]
                        if len(nums) >= 6:
                            entry["top5"] = nums[5]
                        result_rows.append(entry)
            except (ValueError, TypeError):
                continue

        return pd.DataFrame(result_rows)

    df = cached("census_us_income_quintiles", _load, max_age_days=30)
    df = df[(df["year"] >= start_year) & (df["year"] <= end_year)]
    return df.sort_values("year").reset_index(drop=True)
