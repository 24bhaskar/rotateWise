"""B15.2 unit tests: leakage guards, weight normalisation, explainer fallback, one-time final run."""
import json

import numpy as np
import pandas as pd
import pytest

import src.cv as cv
from src.detrend import anomalies, fit_trends
from src.explain import explain, grounded
from src.features import season_features
from src.rotations import SLIDERS, criterion_weights, month_weights_ok
from src.stress_profile import month_weights


def toy_yields():
    rows = [{"fips": f, "year": y, "yield_bu_ac": 100 + 2 * (y - 2000) + (5 if y == 2010 else 0)}
            for f in ("19001", "19003") for y in range(2000, 2020)]
    return pd.DataFrame(rows)


def test_trend_uses_only_given_years():
    y = toy_yields()
    with_2010 = fit_trends(y, range(2000, 2020))
    without = fit_trends(y, [t for t in range(2000, 2020) if t != 2010])
    assert without["19001"][0] == pytest.approx(2.0)  # the 2010 bump never enters its own trend
    assert with_2010["19001"][0] != pytest.approx(2.0)
    a = anomalies(y[y.year == 2010], without)
    assert a.anom_pct.iloc[0] == pytest.approx(5 / 120 * 100)


def test_loyo_never_fits_trend_on_heldout_year(monkeypatch):
    seen = []
    real = cv.fit_trends

    def spy(y, years, method="ols"):
        seen.append(set(years))
        return real(y, years, method)

    monkeypatch.setattr(cv, "fit_trends", spy)
    y = toy_yields()
    f = pd.DataFrame([{"fips": r.fips, "year": r.year, "x": 0.0} for r in y.itertuples()])

    class Const:
        def fit(self, df):
            return self

        def predict(self, df):
            return np.zeros(len(df))

    out = cv.loyo(Const(), y, f, years=list(range(2000, 2020)))
    assert len(seen) == 20
    for held, years in zip(range(2000, 2020), seen):
        assert held not in years
    assert set(out.year) == set(range(2000, 2020))


def test_load_dev_excludes_test_years():
    y, f = cv.load_dev("corn")
    assert y.year.max() < cv.TEST_START and f.year.max() < cv.TEST_START


def test_feature_windows_ignore_dates_after_season():
    dates = pd.date_range("2012-01-01", "2012-12-31")
    base = pd.DataFrame({"date": dates, "t2m_max": 25.0, "t2m_min": 10.0, "prectotcorr": 2.0, "gwetroot": 0.5,
                         "evptrns": 5.0})
    late = base.copy()
    after = late.date > "2012-09-30"
    late.loc[after, ["t2m_max", "t2m_min", "prectotcorr", "gwetroot", "evptrns"]] = [99.0, -50.0, 500.0, 0.0, 0.0]
    a, b = season_features(base), season_features(late)
    assert a == b


def test_month_weights_sum_to_one():
    contrib = pd.DataFrame({"jul_tmax_mean": [1.0, -2.0], "gwetroot_aug_mean": [0.5, 0.5], "spring_frost_days": [0.1, 0]})
    w = month_weights(contrib)
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-3)
    assert month_weights_ok(w)


@pytest.mark.parametrize("sliders", [{"water": 3, "soil": 3, "income": 3, "labor": 3},
                                     {"water": 5, "soil": 0, "income": 1, "labor": 0},
                                     {"water": 0, "soil": 0, "income": 0, "labor": 0}])
def test_slider_weights_sum_to_one(sliders):
    lam, _ = criterion_weights(sliders, excluded={"WaterUse": "x", "SoilHealth": "x"})
    assert sum(lam.values()) == pytest.approx(1.0)
    assert lam["WaterUse"] == 0 and lam["SoilHealth"] == 0
    assert set(sliders) == set(SLIDERS)


CARD = {"name": "Corn → soybean + winter cereal rye", "rank": 1, "score": 0.71, "why_suggested": "Bare 58% of the year.",
        "benefits": ["Bare share falls from 58% to 20%."], "risks_needing_local_review": ["N tie-up."]}


class FakeClient:
    def __init__(self, text=None, fail=False):
        self.text, self.fail = text, fail
        self.models = self

    def generate_content(self, model, contents):
        if self.fail:
            raise RuntimeError("API down")
        return type("R", (), {"text": self.text})()


def test_explainer_rejects_invented_numbers():
    text, src = explain(CARD, client=FakeClient("Rye cuts erosion by 73% and adds 40 bushels."))
    assert src == "template"


def test_explainer_accepts_grounded_numbers():
    text, src = explain(CARD, client=FakeClient("Rye drops bare soil from 58% to 20% of the year."))
    assert src == "gemini" and grounded(text, CARD)


def test_explainer_falls_back_when_api_fails():
    assert explain(CARD, client=FakeClient(fail=True))[1] == "template"


def test_final_refuses_second_run(tmp_path, monkeypatch):
    import src.final_eval as fe
    lock = tmp_path / "final_test.lock"
    lock.write_text("run at earlier")
    monkeypatch.setattr(fe, "LOCK", lock)
    monkeypatch.delenv("FORCE", raising=False)
    with pytest.raises(SystemExit):
        fe.main()
