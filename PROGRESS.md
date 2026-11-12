# Progress

## Done
- **Phase 1: ingestion and warehouse.** Ingest, DuckDB, dbt (3 layers, 40 tests), `scripts/check.sh`.
- **Phase 2: forecasting and backtest.** Features with leakage tests, baselines, LightGBM, rolling-origin backtest, conformal intervals, weekly forecast job, dashboard, workflows.

## Next
- Phase 3: SHAP drivers and the plain-English findings page.
- Phase 4: screenshots, full README, interview notes, final results.

## Needs me
- Create the GitHub repository (creation was blocked by the permission prompt): `gh repo create abhiramvedipala/fuel-price-pulse --private --source=. --remote=origin`, then push all branches. Until then CI and the weekly workflow have not run.
- Streamlit Community Cloud deploy (needs my account); steps will be in the README.
