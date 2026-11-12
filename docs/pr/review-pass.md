## What this changes
Acts on a review of the first release. Every model setting was chosen on the 52 validation origins before the 104-week test window; the test numbers were read only after the choices were fixed.

- **Intervals (adopted):** errors are scaled by trailing 13-week volatility and calibrated over 104 weeks. Test coverage goes from 68.5% to 79.1% (80% target). Average bands are wider (mean half-width 0.124-0.335 vs 0.075-0.221 $/gal).
- **Per-horizon shrinkage, stronger regularisation for 3-4 weeks, level-free features (all rejected):** none helped on validation; numbers are in `reports/model_experiments.md` and DECISIONS.md #26-#28. The loss to last value at 3-4 weeks stands.
- **Correction:** 2026 prices did not leave the training range (U.S. gasoline peaked at $4.50 vs a $1.72-$5.01 training range). Fixed in README, DECISIONS and interview notes.
- **README:** states that across all horizons the model is slightly worse than last value (MAE 0.1496 vs 0.1473), real commands in the results table, a second dashboard screenshot.
- **Weekly workflow:** runs Monday 22:00 UTC (after EIA's release) with a Tuesday retry; a new `fuelpulse.freshness` check fails with the date, age and limit; the commit message names the EIA week. The old dbt source freshness step could never fail there because the warehouse is rebuilt each run.

## How it was tested
- `scripts/check.sh` and `--fixture` both pass: 27 pytest tests (new: interval scaling, freshness), 46 dbt nodes.
- Full backtest rerun: point forecasts and MAE identical to before; only intervals differ.

## Numbers (before to after)
| Weeks ahead | MAE LightGBM | MAE last value | Coverage before | Coverage after |
|---|---|---|---|---|
| 1 | 0.0707 | 0.0756 | 71.1% | 79.9% |
| 2 | 0.1281 | 0.1292 | 68.3% | 78.4% |
| 3 | 0.1770 | 0.1730 | 67.1% | 79.0% |
| 4 | 0.2226 | 0.2114 | 67.4% | 79.2% |

## Open questions
- The first week of a sudden shock is still under-covered because volatility is measured before it starts; adaptive conformal updates are the next step.
