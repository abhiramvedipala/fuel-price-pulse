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
