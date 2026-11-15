"""`make web-data`: precompute everything the static web app shows into web/public/data/*.json.

Python stays the source of truth for every number and every sentence on a strategy card. The browser only
re-weights the precomputed criteria with the visitor's priorities (web/src/lib/scoring.ts mirrors
`rotations.criterion_weights/score/rank/weight_sensitivity`) and looks up precomputed what-if scenarios.
"""
import datetime as dt
import json
import math
from concurrent.futures import ProcessPoolExecutor

import geopandas as gpd
import numpy as np
import pandas as pd

from src import rotations as rot
from src import scenario as scen
from src.calendar import MONTH_NAMES
from src.detrend import anomalies, fit_trends
from src.features import FEATURE_MONTHS, LABELS
from src.paths import (COUNTIES_CSV, COUNTIES_GEOJSON, DATA, FEATURES, MODELS, POWER_DAILY, PROCESSED, REPORTS, ROOT,
                       YIELDS)

OUT = ROOT / "web" / "public" / "data"
DEMO = "19169"
CROPS = {"corn": "corn", "soy": "soybean"}
SHIFTS = (-21, -14, 0, 14, 21)
RYE_PASSES = (rot.RYE_EXTRA_PASSES - 1, rot.RYE_EXTRA_PASSES, rot.RYE_EXTRA_PASSES + 1)
FIXTURE_SLIDERS = [{"water": 3, "soil": 3, "income": 3, "labor": 3}, {"water": 0, "soil": 0, "income": 0, "labor": 0},
                   {"water": 5, "soil": 5, "income": 1, "labor": 1}, {"water": 1, "soil": 1, "income": 5, "labor": 5},
                   {"water": 0, "soil": 5, "income": 0, "labor": 0}, {"water": 5, "soil": 0, "income": 0, "labor": 0},
                   {"water": 0, "soil": 0, "income": 5, "labor": 0}, {"water": 0, "soil": 0, "income": 0, "labor": 5},
                   {"water": 2, "soil": 4, "income": 3, "labor": 1}, {"water": 4, "soil": 1, "income": 2, "labor": 5}]


