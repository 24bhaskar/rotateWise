"""`make select`: model ladder, LOYO CV, selection rule, robustness checks. Development years ONLY.

Writes experiments/log.csv, models/cv_by_year.parquet, models/cv_oof.parquet, models/dev_results.json,
models/final_spec.json and models/experiment_table.csv. Never loads a test-period yield (see cv.load_dev).
"""
import copy
import datetime as dt
import json
import time

import numpy as np
import pandas as pd

from src.cv import DEV_YEARS, expanding, fold_frame, load_dev, loyo, shuffle_weather, spatial
from src.features import FEATURE_SETS, SOIL_MOISTURE
from src.metrics import per_year, summary
from src.models import SEED, LGBM, Average, Linear, StateLocalChain, candidates
from src.paths import EXPERIMENTS, MODELS, REPORTS
from src.uncertainty import boot_years, conformal_halfwidth, coverage

LOG = EXPERIMENTS / "log.csv"
SIMPLICITY = ["M2", "M3", "M4", "M5", "M6", "M8", "M7", "E", "C"]


def log(row):
    row = {"timestamp": dt.datetime.now().isoformat(timespec="seconds"), "seed": SEED, **row}
    pd.DataFrame([row]).to_csv(LOG, mode="a", header=not LOG.exists(), index=False)


def describe(m):
    p = {"features": getattr(m, "feats", None)}
    for k in ("alpha", "lam", "n_estimators", "params", "l1_ratio", "kind", "engineered"):
        if hasattr(m, k):
            v = getattr(m, k)
            p[k] = {kk: vv for kk, vv in v.items() if kk != "monotone_constraints"} if isinstance(v, dict) else v
    return json.dumps(p, default=str)


def rank_key(mid):
    return next(i for i, p in enumerate(SIMPLICITY) if mid.startswith(p))


def select(res, py):
    """Apply reports/selection_rule.md. res: {id: summary}, py: {id: per-year frame}."""
    m2 = py["M2"].rmse
    ok = [k for k in res if k not in ("M0", "M1", "M2")
          and res[k]["rmse"] < res["M0"]["rmse"] and res[k]["rmse"] < res["M2"]["rmse"]
          and int((py[k].rmse < m2).sum()) >= 12]
    notes = {"qualified": ok}
    if not ok:
        notes["reason"] = "no candidate beat M0 and M2 in mean RMSE and in >= 12 of 20 years; M2 is the main model"
        return "M2", notes
    best = min(ok, key=lambda k: res[k]["rmse"])
    within = [k for k in ok if res[k]["rmse"] <= res[best]["rmse"] + res[best]["rmse_se"]]
    choice = min(within, key=lambda k: (rank_key(k), res[k]["rmse"]))
    ci = res[choice]["boot"]["diff_vs_ref"]
    notes.update(best=best, within_1se=within, diff_vs_m2_ci=ci)
    if ci[0] <= 0 <= ci[1]:
        notes["reason"] = f"{choice} qualified, but its RMSE difference vs M2 has a 90% interval including 0: tie -> M2"
        return "M2", notes
    notes["reason"] = f"simplest model within 1 SE of the best ({best}); interval vs M2 excludes 0"
    return choice, notes


def with_feats(model, feats):
    m = copy.deepcopy(model)
    if isinstance(m, LGBM):
        return LGBM(feats, **{k: m.params[k] for k in ("num_leaves", "max_depth", "min_child_samples", "reg_lambda")})
    if hasattr(m, "engineered") and m.engineered and "gwetroot_aug_mean" not in feats:
        m.engineered = False
    m.feats = feats
    return m


def clim_anomaly_features(feats):
    def fn(d, train_years):
        mu = d[d.year.isin(train_years)].groupby("fips")[feats].mean()
        d = d.copy()
        d[feats] = d[feats] - mu.loc[d.fips].to_numpy()
        return d
    return fn


def pooled_loyo(model, crop):
    """A2: corn and soybean pooled with a crop indicator; scored on `crop` only."""
    yc, f = load_dev("corn")
    ys, _ = load_dev("soy")
    out = []
    for h in DEV_YEARS:
        tr_years = [t for t in DEV_YEARS if t != h]
        d = pd.concat([fold_frame(yc, f, tr_years).assign(is_corn=1), fold_frame(ys, f, tr_years).assign(is_corn=0)])
        m = with_feats(model, model.feats + ["is_corn"]).fit(d[d.year != h])
        te = d[(d.year == h) & (d.is_corn == int(crop == "corn"))]
        out.append(te[["fips", "year", "anom_pct"]].assign(pred=m.predict(te)))
    return pd.concat(out)


