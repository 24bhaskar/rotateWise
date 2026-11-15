"""What-if scenarios: replay every season for a county with shifted temperature and scaled rain, clip features to
the range the model was trained on (plus a 5% margin), and predict with the final models.

Soil wetness (GWETROOT) and evapotranspiration are NOT re-simulated (a stated limitation). Because of that, every
feature depends on either the temperature shift or the rain change, never both, so a full grid can be assembled
from one rebuild per temperature step and one per rain step (`grid`), with the same result as `run` at each point.
"""
import json
import pickle

import numpy as np
import pandas as pd

from src.features import S2, build
from src.paths import MODELS

TEMP_STEPS = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
RAIN_STEPS = list(range(-25, 30, 5))
TEMP_FEATS = ["jul_tmax_mean", "heat_days_jul_aug", "tmin_aug_mean", "spring_frost_days", "gdd_season"]
RAIN_FEATS = ["precip_jun_aug", "precip_jul_aug", "water_balance_jja", "heavy_rain_days_mj"]
CROP_KEY = {"corn": "corn", "soybean": "soy"}
PAD = 0.05


def load_models():
    out = {}
    for c in ("corn", "soy"):
        with open(MODELS / f"{c}_final.pkl", "rb") as fh:
            out[c] = pickle.load(fh)["model"]
    return out


def load_ranges():
    return json.loads((MODELS / "feature_ranges.json").read_text())


def perturb(daily, d_temp=0.0, d_rain=0.0):
    d = daily.copy()
    d[["t2m_max", "t2m_min"]] += d_temp
    d["prectotcorr"] *= 1 + d_rain / 100
    return d


def clip(f, ranges):
    """Clip features to the training range +/- 5%; returns (clipped frame, number of clipped values)."""
    f = f.copy()
    n = 0
    for c in S2:
        lo, hi = ranges[c]["min"], ranges[c]["max"]
        pad = PAD * (hi - lo)
        n += int(((f[c] < lo - pad) | (f[c] > hi + pad)).sum())
        f[c] = f[c].clip(lo - pad, hi + pad)
    return f, n


def predict(models, f):
    f = f.assign(prev_anom=0.0)
    return {crop: np.asarray(models[key].predict(f), dtype=float) for crop, key in CROP_KEY.items()}


def run(daily, d_temp, d_rain, models, ranges):
    """Per-season predictions for one scenario (what the app's sliders show)."""
    f, n = clip(build(perturb(daily, d_temp, d_rain)), ranges)
    p = predict(models, f)
    return {"years": f.year.tolist(), "clipped_values": n, "n_years": len(f),
            **{crop: v.tolist() for crop, v in p.items()}}


def grid(daily, models, ranges, temps=TEMP_STEPS, rains=RAIN_STEPS):
    """Mean predicted anomaly for every (temperature, rain) step."""
    base = build(daily).set_index("year")
    by_t = {t: build(perturb(daily, t, 0)).set_index("year")[TEMP_FEATS] for t in temps}
    by_r = {r: build(perturb(daily, 0, r)).set_index("year")[RAIN_FEATS] for r in rains}
    rows = []
    for t in temps:
        for r in rains:
            f = base.copy()
            f[TEMP_FEATS] = by_t[t]
            f[RAIN_FEATS] = by_r[r]
            f, n = clip(f.reset_index(), ranges)
            p = predict(models, f)
            rows.append({"t": t, "r": r, "corn": round(float(p["corn"].mean()), 3),
                         "soybean": round(float(p["soybean"].mean()), 3), "clipped": n})
    return rows


def frame(rows):
    return pd.DataFrame(rows)
