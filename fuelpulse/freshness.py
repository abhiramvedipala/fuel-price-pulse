"""Fail the weekly job with a plain message when EIA data is stale.

    python -m fuelpulse.freshness

The warehouse is rebuilt from scratch on every weekly run, so dbt's source
freshness (which reads loaded_at) always sees "just now" and can never fire
there. This checks the newest EIA *week* instead.

Retail weeks start on a Monday and are published that afternoon. A run on
the following Monday that still sees last week as the newest week means the
release is late: warn at 7 days, fail beyond 9. Crude spot prices land about
a week behind retail, so they get a looser limit.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import duckdb

from fuelpulse.ingest import DB_PATH, SERIES

RETAIL_WARN_DAYS, RETAIL_FAIL_DAYS, CRUDE_FAIL_DAYS = 7, 9, 21


def newest_weeks(db_path: Path) -> dict[str, date]:
    con = duckdb.connect(str(db_path), read_only=True)
    out = {}
    for label, crude in (("retail", False), ("crude", True)):
        ids = [s for s, (region, _) in SERIES.items() if (region == "GLOBAL") == crude]
        marks = ",".join("?" * len(ids))
        out[label] = con.execute(
            f"select max(week) from raw_prices where series_id in ({marks})", ids
        ).fetchone()[0]
    con.close()
    return out


def check(newest: dict[str, date], today: date) -> tuple[list[str], list[str]]:
    """Return (warnings, errors) as readable sentences."""
    warnings, errors = [], []
    retail_age = (today - newest["retail"]).days
    if retail_age > RETAIL_FAIL_DAYS:
        errors.append(
            f"Newest EIA retail week is {newest['retail']} ({retail_age} days old, limit "
            f"{RETAIL_FAIL_DAYS}). EIA has skipped a release or the source changed; "
            "check https://www.eia.gov/petroleum/gasdiesel/ and re-run once it is published."
        )
    elif retail_age >= RETAIL_WARN_DAYS:
        warnings.append(
            f"Newest EIA retail week is {newest['retail']} ({retail_age} days old): this "
            "week's release is not out yet. Forecast uses last week's data; the next "
            "scheduled run will pick up the new week."
        )
    crude_age = (today - newest["crude"]).days
    if crude_age > CRUDE_FAIL_DAYS:
        errors.append(
            f"Newest EIA crude price is {newest['crude']} ({crude_age} days old, limit "
            f"{CRUDE_FAIL_DAYS}). The WTI/Brent spot series has stopped updating."
        )
    return warnings, errors


def main() -> None:
    p = argparse.ArgumentParser(description="Check the newest EIA week is recent enough")
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = p.parse_args()
    newest = newest_weeks(args.db)
    warnings, errors = check(newest, args.today)
    print(f"newest retail week {newest['retail']}, newest crude week {newest['crude']}")
    for w in warnings:
        print(f"::warning title=EIA release late::{w}")
    for e in errors:
        print(f"::error title=EIA data stale::{e}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
