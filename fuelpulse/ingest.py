"""Ingest weekly EIA fuel and crude prices into DuckDB.

Two sources produce the same raw table:
  * EIA API v2 when EIA_API_KEY is set,
  * EIA's public no-key weekly history spreadsheets otherwise.

Rows are upserted by (series_id, week), so re-running never duplicates
and only touches rows whose value actually changed.
"""

from __future__ import annotations

import argparse
import io
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("FUELPULSE_DB", ROOT / "data" / "warehouse.duckdb"))
DEFAULT_START = date(2015, 1, 1)

REGIONS = {"NUS": "US", "R10": "PADD1", "R20": "PADD2", "R30": "PADD3", "R40": "PADD4",
           "R50": "PADD5"}

# series_id -> (region, product)
SERIES: dict[str, tuple[str, str]] = {}
for _code, _region in REGIONS.items():
    SERIES[f"EMM_EPMR_PTE_{_code}_DPG"] = (_region, "gasoline")
    SERIES[f"EMD_EPD2D_PTE_{_code}_DPG"] = (_region, "diesel")
SERIES["RWTC"] = ("GLOBAL", "wti")
SERIES["RBRTE"] = ("GLOBAL", "brent")

XLS_URL = "https://www.eia.gov/dnav/pet/hist_xls/{sid}w.xls"
API_URL = "https://api.eia.gov/v2/seriesid/PET.{sid}.W"

DDL = """
create table if not exists raw_prices (
    series_id varchar not null,
    week date not null,
    value double not null,
    source varchar not null,
    loaded_at timestamp not null,
    primary key (series_id, week)
)
"""


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=1.0, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = "fuelpulse/0.1"
    return s


def fetch_xls(sid: str, http: requests.Session) -> pd.DataFrame:
    resp = http.get(XLS_URL.format(sid=sid), timeout=60)
    resp.raise_for_status()
    df = pd.read_excel(io.BytesIO(resp.content), sheet_name="Data 1", skiprows=2,
                       engine="calamine").iloc[:, :2]
    df.columns = ["week", "value"]
    return df


def fetch_api(sid: str, http: requests.Session, key: str) -> pd.DataFrame:
    resp = http.get(API_URL.format(sid=sid), params={"api_key": key}, timeout=60)
    resp.raise_for_status()
    rows = resp.json()["response"]["data"]
    return pd.DataFrame({"week": [r["period"] for r in rows], "value": [r["value"] for r in rows]})


def normalize(df: pd.DataFrame, sid: str, source: str) -> pd.DataFrame:
    out = df.copy()
    out["week"] = pd.to_datetime(out["week"], errors="coerce").dt.date
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["week", "value"])
    out["series_id"] = sid
    out["source"] = source
    return out[["series_id", "week", "value", "source"]].drop_duplicates(["series_id", "week"])


def fetch_all(key: str | None) -> pd.DataFrame:
    http = session()
    frames = []
    for sid in SERIES:
        if key:
            frames.append(normalize(fetch_api(sid, http, key), sid, "eia_api_v2"))
        else:
            frames.append(normalize(fetch_xls(sid, http), sid, "eia_hist_xls"))
    return pd.concat(frames, ignore_index=True)


def watermark(con: duckdb.DuckDBPyConnection) -> date | None:
    """Latest week already loaded, minus 4 weeks so EIA revisions are picked up."""
    row = con.execute("select max(week) from raw_prices").fetchone()
    return row[0] - timedelta(weeks=4) if row and row[0] else None


def upsert(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Insert new (series_id, week) rows and update changed values. Returns rows written."""
    con.execute(DDL)
    con.register("incoming", df[["series_id", "week", "value", "source"]])
    written = con.execute("""
        select count(*) from incoming i
        left join raw_prices r using (series_id, week)
        where r.value is null or r.value <> i.value
    """).fetchone()[0]
    con.execute("""
        insert into raw_prices
        select series_id, week, value, source, ? from incoming
        on conflict (series_id, week) do update
            set value = excluded.value, source = excluded.source,
                loaded_at = excluded.loaded_at
            where raw_prices.value <> excluded.value
    """, [datetime.now(UTC).replace(tzinfo=None)])
    con.unregister("incoming")
    return written


def run(since: date | None = None, db_path: Path = DB_PATH,
        source_df: pd.DataFrame | None = None, start: date = DEFAULT_START) -> int:
    load_dotenv(ROOT / ".env")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(DDL)
    since = max(since or watermark(con) or start, start)
    df = source_df if source_df is not None else fetch_all(os.environ.get("EIA_API_KEY") or None)
    df = df.assign(week=pd.to_datetime(df["week"]).dt.date)
    written = upsert(con, df[df["week"] >= since])
    con.close()
    return written


def main() -> None:
    p = argparse.ArgumentParser(description="Load EIA weekly prices into DuckDB")
    p.add_argument("--since", type=date.fromisoformat, help="only load weeks on/after this date")
    p.add_argument("--fixture", type=Path, help="load a raw_prices CSV instead of calling EIA")
    p.add_argument("--db", type=Path, default=DB_PATH)
    args = p.parse_args()
    src = pd.read_csv(args.fixture) if args.fixture else None
    n = run(args.since, args.db, src)
    print(f"ingest: {n} rows inserted or updated in {args.db}")


if __name__ == "__main__":
    main()
