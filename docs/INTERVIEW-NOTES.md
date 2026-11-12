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
