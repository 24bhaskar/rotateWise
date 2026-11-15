# Provenance and AI-assistance log

What was AI-assisted, and what a human has checked. Human-check column is filled in by the team.

| Date (ET) | Item | Made by | AI tool and role | Human checked? |
|---|---|---|---|---|
| 2026-11-14 | All code in `src/`, `app.py`, `tests/` | Claude Code (Claude Opus 5.5) | Wrote the code from the team's proposal; ran it | [ ] |
| 2026-11-14 | `reports/source_checks.csv` | Claude Code | Ran one live request per data source and logged the result | [ ] |
| 2026-11-14 | `data/sources.csv`, `data/crop_calendar.csv`, `data/crop_traits.csv` | Claude Code | Located documents and summarised them in its own words; values from NASS Crop Progress are computed from data | [ ] |
| 2026-11-14 | README write-up drafts | Claude Code | Drafted text from computed results | [ ] |
| 2026-11-14 | Reading web sources for S02-S13 | Claude Code web-reader subagents | Opened each page and reported facts in their own words; one page carried embedded instructions to the reader, which were ignored | [ ] |
| 2026-11-14 18:48 CT | One-time test run (`models/final_test_run.json`, lock file) | Claude Code | Ran `src.final_eval` once; no reruns (`final_test_reruns.log` absent) | [ ] |
| 2026-11-14 | Website (`web/`), `src/export_web.py`, `src/scenario.py` | Claude Code | Designed and built the static site from the team-approved plan; wrote all page copy, which is built only from exported numbers and card text | [ ] |
| optional | Plain-language summaries in the app | Gemini (if `GEMINI_API_KEY` set) | Rewrites computed numbers; output discarded if it adds any number not in the input | n/a |

## Disclosure: test-period exposure before the revised protocol

Before the revised proposal arrived (2026-11-14, afternoon ET), an earlier prototype of this project
trained a LightGBM model on 1995-2019 and **scored it on 2020-2024**. Its test MAE values were seen by the
builder and the team. That prototype used a different target (bu/acre anomaly, not percent), different
features, and no selection rule. The revised pipeline's features, model ladder and selection rule were
fixed from the proposal text, not tuned to those numbers, but the 2020-2024 years cannot be called
fully unseen. **2025 is the only test year never looked at before the final run**, so it is reported separately.

One design choice was influenced by the prototype: monotone constraints on heat and dryness features.
They were added after the prototype's *scenario* output went the wrong direction (not after looking at test
scores). The revised proposal also requires them (spec B9.2, M7).
