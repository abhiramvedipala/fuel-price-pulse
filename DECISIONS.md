# Decisions

Short log of choices made during the build, newest phase last. Each entry: what, why, what was rejected.

## Phase 1: ingestion and warehouse

1. **No-key spreadsheets are the default source; the API is optional.**
   EIA's `hist_xls` weekly files need no key, so the weekly job and a fresh clone work with zero secrets. The API v2 path is used only when `EIA_API_KEY` is set. Both normalise to the same `raw_prices` table. Rejected: requiring the key, which would make CI depend on a secret.
2. **History from 2015, backtest window reported separately.**
   I load ~12 years so the model sees several price regimes (2015 crash, 2020, 2022 spike). The backtest covers only the last 2 years and says so.
3. **Regions are the U.S. average plus PADD 1-5.**
   Six regions x two fuels = 12 retail series. Florida sits inside PADD 1C; I did not add sub-PADD series because EIA's sub-PADD diesel coverage is uneven and it would triple the series count for little modelling value.
4. **Upsert only when the value changed.**
   `ON CONFLICT ... DO UPDATE ... WHERE value <> excluded.value` means a re-run writes zero rows and `loaded_at` records the last real change. Rejected: `INSERT OR REPLACE`, which rewrites every row and makes "did anything change?" unanswerable.
5. **Watermark re-reads the last 4 weeks.**
   EIA occasionally revises recent weeks. `--since` defaults to the newest loaded week minus 4 weeks, so revisions are picked up without reloading history.
6. **Crude joins to retail point-in-time with an ASOF join.**
   EIA dates crude weeks by Friday and retail weeks by Monday. A retail Monday gets the newest crude week that ended at least 3 days earlier. Rejected: joining on calendar week, which would attach a Friday four days in the future.
7. **Features live in Python, not dbt.**
   dbt owns cleaning, alignment and tests; lags and rolling means are built in `fuelpulse/features.py` so training, backtest and the leakage test all run the exact same code.
8. **Two freshness checks.**
   dbt source freshness watches `loaded_at`; the `max_age_days` test watches the newest EIA week. Only the second catches "the job ran but EIA published nothing new".
9. **Working notes stay out of git.**
   The build brief and local tooling config are gitignored; the repo holds only the project.
