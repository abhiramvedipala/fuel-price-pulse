# Interview notes

## Phase 1: ingestion and warehouse

### What this phase built
- `fuelpulse/ingest.py`: pulls 14 weekly EIA series (regular gasoline and diesel for the U.S. and PADD 1-5, plus WTI and Brent) into DuckDB.
- Two interchangeable sources: API v2 with a key, public spreadsheets without one.
- Idempotent upserts keyed by (series_id, week) and a `--since` watermark.
- A dbt project with three layers (staging, intermediate, marts) and 40 data tests.
- `scripts/check.sh`, one command that lints, tests, ingests and builds dbt, with an offline `--fixture` mode.

### Key decisions and "why not X?"
- **Why DuckDB and not Postgres?** The whole dataset is under 10k rows per load and one writer. A single file needs no server, runs in CI for free, and dbt-duckdb gives me the same SQL modelling workflow. I would move to Postgres or a cloud warehouse when there are concurrent writers.
- **Why not just `INSERT OR REPLACE`?** It rewrites every row each run, so I could not tell a no-op run from a revision. Updating only when the value differs makes the second run write 0 rows, which I assert in a test.
- **Why an ASOF join for crude?** Crude weeks end Friday, retail weeks start Monday. Joining by calendar week would give Monday's row a crude price from four days later. The ASOF join takes the latest crude week that had already ended.
- **Why keep features out of dbt?** One Python function builds features for training, backtest and the leakage test, so they cannot drift apart.

### Hardest problem
The offline fixture build failed two not-null tests that the live build passed. The first retail Monday in the fixture came before its first crude Friday, so the left ASOF join returned nulls for 12 rows. The live data hid this because its first crude week happens to precede its first retail week. I made the join inner so a history starts where crude is known. The lesson: the fixture run is a second dataset, and it found an edge the main data never would.

### Likely questions
1. **How do you know the pipeline is idempotent?** A test runs ingest twice on the same input and asserts the second run reports 0 rows written and the table is identical, including `loaded_at`. Another test changes one value and asserts exactly one row updates with no duplicate.
2. **What happens if EIA revises last week's number?** The watermark re-reads the last 4 weeks on every run, and the upsert updates only rows whose value changed. History older than that is not re-read unless I pass `--since`.
3. **How would you notice the feed going stale?** Two checks. dbt source freshness errors if nothing was loaded for 15 days, and a `max_age_days` test fails the build if the newest EIA week is more than 14 days old, which catches a job that runs but gets no new data.
4. **What do your dbt tests cover?** Uniqueness of the panel key, not-null on prices, accepted values for region and fuel, a $1-$10 per gallon range check, contiguous 7-day steps per series, and that the joined crude week is always in the past.
5. **Why three dbt layers for such a small dataset?** Each layer has one job: staging renames and types a source, intermediate does the one hard join, marts shape data for a consumer. When the join logic had a bug, I fixed one model and both marts picked it up.

### Files to open
- `fuelpulse/ingest.py` (upsert and watermark)
- `dbt/models/intermediate/int_weekly_panel.sql` (ASOF join)
- `dbt/tests/` (singular and generic tests)
- `tests/test_ingest.py`
- `scripts/check.sh`

## Phase 2: forecasting and backtest

### What this phase built
- `fuelpulse/features.py`: lags, rolling-mean deviations, crude changes, retail margin over crude, week-of-year and holiday flags (Memorial Day, July 4th, Labor Day, Thanksgiving).
- `fuelpulse/model.py`: two baselines (last value, seasonal naive) and a direct multi-horizon LightGBM (one model per horizon, 1-4 weeks) with split-conformal 80% intervals.
- `fuelpulse/backtest.py`: rolling-origin evaluation over the last 104 weeks, scored on MAE, RMSE and MAPE per horizon and region.
- Leakage tests that remove or inflate future weeks and require every feature to be unchanged.
- `fuelpulse/forecast.py`: the weekly refit-and-forecast entry point.

### Key decisions and "why not X?"
- **Why predict changes?** Trees cannot extrapolate. Prices rose well above the training range in 2026; a level model would have been capped.
- **Why not tune on the test window?** I picked parameters and pooled-vs-per-series on the 52 origins before it. The test window only scores.
- **Why conformal intervals?** No extra models and an honest, simple recipe. Why not quantile regression? It needs three models per horizon and I would still have to check coverage afterwards.
- **Why direct multi-horizon, not recursive?** Recursive forecasting feeds its own predictions back in and compounds errors; direct models each target one horizon.

