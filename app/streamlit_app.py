"""Fuel Price Pulse dashboard.

Reads the warehouse mart and the report files written by the weekly job.
Run locally with: uv run streamlit run app/streamlit_app.py

FUELPULSE_REPORTS overrides the reports folder and FUELPULSE_DB the
warehouse path, which is how the smoke test points the app at fixtures.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
REPORTS = Path(os.environ.get("FUELPULSE_REPORTS", ROOT / "reports"))
DB = Path(os.environ.get("FUELPULSE_DB", ROOT / "data" / "warehouse.duckdb"))

REGIONS = ["US", "PADD1", "PADD2", "PADD3", "PADD4", "PADD5"]
PRODUCTS = ["gasoline", "diesel"]
METHODS = ["LightGBM", "Last value", "Seasonal naive"]

LABELS = {
    "price": "Current retail price",
    "chg_1w": "Price change, last week",
    "chg_2w": "Price change, last 2 weeks",
    "chg_4w": "Price change, last 4 weeks",
    "chg_13w": "Price change, last 13 weeks",
    "chg_52w": "Price change, last year",
    "dev_mean_4w": "Price vs its 4-week average",
    "dev_mean_13w": "Price vs its 13-week average",
    "wti": "Crude (WTI) price",
    "wti_chg_1w": "Crude (WTI) change, last week",
    "wti_chg_2w": "Crude (WTI) change, last 2 weeks",
    "wti_chg_4w": "Crude (WTI) change, last 4 weeks",
    "brent_minus_wti": "Brent premium over WTI",
    "spread": "Retail margin over crude",
    "spread_dev_26w": "Retail margin vs its 26-week average",
    "seasonal_chg": "Typical seasonal move for these weeks",
    "target_woy_sin": "Time of year (cycle, sine)",
    "target_woy_cos": "Time of year (cycle, cosine)",
    "target_holiday": "Holiday in the target week",
    "region": "Region",
    "product": "Fuel type",
}


@st.cache_data
def load_history(db: str, fallback: str) -> pd.DataFrame | None:
    if Path(db).exists():
        try:
            with duckdb.connect(db, read_only=True) as con:
                return con.execute("select * from mart_price_history").df()
        except duckdb.Error:
            pass  # table missing or DB locked: try the committed snapshot
    if Path(fallback).exists():
        return pd.read_parquet(fallback)
    return None


@st.cache_data
def load_csv(path: str) -> pd.DataFrame | None:
    return pd.read_csv(path) if Path(path).exists() else None


@st.cache_data
def load_run_log(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def pick(df: pd.DataFrame | None, region: str, product: str) -> pd.DataFrame | None:
    if df is None:
        return None
    out = df[(df["region"] == region) & (df["product"] == product)]
    return out if len(out) else None


st.set_page_config(page_title="Fuel Price Pulse", layout="wide")

with st.sidebar:
    # ?region=PADD5&fuel=diesel opens a specific series (used for screenshots and links)
    qp = st.query_params
    region = st.selectbox("Region", REGIONS, index=REGIONS.index(qp["region"])
                          if qp.get("region") in REGIONS else 0)
    product = st.selectbox("Fuel", PRODUCTS, index=PRODUCTS.index(qp["fuel"])
                           if qp.get("fuel") in PRODUCTS else 0)

history = load_history(str(DB), str(REPORTS / "history.parquet"))
if history is not None:
    history = history.assign(week=pd.to_datetime(history["week"]))
series = pick(history, region, product)
series = series.sort_values("week") if series is not None else None

# Header
st.title("Fuel Price Pulse")
st.caption("Weekly US retail fuel prices from EIA, with a 4-week LightGBM forecast.")
run_log = load_run_log(str(REPORTS / "run_log.json"))
c1, c2 = st.columns(2)
finished = run_log.get("finished_at")
if finished:
    try:
        finished = datetime.fromisoformat(finished).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        pass
c1.metric("Last refresh", finished or "unknown")
c2.metric("Latest EIA week",
          history["week"].max().strftime("%Y-%m-%d") if history is not None else "unknown")

# Price history
st.header(f"{region} {product} price history")
if series is None:
    st.info("No price history found. Run ingest and dbt build, or commit reports/history.parquet.")
else:
    last = series.iloc[-1]
    m1, m2, m3 = st.columns(3)
    m1.metric("Latest price ($/gal)", f"{last['price']:.3f}",
              f"{last['change_1w']:+.3f} vs last week" if pd.notna(last["change_1w"]) else None)
    m2.metric("Change vs a year ago",
              f"{last['change_52w']:+.3f}" if pd.notna(last["change_52w"]) else "n/a")
    m3.metric("Retail margin over crude",
              f"{last['spread_over_wti']:.3f}" if pd.notna(last["spread_over_wti"]) else "n/a")
    max_years = max(1, int((series["week"].max() - series["week"].min()).days // 365) + 1)
    years = st.slider("Years shown", 1, max_years, min(3, max_years))
    shown = series[series["week"] >= series["week"].max() - pd.DateOffset(years=years)]
    long = shown.melt("week", ["price", "avg_4w"], var_name="series", value_name="usd")
    st.altair_chart(alt.Chart(long).mark_line().encode(
        x=alt.X("week:T", title=None), y=alt.Y("usd:Q", title="$ per gallon",
                                               scale=alt.Scale(zero=False)),
        color=alt.Color("series:N", title=None)), use_container_width=True)

# Forecast
st.header("4-week forecast (80% interval)")
fc = pick(load_csv(str(REPORTS / "forecast.csv")), region, product)
if fc is None:
    st.info("No forecast found. Run `uv run python -m fuelpulse.forecast`.")
else:
    fc = fc.assign(target_week=pd.to_datetime(fc["target_week"])).sort_values("horizon")
    layers = []
    if series is not None:
        recent = series.tail(26)
        layers.append(alt.Chart(recent).mark_line().encode(
            x=alt.X("week:T", title="Week"),
            y=alt.Y("price:Q", title="$ per gallon", scale=alt.Scale(zero=False))))
    band = alt.Chart(fc).mark_area(opacity=0.25).encode(
        x="target_week:T", y="lo:Q", y2="hi:Q")
    points = alt.Chart(fc).mark_line(point=True, strokeDash=[4, 3]).encode(
        x="target_week:T", y=alt.Y("pred_model:Q", scale=alt.Scale(zero=False)),
        tooltip=["target_week:T", "pred_model:Q", "lo:Q", "hi:Q"])
    st.altair_chart(alt.layer(*layers, band, points))
    table = fc[["horizon", "target_week", "pred_model", "lo", "hi"]].rename(columns={
        "horizon": "Weeks ahead", "target_week": "Week", "pred_model": "Forecast ($/gal)",
        "lo": "Low (10%)", "hi": "High (90%)"})
    table["Week"] = table["Week"].dt.strftime("%Y-%m-%d")
    st.dataframe(table.round(3), hide_index=True)

# Model vs baselines
st.header("Model vs baselines: backtest MAE")
metrics = pick(load_csv(str(REPORTS / "backtest_metrics.csv")), region, product)
if metrics is None:
    st.info("No backtest metrics found. Run `uv run python -m fuelpulse.backtest`.")
else:
    st.altair_chart(alt.Chart(metrics).mark_bar().encode(
        x=alt.X("horizon:O", title="Weeks ahead"),
        xOffset=alt.XOffset("method:N", sort=METHODS),
        y=alt.Y("mae:Q", title="Mean absolute error ($/gal)"),
        color=alt.Color("method:N", sort=METHODS, title="Method"),
        tooltip=["method", "horizon", "mae", "rmse", "mape", "n"],
    ))
    st.caption("Lower is better. Each bar is scored on the same held-out weeks.")

# Drivers
st.header("Top drivers of the forecast")
shap = pick(load_csv(str(REPORTS / "shap_drivers.csv")), region, product)
if shap is None:
    st.info("No driver report found for this series.")
else:
    top = shap.sort_values("rank").head(8)
    top = top.assign(label=top["feature"].map(LABELS).fillna(top["feature"]))
    st.altair_chart(alt.Chart(top).mark_bar().encode(
        x=alt.X("mean_abs_shap:Q", title="Average impact on forecast ($/gal)"),
        y=alt.Y("label:N", sort="-x", title=None),
        tooltip=["feature", "mean_abs_shap"],
    ))
