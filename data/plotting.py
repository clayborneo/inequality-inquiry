"""Shared plotting utilities for consistent, publication-quality figures."""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from data.config import COUNTRY_COLORS, COUNTRY_NAMES, FIGURES_DIR


def set_style():
    """Apply project-wide matplotlib/seaborn style settings."""
    sns.set_theme(style="whitegrid", font_scale=1.1)
    plt.rcParams.update({
        "figure.figsize": (10, 6),
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "font.family": "sans-serif",
    })


def country_color(code: str) -> str:
    """Return the consistent color for a country code."""
    return COUNTRY_COLORS.get(code, "#333333")


def country_name(code: str) -> str:
    """Return the display name for a country code."""
    return COUNTRY_NAMES.get(code, code)


def annotate_countries(ax, x_vals, y_vals, labels, fontsize=9, **kwargs):
    """Add country-name annotations to scatter plots.

    Attempts to use adjustText for collision avoidance if available,
    falls back to simple annotation otherwise.
    """
    try:
        from adjustText import adjust_text
        texts = []
        for xi, yi, label in zip(x_vals, y_vals, labels):
            name = country_name(label) if len(label) <= 3 else label
            texts.append(ax.text(xi, yi, name, fontsize=fontsize, **kwargs))
        adjust_text(texts, ax=ax)
    except ImportError:
        for xi, yi, label in zip(x_vals, y_vals, labels):
            name = country_name(label) if len(label) <= 3 else label
            ax.annotate(name, (xi, yi), fontsize=fontsize,
                        textcoords="offset points", xytext=(5, 5), **kwargs)


def lorenz_curve(ax, shares, label=None, color=None, **kwargs):
    """Plot a Lorenz curve from income/wealth shares by quantile.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    shares : array-like
        Income/wealth shares for each quantile (e.g., decile shares summing to 1).
    label : str, optional
    color : str, optional
    """
    shares = np.asarray(shares)
    cum_pop = np.concatenate([[0], np.cumsum(np.ones(len(shares)) / len(shares))])
    cum_share = np.concatenate([[0], np.cumsum(shares)])

    ax.plot(cum_pop, cum_share, label=label, color=color, linewidth=2, **kwargs)
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xlabel("Cumulative share of population")
    ax.set_ylabel("Cumulative share of income")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")


def slope_chart(ax, left_values, right_values, labels, left_label="Market",
                right_label="Disposable", colors=None):
    """Draw a slope chart connecting paired values (e.g., market → disposable Gini).

    Parameters
    ----------
    ax : matplotlib.axes.Axes
    left_values, right_values : array-like
    labels : list of str (country codes)
    left_label, right_label : str
    colors : list of str, optional
    """
    if colors is None:
        colors = [country_color(c) for c in labels]

    for lv, rv, label, color in zip(left_values, right_values, labels, colors):
        ax.plot([0, 1], [lv, rv], color=color, linewidth=2, alpha=0.8)
        ax.text(-0.05, lv, country_name(label), ha="right", va="center",
                fontsize=9, color=color)
        ax.text(1.05, rv, f"{rv:.3f}", ha="left", va="center",
                fontsize=9, color=color)

    ax.set_xlim(-0.3, 1.3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([left_label, right_label])
    ax.set_ylabel("Gini coefficient")
    ax.grid(axis="x", alpha=0)


def save_figure(fig, name: str, formats=("png",)):
    """Save figure to the figures/ directory."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for fmt in formats:
        path = FIGURES_DIR / f"{name}.{fmt}"
        fig.savefig(path, bbox_inches="tight")
