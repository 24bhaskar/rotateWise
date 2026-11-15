"""B9.6 uncertainty: year-level bootstrap of metrics, and split-conformal prediction intervals."""
import numpy as np

N_BOOT = 2000


def boot_years(py_model, py_m0, py_ref=None, n=N_BOOT, seed=42, level=0.90):
    """Resample years with replacement. Intervals on MAE, RMSE, skill vs M0, and paired RMSE diff vs ref."""
    rng = np.random.default_rng(seed)
    years = py_model.index.to_numpy()
    lo, hi = (1 - level) / 2, 1 - (1 - level) / 2
    draws = {"mae": [], "rmse": [], "skill": [], "diff_vs_ref": []}
    for _ in range(n):
        s = rng.choice(years, size=len(years), replace=True)
        m, z = py_model.loc[s], py_m0.loc[s]
        draws["mae"].append(m.mae.mean())
        draws["rmse"].append(m.rmse.mean())
        draws["skill"].append(1 - m.rmse.mean() / z.rmse.mean())
        if py_ref is not None:
            draws["diff_vs_ref"].append(m.rmse.mean() - py_ref.loc[s].rmse.mean())
    return {k: [round(float(np.quantile(v, lo)), 3), round(float(np.quantile(v, hi)), 3)]
            for k, v in draws.items() if v}


def conformal_halfwidth(residuals, level=0.90):
    """Split-conformal: the level-quantile of absolute out-of-fold residuals (finite-sample corrected)."""
    r = np.sort(np.abs(np.asarray(residuals)))
    k = int(np.ceil((len(r) + 1) * level)) - 1
    return float(r[min(k, len(r) - 1)])


def coverage(actual, pred, half):
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(pred)) <= half))
