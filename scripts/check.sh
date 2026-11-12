#!/usr/bin/env bash
# One command to verify the repo: lint, tests, ingest, dbt build, backtest.
#   scripts/check.sh            live EIA data into data/warehouse.duckdb
#   scripts/check.sh --fixture  offline, frozen fixture into data/ci.duckdb (CI)
set -euo pipefail
cd "$(dirname "$0")/.."

DBT_ARGS=(--project-dir dbt --profiles-dir dbt)
INGEST_ARGS=()
if [[ "${1:-}" == "--fixture" ]]; then
  export FUELPULSE_DB="data/ci.duckdb"
  rm -f "$FUELPULSE_DB"
  INGEST_ARGS=(--fixture data/fixtures/raw_prices.csv --db "$FUELPULSE_DB")
  # The fixture is frozen, so the data-age test cannot apply to it.
  DBT_ARGS+=(--vars '{max_staleness_days: 100000}')
fi

echo "== ruff ==";   uv run ruff check .
echo "== pytest =="; uv run pytest -q
echo "== ingest =="; uv run python -m fuelpulse.ingest ${INGEST_ARGS[@]+"${INGEST_ARGS[@]}"}
echo "== dbt build =="; uv run dbt build "${DBT_ARGS[@]}"
echo "== forecast smoke =="
SMOKE="$(mktemp -d)"
uv run python -m fuelpulse.forecast --db "${FUELPULSE_DB:-data/warehouse.duckdb}" --reports "$SMOKE" > /dev/null
test -s "$SMOKE/forecast.csv"
if [[ -z "${FUELPULSE_DB:-}" ]]; then
  echo "== backtest smoke (8 origins; full run: python -m fuelpulse.backtest) =="
  uv run python -m fuelpulse.backtest --weeks 8 --val-weeks 8 --refit-every 8 \
    --out "$SMOKE" --chart "$SMOKE/mae.png" > /dev/null
fi
echo "check.sh: all green"
