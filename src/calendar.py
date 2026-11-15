"""Vulnerability calendar inputs: county x month climatology and risk frequencies from NASA POWER.

Risk frequencies are the share of years in which a month had the condition:
  frost       at least one day with Tmin <= 0 C
  heat stress at least 3 days with Tmax > 30 C
  dry spell   a run of 10+ consecutive days with < 1 mm rain
  heavy rain  at least one day with > 25 mm rain
  deficit     monthly rain minus evapotranspiration < 0
`r_m` is the county's share of annual heavy-rain days falling in month m (used for erosion exposure).
By default only development years are used (spec B8); the app uses all years after the final test run.
"""
import numpy as np
import pandas as pd

from src.features import FROST_C, HEAT_C, HEAVY_RAIN_MM, LATENT_HEAT_MJ
from src.paths import POWER_DAILY, PROCESSED

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DRY_MM, DRY_RUN = 1.0, 10


def _longest_dry(s):
    run = best = 0
    for v in s:
        run = run + 1 if v < DRY_MM else 0
        best = max(best, run)
    return best


def county_month(daily, years=None):
    d = daily.copy()
    d["year"], d["month"] = d.date.dt.year, d.date.dt.month
    if years is not None:
        d = d[d.year.isin(years)]
    d["et_mm"] = d.evptrns / LATENT_HEAT_MJ
    g = d.groupby(["fips", "year", "month"])
    py = g.agg(tmax=("t2m_max", "mean"), tmin=("t2m_min", "mean"), prcp=("prectotcorr", "sum"), et=("et_mm", "sum"),
               gwetroot=("gwetroot", "mean"),
               frost_days=("t2m_min", lambda s: int((s <= FROST_C).sum())),
               heat_days=("t2m_max", lambda s: int((s > HEAT_C).sum())),
               heavy_days=("prectotcorr", lambda s: int((s > HEAVY_RAIN_MM).sum())),
               longest_dry=("prectotcorr", _longest_dry)).reset_index()
    py["water_balance"] = py.prcp - py.et
    py["frost"], py["heat"] = py.frost_days > 0, py.heat_days >= 3
    py["dry_spell"], py["heavy"] = py.longest_dry >= DRY_RUN, py.heavy_days > 0
    py["deficit"] = py.water_balance < 0
    clim = py.groupby(["fips", "month"]).agg(
        **{f"{v}_mean": (v, "mean") for v in ("tmax", "tmin", "prcp", "et", "gwetroot", "water_balance", "heavy_days")},
        **{f"{v}_std": (v, "std") for v in ("tmax", "prcp", "gwetroot")},
        frost_freq=("frost", "mean"), heat_freq=("heat", "mean"), dry_spell_freq=("dry_spell", "mean"),
        heavy_rain_freq=("heavy", "mean"), deficit_freq=("deficit", "mean")).reset_index()
    tot = clim.groupby("fips").heavy_days_mean.transform("sum")
    clim["r_m"] = np.where(tot > 0, clim.heavy_days_mean / tot, 1 / 12)
    return clim, py


def main():
    daily = pd.read_parquet(POWER_DAILY)
    dev, _ = county_month(daily, years=range(2000, 2020))
    dev.to_parquet(PROCESSED / "climatology_county_month.parquet", index=False)
    full, per_year = county_month(daily)
    full.to_parquet(PROCESSED / "climatology_county_month_all_years.parquet", index=False)
    per_year.to_parquet(PROCESSED / "county_month_by_year.parquet", index=False)
    print(dev[dev.fips == "19169"][["month", "frost_freq", "heat_freq", "dry_spell_freq", "heavy_rain_freq",
                                     "deficit_freq", "r_m"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
