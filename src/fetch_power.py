"""D2: NASA POWER daily data (AG community) at every Iowa county centroid, 2000-2025.

POWER blends MERRA-2 reanalysis with satellite inputs. GWETROOT/GWETTOP are model-derived
root-zone / surface soil wetness (0-1). Units confirmed by src.source_checks:
T2M_MAX/T2M_MIN C, PRECTOTCORR mm/day, EVPTRNS MJ/m2/day, RH2M %, WS2M m/s. Missing = -999.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests

from src.paths import COUNTIES_CSV, POWER_DAILY, RAW, REPORTS

PARAMS = ["T2M_MAX", "T2M_MIN", "PRECTOTCORR", "GWETROOT", "GWETTOP", "EVPTRNS", "RH2M", "WS2M"]
START, END = "20000101", "20251231"
URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
CACHE = RAW / "power_2000_2025"
CACHE.mkdir(parents=True, exist_ok=True)


def fetch_one(fips, lat, lon, retries=4):
    out = CACHE / f"{fips}.parquet"
    if out.exists():
        return out
    q = {"parameters": ",".join(PARAMS), "community": "AG", "latitude": lat, "longitude": lon,
         "start": START, "end": END, "format": "JSON"}
    for attempt in range(retries):
        try:
            r = requests.get(URL, params=q, timeout=300)
            r.raise_for_status()
            df = pd.DataFrame(r.json()["properties"]["parameter"])
            df.index = pd.to_datetime(df.index, format="%Y%m%d")
            df = df.replace(-999.0, np.nan).rename_axis("date").reset_index()
            df.columns = [c.lower() for c in df.columns]
            df.insert(0, "fips", fips)
            df.to_parquet(out, index=False)
            return out
        except Exception as e:  # network hiccups: back off and retry
            if attempt == retries - 1:
                raise
            print(f"  {fips}: retry {attempt + 1} after {e!r}")
            time.sleep(5 * (attempt + 1))


def main():
    counties = pd.read_csv(COUNTIES_CSV, dtype={"fips": str})
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(fetch_one, r.fips, r.lat, r.lon): r.fips for r in counties.itertuples()}
        for i, f in enumerate(as_completed(futs), 1):
            f.result()
            if i % 10 == 0:
                print(f"[{i}/{len(futs)}]")
    df = pd.concat(pd.read_parquet(p) for p in sorted(CACHE.glob("*.parquet")))
    df.to_parquet(POWER_DAILY, index=False)
    # POWER meteorology comes from the MERRA-2 grid (0.5 deg lat x 0.625 deg lon), so nearby
    # centroids can share a cell. Approximate the count by snapping centroids to that grid.
    cells = counties.assign(cell=(counties.lat / 0.5).round().astype(str) + "_" + (counties.lon / 0.625).round().astype(str))
    info = {"counties": len(counties), "approx_unique_merra2_cells": int(cells.cell.nunique()),
            "missing_values": {c: int(df[c].isna().sum()) for c in df.columns if c not in ("fips", "date")}}
    (REPORTS / "power_grid_cells.json").write_text(json.dumps(info, indent=1))
    print(f"saved {len(df):,} rows; {info}")


if __name__ == "__main__":
    main()
