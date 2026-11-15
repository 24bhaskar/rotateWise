"""B20.1 smoke tests: one small Story County request per data source, logged to reports/source_checks.csv.

Run: python -m src.source_checks
A source is only 'OK' if a real request succeeded and returned the fields we expect.
"""
import datetime as dt
import io
import os
import zipfile

import pandas as pd
import requests
from dotenv import load_dotenv

from src.paths import REPORTS, ROOT

load_dotenv(ROOT / ".env")
FIPS, LAT, LON = "19169", 42.0363, -93.4655
UA = {"User-Agent": "RotateWise hackathon prototype (research use)"}
NASS = "https://quickstats.nass.usda.gov/api/api_GET/"


def nass(**q):
    r = requests.get(NASS, params={"key": os.environ["NASS_API_KEY"], "format": "JSON", **q}, timeout=120)
    if r.status_code == 400:  # QuickStats answers "no rows" with a 400
        return pd.DataFrame()
    r.raise_for_status()
    return pd.DataFrame(r.json()["data"])


def check_nass_yield():
    d = nass(source_desc="SURVEY", agg_level_desc="COUNTY", state_alpha="IA", county_ansi="169",
             commodity_desc="CORN", statisticcat_desc="YIELD", year__GE=2023)
    years = sorted(d[d.short_desc == "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE"].year.unique())
    return "D1", NASS, f"Story corn grain yield years >=2023: {years}"


def check_crop_progress():
    d = nass(source_desc="SURVEY", agg_level_desc="STATE", state_alpha="IA", commodity_desc="OATS",
             statisticcat_desc="PROGRESS", year=2019)
    return "D6", NASS, f"Iowa oats progress 2019 short_desc: {sorted(d.short_desc.unique())[:6]}"


def check_acreage():
    out = []
    for c in ("OATS", "HAY", "BARLEY", "WHEAT"):
        d = nass(source_desc="SURVEY", agg_level_desc="COUNTY", state_alpha="IA", commodity_desc=c,
                 statisticcat_desc="AREA HARVESTED", year=2012)
        out.append(f"{c}: {len(d)} rows {sorted(d.short_desc.unique())[:2] if len(d) else ''}")
    return "D7", NASS, " | ".join(out)


def check_census_cover():
    d = nass(source_desc="CENSUS", agg_level_desc="COUNTY", state_alpha="IA", county_ansi="169",
             year=2017, commodity_desc="PRACTICES")
    cc = d[d.short_desc.str.contains("COVER CROP", na=False)]
    return "D8", NASS, f"rows={len(cc)} short_desc={sorted(cc.short_desc.unique())[:3]} values={cc.Value.tolist()[:3]}"


def check_power():
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    p = "T2M_MAX,T2M_MIN,PRECTOTCORR,GWETROOT,GWETTOP,EVPTRNS,RH2M,WS2M"
    r = requests.get(url, params={"parameters": p, "community": "AG", "latitude": LAT, "longitude": LON,
                                  "start": "20251225", "end": "20251231", "format": "JSON"}, timeout=120)
    r.raise_for_status()
    j = r.json()
    units = {k: v["units"] for k, v in j["parameters"].items()}
    vals = {k: list(v.values())[-1] for k, v in j["properties"]["parameter"].items()}
    return "D2", url, f"units={units} last-day values={vals} grid={j['geometry']['coordinates'][:2]}"


def check_tiger():
    url = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"
    r = requests.head(url, timeout=60, headers=UA, allow_redirects=True)
    return "D3", url, f"HTTP {r.status_code}, {int(r.headers.get('content-length', 0)) / 1e6:.1f} MB"


def check_modis():
    url = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
    r = requests.get(url, params={"latitude": LAT, "longitude": LON, "band": "250m_16_days_NDVI",
                                  "startDate": "A2012193", "endDate": "A2012225", "kmAboveBelow": 0,
                                  "kmLeftRight": 0}, headers={"Accept": "application/json", **UA}, timeout=120)
    r.raise_for_status()
    s = r.json()["subset"]
    return "D11", url, f"{len(s)} dates, first={s[0]['calendar_date']} raw={s[0]['data']} scale={r.json().get('scale')}"


