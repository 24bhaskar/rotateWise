"""B9.1 exploratory analysis on development years only (2000-2019). Writes reports/eda.md + eda.json.

Test years are used only for feature *ranges* (weather), never for yields.
"""
import json

import numpy as np
import pandas as pd

from src.detrend import anomalies, fit_trends
from src.features import S2
from src.paths import FEATURES, REPORTS, YIELDS

DEV = list(range(2000, 2020))


def vif(X):
    X = (X - X.mean()) / X.std()
    out = {}
    for c in X:
        others = X.drop(columns=c)
        beta, *_ = np.linalg.lstsq(np.c_[np.ones(len(X)), others], X[c], rcond=None)
        r2 = 1 - ((X[c] - np.c_[np.ones(len(X)), others] @ beta) ** 2).sum() / ((X[c] - X[c].mean()) ** 2).sum()
        out[c] = round(float(1 / max(1 - r2, 1e-9)), 2)
    return out


def main():
    y = pd.read_parquet(YIELDS)
    y = y[y.year.isin(DEV)]  # dev outcomes only
    f = pd.read_parquet(FEATURES)
    res, lines = {}, ["# Exploratory analysis (development years 2000-2019 only)", ""]
    for crop in ("corn", "soy"):
        a = anomalies(y[y.crop == crop], fit_trends(y[y.crop == crop], DEV))
        state = a.groupby("year").anom_pct.mean()
        shared = state.loc[a.year].to_numpy()
        share = float(np.var(shared) / np.var(a.anom_pct))
        piv = a.pivot(index="fips", columns="year", values="anom_pct")
        ac = float(np.nanmean([piv[yr].corr(piv[yr - 1]) for yr in DEV[1:]]))
        lag = a.assign(prev=a.groupby("fips").anom_pct.shift(1)).dropna(subset=["prev"])
        m = a.merge(f, on=["fips", "year"])
        corr = m[S2].corrwith(m.anom_pct).round(3).to_dict()
        res[crop] = {"county_years": len(a), "missing_county_years": int(99 * len(DEV) - len(a)),
                     "share_variance_statewide_year": round(share, 3),
                     "mean_crosssection_corr_with_previous_year": round(ac, 3),
                     "pooled_lag1_corr": round(float(lag.anom_pct.corr(lag.prev)), 3),
                     "corr_anomaly_with_features": corr,
                     "worst_years": state.nsmallest(3).round(1).to_dict(),
                     "best_years": state.nlargest(3).round(1).to_dict()}
    fd, ft = f[f.year.isin(DEV)], f[f.year >= 2020]
    res["feature_corr"] = fd[S2].corr().round(2).to_dict()
    res["vif"] = vif(fd[S2])
    res["ranges"] = {c: {"dev_min": round(float(fd[c].min()), 2), "dev_max": round(float(fd[c].max()), 2),
                         "test_min": round(float(ft[c].min()), 2), "test_max": round(float(ft[c].max()), 2)}
                     for c in S2}
    res["power_cells"] = json.loads((REPORTS / "power_grid_cells.json").read_text())["approx_unique_merra2_cells"]
    (REPORTS / "eda.json").write_text(json.dumps(res, indent=1, default=str))

    c, s = res["corn"], res["soy"]
    high_vif = {k: v for k, v in res["vif"].items() if v > 5}
    outside = [k for k, r in res["ranges"].items() if r["test_min"] < r["dev_min"] or r["test_max"] > r["dev_max"]]
    lines += [
        f"**Findings.** {c['share_variance_statewide_year']:.0%} of corn and {s['share_variance_statewide_year']:.0%} "
        "of soybean anomaly variance is shared by all counties in the same year, so the year is the real unit "
        f"of evidence (20 dev years; POWER has only about {res['power_cells']} distinct grid cells for 99 counties). "
        f"Persistence is weak: the pooled lag-1 correlation of anomalies is {c['pooled_lag1_corr']:.2f} (corn) "
        f"and {s['pooled_lag1_corr']:.2f} (soy). The worst corn years were "
        f"{', '.join(f'{k} ({v:+.0f}%)' for k, v in c['worst_years'].items())}. "
        "The features most correlated with corn anomalies are "
        + ", ".join(f"{k} ({v:+.2f})" for k, v in sorted(c["corr_anomaly_with_features"].items(), key=lambda kv: -abs(kv[1]))[:4])
        + f". Features with variance inflation above 5: {high_vif or 'none'}; heat, Tmax and degree days overlap, "
        "which favours regularised models. Test-period weather outside the dev range: "
        f"{outside or 'none'}. SMAP vs POWER comparison: not run (no Earthdata credentials; see human_todo.md).",
        "", "Full numbers: `reports/eda.json`."]
    (REPORTS / "eda.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
