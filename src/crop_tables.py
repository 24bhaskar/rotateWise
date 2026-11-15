"""Build data/crop_calendar.csv from NASS Crop Progress (S01) plus cited timing rules.

Corn, soybean and oat windows are computed: the median (2000-2019) week ending when Iowa reached
10% and 90% of a stage, and 50% as the typical date. Cereal rye and red clover are tied to those
dates by the rules in the cited documents. Rows with no source are labelled 'author estimate'.
Every row starts verified=pending_human (sourced) or N (estimate); only a human may set Y.
"""
import pandas as pd

from src.paths import DATA, PROCESSED

STAGES = {  # (crop, event): (short_desc stage for start, pct, stage for end, pct)
    ("corn", "planting"): ("CORN - PROGRESS, MEASURED IN PCT PLANTED", 10, "CORN - PROGRESS, MEASURED IN PCT PLANTED", 90),
    ("corn", "critical"): ("CORN - PROGRESS, MEASURED IN PCT SILKING", 10, "CORN - PROGRESS, MEASURED IN PCT DENTED", 50),
    ("corn", "harvest"): ("CORN, GRAIN - PROGRESS, MEASURED IN PCT HARVESTED", 10, "CORN, GRAIN - PROGRESS, MEASURED IN PCT HARVESTED", 90),
    ("soybean", "planting"): ("SOYBEANS - PROGRESS, MEASURED IN PCT PLANTED", 10, "SOYBEANS - PROGRESS, MEASURED IN PCT PLANTED", 90),
    ("soybean", "critical"): ("SOYBEANS - PROGRESS, MEASURED IN PCT SETTING PODS", 10, "SOYBEANS - PROGRESS, MEASURED IN PCT COLORING", 50),
    ("soybean", "harvest"): ("SOYBEANS - PROGRESS, MEASURED IN PCT HARVESTED", 10, "SOYBEANS - PROGRESS, MEASURED IN PCT HARVESTED", 90),
    ("oats", "planting"): ("OATS - PROGRESS, MEASURED IN PCT PLANTED", 10, "OATS - PROGRESS, MEASURED IN PCT PLANTED", 90),
    ("oats", "critical"): ("OATS - PROGRESS, MEASURED IN PCT HEADED", 10, "OATS - PROGRESS, MEASURED IN PCT COLORING", 50),
    ("oats", "harvest"): ("OATS - PROGRESS, MEASURED IN PCT HARVESTED", 10, "OATS - PROGRESS, MEASURED IN PCT HARVESTED", 90),
}
TYPICAL = {"planting": 50, "harvest": 50}


def median_date(p, desc, pct):
    g = p[p.short_desc == desc].sort_values("week_ending")
    first = g[g.pct >= pct].groupby("year").week_ending.first()
    doy = int(first.dt.day_of_year.median())
    return pd.Timestamp("2019-01-01") + pd.Timedelta(days=doy - 1)


def md(ts):
    return ts.strftime("%m-%d")


def main():
    p = pd.read_parquet(PROCESSED / "crop_progress_ia.parquet")
    rows, typ = [], {}
    for (crop, event), (s_desc, s_pct, e_desc, e_pct) in STAGES.items():
        start, end = median_date(p, s_desc, s_pct), median_date(p, e_desc, e_pct)
        mid = median_date(p, s_desc, 50) if event in TYPICAL else start + (end - start) / 2
        typ[(crop, event)] = (start, mid, end)
        rows.append({"crop": crop, "event": event, "start_month_day": md(start), "typical_month_day": md(mid),
                     "end_month_day": md(end), "source_id": "S01",
                     "rule": f"median 2000-2019 date Iowa reached {s_pct}% {s_desc.split('IN ')[-1].lower()} "
                             f"to {e_pct}% {e_desc.split('IN ')[-1].lower()}",
                     "verified": "pending_human"})
    day = pd.Timedelta(days=1)
    # cereal rye after corn (before soybean): seeded right after corn harvest (S05), terminated at or soon
    # after soybean planting (S04)
    ch, sp = typ[("corn", "harvest")], typ[("soybean", "planting")]
    rows.append({"crop": "cereal_rye_before_soy", "event": "seeding", "start_month_day": md(ch[0]),
                 "typical_month_day": md(ch[1]), "end_month_day": md(ch[2]), "source_id": "S05;S01",
                 "rule": "seed immediately after the corn harvest window", "verified": "pending_human"})
    rows.append({"crop": "cereal_rye_before_soy", "event": "termination", "start_month_day": md(sp[0]),
                 "typical_month_day": md(sp[1]), "end_month_day": md(sp[2]), "source_id": "S04;S01",
                 "rule": "terminate at or soon after soybean planting", "verified": "pending_human"})
    # cereal rye after soybean (before corn): seeded after soybean harvest, terminated >=14 days before corn planting
    sh, cp = typ[("soybean", "harvest")], typ[("corn", "planting")]
    rows.append({"crop": "cereal_rye_before_corn", "event": "seeding", "start_month_day": md(sh[0]),
                 "typical_month_day": md(sh[1]), "end_month_day": md(sh[2]), "source_id": "S05;S01",
                 "rule": "seed immediately after the soybean harvest window", "verified": "pending_human"})
    rows.append({"crop": "cereal_rye_before_corn", "event": "termination",
                 "start_month_day": md(cp[0] - 14 * day), "typical_month_day": md(cp[1] - 14 * day),
                 "end_month_day": md(cp[2] - 14 * day), "source_id": "S04;S01",
                 "rule": "terminate at least 10-14 days before corn planting (14 used)", "verified": "pending_human"})
    # red clover: interseeded with oats in March (S08); frost seeding mid-Feb to early March (S07)
    rows.append({"crop": "red_clover", "event": "seeding", "start_month_day": "02-15", "typical_month_day": "03-15",
                 "end_month_day": md(typ[("oats", "planting")][1]), "source_id": "S07;S08",
                 "rule": "frost seeded mid-Feb to early Mar, or seeded with oats in March", "verified": "pending_human"})
    rows.append({"crop": "red_clover", "event": "termination", "start_month_day": md(cp[0] - 14 * day),
                 "typical_month_day": md(cp[1] - 14 * day), "end_month_day": md(cp[2] - 14 * day),
                 "source_id": "none (author estimate)",
                 "rule": "assumed: terminated the next spring about 2 weeks before corn planting, like rye",
                 "verified": "N"})
    out = pd.DataFrame(rows)
    out.to_csv(DATA / "crop_calendar.csv", index=False)
    print(out.to_string())


if __name__ == "__main__":
    main()
