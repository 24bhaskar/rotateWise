# Provenance and AI-assistance log

What was AI-assisted, and what a human has checked.

| Date (ET) | Item | Helped By | AI tool and role | Human checked? |
|---|---|---|---|---|
| 2026-11-14 | All code in `src/`, `app.py`, `tests/` | Claude Code (Claude Opus 5.5) | Wrote the code from the team's proposal; ran it | Yes |
| 2026-11-14 | `reports/source_checks.csv` | Claude Code | Ran one live request per data source and logged the result | Yes |
| 2026-11-14 | `data/sources.csv`, `data/crop_calendar.csv`, `data/crop_traits.csv` | Claude Code | Located documents and summarised them in its own words; values from NASS Crop Progress are computed from data | Yes |
| 2026-11-14 | README write-up drafts | Claude Code | Drafted text from computed results | Yes |
| 2026-11-14 | Reading web sources for S02-S13 | Claude Code web-reader subagents | Opened each page and reported facts in their own words; one page carried embedded instructions to the reader, which were ignored | Yes |
| 2026-11-14 18:48 CT | One-time test run (`models/final_test_run.json`, lock file) | Claude Code | Ran `src.final_eval` once; no reruns (`final_test_reruns.log` absent) | Yes |
| 2026-11-14 | Website (`web/`), `src/export_web.py`, `src/scenario.py` | Claude Code | Designed and built the static site from the team-approved plan; wrote all page copy, which is built only from exported numbers and card text | Yes |
| optional | Plain-language summaries in the app | Gemini (if `GEMINI_API_KEY` set) | Rewrites computed numbers; output discarded if it adds any number not in the input | n/a |

## Disclosure:

An earlier prototype of this project trained a LightGBM model on 1995-2019 and **scored it on 2020-2024**.  **2025 is the only test year never looked at before the final run**, so it is reported separately.
