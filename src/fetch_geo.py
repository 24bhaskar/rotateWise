"""D3: Census cartographic county boundaries (TIGER/GENZ 2023, 1:500k), Iowa only.

Centroids are computed in an equal-area projection (EPSG:5070) and converted back to lat/lon.
"""
import io
import zipfile

import geopandas as gpd
import requests

from src.paths import COUNTIES_CSV, COUNTIES_GEOJSON, RAW

URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"


def main():
    zpath = RAW / "cb_2023_us_county_500k.zip"
    if not zpath.exists():
        zpath.write_bytes(requests.get(URL, timeout=300).content)
    zdir = RAW / "cb_2023_us_county_500k"
    zipfile.ZipFile(io.BytesIO(zpath.read_bytes())).extractall(zdir)
    g = gpd.read_file(next(zdir.glob("*.shp")))
    g = g[g.STATEFP == "19"].copy()
    g["fips"] = g.STATEFP + g.COUNTYFP
    cent = g.to_crs(5070).centroid.to_crs(4326)
    g["lat"], g["lon"] = cent.y.round(4), cent.x.round(4)
    g = g.rename(columns={"NAME": "county"}).sort_values("fips")
    assert len(g) == 99, len(g)
    g[["fips", "county", "lat", "lon"]].to_csv(COUNTIES_CSV, index=False)
    g[["fips", "county", "geometry"]].to_file(COUNTIES_GEOJSON, driver="GeoJSON")
    print(f"saved {len(g)} counties")


if __name__ == "__main__":
    main()
