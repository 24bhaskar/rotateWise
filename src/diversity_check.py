"""B11.6 suggestive evidence: did counties with more hay/oats/small grain lose less than the model expected?

Outcome: actual minus model-predicted anomaly (dev years use leave-one-year-out predictions, so the model never
saw the year it predicts). Predictor: share of harvested acres in hay + oats + wheat + barley (NASS survey; the
latest year at or before the target year). Confounded by soils, livestock, farm size and management.
"""
import json

import numpy as np
import pandas as pd

from src.paths import MODELS, PROCESSED


def share_for(acre, years):
    a = acre.dropna(subset=["share_diverse"]).sort_values("year")
    rows = []
    for y in years:
        last = a[a.year <= y].groupby("fips").tail(1)
        rows.append(last[["fips", "share_diverse"]].assign(year=y, share_year=last.year))
    return pd.concat(rows)


def slope(df):
    x, y = df.share_diverse.to_numpy() * 100, df.resid.to_numpy()  # per 10 percentage points below
    return float(np.polyfit(x, y, 1)[0] * 10) if len(df) > 5 and np.ptp(x) > 0 else np.nan


def boot(df, by, n=2000, seed=42):
    rng = np.random.default_rng(seed)
    groups = df[by].unique()
    vals = []
    for _ in range(n):
        pick = rng.choice(groups, len(groups), replace=True)
        vals.append(slope(pd.concat([df[df[by] == g] for g in pick])))
    return [round(float(np.nanquantile(vals, 0.05)), 2), round(float(np.nanquantile(vals, 0.95)), 2)]


def main():
    spec = json.loads((MODELS / "final_spec.json").read_text())
    acre = pd.read_parquet(PROCESSED / "acreage_diversity.parquet")
    out = {"units": "change in (actual - predicted) anomaly, percentage points, per +10 points of diverse-crop share",
           "caveat": "Suggestive only: counties differ in soils, livestock, farm size and management."}
    for crop in ("corn", "soy"):
        oof = pd.read_parquet(MODELS / "cv_oof.parquet")
        oof = oof[(oof.crop == crop) & (oof.model_id == spec[crop]["model_id"])]
        rows = [oof[["fips", "year", "anom_pct", "pred"]]]
        tp = MODELS / "test_predictions.parquet"
        if tp.exists():
            t = pd.read_parquet(tp)
            t = t[t.crop == crop]
            rows.append(t.rename(columns={"pred_selected": "pred"})[["fips", "year", "anom_pct", "pred"]])
        d = pd.concat(rows)
        d["resid"] = d.anom_pct - d.pred
        d = d.merge(share_for(acre, sorted(d.year.unique())), on=["fips", "year"])
        res = {"all_years": {"slope": round(slope(d), 3), "ci90_year_bootstrap": boot(d, "year"),
                             "n": len(d), "years": [int(d.year.min()), int(d.year.max())]}}
        for yr in (2012, 2020):
            s = d[d.year == yr]
            if len(s):
                res[str(yr)] = {"slope": round(slope(s), 3), "ci90_county_bootstrap": boot(s, "fips"), "n": len(s),
                                "share_from_year": int(s.share_year.max()),
                                "median_share_pct": round(float(s.share_diverse.median() * 100), 1)}
        out[crop] = res
    (MODELS / "diversity_check.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