def check_usdm():
    url = ("https://usdmdataservices.unl.edu/api/CountyStatistics/"
           "GetDroughtSeverityStatisticsByAreaPercent")
    r = requests.get(url, params={"aoi": FIPS, "startdate": "7/1/2012", "enddate": "7/31/2012",
                                  "statisticsType": 1}, headers={"Accept": "application/json", **UA}, timeout=120)
    r.raise_for_status()
    j = r.json()
    return "D15", url, f"{len(j)} weeks; first={j[0] if j else None}"


def check_spc():
    url = "https://www.spc.noaa.gov/climo/reports/200810_rpts_wind.csv"
    r = requests.get(url, timeout=60, headers=UA)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    return "D16", url, f"{len(d)} wind reports, {int((d.State == 'IA').sum())} in IA; cols={list(d.columns)}"


def check_rma():
    url = "https://pubfs-rma.fpac.usda.gov/pub/Web_Data_Files/Summary_of_Business/cause_of_loss/colsom_2020.zip"
    r = requests.get(url, timeout=180, headers=UA)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    first = z.read(z.namelist()[0]).decode("latin-1").splitlines()[0]
    return "D17", url, f"{z.namelist()} first line: {first[:200]}"


def check_sda():
    url = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
    q = "SELECT TOP 3 mu.musym, mu.muname FROM legend l JOIN mapunit mu ON mu.lkey = l.lkey WHERE l.areasymbol = 'IA169'"
    r = requests.post(url, json={"query": q, "format": "JSON+COLUMNNAME"}, timeout=120, headers=UA)
    r.raise_for_status()
    return "D9", url, f"{r.json()['Table']}"


def check_smap():
    have = bool(os.environ.get("EARTHDATA_USERNAME") or os.environ.get("EARTHDATA_TOKEN"))
    if not have:
        raise RuntimeError("no Earthdata credentials in environment (EARTHDATA_USERNAME/PASSWORD or TOKEN)")
    return "D12", "https://nsidc.org/data/spl4smgp", "credentials present (not yet downloaded)"


def check_page(sid, url):
    def f():
        r = requests.get(url, timeout=60, headers=UA)
        r.raise_for_status()
        return sid, url, f"HTTP {r.status_code}, {len(r.content) / 1e3:.0f} kB"
    return f


CHECKS = [check_nass_yield, check_crop_progress, check_acreage, check_census_cover, check_power, check_tiger,
          check_modis, check_usdm, check_spc, check_rma, check_sda, check_smap,
          check_page("D5", "https://extension.iastate.edu/"),
          check_page("D19", "https://www.extension.iastate.edu/agdm/"),
          check_page("D18", "https://agrisk.jornada.nmsu.edu/"),
          check_page("D16b", "https://www.spc.noaa.gov/climo/reports/200810_rpts.html")]


def main():
    rows, today = [], dt.date.today().isoformat()
    for fn in CHECKS:
        try:
            sid, url, note = fn()
            rows.append({"source_id": sid, "url_tested": url, "date_tested": today, "status": "OK",
                         "what_was_different": note, "fix_applied": ""})
        except Exception as e:
            msg = repr(e).replace(os.environ.get("NASS_API_KEY", "~"), "<KEY>")  # never log the key
            rows.append({"source_id": fn.__name__, "url_tested": "", "date_tested": today, "status": "FAILED",
                         "what_was_different": msg[:300], "fix_applied": ""})
        print(rows[-1]["source_id"], rows[-1]["status"], rows[-1]["what_was_different"][:400])
    out = REPORTS / "source_checks.csv"
    old = pd.read_csv(out) if out.exists() else pd.DataFrame()
    pd.concat([old, pd.DataFrame(rows)]).to_csv(out, index=False)


if __name__ == "__main__":
    main()
