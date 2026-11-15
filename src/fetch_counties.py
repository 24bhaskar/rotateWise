"""Download US county polygons, keep Iowa's 99 counties, and compute centroids."""
import json

import pandas as pd
import requests

from src.paths import COUNTIES_CSV, COUNTIES_GEOJSON

URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
IOWA_STATE_FIPS = "19"


def ring_centroid(ring):
    """Area-weighted centroid of a polygon ring (shoelace formula)."""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def main():
    geo = requests.get(URL, timeout=120).json()
    feats = [f for f in geo["features"] if f["properties"]["STATE"] == IOWA_STATE_FIPS]
    rows = []
    for f in feats:
        g = f["geometry"]
        ring = g["coordinates"][0] if g["type"] == "Polygon" else max(
            (p[0] for p in g["coordinates"]), key=len)
        lon, lat = ring_centroid([tuple(pt[:2]) for pt in ring])
        rows.append({"fips": f["id"], "county": f["properties"]["NAME"],
                     "county_code": f["properties"]["COUNTY"], "lat": round(lat, 4), "lon": round(lon, 4)})
    df = pd.DataFrame(rows).sort_values("fips")
    assert len(df) == 99, f"expected 99 Iowa counties, got {len(df)}"
    df.to_csv(COUNTIES_CSV, index=False)
    COUNTIES_GEOJSON.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    print(f"saved {len(df)} counties -> {COUNTIES_CSV.name}, {COUNTIES_GEOJSON.name}")


if __name__ == "__main__":
    main()
