"""General Social Survey (GSS) happiness data loader.

Loads the GSS HAPPY variable from a locally downloaded CSV file.
GSS data must be downloaded manually from https://gss.norc.org/

Download instructions:
    1. Go to https://gssdataexplorer.norc.org/
    2. Search for variables: YEAR, HAPPY, WTSSALL
    3. Add them to your extract and download as CSV
    4. Place the file at: raw_data/gss_happiness.csv

Alternatively, download the full cumulative data file from
https://gss.norc.org/ under "Quick Downloads" and extract
the relevant columns.

HAPPY coding:
    1 = Very happy
    2 = Pretty happy
    3 = Not too happy
    0, 8, 9 = Missing (IAP, DK, NA)
"""

import pandas as pd
import numpy as np

from data.cache import cached
from data.config import RAW_DATA_DIR


_GSS_FILE = RAW_DATA_DIR / "gss_happiness.csv"

_DOWNLOAD_MSG = (
    "GSS data file not found at raw_data/gss_happiness.csv.\n"
    "To download:\n"
    "  1. Go to https://gssdataexplorer.norc.org/\n"
    "  2. Search for variables: YEAR, HAPPY, WTSSALL\n"
    "  3. Add them to your extract and download as CSV\n"
    "  4. Place the file at: raw_data/gss_happiness.csv\n"
    "\n"
    "Or download the full cumulative file from https://gss.norc.org/"
)


def load_gss() -> pd.DataFrame:
    """Load and parse the GSS happiness extract.

    Returns
    -------
    pd.DataFrame
        Columns: year, happy (1/2/3), weight
    """
    if not _GSS_FILE.exists():
        raise FileNotFoundError(_DOWNLOAD_MSG)

    df = pd.read_csv(_GSS_FILE)

    # Normalize column names (GSS exports may vary in case)
    df.columns = df.columns.str.upper().str.strip()

    if "YEAR" not in df.columns or "HAPPY" not in df.columns:
        raise ValueError(
            f"Expected columns YEAR and HAPPY in {_GSS_FILE}. "
            f"Found: {list(df.columns)}"
        )

    # Use WTSSALL if available, otherwise WTSSCOMP, otherwise uniform
    weight_col = None
    for candidate in ["WTSSALL", "WTSSCOMP", "WEIGHT"]:
        if candidate in df.columns:
            weight_col = candidate
            break

    result = pd.DataFrame({
        "year": df["YEAR"].astype(int),
        "happy": df["HAPPY"],
    })

    if weight_col is not None:
        result["weight"] = pd.to_numeric(df[weight_col], errors="coerce")
    else:
        result["weight"] = 1.0

    # Handle both numeric (1/2/3) and string label formats
    _LABEL_TO_CODE = {
        "very happy": 1, "pretty happy": 2, "not too happy": 3,
        # Common variations
        "very_happy": 1, "pretty_happy": 2, "not_too_happy": 3,
    }
    happy_raw = result["happy"]
    happy_numeric = pd.to_numeric(happy_raw, errors="coerce")
    # If most values converted to numeric, use those; otherwise map strings
    if happy_numeric.notna().sum() > len(happy_raw) * 0.5:
        result["happy"] = happy_numeric
    else:
        result["happy"] = (happy_raw.astype(str).str.strip().str.lower()
                           .map(_LABEL_TO_CODE))

    result = result[result["happy"].isin([1, 2, 3])].copy()
    result["happy"] = result["happy"].astype(int)

    # Fill missing weights with 1.0 (GSS changed weight variable names
    # for 2021+ surveys; uniform weights are acceptable for trend analysis)
    result["weight"] = result["weight"].fillna(1.0)
    result = result[result["weight"] > 0]

    return result.reset_index(drop=True)


def get_gss_happiness_trend() -> pd.DataFrame:
    """Compute weighted annual happiness distribution from GSS.

    Returns
    -------
    pd.DataFrame
        Columns: year, pct_very_happy, pct_pretty_happy, pct_not_happy,
                 mean_happy (higher = happier, scale 1-3), n_respondents
    """
    df = load_gss()

    results = []
    for year, group in df.groupby("year"):
        w = group["weight"].values
        h = group["happy"].values
        total_w = w.sum()

        if total_w == 0:
            continue

        # Invert scale so higher = happier: 1 (not happy) -> 3 (very happy)
        h_inv = 4 - h

        results.append({
            "year": int(year),
            "pct_very_happy": np.sum(w * (h == 1)) / total_w * 100,
            "pct_pretty_happy": np.sum(w * (h == 2)) / total_w * 100,
            "pct_not_happy": np.sum(w * (h == 3)) / total_w * 100,
            "mean_happy": np.sum(w * h_inv) / total_w,
            "n_respondents": len(group),
        })

    return pd.DataFrame(results).sort_values("year").reset_index(drop=True)
