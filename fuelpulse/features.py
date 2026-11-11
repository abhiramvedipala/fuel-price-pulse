"""Feature building for the weekly forecaster.

Every feature on the row for week t uses only information published on or
before t. The target for horizon h is the price change from t to t+h, so
tree models learn moves rather than levels they cannot extrapolate.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from fuelpulse.ingest import DB_PATH

HORIZONS = (1, 2, 3, 4)
KEYS = ["region", "product"]
GALLONS_PER_BARREL = 42.0

BASE_FEATURES = [
    "price", "chg_1w", "chg_2w", "chg_4w", "chg_13w", "chg_52w",
    "dev_mean_4w", "dev_mean_13w",
    "wti", "wti_chg_1w", "wti_chg_2w", "wti_chg_4w", "brent_minus_wti",
    "spread", "spread_dev_26w",
]
HORIZON_FEATURES = ["seasonal_chg", "target_woy_sin", "target_woy_cos", "target_holiday"]
CATEGORICAL = ["region", "product"]
FEATURES = BASE_FEATURES + HORIZON_FEATURES + CATEGORICAL


def holidays(year: int) -> list[date]:
    """Memorial Day, July 4th, Labor Day and Thanksgiving for a year."""
    may31 = date(year, 5, 31)
    memorial = may31 - timedelta(days=may31.weekday())  # last Monday of May
    sep1 = date(year, 9, 1)
    labor = sep1 + timedelta(days=(7 - sep1.weekday()) % 7)  # first Monday of September
    nov1 = date(year, 11, 1)
    thanksgiving = nov1 + timedelta(days=(3 - nov1.weekday()) % 7 + 21)  # 4th Thursday
    return [memorial, date(year, 7, 4), labor, thanksgiving]


def is_holiday_week(week: pd.Series) -> pd.Series:
    """1 when a holiday falls in the 7 days starting at `week` (a Monday)."""
    weeks = pd.to_datetime(week)
    years = range(weeks.dt.year.min(), weeks.dt.year.max() + 2)
    starts = {
        pd.Timestamp(h - timedelta(days=h.weekday())) for y in years for h in holidays(y)
    }
    return weeks.isin(starts).astype(int)


def load_panel(db_path: Path = DB_PATH) -> pd.DataFrame:
    con = duckdb.connect(str(db_path), read_only=True)
    df = con.execute(
        "select region, product, week, price, wti, brent from mart_model_input order by 1, 2, 3"
    ).df()
    con.close()
    df["week"] = pd.to_datetime(df["week"])
    return df


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add backward-looking features. One row per region x product x week."""
    df = panel.sort_values(KEYS + ["week"]).reset_index(drop=True).copy()
    g = df.groupby(KEYS, sort=False)
    for n in (1, 2, 4, 13, 52):
        df[f"chg_{n}w"] = df["price"] - g["price"].shift(n)
    for n in (4, 13):
        mean = g["price"].transform(lambda s, n=n: s.rolling(n).mean())
        df[f"dev_mean_{n}w"] = df["price"] - mean
    for n in (1, 2, 4):
        df[f"wti_chg_{n}w"] = df["wti"] - g["wti"].shift(n)
    df["brent_minus_wti"] = df["brent"] - df["wti"]
    df["spread"] = df["price"] - df["wti"] / GALLONS_PER_BARREL
    spread_mean = df.groupby(KEYS, sort=False)["spread"].transform(lambda s: s.rolling(26).mean())
    df["spread_dev_26w"] = df["spread"] - spread_mean
    for col in CATEGORICAL:
        df[col] = df[col].astype("category")
    return df


def design(feats: pd.DataFrame, h: int) -> pd.DataFrame:
    """Features plus target for horizon h. `y` is NaN where t+h is not yet known."""
    df = feats.copy()
    g = df.groupby(KEYS, sort=False, observed=True)["price"]
    # Change over the same h weeks one year ago: price[t+h-52] - price[t-52]. Both in the past.
    df["seasonal_chg"] = g.shift(52 - h) - g.shift(52)
    target_week = df["week"] + pd.Timedelta(weeks=h)
    woy = target_week.dt.isocalendar().week.astype(float)
    df["target_woy_sin"] = np.sin(2 * np.pi * woy / 52.18)
    df["target_woy_cos"] = np.cos(2 * np.pi * woy / 52.18)
    df["target_holiday"] = is_holiday_week(target_week)
    df["target_week"] = target_week
    df["y"] = g.shift(-h) - df["price"]
    return df
