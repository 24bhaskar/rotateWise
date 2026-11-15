"""D1/D6/D7/D8: USDA NASS QuickStats.

- county corn-grain and soybean yields 2000-latest (target), suppressed values kept as NaN
- county harvested acres of corn, soybeans, hay, oats, wheat, barley (diversity check)
- Census of Agriculture county cover-crop acres (2012, 2017, 2022)
- Iowa state-level weekly crop progress for corn, soybeans, oats (crop calendar)
"""
import os

import pandas as pd
import requests
from dotenv import load_dotenv

from src.paths import PROCESSED, RAW, ROOT

URL = "https://quickstats.nass.usda.gov/api/api_GET/"
YIELD_DESC = {"corn": "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE", "soy": "SOYBEANS - YIELD, MEASURED IN BU / ACRE"}
ACRE_DESC = {"corn": "CORN, GRAIN - ACRES HARVESTED", "soy": "SOYBEANS - ACRES HARVESTED",
             "hay": "HAY - ACRES HARVESTED", "oats": "OATS - ACRES HARVESTED",
             "wheat": "WHEAT - ACRES HARVESTED", "barley": "BARLEY - ACRES HARVESTED"}
COVER_DESC = "PRACTICES, LAND USE, CROPLAND, COVER CROP PLANTED, (EXCL CRP) - ACRES"


def get(key, **q):
    r = requests.get(URL, params={"key": key, "format": "JSON", **q}, timeout=300)
    if r.status_code == 400:  # QuickStats returns 400 when there are no matching rows
        return pd.DataFrame()
    r.raise_for_status()
    return pd.DataFrame(r.json()["data"])


def county_rows(df):
    if df.empty:
        return pd.DataFrame(columns=["fips", "county", "year", "value", "suppressed", "raw_value"])
    df = df[df["county_ansi"].str.strip() != ""]  # drop "OTHER (COMBINED) COUNTIES"
    val = pd.to_numeric(df["Value"].str.replace(",", ""), errors="coerce")
    return pd.DataFrame({"fips": df["state_fips_code"] + df["county_ansi"], "county": df["county_name"].str.title(),
                         "year": df["year"].astype(int), "value": val, "suppressed": val.isna(),
                         "raw_value": df["Value"].str.strip()})


def main():
    load_dotenv(ROOT / ".env")
    key = os.environ.get("NASS_API_KEY")
    if not key:
        raise SystemExit("NASS_API_KEY missing: add it to .env")
    base = dict(agg_level_desc="COUNTY", state_alpha="IA", year__GE=2000)

    ys = []
    for crop, desc in YIELD_DESC.items():
        d = county_rows(get(key, source_desc="SURVEY", short_desc=desc, reference_period_desc="YEAR", **base))
        ys.append(d.assign(crop=crop).rename(columns={"value": "yield_bu_ac"}))
    y = pd.concat(ys).drop_duplicates(["fips", "year", "crop"])
    y[["fips", "county", "crop", "year", "yield_bu_ac", "suppressed", "raw_value"]].to_parquet(
        PROCESSED / "yields.parquet", index=False)
    print(y.groupby("crop").agg(first=("year", "min"), last=("year", "max"), rows=("year", "size"),
                                suppressed=("suppressed", "sum")))

    acres = []
    for name, desc in ACRE_DESC.items():
        d = county_rows(get(key, source_desc="SURVEY", short_desc=desc, reference_period_desc="YEAR", **base))
        acres.append(d.assign(crop=name))
    a = pd.concat(acres).drop_duplicates(["fips", "year", "crop"])
    a.to_parquet(RAW / "nass_acres_long.parquet", index=False)
    w = a.pivot_table(index=["fips", "year"], columns="crop", values="value").reset_index()
    for c in ACRE_DESC:
        if c not in w:
            w[c] = float("nan")
    small = w[["oats", "wheat", "barley"]].sum(axis=1, min_count=1)
    w["small_grain_acres"] = small
    total = w[["corn", "soy", "hay", "oats", "wheat", "barley"]].sum(axis=1, min_count=1)
    w["share_diverse"] = w[["hay", "oats", "wheat", "barley"]].sum(axis=1, min_count=1) / total
    w.rename(columns={"hay": "hay_acres", "oats": "oats_acres"})[
        ["fips", "year", "hay_acres", "oats_acres", "small_grain_acres", "share_diverse"]].to_parquet(
        PROCESSED / "acreage_diversity.parquet", index=False)
    print(f"acreage rows: {len(w)}, years {w.year.min()}-{w.year.max()}")

    cc = []
    for yr in (2012, 2017, 2022):
        d = get(key, source_desc="CENSUS", short_desc=COVER_DESC, agg_level_desc="COUNTY", state_alpha="IA", year=yr)
        if len(d):
            cc.append(county_rows(d))
    cc = pd.concat(cc).rename(columns={"year": "census_year", "value": "cover_crop_acres"})
    cc[["fips", "census_year", "cover_crop_acres"]].to_parquet(PROCESSED / "cover_crop_census.parquet", index=False)
    print(f"cover-crop census rows: {len(cc)} years {sorted(cc.census_year.unique())}")

    prog = []
    for c in ("CORN", "SOYBEANS", "OATS"):
        d = get(key, source_desc="SURVEY", agg_level_desc="STATE", state_alpha="IA", commodity_desc=c,
                statisticcat_desc="PROGRESS", year__GE=2000, year__LE=2019)
        prog.append(pd.DataFrame({"crop": c.lower(), "year": d.year.astype(int), "short_desc": d.short_desc,
                                  "week_ending": pd.to_datetime(d.week_ending),
                                  "pct": pd.to_numeric(d.Value, errors="coerce")}))
    p = pd.concat(prog)
    p.to_parquet(PROCESSED / "crop_progress_ia.parquet", index=False)
    print(f"crop progress rows: {len(p)}; stages: {sorted(p.short_desc.unique())}")


if __name__ == "__main__":
    main()
