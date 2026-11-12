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
