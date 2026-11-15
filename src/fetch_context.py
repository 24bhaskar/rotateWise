"""Failure-panel and soil context for the demo county (D9, D15, D16, D17).

- US Drought Monitor weekly drought categories, Story County, 2000-2025
- NOAA SPC wind reports for 10 Aug 2020 (the derecho)
- USDA RMA cause-of-loss (Summary of Business with month of loss), Iowa corn and soybeans, 2008-2025
- SSURGO (Soil Data Access) map-unit summary for Story County (descriptive only)
Causes of loss are matched by their published descriptions (layout as of 6/2/2022, field 13), not by guessed codes.
"""
import datetime as dt
import io
import json
import time
import zipfile

import pandas as pd
import requests

from src.paths import PROCESSED, RAW

FIPS, AREA = "19169", "IA169"
UA = {"User-Agent": "RotateWise hackathon prototype (research use)"}
RMA_URL = "https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/cause_of_loss/colsom_{y}.zip"
RMA_COLS = ["commodity_year", "state_code", "state_abbr", "county_code", "county_name", "commodity_code",
            "commodity_name", "plan_code", "plan_abbr", "coverage_category", "stage_code", "cause_code", "cause",
            "month", "month_name", "year_of_loss", "policies_earning", "policies_indemnified", "net_planted_qty",
            "net_endorsed_acres", "liability", "total_premium", "producer_premium", "subsidy", "state_subsidy",
            "additional_subsidy", "efa_discount", "net_determined_qty", "indemnity", "loss_ratio"]
CAUSE_GROUPS = {"drought": ["drought"], "heat": ["heat"], "wind": ["wind", "derecho", "hurricane", "tornado"],
                "hail": ["hail"], "excess moisture": ["excess moisture", "flood"]}


def usdm():
    url = "https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"
    rows = []
    for y in range(2000, 2026):
        r = requests.get(url, params={"aoi": FIPS, "startdate": f"1/1/{y}", "enddate": f"12/31/{y}",
                                      "statisticsType": 1}, headers={"Accept": "application/json", **UA}, timeout=120)
        r.raise_for_status()
        rows += r.json()
        time.sleep(0.3)
    d = pd.DataFrame(rows)
    d = pd.DataFrame({"fips": d.fips, "week": pd.to_datetime(d.validStart),
                      **{c: d[c].astype(float) for c in ("none", "d0", "d1", "d2", "d3", "d4")}})
    d.drop_duplicates("week").sort_values("week").to_parquet(PROCESSED / "usdm_county.parquet", index=False)
    print(f"USDM: {len(d)} weeks")


def spc():
    url = "https://www.spc.noaa.gov/climo/reports/200810_rpts_wind.csv"
    d = pd.read_csv(io.StringIO(requests.get(url, headers=UA, timeout=60).text))
    d.to_csv(RAW / "spc_200810_wind.csv", index=False)
    ia = d[d.State == "IA"]
    meta = {"url": url, "page": "https://www.spc.noaa.gov/climo/reports/200810_rpts.html",
            "retrieved": dt.date.today().isoformat(), "wind_reports_total": len(d), "wind_reports_iowa": len(ia),
            "story_county_reports": int((ia.County.str.upper() == "STORY").sum()),
            "max_speed_reported_mph_iowa": None if ia.Speed.astype(str).str.isnumeric().sum() == 0
            else int(pd.to_numeric(ia.Speed, errors="coerce").max()),
            "summary": ("NOAA SPC logged hundreds of severe-wind reports on 10 August 2020, many across central "
                        "Iowa, as a fast-moving line of storms (a derecho) crossed the state.")}
    (PROCESSED / "spc_20200810.json").write_text(json.dumps(meta, indent=1))
    ia.to_parquet(PROCESSED / "spc_20200810_iowa.parquet", index=False)
    print(f"SPC: {meta}")


