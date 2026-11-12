"""Rolling-origin backtest of the forecaster against two baselines.

For each origin week in the test window the model only sees rows whose
targets were already published, forecasts 1-4 weeks ahead, and is scored
against what EIA later reported. Writes reports/ and one chart.

    python -m fuelpulse.backtest            # last 104 origins, refit every 4 weeks
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fuelpulse.features import HORIZONS, build_features, load_panel
from fuelpulse.ingest import DB_PATH, ROOT
from fuelpulse.model import COVERAGE, fit_all, forecast, make_designs

METHODS = {"pred_model": "LightGBM", "pred_last_value": "Last value",
           "pred_seasonal_naive": "Seasonal naive"}
CMD = "uv run python -m fuelpulse.backtest"


def origins(designs: dict, n: int) -> list[pd.Timestamp]:
    """The last n weeks whose 4-week-ahead actual is already known."""
    d = designs[max(HORIZONS)]
    known = sorted(d.loc[d["y"].notna(), "week"].unique())
    return [pd.Timestamp(w) for w in known[-n:]]


def run_window(designs: dict, weeks: list[pd.Timestamp], mode: str, refit_every: int,
               intervals: bool) -> pd.DataFrame:
    frames, fitted = [], None
    for i, origin in enumerate(weeks):
        if i % refit_every == 0:
            fitted = fit_all(designs, origin, mode, intervals)
        frames.append(forecast(fitted, designs, origin))
    return pd.concat(frames, ignore_index=True)


def score(preds: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """MAE, RMSE and MAPE per method, long format."""
    rows = []
    for keys, part in preds.groupby(by, observed=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        for col, name in METHODS.items():
            err = part[col] - part["actual"]
            rows.append({**dict(zip(by, keys, strict=True)), "method": name, "n": len(part),
                         "mae": err.abs().mean(), "rmse": np.sqrt((err**2).mean()),
                         "mape": (err.abs() / part["actual"]).mean() * 100})
    return pd.DataFrame(rows)


def choose_mode(designs: dict, val_weeks: list[pd.Timestamp], refit_every: int) -> dict:
    """Pooled vs per-series, judged on the year before the test window."""
    out = {}
    for mode in ("pooled", "per_series"):
        p = run_window(designs, val_weeks, mode, refit_every, intervals=False)
        out[mode] = float((p["pred_model"] - p["actual"]).abs().mean())
    return out


def pivot(scores: pd.DataFrame, index: str, value: str) -> pd.DataFrame:
    return scores.pivot(index=index, columns="method", values=value)[list(METHODS.values())]


def md_table(df: pd.DataFrame, fmt: str) -> str:
    head = f"| {df.index.name} | " + " | ".join(df.columns) + " |\n"
    head += "|---" * (len(df.columns) + 1) + "|\n"
    return head + "".join(
        f"| {idx} | " + " | ".join(fmt.format(v) for v in row) + " |\n"
        for idx, row in zip(df.index, df.to_numpy(), strict=True))


def report(preds: pd.DataFrame, by_h: pd.DataFrame, by_region: pd.DataFrame, val: dict,
           mode: str, refit_every: int) -> str:
    first, last = preds["origin"].min().date(), preds["origin"].max().date()
    n_origins = preds["origin"].nunique()
    mae = pivot(by_h, "horizon", "mae")
    gain_last = (1 - mae["LightGBM"] / mae["Last value"]) * 100
    gain_seas = (1 - mae["LightGBM"] / mae["Seasonal naive"]) * 100
    covered = preds.assign(hit=preds["actual"].between(preds["lo"], preds["hi"]))
    cov = covered.groupby("horizon")["hit"].mean() * 100
    width = (preds["hi"] - preds["lo"]).groupby(preds["horizon"]).mean() / 2
    overall = score(preds.assign(all="all"), ["all"]).set_index("method")
    lines = [
        "## Backtest\n",
        f"Command: `{CMD}`\n",
        f"Rolling-origin evaluation over {n_origins} weekly origins ({first} to {last}), "
        f"{preds[['region', 'product']].drop_duplicates().shape[0]} series, "
        f"{len(preds):,} forecasts. The model is refit every {refit_every} weeks on rows whose "
        "targets were already published at that origin. Errors are in dollars per gallon.\n",
        f"Model choice: **{mode}**. On the 52 origins before the test window, validation MAE "
        f"was {val['pooled']:.4f} pooled vs {val['per_series']:.4f} per-series.\n",
        "### MAE by horizon ($/gal)\n",
        md_table(mae.rename_axis("Weeks ahead"), "{:.4f}"),
        "\n### RMSE by horizon ($/gal)\n",
        md_table(pivot(by_h, "horizon", "rmse").rename_axis("Weeks ahead"), "{:.4f}"),
        "\n### MAPE by horizon (%)\n",
        md_table(pivot(by_h, "horizon", "mape").rename_axis("Weeks ahead"), "{:.2f}"),
        "\n### LightGBM MAE change vs each baseline (positive = model is better)\n",
        md_table(pd.DataFrame({"vs last value (%)": gain_last, "vs seasonal naive (%)": gain_seas}
                              ).rename_axis("Weeks ahead"), "{:+.1f}"),
        "\n### All horizons combined\n",
        md_table(overall[["mae", "rmse", "mape"]].rename(
            columns={"mae": "MAE", "rmse": "RMSE", "mape": "MAPE (%)"}
        ).loc[list(METHODS.values())].rename_axis("Method"), "{:.4f}"),
        "\n### MAE by region, all horizons ($/gal)\n",
        md_table(pivot(by_region, "region", "mae").rename_axis("Region"), "{:.4f}"),
        f"\n### {COVERAGE:.0%} prediction intervals (split conformal, scaled by trailing "
        "volatility, 104-week calibration)\n",
        md_table(pd.DataFrame({"Empirical coverage (%)": cov, "Mean half-width ($/gal)": width}
                              ).rename_axis("Weeks ahead"), "{:.3f}"),
        f"\nOverall coverage: {covered['hit'].mean() * 100:.1f}% against a {COVERAGE:.0%} "
        "target.\n",
        "\nFull per-region, per-fuel, per-horizon scores: `reports/backtest_metrics.csv`. "
        "Chart: `docs/backtest_mae.png`.\n",
    ]
    return "\n".join(lines)


def chart(by_h: pd.DataFrame, path: Path) -> None:
    mae = pivot(by_h, "horizon", "mae")
    ax = mae.plot(kind="bar", figsize=(7, 4), width=0.8, color=["#1f6feb", "#8b949e", "#d29922"])
    ax.set(xlabel="Weeks ahead", ylabel="MAE ($/gal)",
           title="Backtest error by horizon: model vs baselines")
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=150)
    plt.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Rolling-origin backtest")
    p.add_argument("--weeks", type=int, default=104, help="number of test origins")
    p.add_argument("--val-weeks", type=int, default=52)
    p.add_argument("--refit-every", type=int, default=4)
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--out", type=Path, default=ROOT / "reports")
    p.add_argument("--chart", type=Path, default=ROOT / "docs" / "backtest_mae.png")
    args = p.parse_args()

    designs = make_designs(build_features(load_panel(args.db)))
    all_weeks = origins(designs, args.weeks + args.val_weeks)
    val_weeks, test_weeks = all_weeks[:-args.weeks], all_weeks[-args.weeks:]

    val = choose_mode(designs, val_weeks, args.refit_every)
    mode = min(val, key=val.get)
    preds = run_window(designs, test_weeks, mode, args.refit_every, intervals=True)

    by_h = score(preds, ["horizon"])
    by_region = score(preds, ["region"])
    detail = score(preds, ["region", "product", "horizon"])
    args.out.mkdir(parents=True, exist_ok=True)
    preds.to_csv(args.out / "backtest_predictions.csv", index=False, float_format="%.4f")
    detail.to_csv(args.out / "backtest_metrics.csv", index=False, float_format="%.5f")
    text = report(preds, by_h, by_region, val, mode, args.refit_every)
    (args.out / "backtest.md").write_text(text)
    (args.out / "model_choice.json").write_text(json.dumps({"mode": mode, "validation_mae": val}))
    chart(by_h, args.chart)
    print(text)


if __name__ == "__main__":
    main()
