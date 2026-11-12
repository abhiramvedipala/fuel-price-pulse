"""Assemble RESULTS.md from artifacts other commands produced.

Every number is read from the warehouse or a file under reports/ or
dbt/target/, and each section names the command that produced it.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from fuelpulse.ingest import DB_PATH, ROOT

REPORTS = ROOT / "reports"


def ingest_section(db_path: Path = DB_PATH) -> str:
    con = duckdb.connect(str(db_path), read_only=True)
    rows, series, first, last = con.execute(
        "select count(*), count(distinct series_id), min(week), max(week) from raw_prices"
    ).fetchone()
    panel, weeks, pfirst, plast = con.execute(
        "select count(*), count(distinct week), min(week), max(week) from mart_model_input"
    ).fetchone()
    con.close()
    return (
        "## Data ingested\n\n"
        "Command: `uv run python -m fuelpulse.ingest && "
        "uv run dbt build --project-dir dbt --profiles-dir dbt`\n\n"
        "| Measure | Value |\n|---|---|\n"
        f"| EIA series ingested | {series} (12 retail, 2 crude) |\n"
        f"| Raw rows (series x week) | {rows:,} |\n"
        f"| Raw date range | {first} to {last} |\n"
        f"| Weeks in the modelling panel | {weeks} ({weeks / 52.18:.1f} years) |\n"
        f"| Panel rows (6 regions x 2 fuels x weeks) | {panel:,} |\n"
        f"| Panel date range | {pfirst} to {plast} |\n"
    )


def dbt_section() -> str:
    path = ROOT / "dbt" / "target" / "run_results.json"
    if not path.exists():
        return ""
    results = json.loads(path.read_text())["results"]
    tests = [r for r in results if r["unique_id"].startswith("test.")]
    passed = sum(r["status"] == "pass" for r in tests)
    models = sum(r["unique_id"].startswith(("model.", "seed.")) for r in results)
    return (
        "## dbt tests\n\n"
        "Command: `uv run dbt build --project-dir dbt --profiles-dir dbt` "
        "(counts read from `dbt/target/run_results.json`)\n\n"
        "| Measure | Value |\n|---|---|\n"
        f"| dbt data tests | {len(tests)} ({passed} passing) |\n"
        f"| Models and seeds built | {models} |\n"
    )


def file_section(name: str) -> str:
    path = REPORTS / name
    return path.read_text() if path.exists() else ""


def build() -> str:
    parts = [
        "# Results\n\nEvery number below is produced by a script in this repo. "
        "Regenerate the whole file with `uv run python -m fuelpulse.results` after "
        "running the commands listed in each section.\n",
        ingest_section(),
        dbt_section(),
        file_section("backtest.md"),
        file_section("backtest_before.md"),
        file_section("model_experiments.md"),
        file_section("shap.md"),
    ]
    return "\n".join(p for p in parts if p)


if __name__ == "__main__":
    (ROOT / "RESULTS.md").write_text(build())
    print("wrote RESULTS.md")
