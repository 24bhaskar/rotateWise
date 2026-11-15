"""B11 rotation engine: a transparent weighted heuristic, NOT an ML prediction of each strategy's yield.

Inputs: the model's stress profile (month weights), the crop calendar (NASS Crop Progress + cited rules),
the county's heavy-rain climatology (NASA POWER), the cited trait table, and rotation-level economics.

Criteria (0-1, higher is better), min-max scaled across the three strategies:
  StressExposure   overlap of each grain crop's critical period with the months the model found costly
  BareAndErosion   bare-soil share of the year and storm exposure of bare soil
  WaterUse         seasonal crop water use (trait table)                    } excluded when under half of
  SoilHealth       N fixation, rooting depth, residue, organic matter       } their trait cells are sourced
  IncomeStability  rotation-level net-return evidence (ISU CARD; Marsden Farm)
  LaborBurden      relative labour (ISU budgets; Marsden Farm; rye passes = expert rating)
"""
import json

import numpy as np
import pandas as pd

from src.paths import DATA, MODELS

SUPPORT_LINE = "Supports your decision; does not replace your judgment or local expert advice."
DAYS = pd.date_range("2019-01-01", "2019-12-31")  # a non-leap reference year
MONTH_OF_DAY = DAYS.month.to_numpy()

STRATEGIES = {
    "A": {"name": "Existing: corn → soybean", "years": [{"grain": "corn"}, {"grain": "soybean"}]},
    "B": {"name": "Corn → soybean + winter cereal rye", "years": [
        {"grain": "corn", "cover_after": "cereal_rye_before_soy"},
        {"grain": "soybean", "cover_after": "cereal_rye_before_corn"}]},
    "C": {"name": "Corn → soybean → oats with red clover", "years": [
        {"grain": "corn"}, {"grain": "soybean"}, {"grain": "oats", "legume": "red_clover"}]},
}
MODELED = {"corn", "soybean"}
CRITERIA = ["StressExposure", "BareAndErosion", "WaterUse", "SoilHealth", "IncomeStability", "LaborBurden"]
SLIDERS = {"water": {"WaterUse": 0.5, "StressExposure": 0.5}, "soil": {"SoilHealth": 0.5, "BareAndErosion": 0.5},
           "income": {"IncomeStability": 1.0}, "labor": {"LaborBurden": 1.0}}
SLIDER_LABELS = {"water": "Conserve water", "soil": "Soil health", "income": "Income", "labor": "Low labour"}
CRITERION_TRAITS = {"WaterUse": ["seasonal_water_use"],
                    "SoilHealth": ["n_fixation", "rooting_depth", "residue_cover", "soil_organic_matter_contribution"]}
RYE_EXTRA_PASSES = 2  # seeding + termination per rye winter: expert rating from S04/S05 descriptions, verified=N


def load_calendar():
    return pd.read_csv(DATA / "crop_calendar.csv", dtype=str)


def load_traits():
    return pd.read_csv(DATA / "crop_traits.csv", dtype=str).fillna("")


def _doy(md, shift=0):
    return (pd.Timestamp(f"2019-{md}") + pd.Timedelta(days=shift)).dayofyear


def _date(cal, crop, event, shift=0, col="typical_month_day"):
    row = cal[(cal.crop == crop) & (cal.event == event)].iloc[0]
    return _doy(row[col], shift)


def _mark(arr, a, b):
    """Mark days a..b (1-based day of year) inclusive; a > b wraps across the new year."""
    if a <= b:
        arr[a - 1:b] = 1
    else:
        arr[a - 1:] = 1
        arr[:b] = 1


