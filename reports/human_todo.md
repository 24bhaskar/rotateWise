# Human to-do list (spec B16)

Kept up to date by the build. Tick items as you finish them.

## Accounts and keys still needed
- [ ] **NASA Earthdata Login** (EARTHDATA_USERNAME / EARTHDATA_PASSWORD or EARTHDATA_TOKEN in `.env`). Blocks SMAP L4 validation
      (D12) and the POWER-vs-SMAP comparison. Request that failed: `python -m src.source_checks` → check_smap
      "no Earthdata credentials". MODIS NDVI uses the ORNL service and needs no login.
- [ ] Gemini API key (optional; the template explainer works without it).
- [ ] GitHub repo and a **Vercel** account to deploy the website (import repo, Root Directory = `web`).
      Streamlit Community Cloud is now only needed if you also want the analyst fallback online.
- [ ] Team names and roles for both submission forms.

## Decisions to confirm
- [ ] One user: a central-Iowa farmer and the county extension agent they work with.
- [ ] One decision: which rotation to explore with local experts.
- [ ] **Test-period exposure:** 2020-2024 were scored by an earlier prototype before the revised protocol
      (see `reports/provenance.md`). 2025 is the only fully unseen test year. Confirm the write-up wording.
- [x] Frontend: spec B2 ("App: Streamlit") changed to a static React site on Vercel with precomputed data, approved
      by the team on 2026-11-14. The Gemini explainer is not on the website (no safe place for a key); the
      Streamlit fallback keeps it.
- [ ] Review the website's plain-language wording (headlines, "biggest weather drags", questions to ask) with someone
      who works with farmers.
- [ ] Strategy B puts cereal rye in **both** winters (after corn and after soybean). Confirm this matches what you intend.

## Values needing a source or expert confirmation
Every row in `data/crop_calendar.csv` and `data/crop_traits.csv` is `pending_human` or `N` until a person opens the
source and sets `verified=Y`.
- [ ] Calendar: red clover **termination** timing is an author estimate (assumed ~2 weeks before corn planting).
- [ ] Calendar: clover seeding mixes frost seeding (S07, pasture context) and seeding with oats in March (S08); confirm.
- [ ] Traits marked `NEEDS_SOURCE`: water use of oats, red clover, rye; N fixation of corn and soybean; rooting depth
      of all crops; residue of corn and soybean; organic-matter contribution of all crops; oats and rye SCN status;
      clover hay costs and labour; rye labour hours.
- [ ] SARE Chart 2 ratings (N scavenger, soil builder, erosion fighter, ...) are coloured circles that could not be
      read automatically: open https://www.sare.org/wp-content/uploads/chart2-performance-and-roles.pdf and enter them.
- [ ] Expert rating: cereal rye adds 2 field passes per winter (seed + terminate), converted at 0.5 h/acre per pass.
- [ ] ISU pm1999 / CROP 3159 rye seeding-date guidance was found by search but could not be opened; not cited.
- [ ] NRCS Cereal Rye Cover Crop Fact Sheet timed out twice; not cited.
- [ ] ISU slide deck `Dynamics_RyeCoverCrop_CAS_2017.pdf` downloaded but not used (image-only slides).
- [ ] Marsden Farm (S09) used composted manure in the diverse rotations; confirm the card's caveat is sufficient.

## Results to review before presenting
- [ ] **Calendar sensitivity:** shifting crop windows 14-21 days later flips strategy C from first to last for Story
      County. Decide how to present this (README states it).
- [ ] **Soybean model is fragile:** it beats M0 in LOYO and on test, but not in the 2008-2019 expanding-window check.
- [ ] **Intervals under-cover extreme years** (worst dev-year coverage 60% corn, 5% soy).
- [ ] **Diversity check is null/unclear**, and county hay/oats survey data are sparse (median diverse share 0.2%).
- [ ] **MODIS NDVI download** was still running at hand-off (ORNL service slow). Rerun
      `python -m src.fetch_nasa_validation` to finish the remaining years (it resumes from cache).
- [ ] Root-zone wetness (GWETROOT) adds nothing in ablation A1; say so if asked "what does NASA soil data add?"

## Links to check in an incognito window
- [ ] Every URL in `data/sources.csv` and in the README link audit table.
- [ ] Deployed app URL, GitHub repo, Colab notebook, video.

## Rules to check (not verified by the builder)
- [ ] [CONFIRM AGAINST CURRENT RULES] Dual submission of one project to Veritas AI and NASA Space Apps.
- [ ] [CONFIRM AGAINST CURRENT RULES] AI-tool disclosure wording and placement.
- [ ] [CONFIRM AGAINST CURRENT RULES] Video length (proposal says 2 minutes), slide format and limits.
- [ ] [CONFIRM AGAINST CURRENT RULES] Write-up template headings for Veritas; Space Apps project-page fields.
- [ ] [CONFIRM AGAINST CURRENT RULES] 48-hour window and no-prior-work rule versus what was done and when.
- [ ] [CONFIRM AGAINST CURRENT RULES] Team size and eligibility.
