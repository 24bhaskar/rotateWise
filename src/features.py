"""B8 features: NASA POWER daily data -> one feature vector per county x year.

Every window lies inside the target season (Apr 15 - Sep 30), so nothing after harvest leaks in.
This is a hindcast: the features are season summaries known only once the season has ended.
"""
import numpy as np
import pandas as pd

from src.paths import FEATURES, POWER_DAILY

HEAT_C = 30.0          # daily Tmax above which corn and soybean show heat stress
HEAVY_RAIN_MM = 25.0   # heavy-rain day threshold (fixed before modelling)
FROST_C = 0.0
LATENT_HEAT_MJ = 2.45  # EVPTRNS is MJ/m2/day; / 2.45 MJ/kg = mm/day of water evaporated

S0 = ["jul_tmax_mean", "precip_jun_aug", "gwetroot_aug_mean"]
S1 = S0 + ["heat_days_jul_aug", "water_balance_jja"]
S2 = S1 + ["gwetroot_jul_mean", "tmin_aug_mean", "spring_frost_days", "heavy_rain_days_mj", "gdd_season"]
FEATURE_SETS = {"S0": S0, "S1": S1, "S2": S2}
SOIL_MOISTURE = ["gwetroot_aug_mean", "gwetroot_jul_mean"]

# expected direction for corn and soybean (used for monotone constraints): -1 hurts, +1 helps, 0 unclear
EXPECTED_SIGN = {"jul_tmax_mean": -1, "heat_days_jul_aug": -1, "precip_jun_aug": 1, "precip_jul_aug": 1,
                 "gwetroot_aug_mean": 1, "gwetroot_jul_mean": 1, "water_balance_jja": 1, "tmin_aug_mean": -1,
                 "spring_frost_days": -1, "heavy_rain_days_mj": -1, "gdd_season": 0, "is_corn": 0}
# months each feature describes (feeds the stress profile, B11.3)
FEATURE_MONTHS = {"jul_tmax_mean": [7], "heat_days_jul_aug": [7, 8], "precip_jun_aug": [6, 7, 8],
                  "precip_jul_aug": [7, 8], "gwetroot_aug_mean": [8], "gwetroot_jul_mean": [7],
                  "water_balance_jja": [6, 7, 8], "tmin_aug_mean": [8], "spring_frost_days": [4, 5],
                  "heavy_rain_days_mj": [5, 6], "gdd_season": [5, 6, 7, 8, 9]}
LABELS = {"jul_tmax_mean": "July average high temperature", "heat_days_jul_aug": "Jul-Aug days above 30 °C",
          "precip_jun_aug": "Jun-Aug rainfall", "precip_jul_aug": "Jul-Aug rainfall",
          "gwetroot_aug_mean": "August root-zone soil wetness", "gwetroot_jul_mean": "July root-zone soil wetness",
          "water_balance_jja": "Jun-Aug rain minus evapotranspiration", "tmin_aug_mean": "August night temperature",
          "spring_frost_days": "late-spring frost days", "heavy_rain_days_mj": "May-Jun heavy-rain days",
          "gdd_season": "growing degree days (May-Sep)"}
MAX_MISSING_DAYS = 3


def _window(d, m0, d0, m1, d1):
    md = d["date"].dt.month * 100 + d["date"].dt.day
    return d[(md >= m0 * 100 + d0) & (md <= m1 * 100 + d1)]


def season_features(d):
    """d: daily rows for one county and one year."""
    jul, aug = d[d.date.dt.month == 7], d[d.date.dt.month == 8]
    jja = d[d.date.dt.month.isin([6, 7, 8])]
    ja = d[d.date.dt.month.isin([7, 8])]
    mj = d[d.date.dt.month.isin([5, 6])]
    frost = _window(d, 4, 15, 5, 31)
    season = d[d.date.dt.month.between(5, 9)]
    gdd = (season.t2m_max.clip(10, 30) + season.t2m_min.clip(10, 30)) / 2 - 10
    windows = {"jul": jul, "aug": aug, "jja": jja, "mj": mj, "frost": frost}
    missing = max(int(w.isna().any(axis=1).sum()) for w in windows.values())
    return {
        "jul_tmax_mean": jul.t2m_max.mean(),
        "heat_days_jul_aug": int((ja.t2m_max > HEAT_C).sum()),
        "precip_jun_aug": jja.prectotcorr.sum(),
        "precip_jul_aug": ja.prectotcorr.sum(),
        "gwetroot_aug_mean": aug.gwetroot.mean(),
        "gwetroot_jul_mean": jul.gwetroot.mean(),
        "water_balance_jja": jja.prectotcorr.sum() - (jja.evptrns / LATENT_HEAT_MJ).sum(),
        "tmin_aug_mean": aug.t2m_min.mean(),
        "spring_frost_days": int((frost.t2m_min <= FROST_C).sum()),
        "heavy_rain_days_mj": int((mj.prectotcorr > HEAVY_RAIN_MM).sum()),
        "gdd_season": gdd.sum(),
        "max_missing_days": missing,
        "flag_missing": missing > MAX_MISSING_DAYS,
    }


def build(daily):
    d = daily.copy()
    d["year"] = d.date.dt.year
    rows = [{"fips": f, "year": y, **season_features(g)} for (f, y), g in d.groupby(["fips", "year"])]
    return pd.DataFrame(rows)


def main():
    f = build(pd.read_parquet(POWER_DAILY))
    f.to_parquet(FEATURES, index=False)
    print(f"saved {f.shape} -> {FEATURES.name}; flagged county-years: {int(f.flag_missing.sum())}")


if __name__ == "__main__":
    main()
