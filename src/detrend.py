"""Yield trends and anomalies (B8). Trends are only ever fit on years the caller allows.

Target = (yield - trend) / trend * 100, per county and crop.
"""
import numpy as np
import pandas as pd
from scipy.stats import theilslopes

MIN_YEARS = 12  # counties with fewer training years fall back to the pooled state trend + county offset


def fit_trends(y, fit_years, method="ols"):
    """y: yields for one crop (fips, year, yield_bu_ac). Returns {fips: (slope, intercept)}."""
    t = y[y.year.isin(fit_years)].dropna(subset=["yield_bu_ac"])
    pooled_slope = np.polyfit(t.year, t.yield_bu_ac, 1)[0]
    out = {}
    for fips, g in t.groupby("fips"):
        if len(g) >= MIN_YEARS:
            if method == "theilsen":
                slope, icpt = theilslopes(g.yield_bu_ac, g.year)[:2]
            else:
                slope, icpt = np.polyfit(g.year, g.yield_bu_ac, 1)
        else:
            slope = pooled_slope
            icpt = (g.yield_bu_ac - slope * g.year).mean()
        out[fips] = (slope, icpt)
    return out


def anomalies(y, trends):
    """Add trend_bu and anom_pct for counties that have a trend."""
    y = y[y.fips.isin(trends)].copy()
    coef = pd.DataFrame.from_dict(trends, orient="index", columns=["slope", "icpt"])
    y["trend_bu"] = y.year * coef.loc[y.fips, "slope"].to_numpy() + coef.loc[y.fips, "icpt"].to_numpy()
    y["anom_pct"] = (y.yield_bu_ac - y.trend_bu) / y.trend_bu * 100
    return y
