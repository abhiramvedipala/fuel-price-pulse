"""SHAP drivers and failure weeks for the pooled LightGBM forecaster.

    python -m fuelpulse.explain

Trains the same models the weekly job uses (as of the latest week), explains
the most recent 104 weeks of predictions, and writes:
  reports/shap_drivers.csv   region, product, feature, mean_abs_shap, rank
  reports/shap.md            tables for RESULTS.md, including the worst weeks
  docs/shap_summary.png      beeswarm for the 4-week-ahead model
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from fuelpulse.backtest import md_table
from fuelpulse.features import FEATURES, HORIZONS, KEYS, build_features, load_panel
from fuelpulse.ingest import DB_PATH, ROOT
from fuelpulse.model import fit, make_designs, trainable

CMD = "uv run python -m fuelpulse.explain"
RECENT = 104


def shap_values(designs: dict, origin: pd.Timestamp) -> dict[int, tuple[pd.DataFrame, np.ndarray]]:
    """Per horizon: the explained rows and their SHAP matrix (rows x FEATURES)."""
    out = {}
    for h in HORIZONS:
        d = designs[h]
        model = fit(trainable(d, origin), FEATURES)
        recent = d[(d["week"] > origin - pd.Timedelta(weeks=RECENT)) & (d["week"] <= origin)]
        recent = recent.dropna(subset=FEATURES)
        values = shap.TreeExplainer(model).shap_values(recent[FEATURES])
        out[h] = (recent, values)
    return out


def drivers(sv: dict) -> pd.DataFrame:
    """Mean |SHAP| per region x product x feature, averaged over the 4 horizons."""
    frames = []
    for rows, values in sv.values():
        df = pd.DataFrame(np.abs(values), columns=FEATURES)
        df[KEYS] = rows[KEYS].astype(str).to_numpy()
        frames.append(df.groupby(KEYS).mean().stack().rename("mean_abs_shap").reset_index())
    out = pd.concat(frames).groupby(KEYS + ["level_2"], as_index=False)["mean_abs_shap"].mean()
    out = out.rename(columns={"level_2": "feature"})
    out["rank"] = out.groupby(KEYS)["mean_abs_shap"].rank(ascending=False, method="first")
    return out.sort_values(KEYS + ["rank"]).astype({"rank": int})


def worst_weeks(preds_path: Path, n: int = 6) -> pd.DataFrame:
    """Weeks where the 4-week-ahead forecast missed by the most, averaged over series."""
    p = pd.read_csv(preds_path, parse_dates=["origin", "target_week"])
    p = p[p["horizon"] == 4].assign(err=lambda d: d["pred_model"] - d["actual"])
    g = p.groupby("target_week").agg(
        mae=("err", lambda s: s.abs().mean()), bias=("err", "mean"),
        actual_move=("actual", "mean"), origin_price=("origin_price", "mean"))
    g["actual_move"] = g["actual_move"] - g["origin_price"]
    g.index = g.index.strftime("%Y-%m-%d")
    return g.sort_values("mae", ascending=False).head(n)[["mae", "bias", "actual_move"]]


def report(d: pd.DataFrame, worst: pd.DataFrame, origin: pd.Timestamp) -> str:
    overall = d.groupby("feature")["mean_abs_shap"].mean().sort_values(ascending=False)
    top = overall.head(8).to_frame("Mean absolute SHAP ($/gal)")
    top.index.name = "Feature"
    per = d[d["rank"] <= 3].pivot_table(index=["region", "product"], columns="rank",
                                        values="feature", aggfunc="first")
    per.columns = ["#1", "#2", "#3"]
    lines = [
        "## SHAP drivers\n",
        f"Command: `{CMD}`\n",
        f"Models trained on all targets published by {origin.date()}; SHAP computed on the "
        f"last {RECENT} weeks, averaged over the 1-4 week horizons. Values are the average "
        "absolute contribution to the predicted price change, in dollars per gallon.\n",
        "### Top drivers, all series\n",
        md_table(top, "{:.4f}"),
        "\n### Top 3 drivers per region and fuel\n",
        "| Series | #1 | #2 | #3 |\n|---|---|---|---|\n" + "".join(
            f"| {r} {p} | " + " | ".join(row) + " |\n" for (r, p), row in
            zip(per.index, per.to_numpy(), strict=True)),
        "\n### Weeks where the 4-week-ahead forecast failed most\n",
        "Backtest target weeks with the largest average absolute error across the 12 series "
        "(`reports/backtest_predictions.csv`). Bias is forecast minus actual; actual move is "
        "the realised change from the origin price.\n",
        md_table(worst.rename_axis("Target week").rename(
            columns={"mae": "MAE ($/gal)", "bias": "Bias ($/gal)",
                     "actual_move": "Actual move ($/gal)"}), "{:+.3f}"),
    ]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="SHAP drivers")
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--out", type=Path, default=ROOT / "reports")
    p.add_argument("--chart", type=Path, default=ROOT / "docs" / "shap_summary.png")
    args = p.parse_args()

    panel = load_panel(args.db)
    designs = make_designs(build_features(panel))
    origin = panel["week"].max()
    sv = shap_values(designs, origin)
    d = drivers(sv)
    args.out.mkdir(parents=True, exist_ok=True)
    d.to_csv(args.out / "shap_drivers.csv", index=False, float_format="%.5f")
    text = report(d, worst_weeks(args.out / "backtest_predictions.csv"), origin)
    (args.out / "shap.md").write_text(text)

    rows, values = sv[4]
    shap.summary_plot(values, rows[FEATURES], max_display=12, show=False)
    plt.title("What moves the 4-week-ahead price change (SHAP)")
    plt.tight_layout()
    args.chart.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.chart, dpi=150, bbox_inches="tight")
    plt.close()
    print(text)


if __name__ == "__main__":
    main()
