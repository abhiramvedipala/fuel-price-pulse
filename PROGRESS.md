# Progress

## Done
- **Phase 1: ingestion and warehouse.** Ingest, DuckDB, dbt (3 layers, 40 tests), `scripts/check.sh`.
- **Phase 2: forecasting and backtest.** Features with leakage tests, baselines, LightGBM, rolling-origin backtest, conformal intervals, weekly forecast job.
- **Phase 3: explanations and findings.** SHAP drivers, failure weeks, one-page findings.
- **Phase 4: dashboard and schedule.** Streamlit app, CI and weekly workflows, README, interview notes.

All phases are merged to `main` locally with merge commits. `scripts/check.sh` passes in live and `--fixture` modes.

## Next
- Nothing planned inside the build. See README "Known limits and next steps".

## Needs me
- **Create the GitHub repo and push** (creation was blocked by a permission prompt):
  `gh repo create abhiramvedipala/fuel-price-pulse --private --source=. --remote=origin --push`, then push the phase branches.
- **Run the Monday workflow once** (Actions tab, "Weekly refresh", Run workflow) so the Definition of done's `workflow_dispatch` run exists. Neither workflow has run on GitHub yet; the YAML parses and every step was run locally.
- **Deploy to Streamlit Community Cloud** (needs my account): steps are in the README.
- Optional: add a free `EIA_API_KEY` repo secret to use the API path instead of the public files.
