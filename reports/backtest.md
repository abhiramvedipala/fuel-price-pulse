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


### 80% prediction intervals (split conformal, scaled by trailing volatility, 104-week calibration)

| Weeks ahead | Empirical coverage (%) | Mean half-width ($/gal) |
|---|---|---|
| 1 | 79.888 | 0.124 |
| 2 | 78.446 | 0.199 |
| 3 | 79.006 | 0.263 |
| 4 | 79.167 | 0.335 |


Overall coverage: 79.1% against a 80% target.


Full per-region, per-fuel, per-horizon scores: `reports/backtest_metrics.csv`. Chart: `docs/backtest_mae.png`.
