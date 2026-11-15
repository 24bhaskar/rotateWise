"""The static site's data contract (web/public/data), written by src/export_web.py."""
import json

import numpy as np
import pandas as pd
import pytest

from src import scenario as scen
from src.paths import POWER_DAILY, ROOT

DATA = ROOT / "web" / "public" / "data"
pytestmark = pytest.mark.skipif(not (DATA / "state.json").exists(), reason="run `python -m src.export_web` first")


def load(p):
    return json.loads((DATA / p).read_text(encoding="utf-8"))


def test_state_has_every_section():
    s = load("state.json")
    for key in ("meta", "counties", "map_layers", "stress", "calendar", "strategy_calendar", "strategies", "sliders",
                "criteria", "ssurgo", "conformal"):
        assert key in s, key
    assert len(s["counties"]) == 99 and len(s["map_layers"]) == 99
    e = load("evidence.json")
    for key in ("evidence", "failures", "sources", "traits"):
        assert key in e, key


def test_every_county_file_and_grid_size():
    files = list((DATA / "county").glob("*.json"))
    assert len(files) == 99
    c = load("county/19169.json")
    assert len(c["scenario"]) == len(scen.TEMP_STEPS) * len(scen.RAIN_STEPS) == 77
    assert set(c["rotation"]["cards"]) == {"A", "B", "C"}
    for card in c["rotation"]["cards"].values():
        for part in ("why_suggested", "evidence", "benefits", "information_gaps", "risks_needing_local_review", "support_line"):
            assert card[part], part
        assert "rank" not in card and "score" not in card  # ranking is done in the browser


def test_exported_scenario_matches_direct_run():
    c = load("county/19169.json")
    cell = next(r for r in c["scenario"] if r["t"] == 2.0 and r["r"] == -25)
    d = pd.read_parquet(POWER_DAILY, filters=[("fips", "==", "19169")])
    direct = scen.run(d, 2.0, -25, scen.load_models(), scen.load_ranges())
    assert cell["corn"] == pytest.approx(np.mean(direct["corn"]), abs=1e-3)
    assert cell["soybean"] == pytest.approx(np.mean(direct["soybean"]), abs=1e-3)


def test_json_has_no_nan():
    for p in [DATA / "state.json", DATA / "county" / "19169.json"]:
        txt = p.read_text(encoding="utf-8")
        assert "NaN" not in txt and "Infinity" not in txt
