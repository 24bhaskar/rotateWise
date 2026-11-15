"""B9.4 cross-validation on development years. Detrending is refit inside every fold.

Only `load_dev` is used by model selection; it can never return a test-period yield.
"""
import copy

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from src.detrend import anomalies, fit_trends
from src.paths import COUNTIES_CSV, FEATURES, YIELDS

DEV_YEARS = list(range(2000, 2020))
TEST_START = 2020


def load_dev(crop):
    """Dev-period yields and features for one crop. Test years are filtered out on load."""
    y = pd.read_parquet(YIELDS, filters=[("year", "<", TEST_START), ("crop", "==", crop)])
    assert y.year.max() < TEST_START
    f = pd.read_parquet(FEATURES, filters=[("year", "<", TEST_START)])
    return y.dropna(subset=["yield_bu_ac"]), f


def fold_frame(y, f, trend_years, method="ols"):
    """Anomalies from a trend fit only on `trend_years`, joined to features, with persistence input."""
    a = anomalies(y, fit_trends(y, trend_years, method))
    prev = a[["fips", "year", "anom_pct"]].assign(year=lambda d: d.year + 1).rename(columns={"anom_pct": "prev_anom"})
    return a.merge(prev, on=["fips", "year"], how="left").merge(f, on=["fips", "year"])


def loyo(model, y, f, years=DEV_YEARS, method="ols", feature_fn=None):
    """Leave-one-year-out: all counties of the held-out year stay out together, trend refit without it."""
    out = []
    for h in years:
        train_years = [t for t in years if t != h]
        d = fold_frame(y, f, train_years, method)
        if feature_fn is not None:
            d = feature_fn(d, train_years)
        tr, te = d[d.year != h], d[d.year == h]
        m = copy.deepcopy(model).fit(tr)
        out.append(te[["fips", "year", "yield_bu_ac", "trend_bu", "anom_pct"]].assign(
            pred=m.predict(te), fit_rmse=float(np.sqrt(np.mean((m.predict(tr) - tr.anom_pct) ** 2)))))
    return pd.concat(out, ignore_index=True)


def expanding(model, y, f, start=2008, end=2019):
    """Train on all dev years before Y (trend too), predict Y."""
    out = []
    for Y in range(start, end + 1):
        prior = list(range(2000, Y))
        d = fold_frame(y[y.year <= Y], f, prior)
        tr, te = d[d.year < Y], d[d.year == Y]
        m = copy.deepcopy(model).fit(tr)
        out.append(te[["fips", "year", "anom_pct"]].assign(pred=m.predict(te)))
    return pd.concat(out, ignore_index=True)


def regions(k=5, seed=42):
    c = pd.read_csv(COUNTIES_CSV, dtype={"fips": str})
    c["region"] = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(c[["lat", "lon"]])
    return c.set_index("fips").region


def spatial(model, y, f, years=DEV_YEARS):
    """Hold out a block of counties AND the year: train on other regions in other years."""
    reg = regions()
    out = []
    for h in years:
        d = fold_frame(y, f, [t for t in years if t != h])
        d["region"] = d.fips.map(reg)
        for g in sorted(d.region.unique()):
            tr = d[(d.year != h) & (d.region != g)]
            te = d[(d.year == h) & (d.region == g)]
            m = copy.deepcopy(model).fit(tr)
            out.append(te[["fips", "year", "anom_pct"]].assign(pred=m.predict(te), region=g))
    return pd.concat(out, ignore_index=True)


def shuffle_weather(f, seed):
    """Placebo: give every county the weather of a different (randomly permuted) year."""
    rng = np.random.default_rng(seed)
    yrs = np.array(DEV_YEARS)
    perm = dict(zip(yrs, rng.permutation(yrs)))
    while any(k == v for k, v in perm.items()):
        perm = dict(zip(yrs, rng.permutation(yrs)))
    g = f[f.year.isin(DEV_YEARS)].copy()
    g["year"] = g.year.map({v: k for k, v in perm.items()})
    return g