def year_arrays(strategy, cal, shift=0):
    """Per rotation year: daily living-cover (0/1) and critical-period (0/1) arrays.
    Cover from planting to harvest for grain crops; covers and legumes from seeding to termination,
    wrapping into the following rotation year. `shift` moves every window by that many days."""
    yrs = STRATEGIES[strategy]["years"]
    n = len(yrs)
    cover = [np.zeros(365) for _ in range(n)]
    crit = [np.zeros(365) for _ in range(n)]
    for i, y in enumerate(yrs):
        g = y["grain"]
        _mark(cover[i], _date(cal, g, "planting", shift), _date(cal, g, "harvest", shift))
        _mark(crit[i], _date(cal, g, "critical", shift, "start_month_day"), _date(cal, g, "critical", shift, "end_month_day"))
        nxt = (i + 1) % n
        if "cover_after" in y:
            c = y["cover_after"]
            _mark(cover[i], _date(cal, c, "seeding", shift), 365)
            _mark(cover[nxt], 1, _date(cal, c, "termination", shift))
        if "legume" in y:
            lg = y["legume"]
            _mark(cover[i], _date(cal, lg, "seeding", shift), 365)  # clover keeps growing after the oat harvest
            _mark(cover[nxt], 1, _date(cal, lg, "termination", shift))
    return cover, crit


def monthly(arr):
    return np.array([arr[MONTH_OF_DAY == m].mean() for m in range(1, 13)])


def trait_coverage(traits, crops, trait_names=None):
    t = traits[traits.crop.isin(crops)]
    if trait_names:
        t = t[t.trait.isin(trait_names)]
    sourced = (t.value != "NEEDS_SOURCE") & (t.source_id != "")
    return {"sourced": int(sourced.sum()), "total": len(t), "verified_by_human": int((t.verified == "Y").sum()),
            "unverified": int((t.verified != "Y").sum())}


def raw_metrics(clim_county, stress, cal, traits, shift=0, rye_passes=RYE_EXTRA_PASSES):
    """Unscaled metrics per strategy. clim_county: 12 rows (month 1-12) with r_m."""
    r_m = clim_county.sort_values("month").r_m.to_numpy()
    w = {"corn": stress["corn"], "soybean": stress["soybean"], "oats": stress["other_crops_timing_proxy"]}
    cost = {r.crop: float(r.value) for r in traits[traits.trait == "labor_passes"].itertuples()
            if r.value not in ("", "NEEDS_SOURCE")}
    out = {}
    for s, spec in STRATEGIES.items():
        cover, crit = year_arrays(s, cal, shift)
        exp, bare, ero = [], [], []
        for i, y in enumerate(spec["years"]):
            cm, km = monthly(cover[i]), monthly(crit[i])
            wm = w[y["grain"]]
            exp.append(sum(float(wm.get(str(m), wm.get(m, 0))) * km[m - 1] for m in range(4, 11)))
            bare.append(1 - cm.mean())
            ero.append(float((r_m * (1 - cm)).sum()))
        crops = sorted({y["grain"] for y in spec["years"]} | {y.get("legume") for y in spec["years"]} - {None}
                       | {"cereal_rye" for y in spec["years"] if "cover_after" in y})
        base_hours = np.mean([cost["corn"], cost["soybean"]])
        if s == "A":
            labor, income = 1.0, 0.0
        elif s == "B":
            # passes -> hours is not sourced; assume each extra pass ~ the oat budget's 1 h/acre seeding+harvest / 2
            labor = 1.0 + rye_passes * 0.5 / base_hours
            income = -(48.82 + 38.42) / 2  # S12: avg net return of cover crops before corn and before soybean
        else:
            labor = 1.33   # S09: labour >33% higher in the 3-yr rotation (lower bound)
            income = 0.0   # S09: net returns not significantly different from the 2-yr rotation
        out[s] = {"stress_exposure": float(np.mean(exp)), "bare_fraction": float(np.mean(bare)),
                  "erosion_exposure": float(np.mean(ero)), "labor_index": labor, "income_delta_usd_acre_yr": income,
                  "profit_variance_lower": s == "C", "crops": crops,
                  "modeled_years": sum(y["grain"] in MODELED for y in spec["years"]), "cycle_years": len(spec["years"])}
    return out


