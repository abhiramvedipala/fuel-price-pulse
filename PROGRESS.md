# Progress

## Done
- **Phase 1: ingestion and warehouse.** Ingest, DuckDB, dbt (3 layers, 40 tests), `scripts/check.sh`.
- **Phase 2: forecasting and backtest.** Features with leakage tests, baselines, LightGBM, rolling-origin backtest, conformal intervals, weekly forecast job.
- **Phase 3: explanations and findings.** SHAP drivers, failure weeks, one-page findings.
- **Phase 4: dashboard and schedule.** Streamlit app, CI and weekly workflows, README, interview notes.

All phases are merged to `main` with merge commits and pushed. `scripts/check.sh` passes in live and `--fixture` modes. CI is green on `main`, and the weekly workflow ran successfully via `workflow_dispatch` on 2026-11-12 (run 43158846288) and committed its refreshed run log.

## Next
- Nothing planned inside the build. See README "Known limits and next steps".

## Needs me
- **Deploy to Streamlit Community Cloud** (needs my account): steps are in the README.
- Optional: add a free `EIA_API_KEY` repo secret to use the API path instead of the public files.
