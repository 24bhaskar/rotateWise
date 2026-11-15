"""`make final`: ONE evaluation of the frozen spec on the locked test years, then the final refit for the app.

Refuses to run a second time unless FORCE=1 (and then logs the rerun). Steps (spec B9.9):
1. read models/final_spec.json (frozen by `make select`)
2. train on dev years 2000-2019; for each test year Y, the yield trend is fit on years < Y only (expanding);
   a fixed 2000-2019 trend is reported as a sensitivity check
3. write models/final_test_run.json, models/metrics.json, models/test_by_year.parquet
4. only then refit on all years (2000-latest) and write the app artefacts (model, SHAP, stress profile,
   conformal interval, feature ranges)
"""
import datetime as dt
import json
import os
import pickle
import subprocess

import numpy as np
import pandas as pd

from src.cv import DEV_YEARS, TEST_START
from src.detrend import anomalies, fit_trends
from src.features import FEATURE_MONTHS, S2
from src.metrics import per_year, summary
from src.models import Average, StateLocalChain, candidates
from src.paths import FEATURES, MODELS, YIELDS
from src.stress_profile import contributions, month_weights
from src.uncertainty import boot_years, conformal_halfwidth, coverage

LOCK = MODELS / "final_test.lock"


def build(crop, spec):
    c = candidates(crop)
    mid = spec["model_id"]
    if mid == "E1":
        return Average(c[spec["lin"]], c[spec["tree"]], "E1")
    if mid == "E2":
        return Average(c[spec["gam"]], c[spec["tree"]], "E2")
    if mid == "C1":
        return StateLocalChain(c[spec["lin"]].feats)
    return c[mid]


def frame(y, f, trend_years, eval_years):
    a = anomalies(y, fit_trends(y, trend_years))
    prev = a[["fips", "year", "anom_pct"]].assign(year=lambda d: d.year + 1).rename(columns={"anom_pct": "prev_anom"})
    a = a.merge(prev, on=["fips", "year"], how="left").merge(f, on=["fips", "year"])
    return a[a.year.isin(eval_years)]


def git_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "no commit yet"


def main():
    if LOCK.exists() and os.environ.get("FORCE") != "1":
        raise SystemExit(f"final test already run ({LOCK.read_text().strip()}); set FORCE=1 to rerun and it will be logged")
    rerun = LOCK.exists()
    spec_all = json.loads((MODELS / "final_spec.json").read_text())
    dev_res = json.loads((MODELS / "dev_results.json").read_text())
    yall = pd.read_parquet(YIELDS).dropna(subset=["yield_bu_ac"])
    f = pd.read_parquet(FEATURES)
    test_years = sorted(y for y in yall.year.unique() if y >= TEST_START and y in set(f.year))
    run = {"timestamp": dt.datetime.now().isoformat(timespec="seconds"), "git_hash": git_hash(),
           "rerun": rerun, "test_years": test_years, "crops": {}}
    by_year_all, preds_all, metrics = [], [], {}

    for crop, key in (("corn", "corn"), ("soy", "soy")):
        spec = spec_all[crop]
        y = yall[yall.crop == crop]
        train = frame(y[y.year < TEST_START], f, DEV_YEARS, DEV_YEARS)
        cands = candidates(crop)
        models = {"M0": cands["M0"], "M1": cands["M1"], "M2": cands["M2"], "selected": build(crop, spec)}
        fitted = {k: m.fit(train) for k, m in models.items()}
        out = {}
        for trend_kind in ("expanding", "fixed_2000_2019"):
            rows = []
            for Y in test_years:
                ty = list(range(2000, Y)) if trend_kind == "expanding" else DEV_YEARS
                te = frame(y[y.year <= Y], f, ty, [Y])
                rows.append(te.assign(**{f"pred_{k}": m.predict(te) for k, m in fitted.items()}))
            p = pd.concat(rows)
            py = {k: per_year(p.assign(pred=p[f"pred_{k}"])) for k in models}
            res = {k: summary(py[k], py["M0"]) for k in models}
            for k in models:
                res[k]["boot"] = boot_years(py[k], py["M0"], py["M2"])
            half = dev_res[crop]["checks"]["intervals"]["conformal_90_halfwidth_pct"]
            res["selected"]["conformal_90_test_coverage"] = round(coverage(p.anom_pct, p.pred_selected, half), 3)
            res["year_2025_only"] = {k: py[k].loc[2025].round(3).to_dict() for k in models} if 2025 in py["M0"].index else None
            res["year_2020"] = {k: py[k].loc[2020].round(3).to_dict() for k in models}
            out[trend_kind] = res
            if trend_kind == "expanding":
                by_year_all.append(pd.concat([v.assign(model=k, crop=crop) for k, v in py.items()]).reset_index())
                preds_all.append(p.assign(crop=crop)[["fips", "year", "crop", "yield_bu_ac", "trend_bu", "anom_pct"]
                                                      + [f"pred_{k}" for k in models]])
        run["crops"][crop] = {"selected": spec["model_id"], "results": out}
        metrics[crop] = {"selected_model": spec["model_id"], "selected_name": spec["model"],
                         "test_expanding_trend": out["expanding"], "test_fixed_trend": out["fixed_2000_2019"],
                         "dev_cv": {k: dev_res[crop]["results"][k] for k in ("M0", "M1", "M2", spec["model_id"])},
                         "train_vs_cv_gap": dev_res[crop]["checks"]["train_vs_cv_gap"],
                         "placebo": dev_res[crop]["checks"]["placebo"],
                         "spatial_block": dev_res[crop]["checks"]["spatial_block"],
                         "expanding_window_dev": dev_res[crop]["checks"]["expanding_window_2008_2019"],
                         "ablations": dev_res[crop]["checks"]["ablations"],
                         "intervals": dev_res[crop]["checks"]["intervals"],
                         "selection_notes": dev_res[crop]["selection_notes"]}

    (MODELS / "final_test_run.json").write_text(json.dumps(run, indent=1, default=str))
    (MODELS / "metrics.json").write_text(json.dumps(metrics, indent=1, default=str))
    pd.concat(by_year_all).to_parquet(MODELS / "test_by_year.parquet", index=False)
    pd.concat(preds_all).to_parquet(MODELS / "test_predictions.parquet", index=False)
    LOCK.write_text(f"run at {run['timestamp']}{' (FORCED RERUN)' if rerun else ''}\n")
    if rerun:
        with open(MODELS / "final_test_reruns.log", "a") as fh:
            fh.write(f"{run['timestamp']} forced rerun\n")
    print("test evaluation written; refitting on all years for the app")
    refit(spec_all, yall, f, dev_res)


