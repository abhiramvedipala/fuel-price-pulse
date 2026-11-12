"""Baselines, the LightGBM direct multi-horizon forecaster and its intervals.

Direct means one model per horizon (1-4 weeks). Every model predicts the
price *change* from the origin week, and changes are added back to the
origin price to get a level forecast.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd

from fuelpulse.features import (
    BASE_FEATURES,
    FEATURES,
    HELPERS,
    HORIZON_FEATURES,
    HORIZONS,
    KEYS,
    design,
)

NUMERIC = BASE_FEATURES + HORIZON_FEATURES
COVERAGE = 0.80
CALIB_WEEKS = 104
MIN_VOL = 0.01  # $/gal floor so a flat stretch cannot divide by ~zero

# Small, heavily regularised trees with an L1 objective. Chosen on the
# validation year only (see DECISIONS.md); weekly price changes are
# heavy-tailed, and L1 stops a few shock weeks from dominating the fit.
# ponytail: six hand-picked variants, not a search; add Optuna if it matters.
PARAMS = dict(
    objective="l1", n_estimators=200, learning_rate=0.03, num_leaves=7,
    min_child_samples=100,
    subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
    random_state=7, n_jobs=2, deterministic=True, force_row_wise=True, verbose=-1,
)


def trainable(d: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    """Rows whose target was already observed at `origin` and whose lags exist."""
    ok = d["y"].notna() & (d["target_week"] <= origin) & d[NUMERIC].notna().all(axis=1)
    return d[ok]


def fit(train: pd.DataFrame, features: list[str]) -> lgb.LGBMRegressor:
    return lgb.LGBMRegressor(**PARAMS).fit(train[features], train["y"])


@dataclass
class Fitted:
    """Models and interval half-widths as of one origin week."""
    mode: str
    models: dict = field(default_factory=dict)  # h -> model, or (h, region, product) -> model
    half_width: dict[int, float] = field(default_factory=dict)

    def predict_change(self, rows: pd.DataFrame, h: int) -> np.ndarray:
        if self.mode == "pooled":
            return self.models[h].predict(rows[FEATURES])
        out = pd.Series(np.nan, index=rows.index)
        for (region, product), part in rows.groupby(KEYS, observed=True):
            out.loc[part.index] = self.models[(h, region, product)].predict(part[NUMERIC])
        return out.to_numpy()


def conformal_half_width(d: pd.DataFrame, origin: pd.Timestamp, coverage: float = COVERAGE,
                         calib_weeks: int = CALIB_WEEKS) -> float:
    """Volatility-scaled split conformal: returns a multiplier of recent volatility.

    Fit on older data, then measure errors on the most recent weeks, which are
    out of sample for that model. Each error is divided by the series' trailing
    13-week volatility, so the band is wide when prices are moving and narrow
    when they are calm. The forecast's half-width is this multiplier times the
    volatility at the forecast origin. A 104-week window and this scaling were
    chosen on the validation year (DECISIONS.md #25).
    """
    rows = trainable(d, origin)
    rows = rows[rows["vol_13w"].notna()]
    n_weeks = rows["target_week"].nunique()
    calib_weeks = min(calib_weeks, n_weeks // 3)
    split = origin - pd.Timedelta(weeks=calib_weeks)
    older, recent = rows[rows["target_week"] <= split], rows[rows["target_week"] > split]
    resid = np.abs(recent["y"] - fit(older, FEATURES).predict(recent[FEATURES]))
    scaled = resid / recent["vol_13w"].clip(lower=MIN_VOL)
    n = len(scaled)
    level = min(1.0, np.ceil((n + 1) * coverage) / n)  # finite-sample correction
    return float(np.quantile(scaled, level))


def fit_all(designs: dict[int, pd.DataFrame], origin: pd.Timestamp, mode: str = "pooled",
            intervals: bool = True) -> Fitted:
    fitted = Fitted(mode)
    for h in HORIZONS:
        train = trainable(designs[h], origin)
        if mode == "pooled":
            fitted.models[h] = fit(train, FEATURES)
        else:
            for (region, product), part in train.groupby(KEYS, observed=True):
                fitted.models[(h, region, product)] = fit(part, NUMERIC)
        if intervals:
            fitted.half_width[h] = conformal_half_width(designs[h], origin)
    return fitted


def forecast(fitted: Fitted, designs: dict[int, pd.DataFrame], origin: pd.Timestamp
             ) -> pd.DataFrame:
    """Level forecasts from one origin week for every series and horizon."""
    frames = []
    for h in HORIZONS:
        d = designs[h]
        rows = d[(d["week"] == origin) & d[NUMERIC + HELPERS].notna().all(axis=1)]
        out = rows[KEYS + ["week", "target_week", "price"]].rename(
            columns={"week": "origin", "price": "origin_price"})
        out["horizon"] = h
        out["actual"] = rows["price"] + rows["y"]
        out["pred_model"] = rows["price"] + fitted.predict_change(rows, h)
        out["pred_last_value"] = rows["price"]
        out["pred_seasonal_naive"] = rows["price"] + rows["seasonal_chg"]
        width = fitted.half_width.get(h, np.nan) * rows["vol_13w"].clip(lower=MIN_VOL)
        out["lo"], out["hi"] = out["pred_model"] - width, out["pred_model"] + width
        frames.append(out)
    return pd.concat(frames, ignore_index=True)


def make_designs(feats: pd.DataFrame) -> dict[int, pd.DataFrame]:
    return {h: design(feats, h) for h in HORIZONS}
