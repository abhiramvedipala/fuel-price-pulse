## What this builds
- `fuelpulse/ingest.py`: 14 weekly EIA series into DuckDB through either the API v2 (with `EIA_API_KEY`) or the public no-key spreadsheets. Idempotent upserts by (series_id, week), `--since` watermark, retries.
- dbt project (`dbt-duckdb`): `series` seed, 2 staging models, 1 intermediate weekly panel with point-in-time crude, 2 marts.
- `scripts/check.sh` with a `--fixture` mode for offline CI, plus a two-year fixture.
- `fuelpulse/results.py`, which writes RESULTS.md from the warehouse and dbt run results.

## How it was tested
- `scripts/check.sh` (live EIA data) and `scripts/check.sh --fixture` both pass.
- 5 pytest cases: second run writes 0 rows, revisions update in place, `--since` filters, junk rows dropped, fixture has every series.
- 40 dbt data tests: unique, not-null, accepted values, $1-$10/gal range, contiguous weeks, crude never from the future, data age.

## Numbers
- 14 series, 8,664 raw rows, 2015-01-02 to 2026-11-09.
- Modelling panel: 619 weeks x 6 regions x 2 fuels = 7,428 rows.
- 40 of 40 dbt tests passing.

## Open questions
- None blocking. The API v2 path is implemented but has not been exercised against the live API, because no key is configured.
