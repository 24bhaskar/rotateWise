"""RotateWise: compare crop-rotation strategies for an Iowa county using NASA Earth observations and USDA data.

Runs fully offline from cached files in data/processed and models/. County-scale hindcast, not a forecast.
"""
import json
import pickle

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src import rotations as rot
from src import scenario as scen
from src.calendar import MONTH_NAMES
from src.detrend import anomalies
from src.explain import explain
from src.features import LABELS
from src.paths import COUNTIES_CSV, COUNTIES_GEOJSON, DATA, EXPERIMENTS, FEATURES, MODELS, POWER_DAILY, PROCESSED, ROOT, YIELDS

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="RotateWise", page_icon="🌱", layout="wide")
DEMO = "19169"
FOOTER = ("RotateWise supports farmers and extension agents. It does not replace farmer judgment or local "
          "agricultural expertise. County-scale hindcast, not a forecast.")
CROP_KEY = {"corn": "corn", "soybean": "soy"}
TEMP_RANGE, RAIN_RANGE = (-1.0, 2.0), (-25, 25)


def footer():
    st.divider()
    st.caption("⚠️ " + FOOTER)


# ---------------------------------------------------------------- cached loaders
@st.cache_data
def load_static():
    counties = pd.read_csv(COUNTIES_CSV, dtype={"fips": str})
    geo = json.loads(COUNTIES_GEOJSON.read_text())
    feats = pd.read_parquet(FEATURES)
    yields = pd.read_parquet(YIELDS)
    clim = pd.read_parquet(PROCESSED / "climatology_county_month_all_years.parquet")
    return counties, geo, feats, yields, clim


@st.cache_data
def load_model_outputs():
    j = lambda p: json.loads((MODELS / p).read_text())
    out = {"metrics": j("metrics.json"), "spec": j("final_spec.json"), "dev": j("dev_results.json"),
           "ranges": j("feature_ranges.json"), "conf": {c: j(f"conformal_{c}.json") for c in ("corn", "soy")},
           "cv_by_year": pd.read_parquet(MODELS / "cv_by_year.parquet"),
           "test_by_year": pd.read_parquet(MODELS / "test_by_year.parquet"),
           "cv_oof": pd.read_parquet(MODELS / "cv_oof.parquet"),
           "test_pred": pd.read_parquet(MODELS / "test_predictions.parquet"),
           "exp_table": pd.read_csv(MODELS / "experiment_table.csv"),
           "log": pd.read_csv(EXPERIMENTS / "log.csv"),
           "shap": {c: pd.read_parquet(MODELS / f"shap_{c}.parquet") for c in ("corn", "soy")},
           "diversity": j("diversity_check.json") if (MODELS / "diversity_check.json").exists() else None}
    return out


@st.cache_resource
def final_models():
    out = {}
    for c in ("corn", "soy"):
        with open(MODELS / f"{c}_final.pkl", "rb") as fh:
            out[c] = pickle.load(fh)
    return out


@st.cache_data
def county_daily(fips):
    return pd.read_parquet(POWER_DAILY, filters=[("fips", "==", fips)])


@st.cache_data
def context():
    c = {"ndvi": pd.read_parquet(PROCESSED / "ndvi_demo.parquet") if (PROCESSED / "ndvi_demo.parquet").exists() else None,
         "usdm": pd.read_parquet(PROCESSED / "usdm_county.parquet"),
         "rma": pd.read_parquet(PROCESSED / "rma_col_iowa.parquet"),
         "spc": json.loads((PROCESSED / "spc_20200810.json").read_text()),
         "ssurgo": json.loads((PROCESSED / "ssurgo_demo.json").read_text()),
         "sources": pd.read_csv(DATA / "sources.csv"),
         "calendar": rot.load_calendar(), "traits": rot.load_traits()}
    return c