### Hardest problem
Making "no future information" provable rather than claimed. Crude prices are dated on Fridays and retail on Mondays, so a naive join leaks. The dbt panel uses a point-in-time join, and `tests/test_features.py` rebuilds features from a truncated panel and from one with future prices tripled, and asserts every earlier feature is identical for all four horizons. Separately, the training rows at an origin must have targets already published, which a model test checks.

### Likely questions
1. **Did your model beat the baselines?** Against seasonal naive, yes at every horizon (about 10-19% lower MAE). Against last value it wins at 1 week (+6.4%) and 2 weeks (+0.9%), and loses at 3 and 4 weeks (-2.3% and -5.3%). I report that as is; retail prices are close to a random walk over a month.
2. **Why are your intervals under-covered?** Coverage is 68-71% against an 80% target. The calibration window is the last 52 weeks, and the test period contains shocks bigger than anything in it, so errors grow after calibration. Fixes I would try: a longer window, adaptive conformal updates, or scaling by recent volatility.
3. **How do you prevent leakage?** Three layers: the point-in-time crude join in dbt, features computed only from past rows, and tests that perturb the future and check earlier features do not move. Training sets also exclude rows whose target is not yet published at the origin.
4. **Why a rolling-origin backtest?** A single split hides regime changes. Rolling origins reproduce what the weekly job does: train on what is known, forecast, score once the truth arrives.
5. **Why LightGBM for 6k rows per horizon?** It handles the categoricals and interactions with little tuning, and it supports exact SHAP. I kept it small (200 trees, 7 leaves) and compared it with simple baselines so the gain is measured, not assumed.

### Files to open
- `fuelpulse/features.py`, `tests/test_features.py` (leakage)
- `fuelpulse/model.py` (baselines, conformal)
- `fuelpulse/backtest.py`, `reports/backtest.md`

## Phase 3: explanations and findings

### What this phase built
- `fuelpulse/explain.py`: exact SHAP (TreeExplainer) for the four horizon models, per-series driver ranking, and the worst backtest weeks.
- `reports/shap_drivers.csv`, `reports/shap.md`, `docs/shap_summary.png`.
- `docs/findings.md`: a one-page plain-English report for a gas-station owner.

### Key decisions and "why not X?"
- **Why SHAP and not feature importance?** Gain importance is biased toward high-cardinality features and has no sign. SHAP is additive in dollars per gallon, so "WTI contributes about 1.6 cents on average" is a meaningful sentence.
- **Why trust a plain-English report?** Every figure in it comes from a script's output, and I deleted one sentence I could not back with a test.
- **Why report that drivers are identical across regions?** Because they are. Regional differences exist in level, not in which signals matter, and inventing differences would mislead.

### Hardest problem
Deciding what the failures mean. The six worst weeks cluster in March 2026, when gasoline rose about $1.30 in four weeks and the model forecast almost none of it. Crude had also jumped, but a model trained mostly on moderate moves cannot extrapolate a regime like that. I wrote that down as a limitation instead of tuning the model on those weeks, which would have leaked the test window into training.

### Likely questions
1. **What drives prices in your model?** Last week's price change (mean |SHAP| 0.032 $/gal), the WTI level (0.016), then seasonality (0.015). The same ranking holds in all 12 series.
2. **Does SHAP prove causation?** No. It describes what the model uses. Crude plausibly causes pump moves, but the momentum term also stands in for things the data does not contain, such as wholesale prices.
3. **Where does the model fail?** Supply shocks: the four worst 4-week misses are March 2026, with errors of $0.79 to $1.25 per gallon, all in one direction (forecast too low).
4. **How would you improve it?** Add daily wholesale (RBOB) prices, which lead retail by days; add volatility-scaled intervals; evaluate against a no-change baseline with a Diebold-Mariano test.
5. **Who is the findings report for?** A station owner. It avoids model jargon, gives ranges instead of point values, and says plainly that past two weeks "no change" is competitive.

### Files to open
- `fuelpulse/explain.py`, `reports/shap.md`
- `docs/findings.md`, `docs/shap_summary.png`