def _minmax(vals, higher_better):
    lo, hi = min(vals.values()), max(vals.values())
    if hi - lo < 1e-9:
        return {k: 1.0 for k in vals}
    return {k: ((v - lo) / (hi - lo) if higher_better else (hi - v) / (hi - lo)) for k, v in vals.items()}


def criteria(raw, traits):
    """Scaled criteria, plus which criteria are excluded for lack of sourced data."""
    all_crops = sorted({c for v in raw.values() for c in v["crops"]})
    excluded = {}
    for crit_name, tnames in CRITERION_TRAITS.items():
        cov = trait_coverage(traits, all_crops, tnames)
        if cov["sourced"] < cov["total"] / 2:
            excluded[crit_name] = f"insufficient sourced data ({cov['sourced']} of {cov['total']} trait values sourced)"
    se = _minmax({k: v["stress_exposure"] for k, v in raw.items()}, False)
    bare = _minmax({k: v["bare_fraction"] for k, v in raw.items()}, False)
    ero = _minmax({k: v["erosion_exposure"] for k, v in raw.items()}, False)
    inc = _minmax({k: v["income_delta_usd_acre_yr"] + (1 if v["profit_variance_lower"] else 0) for k, v in raw.items()}, True)
    lab = _minmax({k: v["labor_index"] for k, v in raw.items()}, False)
    c = {k: {"StressExposure": se[k], "BareAndErosion": (bare[k] + ero[k]) / 2, "IncomeStability": inc[k],
             "LaborBurden": lab[k], "WaterUse": None, "SoilHealth": None} for k in raw}
    return c, excluded


def criterion_weights(sliders, excluded):
    """Slider values (0-5) -> criterion weights summing to 1, dropping excluded criteria (approach (a), B20.3)."""
    s = {k: max(float(v), 0.0) for k, v in sliders.items()}
    note = None
    if sum(s.values()) == 0:
        s, note = {k: 1.0 for k in SLIDERS}, "All priorities were zero, so equal weights are used."
    lam = {c: 0.0 for c in CRITERIA}
    for k, v in s.items():
        # an excluded criterion's share moves to the slider's remaining criteria, so each priority keeps its weight
        kept = {c: share for c, share in SLIDERS[k].items() if c not in excluded}
        for c, share in kept.items():
            lam[c] += v * share / sum(kept.values())
    tot = sum(lam.values())
    return {c: v / tot for c, v in lam.items()}, note


def score(crit, weights):
    return {k: sum(weights[c] * (v[c] or 0.0) for c in CRITERIA) for k, v in crit.items()}


def rank(scores):
    return sorted(scores, key=lambda k: -scores[k])


def weight_sensitivity(crit, excluded, n=2000, seed=42):
    """Dirichlet(1,1,1,1) draws over the four sliders: share of draws each strategy ranks first, and rank range."""
    rng = np.random.default_rng(seed)
    firsts, ranks = {k: 0 for k in crit}, {k: [] for k in crit}
    for wv in rng.dirichlet(np.ones(4), size=n):
        lam, _ = criterion_weights(dict(zip(SLIDERS, wv)), excluded)
        order = rank(score(crit, lam))
        firsts[order[0]] += 1
        for i, k in enumerate(order, 1):
            ranks[k].append(i)
    return {k: {"share_first": round(firsts[k] / n, 3), "rank_min": min(ranks[k]), "rank_max": max(ranks[k])} for k in crit}


def calendar_sensitivity(clim_county, stress, cal, traits, sliders, shifts=(-21, -14, 0, 14, 21)):
    out = {}
    for d in shifts:
        raw = raw_metrics(clim_county, stress, cal, traits, shift=d)
        crit, exc = criteria(raw, traits)
        lam, _ = criterion_weights(sliders, exc)
        out[d] = {"ranking": rank(score(crit, lam)),
                  "stress_exposure": {k: round(v["stress_exposure"], 4) for k, v in raw.items()}}
    return out


