import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


def _write_inputs(d: Path) -> None:
    weeks = pd.date_range("2022-01-03", periods=200, freq="7D")
    price = 3.0 + 0.001 * pd.Series(range(200))
    hist = pd.DataFrame({
        "region": "US", "product": "gasoline", "week": weeks, "price": price,
        "wti": 80.0, "brent": 84.0, "change_1w": price.diff(), "change_52w": price.diff(52),
        "avg_4w": price.rolling(4, min_periods=1).mean(), "spread_over_wti": price - 80 / 42,
    })
    hist.to_parquet(d / "history.parquet")
    origin = weeks[-1]
    pd.DataFrame({
        "region": "US", "product": "gasoline", "origin": origin.date(),
        "target_week": [(origin + pd.Timedelta(weeks=h)).date() for h in range(1, 5)],
        "horizon": range(1, 5), "origin_price": price.iloc[-1],
        "pred_model": [3.2, 3.21, 3.22, 3.23], "lo": 3.1, "hi": 3.3,
    }).to_csv(d / "forecast.csv", index=False)
    pd.DataFrame([
        {"region": "US", "product": "gasoline", "horizon": h, "method": m,
         "n": 100, "mae": 0.05 * h, "rmse": 0.07 * h, "mape": 1.5 * h}
        for h in range(1, 5) for m in ["LightGBM", "Last value", "Seasonal naive"]
    ]).to_csv(d / "backtest_metrics.csv", index=False)
    pd.DataFrame({
        "region": "US", "product": "gasoline",
        "feature": ["wti_chg_1w", "spread", "chg_1w", "unknown_feature"],
        "mean_abs_shap": [0.04, 0.03, 0.02, 0.01], "rank": [1, 2, 3, 4],
    }).to_csv(d / "shap_drivers.csv", index=False)
    (d / "run_log.json").write_text(json.dumps({"finished_at": "2026-11-09T15:20:00+00:00"}))


def _run(tmp_path, monkeypatch) -> AppTest:
    monkeypatch.setenv("FUELPULSE_REPORTS", str(tmp_path))
    monkeypatch.setenv("FUELPULSE_DB", str(tmp_path / "missing.duckdb"))
    return AppTest.from_file(APP, default_timeout=30).run()


def test_app_renders_all_sections(tmp_path, monkeypatch):
    _write_inputs(tmp_path)
    at = _run(tmp_path, monkeypatch)
    assert not at.exception
    assert not at.info  # every section found its data
    assert len(at.dataframe) == 1


def test_app_survives_missing_files(tmp_path, monkeypatch):
    at = _run(tmp_path, monkeypatch)
    assert not at.exception
    assert len(at.info) == 4
