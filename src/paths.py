"""Shared file locations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
MODELS = ROOT / "models"

PROCESSED = DATA / "processed"
COUNTIES_GEOJSON = PROCESSED / "iowa_counties.geojson"
COUNTIES_CSV = PROCESSED / "iowa_counties.csv"
POWER_DAILY = PROCESSED / "power_daily.parquet"
YIELDS = PROCESSED / "yields.parquet"
FEATURES = PROCESSED / "features_county_year.parquet"
REPORTS = ROOT / "reports"
EXPERIMENTS = ROOT / "experiments"

for d in (DATA, RAW, MODELS, PROCESSED, REPORTS, EXPERIMENTS):
    d.mkdir(parents=True, exist_ok=True)
