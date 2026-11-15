"""B9.5 metrics. The held-out year is the unit of evidence: compute per year, then summarise."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def per_year(p):
    """p: rows with year, anom_pct (actual), pred. One row per year."""
    def one(g):
        e = g.pred - g.anom_pct
        rho = spearmanr(g.pred, g.anom_pct).statistic if g.pred.nunique() > 1 else np.nan
        return pd.Series({"mae": e.abs().mean(), "rmse": np.sqrt((e ** 2).mean()), "bias": e.mean(),
                          "spearman": rho, "state_actual": g.anom_pct.mean(), "state_pred": g.pred.mean(),
                          "state_err": g.pred.mean() - g.anom_pct.mean(), "n": len(g)})
    return p.groupby("year")[["pred", "anom_pct"]].apply(one)


def summary(py, py_m0=None):
    s = {"mae": py.mae.mean(), "rmse": py.rmse.mean(), "rmse_se": py.rmse.std(ddof=1) / np.sqrt(len(py)),
         "bias": py.bias.mean(), "spearman_within_year": py.spearman.mean(),
         "state_mean_abs_err": py.state_err.abs().mean(),
         "pooled_rmse": float(np.sqrt(np.average(py.rmse ** 2, weights=py.n))),  # county-weighted
         "n_years": len(py)}
    if py_m0 is not None:
        s["skill_vs_m0"] = 1 - py.rmse.mean() / py_m0.rmse.mean()
    worst = py.nsmallest(3, "state_actual")
    best = py.nlargest(3, "state_actual")
    s["sign_acc_worst3"] = float((np.sign(worst.state_pred) == np.sign(worst.state_actual)).mean())
    s["sign_acc_best3"] = float((np.sign(best.state_pred) == np.sign(best.state_actual)).mean())
    s["bias_worst3"] = float(worst.state_err.mean())
    return {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in s.items()}
