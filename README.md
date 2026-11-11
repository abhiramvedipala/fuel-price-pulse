# Fuel Price Pulse

Weekly forecasts of U.S. retail gasoline and diesel prices, four weeks ahead, built on public EIA data.

## Problem
I work at a gas station, and the question that comes up every week is simple: where are prices heading over the next month? This project ingests the government's weekly price surveys, models them, and (in later phases) forecasts them against honest baselines.

## Quick start
Prerequisites: [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
scripts/check.sh
```

`scripts/check.sh` lints, runs the tests, ingests EIA data into `data/warehouse.duckdb` and runs `dbt build`. No API key is needed. Add `--fixture` to run fully offline.

## Status
Phase 1 (ingestion and warehouse) is complete. See [PROGRESS.md](PROGRESS.md), [RESULTS.md](RESULTS.md) and [DECISIONS.md](DECISIONS.md). The full README arrives with the dashboard in Phase 4.
