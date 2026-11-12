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

## Phase 2: forecasting and backtest

10. **The model predicts the price change, not the price.**
    Trees cannot extrapolate beyond levels seen in training, and prices moved from about $3.1 to $4.2 in 2026. Predicting the h-week change and adding it to the origin price avoids that. Rejected: predicting levels, which would cap forecasts at the training range.
11. **One pooled model per horizon, not one per series.**
    I compared pooled (region and fuel as categoricals) with 12 separate models per horizon on the 52 origins before the test window: validation MAE 0.0819 vs 0.0827. Pooled won narrowly and has far more rows per model, so it is the default. The choice is recomputed on every backtest and saved in `reports/model_choice.json`.
12. **L1 objective and small trees.**
    I tried six settings on the validation year only. The test window was never used to choose. L1 with 7 leaves and `min_child_samples=100` had the lowest validation MAE (mean 0.0822 vs 0.0906 for the first L2 attempt). Weekly changes have fat tails, and L1 keeps a few shock weeks from dominating. This was a hand-picked comparison of six variants, not a search.
13. **Seasonal naive = last value plus last year's change.**
    A raw "same week last year" price is a poor baseline when the level moves a lot year to year. Adding the change over the same h weeks a year earlier to today's price keeps the seasonal shape and the current level.
14. **Intervals use split conformal, not quantile LightGBM.**
    The 80% half-width is the 80th percentile of absolute errors on the most recent 52 weeks, from a model that never saw those weeks. It needs no extra models and has a finite-sample guarantee under exchangeability. That assumption fails here: coverage was 68-71% against 80%, because errors are larger in shock periods than in the calibration window. I report the real coverage and do not widen the intervals to hit the target.
15. **Weekly backtest refit every 4 weeks.**
    Refitting 104 times x 4 horizons is slow on a shared 16 GB machine. Every 4 weeks keeps the model within a month of fresh data and costs a quarter of the time.
16. **The result is reported as it came out.**
    The model beats seasonal naive at every horizon and last value at 1-2 weeks, but is 2-5% worse than last value at 3-4 weeks. A last-value forecast is hard to beat on a series with a large random-walk component. The README says so.

## Phase 3: explanations and findings

17. **SHAP on the pooled models as of the latest week.**
    TreeExplainer is exact for trees and fast here. I explain the last 104 weeks and average |SHAP| over the four horizons so the table does not depend on one horizon. Per-region drivers come from grouping the pooled model's SHAP values; the top three are identical in all 12 series, which I report as is rather than forcing differences.
18. **Failure weeks come from the backtest, not from SHAP.**
    The worst 4-week misses are listed straight from `reports/backtest_predictions.csv`, so they are the same out-of-sample forecasts scored in the backtest.
19. **Findings page only states what a script measured.**
    A claim I could not back (margin snap-back) was removed; the momentum claim cites its measured correlation. Rule of thumb of 2.4 cents per $1 crude is arithmetic (42 gallons per barrel), not a model result.

## Phase 4: dashboard and schedule

20. **The dashboard reads committed files, with the warehouse as a bonus.**
    Streamlit Cloud has no DuckDB file, so the app prefers `data/warehouse.duckdb` when present and otherwise reads `reports/history.parquet` and the CSVs the weekly job commits. One code path works locally and hosted. Rejected: committing the warehouse (binary, grows every week).
21. **The weekly job commits data back to the repo.**
    It is the simplest way to give the free hosted dashboard fresh numbers with no database or secrets. The cost is a weekly data commit by a bot identity; history stays readable because the commit message names the EIA week.
22. **CI uses a frozen fixture, the weekly job uses live data.**
    CI must be deterministic and offline, so it runs `check.sh --fixture` and relaxes the data-age test that a frozen sample cannot satisfy. The weekly job is the one that exercises the live files and fails on stale data.
23. **Full backtest stays out of CI.**
    It takes about five minutes with 2 worker threads. `check.sh` runs an 8-origin smoke backtest on live data instead, so the script is exercised on every check; the full run is one documented command.
24. **No local remote yet.**
    Creating the GitHub repository was blocked by a permission prompt, so phases were merged locally with merge commits (`--no-ff`) on the same branch-per-phase layout, ready to push. Workflows have therefore not run on GitHub.
