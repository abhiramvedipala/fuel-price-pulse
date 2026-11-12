"""Weekly production run: refit on all published data and forecast 4 weeks.

    python -m fuelpulse.forecast

Writes reports/forecast.csv, reports/history.parquet (dashboard fallback
when no warehouse exists, e.g. Streamlit Cloud), reports/run_log.json and
appends one line to reports/run_log.md.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from fuelpulse.features import build_features, load_panel
from fuelpulse.ingest import DB_PATH, ROOT
from fuelpulse.model import fit_all, forecast, make_designs

COLUMNS = ["region", "product", "origin", "target_week", "horizon", "origin_price",
           "pred_model", "lo", "hi"]


def model_mode(reports: Path) -> str:
    path = reports / "model_choice.json"
    return json.loads(path.read_text())["mode"] if path.exists() else "pooled"


def run(db_path: Path = DB_PATH, reports: Path = ROOT / "reports") -> dict:
    started = datetime.now(UTC)
    reports.mkdir(parents=True, exist_ok=True)
    panel = load_panel(db_path)
    designs = make_designs(build_features(panel))
    origin = panel["week"].max()
    mode = model_mode(reports)
    fitted = fit_all(designs, origin, mode, intervals=True)
    fc = forecast(fitted, designs, origin)[COLUMNS]
    fc.to_csv(reports / "forecast.csv", index=False, float_format="%.4f")

    con = duckdb.connect(str(db_path), read_only=True)
    con.execute("select * from mart_price_history order by region, product, week").df() \
        .to_parquet(reports / "history.parquet", index=False)
    con.close()

    log = {
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "latest_eia_week": str(origin.date()),
        "mode": mode,
        "series": int(fc[["region", "product"]].drop_duplicates().shape[0]),
        "forecasts": len(fc),
        "us_gasoline_4w": round(float(fc.query(
            "region == 'US' and product == 'gasoline' and horizon == 4")["pred_model"].iloc[0]), 3),
    }
    (reports / "run_log.json").write_text(json.dumps(log, indent=2) + "\n")
    md = reports / "run_log.md"
    if not md.exists():
        md.write_text("# Weekly run log\n\n| Finished (UTC) | Latest EIA week | Model | "
                      "Forecasts | US gasoline, 4 weeks ahead ($/gal) |\n|---|---|---|---|---|\n")
    with md.open("a") as f:
        f.write(f"| {log['finished_at']} | {log['latest_eia_week']} | {mode} | "
                f"{log['forecasts']} | {log['us_gasoline_4w']:.3f} |\n")
    return log


def main() -> None:
    p = argparse.ArgumentParser(description="Refit and forecast 4 weeks ahead")
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--reports", type=Path, default=ROOT / "reports")
    args = p.parse_args()
    print(json.dumps(run(args.db, args.reports), indent=2))


if __name__ == "__main__":
    main()
