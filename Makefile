# RotateWise pipeline. On Windows without make: python -m src.run <target>
PY ?= python

.PHONY: data features eda select final web-data web app test

data:
	$(PY) -m src.source_checks
	$(PY) -m src.fetch_geo
	$(PY) -m src.fetch_power
	$(PY) -m src.fetch_nass
	$(PY) -m src.fetch_context
	$(PY) -m src.fetch_nasa_validation
	$(PY) -m src.crop_tables

features:
	$(PY) -m src.features
	$(PY) -m src.calendar

eda:
	$(PY) -m src.eda

# model ladder and selection on development years 2000-2019 only
select:
	$(PY) -m src.train

# one-time test evaluation; refuses to run twice unless FORCE=1
final:
	$(PY) -m src.final_eval
	$(PY) -m src.diversity_check

web-data:
	$(PY) -m src.export_web

# the website (static, deploys to Vercel); needs Node 20+
web: web-data
	cd web && npm ci && npm test && npm run build

# Streamlit analyst view (fallback)
app:
	$(PY) -m streamlit run app.py

test:
	$(PY) -m pytest -q tests