def refit(spec_all, yall, f, dev_res):
    all_years = sorted(set(yall.year) & set(f.year))
    ranges, profile = {}, {}
    for crop in ("corn", "soy"):
        y = yall[yall.crop == crop]
        d = frame(y, f, all_years, all_years)
        m = build(crop, spec_all[crop]).fit(d)
        with open(MODELS / f"{crop}_final.pkl", "wb") as fh:
            pickle.dump({"model": m, "trends": fit_trends(y, all_years), "spec": spec_all[crop]}, fh)
        contrib = contributions(m, d)
        contrib.assign(fips=d.fips.to_numpy(), year=d.year.to_numpy()).to_parquet(MODELS / f"shap_{crop}.parquet", index=False)
        profile[crop] = month_weights(contrib)
        resid = dev_res[crop]["checks"]["intervals"]
        (MODELS / f"conformal_{crop}.json").write_text(json.dumps(
            {"level": 0.9, "halfwidth_pct": resid["conformal_90_halfwidth_pct"],
             "dev_loyo_coverage_mean": resid["conformal_loyo_coverage_by_year_mean"],
             "method": "split-conformal from leave-one-year-out residuals (dev years)"}, indent=1))
    feats = f[f.year.isin(all_years)]
    for c in S2 + ["precip_jul_aug"]:
        ranges[c] = {"min": float(feats[c].min()), "max": float(feats[c].max()),
                     "dev_min": float(feats[feats.year < TEST_START][c].min()),
                     "dev_max": float(feats[feats.year < TEST_START][c].max())}
    (MODELS / "feature_ranges.json").write_text(json.dumps(ranges, indent=1))
    proxy = {m: round((profile["corn"][m] + profile["soy"][m]) / 2, 4) for m in profile["corn"]}
    (MODELS / "stress_profile.json").write_text(json.dumps(
        {"corn": profile["corn"], "soybean": profile["soy"], "other_crops_timing_proxy": proxy,
         "method": "mean |SHAP| per feature from the final model, spread evenly over the months in each feature's "
                   "window (FEATURE_MONTHS), normalised over Apr-Oct to sum to 1",
         "feature_months": FEATURE_MONTHS}, indent=1))
    print("final models, SHAP, stress profile, conformal and feature ranges written")


if __name__ == "__main__":
    main()