@st.cache_data
def scenario(fips, d_temp, d_rain):
    """Replay every season for the county with shifted temperature and scaled rain, clip to the supported
    range, and predict with the final models. Soil wetness and ET are NOT re-simulated (stated limitation)."""
    mods = {k: v["model"] for k, v in final_models().items()}
    return scen.run(county_daily(fips), d_temp, d_rain, mods, load_model_outputs()["ranges"])


def engine(fips, sliders, clim):
    c = context()
    stress = rot.load_stress()
    cc = clim[clim.fips == fips]
    raw = rot.raw_metrics(cc, stress, c["calendar"], c["traits"])
    crit, excluded = rot.criteria(raw, c["traits"])
    lam, note = rot.criterion_weights(sliders, excluded)
    scores = rot.score(crit, lam)
    return raw, crit, excluded, lam, note, scores, stress


# ---------------------------------------------------------------- sidebar
counties, geo, feats, yields, clim = load_static()
names = counties.set_index("fips").county.to_dict()
st.sidebar.title("🌱 RotateWise")
if st.sidebar.button("Reset to defaults"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()
fips = st.sidebar.selectbox("County (Iowa)", list(names), index=list(names).index(DEMO),
                            format_func=lambda f: f"{names[f]} County" + (" (demo)" if f == DEMO else ""), key="fips")
current = st.sidebar.selectbox("Current rotation", ["Corn → soybean", "Continuous corn", "Other"], key="current")
if current != "Corn → soybean":
    st.sidebar.warning("Only a corn → soybean starting rotation is supported in this prototype.")
st.sidebar.subheader("What matters most to you?")
sliders = {k: st.sidebar.slider(lbl, 0, 5, 3, key=f"w_{k}") for k, lbl in rot.SLIDER_LABELS.items()}
st.sidebar.subheader("What if the weather shifts?")
d_temp = st.sidebar.slider("Temperature change (°C)", *TEMP_RANGE, 0.0, 0.5, key="dt",
                           help="Limited to roughly the range the model was trained on.")
d_rain = st.sidebar.slider("Rainfall change (%)", *RAIN_RANGE, 0, 5, key="dp")
st.sidebar.caption(FOOTER)

mo = load_model_outputs()
ctx = context()
raw, crit, excluded, lam, wnote, scores, stress = engine(fips, sliders, clim)
base_s, scen_s = scenario(fips, 0.0, 0), scenario(fips, d_temp, d_rain)
scen_change = {c: float(np.mean(scen_s[c])) for c in CROP_KEY}
base_change = {c: float(np.mean(base_s[c])) for c in CROP_KEY}
cards = rot.cards(raw, crit, excluded, scores, ctx["traits"], scenario=scen_change, county=names[fips],
                  stress=stress, calendar=ctx["calendar"])

st.title(f"Crop-rotation options for {names[fips]} County, Iowa")
st.caption("For a central-Iowa farmer and their county extension agent, deciding which rotation to explore with "
           "local experts. Built on NASA POWER (2000-2025), NASA MODIS, USDA NASS yields and cited extension research.")

tabs = st.tabs(["🗺️ Field", "📅 Risk calendar", "🔄 Rotations", "🧪 Model & evidence", "⚠️ Failures", "📘 Science"])

# ---------------------------------------------------------------- 1 Field
with tabs[0]:
    c1, c2 = st.columns([3, 2])
    with c1:
        metric = st.radio("Map layer", ["Mean |corn anomaly| (%)", "Jul-Aug heat-day trend (days/decade)",
                                        "August root-zone wetness trend (per decade)"], horizontal=True)
        y = yields[yields.crop == "corn"].dropna(subset=["yield_bu_ac"])
        from src.detrend import fit_trends
        an = anomalies(y, fit_trends(y, sorted(y.year.unique())))
        tbl = an.groupby("fips").anom_pct.apply(lambda s: s.abs().mean()).rename("Mean |corn anomaly| (%)").to_frame()
        for col, name in (("heat_days_jul_aug", "Jul-Aug heat-day trend (days/decade)"),
                          ("gwetroot_aug_mean", "August root-zone wetness trend (per decade)")):
            tbl[name] = feats.groupby("fips").apply(lambda g: np.polyfit(g.year, g[col], 1)[0] * 10, include_groups=False)
        tbl = tbl.reset_index()
        # Plotly is bundled with Streamlit, so the map draws with no network (no basemap tiles)
        tbl = tbl.merge(counties[["fips", "county"]], on="fips")
        fig = px.choropleth(tbl, geojson=geo, locations="fips", featureidkey="properties.fips", color=metric,
                            hover_name="county", color_continuous_scale="RdBu" if "wetness" in metric else "YlOrRd")
        fig.add_choropleth(geojson=geo, locations=[fips], z=[1], featureidkey="properties.fips", showscale=False,
                           colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                           marker_line_color="#111", marker_line_width=3, hoverinfo="skip")
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0),
                          coloraxis_colorbar=dict(title=None, orientation="h", y=-0.05))
        st.plotly_chart(fig, width="stretch", config={"topojsonURL": "app/static/"})  # local copy, see static/
        st.caption("Each county is one NASA POWER point at its centre (about 50 km grid, 62 distinct cells for 99 "
                   "counties). The tool describes county-scale conditions around your field, not the field itself.")
    with c2:
        st.subheader("County at a glance")
        f = feats[feats.fips == fips]
        a = an[an.fips == fips]
        st.metric("Corn yield anomaly in 2012 (vs trend)", f"{a[a.year == 2012].anom_pct.mean():+.0f}%")
        st.metric("Average July high (2000-2025)", f"{f.jul_tmax_mean.mean():.1f} °C")
        st.metric("Average Jul-Aug days above 30 °C", f"{f.heat_days_jul_aug.mean():.0f}")
        top = rot.rank(scores)[0]
        st.metric("Best match for your priorities", rot.STRATEGIES[top]["name"], f"score {scores[top]:.2f} (0-1)",
                  delta_color="off")
        if fips == DEMO:
            s = ctx["ssurgo"]
            st.subheader("Soil (SSURGO, county-wide)")
            st.write(f"Surface organic matter about **{s['surface_organic_matter_pct_area_weighted']}%** "
                     f"(area-weighted). Drainage: " + ", ".join(f"{k.lower()} {v:.0f}%" for k, v in
                                                                list(s["drainage_class_pct_of_area"].items())[:3]) + ".")
            st.write("Slope: " + ", ".join(f"{k} {v:.0f}%" for k, v in s["slope_class_pct_of_area"].items()) + " of area.")
            st.caption(f"Source: {s['source']}, retrieved {s['retrieved']}. Descriptive only; your field may differ.")
        else:
            st.info("The soil panel is available for the demo county (Story) only.")
    footer()

