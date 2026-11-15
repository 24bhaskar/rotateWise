"""D11 MODIS NDVI (MOD13Q1 v061, 250 m, 16-day) at the Story County centroid via the ORNL DAAC web service.

D12 SMAP L4 needs NASA Earthdata credentials (EARTHDATA_USERNAME/PASSWORD or EARTHDATA_TOKEN); without them
this step records the blocker and stops. No SMAP values are ever invented.
"""
import os
import time

import pandas as pd
import requests

from src.paths import COUNTIES_CSV, PROCESSED, RAW

BASE = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
HDR = {"Accept": "application/json", "User-Agent": "RotateWise hackathon prototype (research use)"}
SCALE = 0.0001  # MOD13Q1 NDVI scale factor


def get(url, params, retries=5):
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=HDR, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"  retry {i + 1}: {e!r}")
            time.sleep(10 * (i + 1))


def modis(fips="19169"):
    c = pd.read_csv(COUNTIES_CSV, dtype={"fips": str}).set_index("fips").loc[fips]
    cache = RAW / f"modis_ndvi_{fips}.parquet"
    dates = [d["modis_date"] for d in get(f"{BASE}/dates", {"latitude": c.lat, "longitude": c.lon})["dates"]]
    # growing season only (day 90-310), failure years first; the service is slow (~30-60 s per request)
    dates = [d for d in dates if "A2000" <= d < "A2026" and 90 <= int(d[5:]) <= 310]
    have = pd.read_parquet(cache) if cache.exists() else pd.DataFrame()
    rows = have.to_dict("records")
    done = set(have.modis_date) if len(have) else set()
    order = [2012, 2020, 2011, 2013, 2019, 2021] + list(range(2000, 2026))
    chunks = []
    for yr in dict.fromkeys(order):
        todo = [d for d in dates if d[1:5] == str(yr) and d not in done]
        chunks += [todo[i:i + 10] for i in range(0, len(todo), 10)]  # at most 10 dates per request
    for chunk in chunks:
        j = get(f"{BASE}/subset", {"latitude": c.lat, "longitude": c.lon, "band": "250m_16_days_NDVI",
                                   "startDate": chunk[0], "endDate": chunk[-1], "kmAboveBelow": 1, "kmLeftRight": 1})
        for s in j["subset"]:
            px = [v for v in s["data"] if v > -3000]  # fill value -3000
            rows.append({"modis_date": s["modis_date"], "date": s["calendar_date"],
                         "value": sum(px) / len(px) * SCALE if px else None})
        pd.DataFrame(rows).to_parquet(cache, index=False)
        time.sleep(0.5)
    write_processed(pd.DataFrame(rows))


def write_processed(rows=None, fips="19169"):
    """Publish whatever is cached (the download can be resumed later)."""
    d = rows if rows is not None else pd.read_parquet(RAW / f"modis_ndvi_{fips}.parquet")
    d = d.drop_duplicates("modis_date")
    d["date"] = pd.to_datetime(d.date)
    d = d.assign(product="MOD13Q1 v061 NDVI, 3x3 km box mean at county centroid", units="NDVI (unitless)")
    d.sort_values("date")[["date", "value", "product", "units"]].to_parquet(PROCESSED / "ndvi_demo.parquet", index=False)
    print(f"MODIS NDVI: {len(d)} composites {d.date.min():%Y-%m-%d} to {d.date.max():%Y-%m-%d}")


def smap():
    if not (os.environ.get("EARTHDATA_TOKEN") or os.environ.get("EARTHDATA_USERNAME")):
        print("SMAP skipped: no Earthdata credentials (see reports/human_todo.md)")
        return
    raise NotImplementedError("SMAP L4 download via earthaccess: add once credentials are available")


if __name__ == "__main__":
    modis()
    smap()
