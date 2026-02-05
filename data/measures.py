"""Inequality measure computation from distributional data.

Compute Gini, Palma ratio, Theil index, and percentile ratios from raw
income/wealth share data or individual-level data.
"""

import numpy as np


def gini_from_shares(shares):
    """Compute Gini coefficient from ordered quantile shares.

    Parameters
    ----------
    shares : array-like
        Income/wealth shares for each quantile group (e.g., decile shares).
        Must be non-negative and should sum to approximately 1.

    Returns
    -------
    float
        Gini coefficient between 0 (perfect equality) and 1 (perfect inequality).
    """
    shares = np.asarray(shares, dtype=float)
    n = len(shares)
    cum_shares = np.cumsum(shares)
    # Area under Lorenz curve using trapezoidal rule
    # Each group has equal population weight 1/n
    lorenz_area = np.sum((np.concatenate([[0], cum_shares[:-1]]) + cum_shares)) / (2 * n)
    return 1 - 2 * lorenz_area


def gini_from_values(values, weights=None):
    """Compute Gini coefficient from individual income/wealth values.

    Parameters
    ----------
    values : array-like
        Individual income or wealth values.
    weights : array-like, optional
        Sampling weights.

    Returns
    -------
    float
        Gini coefficient.
    """
    values = np.asarray(values, dtype=float)

    if weights is not None:
        weights = np.asarray(weights, dtype=float)
        sorted_idx = np.argsort(values)
        values = values[sorted_idx]
        weights = weights[sorted_idx]
        cum_weights = np.cumsum(weights)
        cum_weighted_values = np.cumsum(values * weights)
        total_weight = cum_weights[-1]
        total_value = cum_weighted_values[-1]
        # Weighted Gini
        numerator = np.sum(cum_weights * values * weights) - total_value * total_weight / 2
        denominator = total_value * total_weight / 2
        return numerator / denominator if denominator > 0 else 0.0
    else:
        values = np.sort(values)
        n = len(values)
        if n == 0:
            return 0.0
        index = np.arange(1, n + 1)
        return (2 * np.sum(index * values) / (n * np.sum(values))) - (n + 1) / n


def palma_ratio(decile_shares):
    """Compute Palma ratio: top 10% share / bottom 40% share.

    Parameters
    ----------
    decile_shares : array-like
        Income shares for each decile (10 values), ordered from bottom to top.

    Returns
    -------
    float
        Palma ratio. Higher values indicate more inequality.
    """
    shares = np.asarray(decile_shares, dtype=float)
    if len(shares) != 10:
        raise ValueError(f"Expected 10 decile shares, got {len(shares)}")

    bottom_40 = np.sum(shares[:4])
    top_10 = shares[9]

    if bottom_40 == 0:
        return float("inf")
    return top_10 / bottom_40


def percentile_ratio(values_at_percentiles, p_high, p_low):
    """Compute a percentile ratio (e.g., P90/P10).

    Parameters
    ----------
    values_at_percentiles : dict
        Mapping from percentile (int) to income/wealth value.
    p_high, p_low : int
        Percentiles to compare.

    Returns
    -------
    float
    """
    high = values_at_percentiles[p_high]
    low = values_at_percentiles[p_low]

    if low == 0:
        return float("inf")
    return high / low


def theil_t(values, weights=None):
    """Compute Theil T index (GE(1)) -- more sensitive to top of distribution.

    Parameters
    ----------
    values : array-like
        Non-negative income/wealth values.
    weights : array-like, optional

    Returns
    -------
    float
        Theil T index. 0 = perfect equality.
    """
    values = np.asarray(values, dtype=float)
    values = values[values > 0]  # Exclude zeros

    if len(values) == 0:
        return 0.0

    if weights is not None:
        weights = np.asarray(weights, dtype=float)
        weights = weights[values > 0]
        mean_val = np.average(values, weights=weights)
        ratios = values / mean_val
        return np.average(ratios * np.log(ratios), weights=weights)
    else:
        mean_val = np.mean(values)
        ratios = values / mean_val
        return np.mean(ratios * np.log(ratios))


def theil_l(values, weights=None):
    """Compute Theil L index (GE(0), Mean Log Deviation) -- more sensitive to bottom.

    Parameters
    ----------
    values : array-like
        Positive income/wealth values.
    weights : array-like, optional

    Returns
    -------
    float
        Theil L index. 0 = perfect equality.
    """
    values = np.asarray(values, dtype=float)
    values = values[values > 0]

    if len(values) == 0:
        return 0.0

    if weights is not None:
        weights = np.asarray(weights, dtype=float)
        weights = weights[values > 0]
        mean_val = np.average(values, weights=weights)
        return np.average(np.log(mean_val / values), weights=weights)
    else:
        mean_val = np.mean(values)
        return np.mean(np.log(mean_val / values))


def theil_decomposition(values, groups, weights=None):
    """Decompose Theil T index into within-group and between-group components.

    Parameters
    ----------
    values : array-like
        Income/wealth values.
    groups : array-like
        Group labels (same length as values).
    weights : array-like, optional

    Returns
    -------
    dict with keys: total, within, between, within_share, between_share
    """
    values = np.asarray(values, dtype=float)
    groups = np.asarray(groups)

    total = theil_t(values, weights)

    if weights is None:
        weights_arr = np.ones(len(values))
    else:
        weights_arr = np.asarray(weights, dtype=float)

    overall_mean = np.average(values, weights=weights_arr)
    unique_groups = np.unique(groups)

    within = 0.0
    between = 0.0

    for g in unique_groups:
        mask = groups == g
        g_vals = values[mask]
        g_weights = weights_arr[mask]
        g_mean = np.average(g_vals, weights=g_weights)
        g_pop_share = g_weights.sum() / weights_arr.sum()
        g_income_share = (g_vals * g_weights).sum() / (values * weights_arr).sum()

        # Within-group contribution
        g_theil = theil_t(g_vals, g_weights)
        within += g_income_share * g_theil

        # Between-group contribution
        if overall_mean > 0:
            between += g_income_share * np.log(g_mean / overall_mean)

    return {
        "total": total,
        "within": within,
        "between": between,
        "within_share": within / total if total > 0 else 0,
        "between_share": between / total if total > 0 else 0,
    }