# ---------------------------------------------------------------- 2 Risk calendar
with tabs[1]:
    cc = clim[clim.fips == fips].sort_values("month")
    st.subheader("How often each risk shows up, by month (share of years, 2000-2025)")
    risk = pd.DataFrame({"Frost (≥1 night ≤ 0 °C)": cc.frost_freq.values, "Heat stress (≥3 days > 30 °C)": cc.heat_freq.values,
                         "Dry spell (≥10 days < 1 mm)": cc.dry_spell_freq.values,
                         "Heavy rain (≥1 day > 25 mm)": cc.heavy_rain_freq.values,
                         "Water deficit (rain < ET)": cc.deficit_freq.values}, index=MONTH_NAMES).T
    fig = px.imshow(risk, color_continuous_scale="YlOrRd", zmin=0, zmax=1, aspect="auto", text_auto=".0%",
                    labels=dict(color="share of years"))
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption("Each cell is the share of years in which that month had the condition (NASA POWER, county centre). "
               "ET = evapotranspiration.")
    st.subheader("When the model says weather matters most")
    wdf = pd.DataFrame({"month": [MONTH_NAMES[m - 1] for m in range(4, 11)],
                        "corn": [stress["corn"][m] for m in range(4, 11)],
                        "soybean": [stress["soybean"][m] for m in range(4, 11)]}).melt("month", var_name="crop", value_name="weight")
    st.plotly_chart(px.bar(wdf, x="month", y="weight", color="crop", barmode="group", height=280,
                           labels={"weight": "share of model's attention (sums to 1)"}), width="stretch")
    st.caption("Month weights from the final model's SHAP values, spread over each feature's months.")
    st.subheader("When the soil is covered, by strategy")
    rows = []
    for k in rot.STRATEGIES:
        cover, crit_ = rot.year_arrays(k, ctx["calendar"])
        for i, arr in enumerate(cover):
            for mi, v in enumerate(rot.monthly(arr)):
                rows.append({"row": f"{k} · year {i + 1} ({rot.STRATEGIES[k]['years'][i]['grain']})",
                             "month": MONTH_NAMES[mi], "cover": v})
    cv_ = pd.DataFrame(rows).pivot(index="row", columns="month", values="cover")[MONTH_NAMES]
    fig = px.imshow(cv_, color_continuous_scale=[[0, "#c8a97e"], [1, "#3d8b4f"]], zmin=0, zmax=1, aspect="auto",
                    labels=dict(color="share of month covered"))
    fig.update_layout(height=330, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    est = ctx["calendar"][ctx["calendar"].verified == "N"]
    st.caption("Brown = bare soil. Grain dates are typical Iowa timing from NASS Crop Progress (2000-2019 medians); "
               "rye and clover follow cited rules. ⚠️ Estimated timing (no source): "
               + "; ".join(f"{r.crop} {r.event}" for r in est.itertuples())
               + ". All dates vary by year and field; actual timing is a local decision.")
    footer()

# ---------------------------------------------------------------- 3 Rotations
with tabs[2]:
    st.subheader("Three strategies, ranked for your priorities")
    if wnote:
        st.info(wnote)
    st.caption("A transparent weighted score from the model's stress months, the crop calendar, county rain data "
               "and cited sources. It is **not** a predicted yield for each strategy.")
    cdf = pd.DataFrame([{"strategy": f"{k}: {rot.STRATEGIES[k]['name']}", "criterion": c, "score": v}
                        for k in crit for c, v in crit[k].items() if v is not None])
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(cdf, x="criterion", y="score", color="strategy", barmode="group", height=380,
                           labels={"score": "0 = worst of the three, 1 = best"})
                    .update_layout(legend=dict(orientation="h", y=-0.35, x=0, title=None)), width="stretch")
    sens = rot.weight_sensitivity(crit, excluded)
    sdf = pd.DataFrame([{"strategy": k, "share of priority mixes where it ranks first": v["share_first"],
                         "rank range": f"{v['rank_min']}-{v['rank_max']}"} for k, v in sens.items()])
    c2.plotly_chart(px.bar(sdf, x="strategy", y="share of priority mixes where it ranks first", height=320,
                           hover_data=["rank range"], range_y=[0, 1]), width="stretch")
    c2.caption("The ranking depends on your priorities; here is how much. 2,000 random priority mixes "
               "(Dirichlet(1,1,1,1) over the four sliders).")
    if excluded:
        st.warning("Not scored for lack of sourced data: " + "; ".join(f"{k} ({v})" for k, v in excluded.items())
                   + ". Their slider weight goes to the remaining criteria.")
    weights_txt = ", ".join(f"{c} {w:.0%}" for c, w in lam.items() if w > 0)
    st.caption(f"Current criterion weights: {weights_txt}.")
    for card in cards:
        k = card["strategy_id"]
        head = f"{'⭐ ' if card['rank'] == 1 else ''}#{card['rank']} {card['name']} · score {card['score']:.2f}"
        with st.expander(head, expanded=card["rank"] == 1):
            st.markdown(f"**Why suggested.** {card['why_suggested']}")
            a1, a2 = st.columns(2)
            a1.markdown("**Evidence**\n" + "\n".join(f"- {e['claim']}: **{e['value']}** ({e['metric']}; {e['data_source_id']})"
                                                     for e in card["evidence"]))
            a1.markdown("**Possible benefits**\n" + "\n".join(f"- {b}" for b in card["benefits"]))
            a2.markdown("**Information gaps**\n" + "\n".join(f"- {g}" for g in card["information_gaps"]))
            a2.markdown("**Risks needing local review**\n" + "\n".join(f"- {r}" for r in card["risks_needing_local_review"]))
            tc = card["trait_coverage"]
            st.caption(f"Modelled years: {card['modeled_years']} of {card['cycle_years']} in the cycle"
                       + (f" ({card['not_modeled_years']} not modelled: oats/clover year)" if card["not_modeled_years"] else "")
                       + f" · Traits sourced: {tc['sourced']} of {tc['total']} · {tc['unverified']} not yet verified "
                         "by a human (expert rating, needs local review) · Sources: " + ", ".join(card["sources"]))
            st.markdown(f"**{card['support_line']}**")
            if st.button("Explain in plain language", key=f"explain_{k}"):
                text, src = explain(card)
                st.info(text)
                st.caption("Gemini, checked: every number appears in the card above." if src == "gemini"
                           else "Template summary (no Gemini key, API unavailable, or output failed the number check).")
    with st.expander("Robustness: calendar shifts and the expert rating"):
        cs = rot.calendar_sensitivity(clim[clim.fips == fips], stress, ctx["calendar"], ctx["traits"], sliders)
        st.dataframe(pd.DataFrame([{"shift all windows (days)": d, "ranking": " > ".join(v["ranking"]),
                                    **{f"exposure {k}": e for k, e in v["stress_exposure"].items()}}
                                   for d, v in cs.items()]), hide_index=True)
        ts = rot.trait_sensitivity(clim[clim.fips == fips], stress, ctx["calendar"], ctx["traits"], sliders)
        st.write("Rye extra field passes (expert rating) ±1: " + "; ".join(f"{p} passes → {' > '.join(r)}" for p, r in ts.items()))
    st.subheader("Scenario (modelled years only; does not change the ranking)")
    st.write(f"Replaying {scen_s['n_years']} seasons with **{d_temp:+.1f} °C** and **{d_rain:+d}% rain**: modelled corn "
             f"anomaly **{scen_change['corn']:+.1f}%** (vs {base_change['corn']:+.1f}% today), soybean "
             f"**{scen_change['soybean']:+.1f}%** (vs {base_change['soybean']:+.1f}%). "
             f"90% interval per season: ±{mo['conf']['corn']['halfwidth_pct']:.0f} pts (corn), "
             f"±{mo['conf']['soy']['halfwidth_pct']:.0f} pts (soybean).")
    if scen_s["clipped_values"]:
        st.warning(f"{scen_s['clipped_values']} feature values fell outside the range the model was trained on and "
                   "were clipped to it, so the response is capped there.")
    st.caption("Soil wetness and evapotranspiration are not re-simulated under the scenario, so drought effects are "
               "likely understated. Oats, rye and clover are not modelled.")
    footer()