def run_crop(crop, eda):
    y, f = load_dev(crop)
    cands = candidates(crop)
    oof, py, res = {}, {}, {}

    def evaluate(mid, model, stage="ladder"):
        t0 = time.time()
        p = loyo(model, y, f)
        oof[mid], py[mid] = p, per_year(p)
        res[mid] = summary(py[mid], py.get("M0", py[mid]))
        res[mid]["train_rmse"] = round(float(p.groupby("year").fit_rmse.first().mean()), 4)
        log({"crop": crop, "stage": stage, "model_id": mid, "model": model.name,
             "feature_set": next((k for k, v in FEATURE_SETS.items() if v == getattr(model, "feats", None)), "custom"),
             "params": describe(model), "cv_rmse": res[mid]["rmse"], "cv_mae": res[mid]["mae"],
             "cv_rmse_se": res[mid]["rmse_se"], "skill_vs_m0": res[mid].get("skill_vs_m0"),
             "train_rmse": res[mid]["train_rmse"], "seconds": round(time.time() - t0, 1)})
        print(f"  {crop} {mid:22s} rmse {res[mid]['rmse']:.2f} mae {res[mid]['mae']:.2f} ({time.time() - t0:.0f}s)")

    for mid, model in cands.items():
        evaluate(mid, model)

    # B9.3 triggers (decided from CV residuals, as written in the selection rule)
    lin = min([k for k in res if k.startswith(("M3", "M5"))], key=lambda k: res[k]["rmse"])
    tree = min([k for k in res if k.startswith("M7")], key=lambda k: res[k]["rmse"])
    gam = min([k for k in res if k.startswith("M6")], key=lambda k: res[k]["rmse"])
    rcorr = float(np.corrcoef(oof[lin].pred - oof[lin].anom_pct, oof[tree].pred - oof[tree].anom_pct)[0, 1])
    triggers = {"residual_corr_linear_tree": round(rcorr, 3), "E_triggered": rcorr < 0.8,
                "statewide_share": eda[crop]["share_variance_statewide_year"],
                "C1_triggered": eda[crop]["share_variance_statewide_year"] >= 0.6}
    if triggers["E_triggered"]:
        evaluate("E1", Average(cands[lin], cands[tree], f"E1 avg({lin},{tree})"), "ensemble")
        evaluate("E2", Average(cands[gam], cands[tree], f"E2 avg({gam},{tree})"), "ensemble")
    if triggers["C1_triggered"]:
        evaluate("C1", StateLocalChain(cands[lin].feats), "chain")

    for k in res:
        res[k]["boot"] = boot_years(py[k], py["M0"], py["M2"])
    chosen, notes = select(res, py)
    model = {**cands, **({"E1": Average(cands[lin], cands[tree], "E1"), "E2": Average(cands[gam], cands[tree], "E2")}
                         if triggers["E_triggered"] else {}),
             **({"C1": StateLocalChain(cands[lin].feats)} if triggers["C1_triggered"] else {})}[chosen]
    print(f"  {crop}: selected {chosen} ({notes['reason']})")

    # B9.8 robustness and diagnostics on the selected model
    checks = {"train_vs_cv_gap": {"train_rmse": res[chosen]["train_rmse"], "cv_rmse": res[chosen]["rmse"]}}
    plac = []
    for s in range(3):
        p = loyo(model, y, shuffle_weather(f, seed=100 + s))
        plac.append(per_year(p).rmse.mean())
    checks["placebo"] = {"shuffled_rmse_mean": round(float(np.mean(plac)), 3), "runs": [round(float(v), 3) for v in plac],
                         "m0_rmse": res["M0"]["rmse"], "real_rmse": res[chosen]["rmse"]}
    sp = per_year(spatial(model, y, f))
    checks["spatial_block"] = {"rmse": round(float(sp.rmse.mean()), 3), "loyo_rmse": res[chosen]["rmse"]}
    exp = {}
    for k in dict.fromkeys(["M0", "M1", "M2", lin, gam, tree, chosen]):
        mm = model if k == chosen else cands[k]
        exp[k] = round(float(per_year(expanding(mm, y, f)).rmse.mean()), 3)
    checks["expanding_window_2008_2019"] = {"rmse": exp, "loyo_rank": sorted(exp, key=lambda k: res[k]["rmse"]),
                                            "expanding_rank": sorted(exp, key=exp.get)}
    abl = {}
    feats = getattr(model, "feats", None)
    if feats is not None and not isinstance(model, StateLocalChain):
        no_soil = [c for c in feats if c not in SOIL_MOISTURE]
        abl["A1_without_gwetroot"] = per_year(loyo(with_feats(model, no_soil), y, f)).rmse.mean()
        abl["A2_pooled_crops"] = per_year(pooled_loyo(model, crop)).rmse.mean()
        abl["A4_climatology_anomaly_features"] = per_year(loyo(model, y, f, feature_fn=clim_anomaly_features(feats))).rmse.mean()
    abl["A3_theilsen_detrending (different target)"] = per_year(loyo(model, y, f, method="theilsen")).rmse.mean()
    abl["A1_reference_selected"] = res[chosen]["rmse"]
    checks["ablations"] = {k: round(float(v), 3) for k, v in abl.items()}
    for k, v in checks["ablations"].items():
        log({"crop": crop, "stage": "ablation", "model_id": f"{chosen}:{k}", "model": model.name, "cv_rmse": v})
    m2_ablate = per_year(loyo(Linear([c for c in FEATURE_SETS["S0"] if c not in SOIL_MOISTURE]), y, f)).rmse.mean()
    checks["ablations"]["A1_M2_without_gwetroot"] = round(float(m2_ablate), 3)

    # B9.6 intervals: split-conformal from LOYO residuals, plus a quantile-LightGBM comparison
    resid = oof[chosen].pred - oof[chosen].anom_pct
    half = conformal_halfwidth(resid)
    lo_m = LGBM(FEATURE_SETS["S2"], objective="quantile", alpha=0.05, name="q05")
    hi_m = LGBM(FEATURE_SETS["S2"], objective="quantile", alpha=0.95, name="q95")
    qlo, qhi = loyo(lo_m, y, f), loyo(hi_m, y, f)
    qcov = float(np.mean((qlo.anom_pct >= qlo.pred) & (qhi.anom_pct <= qhi.pred)))
    # honest per-year coverage of the conformal band: rebuild the half-width without each year
    cov_y = []
    for h in DEV_YEARS:
        mask = oof[chosen].year == h
        hw = conformal_halfwidth(resid[~mask])
        cov_y.append(coverage(oof[chosen].anom_pct[mask], oof[chosen].pred[mask], hw))
    checks["intervals"] = {"conformal_90_halfwidth_pct": round(half, 2),
                           "conformal_loyo_coverage_by_year_mean": round(float(np.mean(cov_y)), 3),
                           "conformal_worst_year_coverage": round(float(np.min(cov_y)), 3),
                           "quantile_lgbm_90_coverage": round(qcov, 3)}

    by_year = pd.concat([v.assign(model_id=k, crop=crop) for k, v in py.items()]).reset_index()
    keep = pd.concat([oof[k].assign(model_id=k, crop=crop) for k in dict.fromkeys(["M0", "M1", "M2", chosen])])
    spec = {"model_id": chosen, "model": model.name, "params": json.loads(describe(model)), "trend": "per-county OLS",
            "features": feats, "lin": lin, "tree": tree, "gam": gam}
    return {"results": res, "selected": chosen, "selection_notes": notes, "triggers": triggers, "checks": checks,
            "spec": spec}, by_year, keep


