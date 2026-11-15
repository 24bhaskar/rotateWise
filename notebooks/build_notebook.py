"""Generate and execute notebooks/training.ipynb (the Colab copy of the training pipeline, outputs visible).

It re-runs dev-only cross-validation for M0, M2 and the selected model and reads the locked test results from
models/ (it never re-runs the one-time test evaluation). Run from the repo root:
    python notebooks/build_notebook.py
"""
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

cells = [
    md("# RotateWise: training pipeline (Colab copy)\n\nCounty-level corn and soybean **yield-anomaly** model for 99 "
       "Iowa counties from NASA POWER weather. Hindcast, county scale. Development years 2000-2019 use "
       "leave-one-year-out CV; test years (2020-2025) were evaluated once by `src/final_eval.py` and are only *read* here."),
    md("## Setup\nIn Colab: clone the repository and install requirements first (cached data and models are in the repo)."),
    code("# !git clone <REPO_URL> rotatewise && %cd rotatewise\n# !pip install -q -r requirements.txt\n"
         "import os, sys, json\nif os.path.basename(os.getcwd()) == 'notebooks':\n    os.chdir('..')\nsys.path.insert(0, '.')\n"
         "import warnings; warnings.filterwarnings('ignore')\nimport pandas as pd, numpy as np"),
    md("## 1. Data: features (B8) and yields, development years only"),
    code("from src.cv import load_dev\nfrom src.features import S0, S1, S2, LABELS\n"
         "y, f = load_dev('corn')\nprint(y.year.min(), y.year.max(), len(y), 'county-years;', f.shape)\n"
         "pd.Series({c: LABELS[c] for c in S2}, name='feature')"),
    md("## 2. Exploratory findings (dev years)"),
    code("print(open('reports/eda.md').read())"),
    md("## 3. Pre-committed selection rule"),
    code("print(open('reports/selection_rule.md').read())"),
    md("## 4. Leave-one-year-out CV: baseline, 3-feature ridge, selected model\nDetrending is refit inside every fold."),
    code("from src.cv import loyo\nfrom src.metrics import per_year, summary\nfrom src.models import candidates\n"
         "spec = json.load(open('models/final_spec.json'))\nrows = {}\nfor crop in ('corn', 'soy'):\n"
         "    y, f = load_dev(crop)\n    c = candidates(crop)\n    m0 = per_year(loyo(c['M0'], y, f))\n"
         "    for k in ('M0', 'M2', spec[crop]['model_id']):\n        py = per_year(loyo(c[k], y, f))\n"
         "        rows[(crop, k)] = summary(py, m0)\n"
         "pd.DataFrame(rows).T[['rmse', 'rmse_se', 'mae', 'skill_vs_m0', 'spearman_within_year']].round(3)"),
    md("## 5. Every model tried (from `experiments/log.csv`)"),
    code("pd.read_csv('models/experiment_table.csv').round(3)"),
    md("## 6. Robustness: train-vs-CV gap, placebo, spatial hold-out, ablations"),
    code("dev = json.load(open('models/dev_results.json'))\nfor crop in dev:\n    print(crop, json.dumps(dev[crop]['checks'], indent=1))"),
    md("## 7. Locked test years (read from the one-time run)"),
    code("run = json.load(open('models/final_test_run.json'))\nprint('run at', run['timestamp'], 'git', run['git_hash'], 'rerun', run['rerun'])\n"
         "m = json.load(open('models/metrics.json'))\nout = {}\nfor crop in m:\n"
         "    t = m[crop]['test_expanding_trend']\n    for k in ('M0', 'M1', 'M2', 'selected'):\n"
         "        out[(crop, k)] = {'rmse': t[k]['rmse'], 'rmse_90ci': t[k]['boot']['rmse'], 'mae': t[k]['mae'],\n"
         "                          'skill_vs_m0': t[k].get('skill_vs_m0')}\npd.DataFrame(out).T"),
    md("## 8. Where it fails: 2012 (held out in LOYO) and 2020 (derecho)"),
    code("oof = pd.read_parquet('models/cv_oof.parquet')\ntp = pd.read_parquet('models/test_predictions.parquet')\n"
         "for crop in ('corn', 'soy'):\n    sel = spec[crop]['model_id']\n"
         "    o = oof[(oof.crop == crop) & (oof.model_id == sel) & (oof.year == 2012)]\n"
         "    t = tp[(tp.crop == crop) & (tp.year == 2020)]\n"
         "    print(f\"{crop}: 2012 predicted {o.pred.mean():+.1f}% vs actual {o.anom_pct.mean():+.1f}% | \"\n"
         "          f\"2020 predicted {t.pred_selected.mean():+.1f}% vs actual {t.anom_pct.mean():+.1f}%\")"),
    md("## 9. Stress profile that feeds the rotation engine"),
    code("sp = json.load(open('models/stress_profile.json'))\npd.DataFrame({k: sp[k] for k in ('corn', 'soybean')}).round(3)"),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
NotebookClient(nb, timeout=1800, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
nbf.write(nb, ROOT / "notebooks" / "training.ipynb")
print("wrote notebooks/training.ipynb")
