## What this builds
- Streamlit dashboard (history, 4-week forecast with 80% band, model vs baseline MAE, top drivers, last refresh) with fallbacks for missing files.
- CI workflow (lint, tests, dbt build on a frozen fixture) and a Monday workflow that ingests, runs `dbt build`, forecasts and commits the refreshed outputs.
- Full README, interview notes, screenshots, the generated RESULTS.md and the final DECISIONS.md.

## How it was tested
- `scripts/check.sh` and `scripts/check.sh --fixture` both pass: ruff, 22 pytest tests, 46 dbt nodes (40 data tests), forecast smoke run, 8-origin backtest.
- Dashboard run against the real committed data and screenshotted in a headless browser.

## Numbers
- 22 pytest tests, 40 dbt data tests, all passing.
- Backtest and SHAP numbers are unchanged from phases 2 and 3 (see RESULTS.md).

## Open questions
- The GitHub repository does not exist yet (creation was blocked), so neither workflow has run on GitHub and no `workflow_dispatch` run has happened.
- Streamlit Community Cloud deploy needs the owner's account; the steps are in the README.
