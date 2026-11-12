## What this builds
- Feature builder (lags, rolling deviations, WTI changes, retail margin, seasonality, holiday weeks) with the target defined as the h-week price change.
- Baselines (last value, seasonal naive), pooled and per-series LightGBM, split-conformal 80% intervals.
- Rolling-origin backtest over 104 weekly origins; `python -m fuelpulse.backtest` writes `reports/backtest.md`, per-series metrics and `docs/backtest_mae.png`.
- `python -m fuelpulse.forecast`, the weekly refit-and-forecast job, and the first committed forecast.
- Streamlit dashboard and two GitHub Actions workflows (CI on push, weekly refresh).

## How it was tested
- 14 new pytest cases: leakage tests for all four horizons, training cut-off, baseline definitions, interval symmetry, hand-checked MAE/RMSE/MAPE, dashboard smoke tests.
- `scripts/check.sh` and `scripts/check.sh --fixture` pass, including a forecast smoke run and a short backtest.

## Numbers (`uv run python -m fuelpulse.backtest`)
- 104 origins (2024-10-21 to 2026-10-12), 12 series, 4,992 forecasts.
- MAE vs last value: +6.4% (1 week), +0.9% (2), -2.3% (3), -5.3% (4). MAE vs seasonal naive: better at every horizon (+9.8% to +18.7%).
- 80% interval coverage: 68-71% (under target; see DECISIONS.md #14).

## Open questions
- Workflows have not run on GitHub yet because the remote repository has not been created.