# ---------------------------------------------------------------- 4 Model & evidence
with tabs[3]:
    crop = st.radio("Crop", ["corn", "soy"], horizontal=True, format_func=lambda c: {"corn": "Corn", "soy": "Soybean"}[c])
    met = mo["metrics"][crop]
    sel = met["selected_model"]
    st.markdown(f"**Selected model:** {met['selected_name']} ({sel}). Why: {met['selection_notes']['reason']}.")
    st.caption("Hindcast: features are season summaries known only after the season ends. Target = yield vs the "
               "county's trend, in %. Dev years 2000-2019 (leave-one-year-out CV); test years locked until one final run.")
    rows = []
    for k, lbl in (("M0", "M0 zero anomaly (trend)"), ("M1", "M1 persistence"), ("M2", "M2 3-feature ridge"), (sel, "Selected")):
        d = met["dev_cv"][k]
        t = met["test_expanding_trend"]["selected" if k == sel else k]
        rows.append({"model": lbl, "dev CV RMSE": d["rmse"], "dev 90% CI": d["boot"]["rmse"],
                     "test RMSE": t["rmse"], "test 90% CI": t["boot"]["rmse"], "test MAE": t["mae"],
                     "test skill vs M0": t.get("skill_vs_m0"), "test within-year Spearman": t["spearman_within_year"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("RMSE/MAE in percentage points of yield anomaly, averaged over years (the year is the unit of "
               "evidence). Intervals: 2,000 year-bootstrap draws. Test trend fit only on years before each test year.")
    tby = mo["test_by_year"]
    cvy = mo["cv_by_year"]
    yr = pd.concat([cvy[(cvy.crop == crop) & cvy.model_id.isin(["M0", "M2", sel])].assign(split="dev CV")
                    .rename(columns={"model_id": "model"}),
                    tby[(tby.crop == crop)].assign(split="test").replace({"model": {"selected": sel}})])
    st.plotly_chart(px.line(yr, x="year", y="rmse", color="model", line_dash="split", markers=True, height=330,
                            labels={"rmse": "RMSE (pct points)"}), width="stretch")
    c1, c2 = st.columns(2)
    sh = mo["shap"][crop]
    cols = [c for c in sh.columns if c not in ("fips", "year")]
    imp = sh[cols].abs().mean().sort_values()
    c1.plotly_chart(px.bar(x=imp.values, y=[LABELS.get(c, c) for c in imp.index], orientation="h", height=330,
                           labels={"x": "mean |effect| on anomaly (pct points)", "y": ""},
                           title="What drives the model (SHAP, all counties)"), width="stretch")
    feat = c2.selectbox("Dependence plot feature", cols, format_func=lambda c: LABELS.get(c, c))
    fx = feats.merge(sh[["fips", "year", feat]].rename(columns={feat: "effect"}), on=["fips", "year"])
    c2.plotly_chart(px.scatter(fx, x=feat, y="effect", opacity=0.3, height=330,
                               labels={feat: LABELS.get(feat, feat), "effect": "effect on anomaly (pct points)"}),
                    width="stretch")
    iv = met["intervals"]
    cov_test = met["test_expanding_trend"]["selected"].get("conformal_90_test_coverage")
    st.markdown(f"**Prediction interval:** ±{iv['conformal_90_halfwidth_pct']:.1f} pts (90% split-conformal). Coverage: "
                f"{iv['conformal_loyo_coverage_by_year_mean']:.0%} in dev (worst year {iv['conformal_worst_year_coverage']:.0%}), "
                f"{cov_test:.0%} on test years. Quantile-LightGBM alternative: {iv['quantile_lgbm_90_coverage']:.0%} coverage in dev.")
    g, p = met["train_vs_cv_gap"], met["placebo"]
    st.markdown(f"**Overfitting checks.** Train RMSE {g['train_rmse']:.2f} vs CV {g['cv_rmse']:.2f}. Placebo (weather "
                f"shuffled across years): {p['shuffled_rmse_mean']:.2f} vs real {p['real_rmse']:.2f} and M0 {p['m0_rmse']:.2f}. "
                f"Spatial block hold-out: {met['spatial_block']['rmse']:.2f}.")
    st.markdown("**Ablations (dev CV RMSE):** " + "; ".join(f"{k}: {v}" for k, v in met["ablations"].items()))
    with st.expander("Every model tried (experiment log)"):
        st.dataframe(mo["exp_table"][mo["exp_table"].crop == crop], hide_index=True)
    footer()

# ---------------------------------------------------------------- 5 Failures
with tabs[4]:
    st.subheader("2012 drought: a real held-out test")
    oof = mo["cv_oof"]
    o12 = oof[(oof.year == 2012) & (oof.model_id == mo["metrics"]["corn"]["selected_model"]) & (oof.crop == "corn")]
    s12 = o12[o12.fips == DEMO]
    st.write(f"Leave-one-year-out (2012 never seen in training): statewide corn anomaly predicted "
             f"**{o12.pred.mean():+.1f}%** vs actual **{o12.anom_pct.mean():+.1f}%**; Story County predicted "
             f"**{s12.pred.mean():+.1f}%** vs actual **{s12.anom_pct.mean():+.1f}%**.")
    u = ctx["usdm"].copy()
    u12 = u[u.week.dt.year.isin([2012, 2020])].assign(year=lambda d: d.week.dt.year.astype(str),
                                                       month=lambda d: d.week.dt.month + d.week.dt.day / 31)
    u12 = u12.melt(["year", "month"], ["d1", "d2", "d3"], var_name="category", value_name="pct").replace(
        {"category": {"d1": "D1+ moderate", "d2": "D2+ severe", "d3": "D3+ extreme"}})
    fig = px.line(u12, x="month", y="pct", color="category", facet_col="year", height=280,
                  labels={"pct": "% of Story County area", "month": "month"})
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption("US Drought Monitor (independent of NASA POWER): weekly share of Story County in each drought category.")
    nd = ctx["ndvi"]
    if nd is not None:
        nd = nd.dropna(subset=["value"]).assign(year=lambda d: d.date.dt.year, doy=lambda d: d.date.dt.day_of_year)
        nd["which"] = np.where(nd.year.isin([2012, 2020]), nd.year.astype(str), "other years")
        st.plotly_chart(px.line(nd.sort_values("date"), x="doy", y="value", color="which", line_group="year",
                                color_discrete_map={"2012": "#d62728", "2020": "#9467bd", "other years": "#c7c7c7"},
                                height=300, labels={"doy": "day of year", "value": "NDVI"},
                                title="NASA MODIS vegetation greenness (NDVI), Story County"), width="stretch")
        st.caption("MOD13Q1 v061, 250 m, 16-day composites, 3×3 km mean at the county centre. Lower peak NDVI = "
                   "stressed or damaged canopy.")
    st.subheader("2020 derecho: where the model fails")
    tp = mo["test_pred"]
    t20 = tp[(tp.year == 2020) & (tp.crop == "corn")]
    spc = ctx["spc"]
    st.write(f"Model on test year 2020: statewide corn predicted **{t20.pred_selected.mean():+.1f}%** vs actual "
             f"**{t20.anom_pct.mean():+.1f}%**; Story County predicted **{t20[t20.fips == DEMO].pred_selected.mean():+.1f}%** vs "
             f"actual **{t20[t20.fips == DEMO].anom_pct.mean():+.1f}%**. On 10 Aug 2020 NOAA SPC logged "
             f"{spc['wind_reports_iowa']} severe-wind reports in Iowa ({spc['story_county_reports']} in Story County; "
             f"highest reported {spc['max_speed_reported_mph_iowa']} mph). **The weather features do not capture wind "
             "damage**, so the model cannot see this loss.")
    r = ctx["rma"]
    r20 = r[(r.year.isin([2012, 2020])) & (r.crop == "corn")]
    st_ = pd.concat([r20[r20.fips == DEMO].assign(area="Story County"), r20.assign(area="Iowa")])
    agg = st_.groupby(["area", "year", "cause_group"]).indemnity.sum().reset_index()
    agg["indemnity ($M)"] = agg.indemnity / 1e6
    agg["year"] = agg.year.astype(str)
    st.plotly_chart(px.bar(agg, x="cause_group", y="indemnity ($M)", color="year", barmode="group", facet_col="area",
                           height=320).update_yaxes(matches=None), width="stretch")
    st.caption("USDA RMA cause-of-loss indemnities for corn (insurance claims, not measured yield loss).")
    st.subheader("Largest errors (test years, corn)")
    tp2 = tp[tp.crop == "corn"].assign(error=lambda d: d.pred_selected - d.anom_pct).merge(counties, on="fips")
    st.dataframe(tp2.reindex(tp2.error.abs().sort_values(ascending=False).index)[
        ["county", "year", "anom_pct", "pred_selected", "error"]].head(10).round(1), hide_index=True)
    footer()

# ---------------------------------------------------------------- 6 Science
with tabs[5]:
    st.markdown("""
**Evapotranspiration (ET):** water leaving the field by evaporation from soil plus transpiration through leaves.
**Water balance:** rain minus ET. Below zero means the crop is drawing on stored soil water.
**Soil moisture / root-zone wetness (GWETROOT):** how full the top metre of soil is, from 0 (dry) to 1 (saturated). NASA POWER takes it from the MERRA-2 model, not from a direct measurement.
**Anomaly vs trend:** yields rise every year with better seed and machinery. The *trend* is that steady rise for each county; the *anomaly* is how far one year fell above or below it, in %. The model learns weather's effect on the anomaly.
**NDVI:** a satellite greenness index from 0 to about 0.9; healthy summer corn is near 0.8-0.9. Drought and wind damage lower it.
**Frost risk:** the share of years with at least one night at or below 0 °C in that month.
**Heat-stress days:** days above 30 °C. Corn is most sensitive around silking in July.
**SHAP:** splits each prediction into how much each weather feature pushed it up or down.
**Nitrogen fixation:** legumes such as soybean and clover host bacteria that turn air nitrogen into plant nitrogen.
**Cover crop:** a crop grown to protect and feed the soil between cash crops, like cereal rye over winter.
**Deep-rooted crop:** roots that reach deeper soil layers, improving structure and water uptake.
""")
    st.subheader("Reanalysis vs satellite vs ground")
    st.markdown("""
| | What it is | Resolution | Strength | Limit |
|---|---|---|---|---|
| NASA POWER | Reanalysis (MERRA-2) plus satellite inputs | ~50 km | Daily, every county, back to the 1980s | Model-derived soil wetness; neighbouring counties share cells |
| NASA SMAP | Satellite microwave sensing, assimilated into a model (L4) | ~9 km | Measures surface soil moisture | Starts 2015; not used here yet (needs an Earthdata login) |
| NASA MODIS NDVI | Satellite greenness | 250 m | Shows real crop stress and damage | Clouds; not a yield |
| Field probe / weather station | Ground measurement | one point | Most accurate for that spot | Covers nothing else |
""")
    st.graphviz_chart("""digraph { rankdir=LR; node [shape=box, style=rounded];
      POWER [label="NASA POWER daily\\n(99 county centres)"]; NASS [label="USDA NASS yields\\n(county x year)"];
      GRID [label="county x month grid\\n→ season features"]; TREND [label="trend fit on earlier years\\n→ % anomaly"];
      MODEL [label="yield-anomaly model\\n(LOYO CV, locked test)"]; CAL [label="crop calendar\\n(NASS Crop Progress + cited rules)"];
      ROT [label="rotation scores\\n+ strategy cards"];
      POWER -> GRID -> MODEL; NASS -> TREND -> MODEL; MODEL -> ROT [label="stress months"]; CAL -> ROT; }""")
    st.subheader("Data and sources")
    st.dataframe(ctx["sources"], hide_index=True)
    st.subheader("Limitations")
    st.markdown("""
- Hindcast, not a forecast: it explains past weather stress; it does not predict this season.
- County scale, not field scale. Field soil, drainage and slope are information gaps.
- About 20 independent weather years for development and 6 test years: evidence, not proof.
- NASA POWER is partly modelled; GWETROOT is not a direct satellite measurement.
- Insurance losses (RMA) are claims, not measured yield loss.
- Rotation scores are a transparent heuristic from cited sources and calendar exposure, not a predicted yield for each strategy.
- Values marked *not yet verified* still need a human expert to confirm them.
""")
    footer()
