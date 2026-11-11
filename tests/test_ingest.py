from datetime import date

import duckdb
import pandas as pd

from fuelpulse import ingest

EARLY = date(2000, 1, 1)


def _rows(values):
    return pd.DataFrame({
        "series_id": ["EMM_EPMR_PTE_NUS_DPG"] * len(values),
        "week": pd.date_range("2025-01-06", periods=len(values), freq="7D").date,
        "value": values,
        "source": "test",
    })


def _table(db):
    con = duckdb.connect(str(db))
    df = con.execute("select * from raw_prices order by week").df()
    con.close()
    return df


def test_second_run_changes_nothing(tmp_path):
    db = tmp_path / "w.duckdb"
    src = _rows([3.1, 3.2, 3.3])
    assert ingest.run(db_path=db, source_df=src, start=EARLY) == 3
    first = _table(db)
    assert ingest.run(db_path=db, source_df=src, start=EARLY) == 0
    pd.testing.assert_frame_equal(first, _table(db))


def test_revised_value_is_updated_not_duplicated(tmp_path):
    db = tmp_path / "w.duckdb"
    ingest.run(db_path=db, source_df=_rows([3.1, 3.2, 3.3]), start=EARLY)
    assert ingest.run(db_path=db, source_df=_rows([3.1, 3.2, 3.9]), start=EARLY) == 1
    t = _table(db)
    assert len(t) == 3 and t["value"].iloc[-1] == 3.9


def test_since_filters_old_weeks(tmp_path):
    n = ingest.run(since=date(2025, 1, 13), db_path=tmp_path / "w.duckdb",
                   source_df=_rows([1.5, 2.5, 3.5]), start=EARLY)
    assert n == 2


def test_normalize_drops_blank_and_footer_rows():
    raw = pd.DataFrame({"week": ["2025-01-06", None, "junk"], "value": [3.0, 2.0, "x"]})
    out = ingest.normalize(raw, "RWTC", "test")
    assert list(out["value"]) == [3.0]


def test_fixture_covers_every_series():
    fx = pd.read_csv(ingest.ROOT / "data" / "fixtures" / "raw_prices.csv")
    assert set(fx["series_id"]) == set(ingest.SERIES)