def main():
    if LOG.exists():
        LOG.rename(LOG.with_suffix(f".{dt.datetime.now():%Y%m%d%H%M%S}.csv"))  # keep earlier runs, start fresh
    eda = json.loads((REPORTS / "eda.json").read_text())
    out, by_year, oof = {}, [], []
    for crop in ("corn", "soy"):
        r, b, o = run_crop(crop, eda)
        out[crop] = r
        by_year.append(b)
        oof.append(o)
    pd.concat(by_year).to_parquet(MODELS / "cv_by_year.parquet", index=False)
    pd.concat(oof).to_parquet(MODELS / "cv_oof.parquet", index=False)
    (MODELS / "dev_results.json").write_text(json.dumps(out, indent=1, default=str))
    (MODELS / "final_spec.json").write_text(json.dumps(
        {c: out[c]["spec"] for c in out} | {"frozen_at": dt.datetime.now().isoformat(timespec="seconds"),
                                            "dev_years": [2000, 2019]}, indent=1, default=str))
    rows = []
    for c in out:
        for k, v in out[c]["results"].items():
            rows.append({"crop": c, "model_id": k, "cv_rmse": v["rmse"], "rmse_90ci": v["boot"]["rmse"],
                         "cv_mae": v["mae"], "skill_vs_m0": v.get("skill_vs_m0"), "skill_90ci": v["boot"]["skill"],
                         "within_year_spearman": v["spearman_within_year"], "train_rmse": v["train_rmse"],
                         "selected": k == out[c]["selected"]})
    pd.DataFrame(rows).to_csv(MODELS / "experiment_table.csv", index=False)
    print("done")


if __name__ == "__main__":
    main()
