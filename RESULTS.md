# Results

Every number below is produced by a script in this repo. Regenerate the whole file with `uv run python -m fuelpulse.results` after running the commands listed in each section.

## Data ingested

Command: `uv run python -m fuelpulse.ingest && uv run dbt build --project-dir dbt --profiles-dir dbt`

| Measure | Value |
|---|---|
| EIA series ingested | 14 (12 retail, 2 crude) |
| Raw rows (series x week) | 8,664 |
| Raw date range | 2015-01-02 to 2026-11-09 |
| Weeks in the modelling panel | 619 (11.9 years) |
| Panel rows (6 regions x 2 fuels x weeks) | 7,428 |
| Panel date range | 2015-01-05 to 2026-11-09 |

## dbt tests

Command: `uv run dbt build --project-dir dbt --profiles-dir dbt` (counts read from `dbt/target/run_results.json`)

| Measure | Value |
|---|---|
| dbt data tests | 40 (40 passing) |
| Models and seeds built | 6 |

## Backtest

Command: `uv run python -m fuelpulse.backtest`

Rolling-origin evaluation over 104 weekly origins (2024-10-21 to 2026-10-12), 12 series, 4,992 forecasts. The model is refit every 4 weeks on rows whose targets were already published at that origin. Errors are in dollars per gallon.

Model choice: **pooled**. On the 52 origins before the test window, validation MAE was 0.0819 pooled vs 0.0827 per-series.

### MAE by horizon ($/gal)

| Weeks ahead | LightGBM | Last value | Seasonal naive |
|---|---|---|---|
| 1 | 0.0707 | 0.0756 | 0.0871 |
| 2 | 0.1281 | 0.1292 | 0.1478 |
| 3 | 0.1770 | 0.1730 | 0.1991 |
| 4 | 0.2226 | 0.2114 | 0.2468 |


### RMSE by horizon ($/gal)

| Weeks ahead | LightGBM | Last value | Seasonal naive |
|---|---|---|---|
| 1 | 0.1187 | 0.1256 | 0.1358 |
| 2 | 0.2086 | 0.2122 | 0.2282 |
| 3 | 0.2857 | 0.2861 | 0.3066 |
| 4 | 0.3539 | 0.3476 | 0.3735 |


### MAPE by horizon (%)

| Weeks ahead | LightGBM | Last value | Seasonal naive |
|---|---|---|---|
| 1 | 1.72 | 1.83 | 2.18 |
| 2 | 3.02 | 3.06 | 3.63 |
| 3 | 4.14 | 4.07 | 4.86 |
| 4 | 5.17 | 4.95 | 5.98 |


### LightGBM MAE change vs each baseline (positive = model is better)

| Weeks ahead | vs last value (%) | vs seasonal naive (%) |
|---|---|---|
| 1 | +6.4 | +18.7 |
| 2 | +0.9 | +13.3 |
| 3 | -2.3 | +11.1 |
| 4 | -5.3 | +9.8 |


### All horizons combined

| Method | MAE | RMSE | MAPE (%) |
|---|---|---|---|
| LightGBM | 0.1496 | 0.2571 | 3.5134 |
| Last value | 0.1473 | 0.2566 | 3.4782 |
| Seasonal naive | 0.1702 | 0.2757 | 4.1609 |


### MAE by region, all horizons ($/gal)

| Region | LightGBM | Last value | Seasonal naive |
|---|---|---|---|
| PADD1 | 0.1291 | 0.1235 | 0.1473 |
| PADD2 | 0.1670 | 0.1593 | 0.1915 |
| PADD3 | 0.1483 | 0.1418 | 0.1638 |
| PADD4 | 0.1532 | 0.1558 | 0.1773 |
| PADD5 | 0.1586 | 0.1647 | 0.1787 |
| US | 0.1413 | 0.1386 | 0.1625 |


### 80% prediction intervals (split conformal)

| Weeks ahead | Empirical coverage (%) | Mean half-width ($/gal) |
|---|---|---|
| 1 | 71.074 | 0.075 |
| 2 | 68.349 | 0.127 |
| 3 | 67.067 | 0.176 |
| 4 | 67.388 | 0.221 |


Overall coverage: 68.5% against a 80% target.


Full per-region, per-fuel, per-horizon scores: `reports/backtest_metrics.csv`. Chart: `docs/backtest_mae.png`.

## SHAP drivers

Command: `uv run python -m fuelpulse.explain`

Models trained on all targets published by 2026-11-09; SHAP computed on the last 104 weeks, averaged over the 1-4 week horizons. Values are the average absolute contribution to the predicted price change, in dollars per gallon.

### Top drivers, all series

| Feature | Mean absolute SHAP ($/gal) |
|---|---|
| chg_1w | 0.0322 |
| wti | 0.0163 |
| target_woy_sin | 0.0148 |
| brent_minus_wti | 0.0092 |
| chg_52w | 0.0085 |
| wti_chg_1w | 0.0070 |
| dev_mean_13w | 0.0059 |
| wti_chg_4w | 0.0055 |


### Top 3 drivers per region and fuel

| Series | #1 | #2 | #3 |
|---|---|---|---|
| PADD1 diesel | chg_1w | wti | target_woy_sin |
| PADD1 gasoline | chg_1w | wti | target_woy_sin |
| PADD2 diesel | chg_1w | wti | target_woy_sin |
| PADD2 gasoline | chg_1w | wti | target_woy_sin |
| PADD3 diesel | chg_1w | wti | target_woy_sin |
| PADD3 gasoline | chg_1w | wti | target_woy_sin |
| PADD4 diesel | chg_1w | wti | target_woy_sin |
| PADD4 gasoline | chg_1w | wti | target_woy_sin |
| PADD5 diesel | chg_1w | wti | target_woy_sin |
| PADD5 gasoline | chg_1w | wti | target_woy_sin |
| US diesel | chg_1w | wti | target_woy_sin |
| US gasoline | chg_1w | wti | target_woy_sin |


### Weeks where the 4-week-ahead forecast failed most

Backtest target weeks with the largest average absolute error across the 12 series (`reports/backtest_predictions.csv`). Bias is forecast minus actual; actual move is the realised change from the origin price.

| Target week | MAE ($/gal) | Bias ($/gal) | Actual move ($/gal) |
|---|---|---|---|
| 2026-03-23 | +1.250 | -1.250 | +1.328 |
| 2026-03-30 | +1.208 | -1.208 | +1.295 |
| 2026-03-16 | +1.016 | -1.016 | +1.093 |
| 2026-03-09 | +0.791 | -0.791 | +0.873 |
| 2026-08-03 | +0.712 | -0.712 | +0.549 |
| 2026-06-22 | +0.712 | +0.712 | -0.632 |