def trait_sensitivity(clim_county, stress, cal, traits, sliders):
    """Vary the one ordinal expert rating (rye extra passes) by +/- 1 step."""
    out = {}
    for p in (RYE_EXTRA_PASSES - 1, RYE_EXTRA_PASSES, RYE_EXTRA_PASSES + 1):
        raw = raw_metrics(clim_county, stress, cal, traits, rye_passes=p)
        crit, exc = criteria(raw, traits)
        lam, _ = criterion_weights(sliders, exc)
        out[p] = rank(score(crit, lam))
    return out


BARE_SOURCES = {"A": "S01", "B": "S01;S04;S05", "C": "S01;S07;S08"}
MONTH_LONG = {4: "April", 5: "May", 6: "June", 7: "July", 8: "August", 9: "September", 10: "October"}


def cards(raw, crit, excluded, scores, traits, scenario=None, county="Story", stress=None, calendar=None):
    """B11.7 data contract. `scenario`: {'corn': pct, 'soybean': pct} modelled anomaly, or None."""
    order = rank(scores)
    a = raw["A"]
    out = []
    corn_w = (stress or {}).get("corn", {})
    top_m = max(corn_w, key=corn_w.get) if corn_w else None
    oats_end = None
    if calendar is not None:
        md = calendar[(calendar.crop == "oats") & (calendar.event == "critical")].end_month_day.iloc[0]
        ts = pd.Timestamp(f"2019-{md}")
        oats_end = f"{ts:%B} {ts.day}"
    for k in order:
        r = raw[k]
        cov = trait_coverage(traits, r["crops"])
        nm = r["cycle_years"] - r["modeled_years"]
        ev = [
            {"claim": "Share of the grain crops' critical periods falling in months the model found costly",
             "data_source_id": "D2;D1;S01", "metric": "stress exposure (model-weighted)", "value": round(r["stress_exposure"], 3)},
            {"claim": "Share of the year with bare soil", "data_source_id": BARE_SOURCES[k],
             "metric": "bare fraction", "value": round(r["bare_fraction"], 3)},
            {"claim": f"Bare soil during months that bring {county} County's heavy-rain days",
             "data_source_id": "D2", "metric": "erosion exposure (share of heavy-rain days on bare soil)",
             "value": round(r["erosion_exposure"], 3)},
        ]
        if scenario:
            ev.append({"claim": "Modelled corn/soybean yield change for modelled years under the selected scenario",
                       "data_source_id": "D1;D2", "metric": "% vs trend (corn / soybean)",
                       "value": f"{scenario['corn']:+.1f} / {scenario['soybean']:+.1f}"})
        gaps = ["Field-level soil, drainage and slope: the tool uses county-scale data only.",
                "Local markets and prices (see ISU Ag Decision Maker crop budgets, S10).",
                "Your equipment, labour and custom-hire options.",
                "Yield response of crops the model does not cover (oats, red clover, cereal rye)."]
        risks = []
        if k == "A":
            why = "Your current rotation, used as the reference for every comparison."
            ben = ["Familiar markets, equipment and management.",
                   "Lowest labour of the three in ISU budgets (about 2.2-2.6 operator hours/acre per year; S10)."]
            risks = [f"Soil is bare about {a['bare_fraction']:.0%} of the year, including months with heavy rain.",
                     "A two-crop cycle gives soybean cyst nematode a host every other year (S11)."]
        elif k == "B":
            why = (f"The field is bare about {a['bare_fraction']:.0%} of the year under corn-soybean. Cereal rye seeded "
                   "right after harvest (S05) covers the soil through winter and spring, when much of the county's "
                   "heavy rain falls.")
            ben = [f"Bare-soil share falls from {a['bare_fraction']:.0%} to {r['bare_fraction']:.0%} of the year.",
                   "Rye produces 3,000-10,000 lb/acre of dry matter (SARE, S06) and holds soil and nutrients (S05).",
                   "Same cash crops, so no new grain markets are needed."]
            risks = ["Rye decomposition ties up soil nitrogen for the next corn crop, more if rye has started jointing; "
                     "terminate at least 10-14 days before corn planting (ISU, S04).",
                     "Possible corn yield drag after rye; Iowa survey data show smaller drag for experienced users (S12).",
                     "Seeding right after harvest and spring termination timing both depend on the season (S04; S05).",
                     "Without cost-share or grazing, cover crops returned about -$38 to -$49 per acre in an Iowa "
                     "survey (S12); check local cost-share programs."]
        else:
            peak = (f"The model puts {corn_w[top_m]:.0%} of corn's weather sensitivity in {MONTH_LONG[top_m]}. "
                    if top_m else "")
            end = f"ends around {oats_end}" if oats_end else "ends in early July"
            why = (f"{peak}The oat crop's critical period (heading to colouring) {end} in a typical Iowa year (NASS Crop "
                   "Progress, S01), so one year in three has a grain crop that is mostly past its sensitive stage "
                   "before the peak stress window. This is calendar exposure, not a predicted yield.")
            ben = ["At Marsden Farm in neighbouring Boone County, the 3-year rotation had corn yields ~4% and soybean "
                   "yields ~9% higher than corn-soybean, with ~80% less synthetic N and 88% less herbicide (S09).",
                   "Net returns were similar to corn-soybean and varied less from year to year (S09).",
                   "Red clover supplies 70-150 lb N/acre and excellent forage (S06; S07)."]
            risks = ["Needs small-grain harvest and hay or grazing equipment, and more labour (>33% more at Marsden; S09).",
                     "Local markets for oats, straw and hay were not checked.",
                     "Red clover establishment can fail in a dry or very wet spring (S07; S08).",
                     "Clovers are soybean cyst nematode hosts (ISU, S11): review with your agronomist.",
                     "Marsden Farm also used composted manure; results may not transfer directly."]
        excluded_txt = [f"{c}: {why_}" for c, why_ in excluded.items()]
        out.append({
            "strategy_id": k, "name": STRATEGIES[k]["name"], "rank": order.index(k) + 1, "score": round(scores[k], 3),
            "criteria": {c: (None if v is None else round(v, 3)) for c, v in crit[k].items()},
            "excluded_criteria": excluded_txt, "why_suggested": why, "evidence": ev, "benefits": ben,
            "information_gaps": gaps, "risks_needing_local_review": risks,
            "modeled_years": r["modeled_years"], "not_modeled_years": nm, "cycle_years": r["cycle_years"],
            "confidence_note": (f"{r['modeled_years']} of {r['cycle_years']} rotation years are modelled; "
                                f"{cov['sourced']} of {cov['total']} trait values sourced, {cov['unverified']} not yet "
                                "verified by a human. Scores are relative and come from a transparent formula, "
                                "not a predicted yield."),
            "trait_coverage": cov,
            "sources": sorted({s for e in ev for s in e["data_source_id"].split(";")} | {"S10"}
                              | ({"S04", "S05", "S06", "S12"} if k == "B" else set())
                              | ({"S01", "S06", "S07", "S08", "S09", "S11"} if k == "C" else set())),
            "support_line": SUPPORT_LINE})
    return out


def month_weights_ok(w, tol=1e-3):
    return abs(sum(w.values()) - 1) < tol and all(v >= 0 for v in w.values())


def load_stress():
    p = json.loads((MODELS / "stress_profile.json").read_text())
    for k in ("corn", "soybean", "other_crops_timing_proxy"):
        p[k] = {int(m): v for m, v in p[k].items()}
    return p