def rma(years=range(2008, 2026)):
    out = []
    for y in years:
        zp = RAW / f"colsom_{y}.zip"
        if not zp.exists():
            r = requests.get(RMA_URL.format(y=y), headers=UA, timeout=300)
            if r.status_code != 200:
                print(f"RMA {y}: HTTP {r.status_code}, skipped")
                continue
            zp.write_bytes(r.content)
        z = zipfile.ZipFile(zp)
        txt = z.read(z.namelist()[0]).decode("latin-1")
        d = pd.read_csv(io.StringIO(txt), sep="|", header=None, dtype=str)
        if d.shape[1] != len(RMA_COLS):
            raise ValueError(f"{y}: {d.shape[1]} columns, layout has {len(RMA_COLS)}")
        d.columns = RMA_COLS
        d = d[d.state_code.str.strip() == "19"]
        d["crop"] = d.commodity_name.str.strip().str.lower().map({"corn": "corn", "soybeans": "soy"})
        d = d.dropna(subset=["crop"])
        out.append(d)
        print(f"RMA {y}: {len(d)} Iowa corn/soy rows")
    d = pd.concat(out)
    d["fips"] = "19" + d.county_code.str.strip().str.zfill(3)
    d["cause"] = d.cause.str.strip()
    grp = d.cause.str.lower()
    d["cause_group"] = "other"
    for g, keys in CAUSE_GROUPS.items():
        d.loc[grp.str.contains("|".join(keys)), "cause_group"] = g
    for c in ("indemnity", "net_determined_qty"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    agg = (d.groupby(["fips", "commodity_year", "month", "crop", "cause", "cause_group"], as_index=False)
           .agg(indemnity=("indemnity", "sum"), loss_acres=("net_determined_qty", "sum")))
    agg = agg.rename(columns={"commodity_year": "year"})
    agg["year"] = agg.year.astype(int)
    agg["month"] = agg.month.astype(int)
    agg.to_parquet(PROCESSED / "rma_col_iowa.parquet", index=False)
    print(f"RMA saved {len(agg)} rows; cause groups: {sorted(agg.cause_group.unique())}")


def ssurgo():
    q = """SELECT mu.mukey, mu.muname, mu.muacres, c.compname, c.comppct_r, c.drainagecl, c.slope_r, ch.om_r
           FROM legend l JOIN mapunit mu ON mu.lkey = l.lkey
           JOIN component c ON c.mukey = mu.mukey AND c.majcompflag = 'Yes'
           LEFT JOIN chorizon ch ON ch.cokey = c.cokey AND ch.hzdept_r = 0
           WHERE l.areasymbol = 'IA169'"""
    r = requests.post("https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest",
                      json={"query": q, "format": "JSON+COLUMNNAME"}, headers=UA, timeout=180)
    r.raise_for_status()
    t = r.json()["Table"]
    d = pd.DataFrame(t[1:], columns=t[0])
    for c in ("muacres", "comppct_r", "slope_r", "om_r"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["acres"] = d.muacres * d.comppct_r / 100
    tot = d.acres.sum()
    drain = (d.groupby("drainagecl").acres.sum() / tot * 100).round(1).sort_values(ascending=False)
    slope = pd.cut(d.slope_r, [-0.1, 2, 5, 9, 100], labels=["0-2%", "2-5%", "5-9%", ">9%"])
    out = {"county": "Story County, Iowa (IA169)", "source": "USDA-NRCS Soil Data Access (SSURGO)",
           "url": "https://sdmdataaccess.sc.egov.usda.gov/", "retrieved": dt.date.today().isoformat(),
           "major_component_acres": round(float(tot)),
           "drainage_class_pct_of_area": drain.to_dict(),
           "surface_organic_matter_pct_area_weighted": round(float((d.om_r * d.acres).sum() / d.acres[d.om_r.notna()].sum()), 2),
           "slope_class_pct_of_area": (d.groupby(slope, observed=True).acres.sum() / tot * 100).round(1).to_dict(),
           "top_map_units": d.groupby("muname").acres.sum().nlargest(5).round().to_dict(),
           "note": "Descriptive only; county-wide summary of major components, not a field-level soil test."}
    (PROCESSED / "ssurgo_demo.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def main():
    for f in (ssurgo, spc, usdm, rma):
        try:
            f()
        except Exception as e:
            print(f"{f.__name__} FAILED: {e!r}")


if __name__ == "__main__":
    main()