def clean(o):
    """JSON-safe: numpy scalars to Python, NaN/inf to None, round floats to 4 places."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        v = float(o)
        return None if math.isnan(v) or math.isinf(v) else round(v, 4)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return o.strftime("%Y-%m-%d")
    return o


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(obj), separators=(",", ":"), allow_nan=False), encoding="utf-8")


def records(df):
    return df.to_dict("records")


# ---------------------------------------------------------------- scenario grid (parallel)
_MODELS, _RANGES = None, None


def _init():
    global _MODELS, _RANGES
    _MODELS, _RANGES = scen.load_models(), scen.load_ranges()


def _grid(fips):
    d = pd.read_parquet(POWER_DAILY, filters=[("fips", "==", fips)])
    return fips, scen.grid(d, _MODELS, _RANGES)


def scenario_grids(fips_list, workers=4):
    with ProcessPoolExecutor(max_workers=workers, initializer=_init) as pool:
        return dict(pool.map(_grid, fips_list))


# ---------------------------------------------------------------- statewide
def geo():
    g = gpd.read_file(COUNTIES_GEOJSON)
    g["geometry"] = g.geometry.simplify(0.004, preserve_topology=True)
    gj = json.loads(g.to_json())
    for f in gj["features"]:
        f["properties"] = {"fips": f["properties"]["fips"], "name": f["properties"]["county"]}

        def rnd(c):
            return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 4), round(c[1], 4)]
        f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
    return gj


def map_layers(feats, yields):
    y = yields[yields.crop == "corn"].dropna(subset=["yield_bu_ac"])
    an = anomalies(y, fit_trends(y, sorted(y.year.unique())))
    t = an.groupby("fips").anom_pct.apply(lambda s: s.abs().mean()).rename("mean_abs_corn_anom").to_frame()
    for col, name in (("heat_days_jul_aug", "heat_trend"), ("gwetroot_aug_mean", "wet_trend")):
        t[name] = feats.groupby("fips").apply(lambda g: np.polyfit(g.year, g[col], 1)[0] * 10, include_groups=False)
    return t, an


def evidence():
    j = lambda p: json.loads((MODELS / p).read_text())
    metrics, dev, spec = j("metrics.json"), j("dev_results.json"), j("final_spec.json")
    cvy, tby = pd.read_parquet(MODELS / "cv_by_year.parquet"), pd.read_parquet(MODELS / "test_by_year.parquet")
    out = {"metrics": metrics, "spec": spec, "conformal": {c: j(f"conformal_{c}.json") for c in CROPS},
           "selection_rule": (REPORTS / "selection_rule.md").read_text(encoding="utf-8"),
           "eda": (REPORTS / "eda.md").read_text(encoding="utf-8"),
           "experiments": records(pd.read_csv(MODELS / "experiment_table.csv")),
           "diversity": j("diversity_check.json"), "by_year": {}, "shap": {}, "triggers": {}}
    for c in CROPS:
        sel = spec[c]["model_id"]
        keep = ["M0", "M1", "M2", sel]
        cv = cvy[(cvy.crop == c) & cvy.model_id.isin(keep)].replace({"model_id": {sel: "selected"}})
        te = tby[tby.crop == c]
        out["by_year"][c] = {"dev": records(cv[["year", "model_id", "rmse", "mae", "state_actual", "state_pred"]]),
                             "test": records(te[["year", "model", "rmse", "mae", "state_actual", "state_pred"]])}
        sh = pd.read_parquet(MODELS / f"shap_{c}.parquet")
        cols = [k for k in sh.columns if k not in ("fips", "year")]
        f = pd.read_parquet(FEATURES)[["fips", "year"] + cols].merge(sh, on=["fips", "year"], suffixes=("", "_shap"))
        dep = {}
        for k in cols:
            bins = pd.qcut(f[k], 15, duplicates="drop")
            g = f.groupby(bins, observed=True).agg(x=(k, "mean"), effect=(f"{k}_shap", "mean"))
            dep[k] = records(g)
        out["shap"][c] = {"importance": [{"feature": k, "label": LABELS.get(k, k), "months": FEATURE_MONTHS.get(k, []),
                                          "mean_abs": float(sh[k].abs().mean())} for k in cols],
                          "dependence": dep}
        out["triggers"][c] = dev[c]["triggers"]
    return out


def failures(counties):
    oof, tp = pd.read_parquet(MODELS / "cv_oof.parquet"), pd.read_parquet(MODELS / "test_predictions.parquet")
    spec = json.loads((MODELS / "final_spec.json").read_text())
    names = counties.set_index("fips").county
    out = {"y2012": {}, "y2020": {}, "largest_test_errors": {}}
    for c in CROPS:
        o = oof[(oof.crop == c) & (oof.model_id == spec[c]["model_id"]) & (oof.year == 2012)]
        t = tp[(tp.crop == c) & (tp.year == 2020)]
        out["y2012"][c] = {"state_actual": o.anom_pct.mean(), "state_pred": o.pred.mean(),
                           "demo_actual": o[o.fips == DEMO].anom_pct.mean(), "demo_pred": o[o.fips == DEMO].pred.mean()}
        out["y2020"][c] = {"state_actual": t.anom_pct.mean(), "state_pred": t.pred_selected.mean(),
                           "demo_actual": t[t.fips == DEMO].anom_pct.mean(), "demo_pred": t[t.fips == DEMO].pred_selected.mean()}
        e = tp[tp.crop == c].assign(error=lambda d: d.pred_selected - d.anom_pct)
        e = e.reindex(e.error.abs().sort_values(ascending=False).index).head(10)
        out["largest_test_errors"][c] = [{"county": names[r.fips], "year": r.year, "actual": r.anom_pct,
                                          "predicted": r.pred_selected, "error": r.error} for r in e.itertuples()]
    out["spc"] = json.loads((PROCESSED / "spc_20200810.json").read_text())
    rma = pd.read_parquet(PROCESSED / "rma_col_iowa.parquet")
    rma = rma[rma.year.isin([2012, 2020])]
    agg = []
    for area, d in (("Story County", rma[rma.fips == DEMO]), ("Iowa", rma)):
        g = d.groupby(["year", "crop", "cause_group"]).indemnity.sum().reset_index()
        agg += records(g.assign(area=area, indemnity_musd=g.indemnity / 1e6).drop(columns="indemnity"))
    out["rma"] = agg
    u = pd.read_parquet(PROCESSED / "usdm_county.parquet")
    u = u[u.week.dt.year.isin([2012, 2020])]
    out["usdm"] = records(u.assign(year=u.week.dt.year, week=u.week.dt.strftime("%Y-%m-%d"))[
        ["year", "week", "d0", "d1", "d2", "d3", "d4"]])
    nd = PROCESSED / "ndvi_demo.parquet"
    if nd.exists():
        n = pd.read_parquet(nd).dropna(subset=["value"])
        out["ndvi"] = {"series": records(n.assign(date=n.date.dt.strftime("%Y-%m-%d"))[["date", "value"]]),
                       "years": sorted(n.date.dt.year.unique().tolist()), "product": n["product"].iloc[0]}
    return out


def strategy_calendar(cal):
    out = {}
    for k, s in rot.STRATEGIES.items():
        cover, crit = rot.year_arrays(k, cal)
        out[k] = {"name": s["name"], "years": [{"grain": y["grain"], "extras": [y[e] for e in ("cover_after", "legume") if e in y],
                                                 "cover": rot.monthly(cover[i]).tolist(), "critical": rot.monthly(crit[i]).tolist()}
                                                for i, y in enumerate(s["years"])]}
    return out


# ---------------------------------------------------------------- per county
def rotation_payload(cc, stress, cal, traits):
    base_raw = rot.raw_metrics(cc, stress, cal, traits)
    crit, excluded = rot.criteria(base_raw, traits)
    equal = {k: 1.0 for k in crit}
    cards = rot.cards(base_raw, crit, excluded, equal, traits, county=cc.attrs.get("name", ""), stress=stress, calendar=cal)
    for c in cards:
        c.pop("rank"), c.pop("score")
    shifts = {}
    for d in SHIFTS:
        r = rot.raw_metrics(cc, stress, cal, traits, shift=d)
        shifts[d] = {"criteria": rot.criteria(r, traits)[0], "stress_exposure": {k: v["stress_exposure"] for k, v in r.items()}}
    passes = {}
    for p in RYE_PASSES:
        r = rot.raw_metrics(cc, stress, cal, traits, rye_passes=p)
        passes[p] = rot.criteria(r, traits)[0]
    raw = {k: {kk: vv for kk, vv in v.items()} for k, v in base_raw.items()}
    return {"raw": raw, "criteria": crit, "excluded": excluded, "cards": {c["strategy_id"]: c for c in cards},
            "calendar_shifts": shifts, "rye_passes": passes}


def drivers(fips):
    out = {}
    for c, label in CROPS.items():
        sh = pd.read_parquet(MODELS / f"shap_{c}.parquet", filters=[("fips", "==", fips)])
        cols = [k for k in sh.columns if k not in ("fips", "year")]
        neg = sh[cols].clip(upper=0).mean().sort_values()
        out[label] = [{"feature": k, "label": LABELS.get(k, k), "months": FEATURE_MONTHS.get(k, []),
                       "mean_negative_effect": float(v)} for k, v in neg.head(3).items() if v < 0]
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    counties = pd.read_csv(COUNTIES_CSV, dtype={"fips": str})
    feats, yields = pd.read_parquet(FEATURES), pd.read_parquet(YIELDS)
    clim = pd.read_parquet(PROCESSED / "climatology_county_month_all_years.parquet")
    cal, traits, stress = rot.load_calendar(), rot.load_traits(), rot.load_stress()
    layers, an_corn = map_layers(feats, yields)
    soy = yields[yields.crop == "soy"].dropna(subset=["yield_bu_ac"])
    an_soy = anomalies(soy, fit_trends(soy, sorted(soy.year.unique())))
    sources = pd.read_csv(DATA / "sources.csv").merge(pd.read_csv(REPORTS / "link_audit.csv")[["id", "status", "checked"]],
                                                      on="id", how="left")
    temps, rains = scen.TEMP_STEPS, scen.RAIN_STEPS

    print("computing scenario grids for 99 counties ...")
    grids = scenario_grids(counties.fips.tolist())

    state = {
        "meta": {"generated": dt.datetime.now().isoformat(timespec="seconds"), "demo_fips": DEMO,
                 "temp_steps": temps, "rain_steps": rains, "dev_years": [2000, 2019], "test_years": [2020, 2025],
                 "support_line": rot.SUPPORT_LINE, "months": MONTH_NAMES,
                 "power_cells": json.loads((REPORTS / "power_grid_cells.json").read_text())["approx_unique_merra2_cells"]},
        "counties": records(counties[["fips", "county", "lat", "lon"]].rename(columns={"county": "name"})),
        "map_layers": {f: r for f, r in layers.round(3).to_dict("index").items()},
        "stress": stress, "calendar": records(cal), "strategy_calendar": strategy_calendar(cal),
        "strategies": {k: {"name": v["name"], "cycle": [y["grain"] for y in v["years"]]} for k, v in rot.STRATEGIES.items()},
        "sliders": {k: {"label": rot.SLIDER_LABELS[k], "criteria": v} for k, v in rot.SLIDERS.items()},
        "criteria": rot.CRITERIA,
        "ssurgo": json.loads((PROCESSED / "ssurgo_demo.json").read_text()),
        "conformal": {c: json.loads((MODELS / f"conformal_{c}.json").read_text()) for c in CROPS},
    }
    write(OUT / "state.json", state)  # small: everything the guided pages need
    write(OUT / "evidence.json", {"evidence": evidence(), "failures": failures(counties),
                                  "sources": records(sources), "traits": records(traits)})
    write(OUT / "iowa.geo.json", geo())

    for c in counties.itertuples():
        f = feats[feats.fips == c.fips]
        cc = clim[clim.fips == c.fips].sort_values("month")
        cc.attrs["name"] = c.county
        ac, as_ = an_corn[an_corn.fips == c.fips], an_soy[an_soy.fips == c.fips]
        worst = ac.loc[ac.anom_pct.idxmin()] if len(ac) else None
        payload = {
            "fips": c.fips, "name": c.county,
            "glance": {"jul_tmax_mean": f.jul_tmax_mean.mean(), "heat_days_jul_aug": f.heat_days_jul_aug.mean(),
                       "corn_2012": ac[ac.year == 2012].anom_pct.mean(), "soy_2012": as_[as_.year == 2012].anom_pct.mean(),
                       "worst_corn_year": None if worst is None else int(worst.year),
                       "worst_corn_anom": None if worst is None else float(worst.anom_pct)},
            "anomalies": {"corn": records(ac[["year", "anom_pct"]]), "soybean": records(as_[["year", "anom_pct"]])},
            "risk": [{"month": MONTH_NAMES[r.month - 1], "frost": r.frost_freq, "heat": r.heat_freq,
                      "dry_spell": r.dry_spell_freq, "heavy_rain": r.heavy_rain_freq, "deficit": r.deficit_freq,
                      "r_m": r.r_m} for r in cc.itertuples()],
            "drivers": drivers(c.fips),
            "scenario": grids[c.fips],
            "rotation": rotation_payload(cc, stress, cal, traits),
        }
        write(OUT / "county" / f"{c.fips}.json", payload)

    story = clim[clim.fips == DEMO].sort_values("month")
    crit, excluded = rot.criteria(rot.raw_metrics(story, stress, cal, traits), traits)
    cases = []
    for s in FIXTURE_SLIDERS:
        lam, note = rot.criterion_weights(s, excluded)
        sc = rot.score(crit, lam)
        cases.append({"sliders": s, "weights": lam, "scores": sc, "rank": rot.rank(sc), "note": note})
    write(OUT / "fixtures" / "scoring.json", {"criteria": crit, "excluded": excluded, "cases": cases,
                                              "sensitivity": rot.weight_sensitivity(crit, excluded)})
    total = sum(p.stat().st_size for p in OUT.rglob("*.json"))
    print(f"wrote {len(list(OUT.rglob('*.json')))} files, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
