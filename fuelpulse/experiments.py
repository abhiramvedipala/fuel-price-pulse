"""Validation-only experiments: level features, shrinkage, regularisation, interval widths.

    python -m fuelpulse.experiments

Uses the 52 origins before the 104-week test window; nothing here touches the test
origins. Output is saved in reports/model_experiments.md and drove DECISIONS.md #25-#28.
"""
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd

from fuelpulse import model as M
from fuelpulse.backtest import origins
from fuelpulse.features import (
    CATEGORICAL,
    FEATURES,
    HORIZONS,
    KEYS,
    build_features,
    design,
    load_panel,
)

warnings.filterwarnings("ignore")


def main() -> None:
    feats = build_features(load_panel())
    g = feats.groupby(KEYS, sort=False, observed=True)
    feats["vol13"] = g["chg_1w"].transform(lambda s: s.rolling(13).std())
    feats["price_dev52"] = feats.price - g["price"].transform(lambda s: s.rolling(52).mean())
    feats["wti_dev52"] = feats.wti - g["wti"].transform(lambda s: s.rolling(52).mean())
    designs = {h: design(feats, h) for h in HORIZONS}
    val = origins(designs, 156)[:52]
    print("validation origins", val[0].date(), "to", val[-1].date())

    LEV = FEATURES
    DEV = [f for f in FEATURES if f not in ("price", "wti")] + ["price_dev52", "wti_dev52"]
    STRONG = dict(num_leaves=4, min_child_samples=200, n_estimators=120)
    GRID = np.arange(0.0, 1.21, 0.05)
    LEVEL = lambda n: min(1.0, np.ceil((n + 1) * 0.8) / n)  # noqa: E731
    lgbfit = lambda tr, fs, over={}: lgb.LGBMRegressor(**{**M.PARAMS, **over}).fit(tr[fs], tr["y"])  # noqa: E731

    mae_rows, cov_rows = [], []
    for fname, fs in (("levels", LEV), ("dev52", DEV)):
        num = [c for c in fs if c not in CATEGORICAL] + ["vol13"]
        for i in range(0, 52, 4):
            o, weeks = val[i], val[i:i + 4]
            for h in HORIZONS:
                d = designs[h]
                tr = d[d["y"].notna() & (d["target_week"] <= o) & d[num].notna().all(axis=1)]
                rows = d[d["week"].isin(weeks) & d["y"].notna() & d[num].notna().all(axis=1)]
                main = lgbfit(tr, fs)
                pred = main.predict(rows[fs])
                variants = {"base": pred}
                if h >= 3:
                    variants["strongreg"] = lgbfit(tr, fs, STRONG).predict(rows[fs])
                calib = {}
                for W in (52, 104):
                    split = o - pd.Timedelta(weeks=W)
                    older, recent = tr[tr["target_week"] <= split], tr[tr["target_week"] > split]
                    cm = lgbfit(older, fs)
                    calib[W] = (recent, cm.predict(recent[fs]))
                recent, rp = calib[52]
                lam = GRID[np.argmin([np.abs(recent["y"] - k * rp).mean() for k in GRID])]
                variants["shrink"] = lam * pred
                for vname, p in variants.items():
                    err = np.abs(rows["y"] - p)
                    for e, e0 in zip(err, np.abs(rows["y"]), strict=True):
                        mae_rows.append(dict(fs=fname, var=vname, h=h, ae=e, ae_last=e0, lam=lam))
                for shrink in ("none", "lam"):
                    s = lam if shrink == "lam" else 1.0
                    center = s * pred
                    for W in (52, 104):
                        recent, rp = calib[W]
                        e_rec = np.abs(recent["y"].to_numpy() - s * rp)
                        key_rec = recent[KEYS].astype(str).agg("|".join, axis=1).to_numpy()
                        key_row = rows[KEYS].astype(str).agg("|".join, axis=1).to_numpy()
                        widths = {}
                        widths["pooled"] = np.full(len(rows), np.quantile(e_rec, LEVEL(len(e_rec))))
                        w = np.empty(len(rows))
                        for k in np.unique(key_row):
                            m = key_rec == k
                            w[key_row == k] = np.quantile(e_rec[m], LEVEL(m.sum()))
                        widths["per_series"] = w
                        vol_rec = recent["vol13"].to_numpy()
                        q = np.quantile(e_rec / vol_rec, LEVEL(len(e_rec)))
                        widths["vol_scaled"] = q * rows["vol13"].to_numpy()
                        for wname, wid in widths.items():
                            hit = np.abs(rows["y"].to_numpy() - center) <= wid
                            for hh, ww in zip(hit, wid, strict=True):
                                cov_rows.append(dict(fs=fname, shrink=shrink, W=W, width=wname, h=h,
                                                     hit=hh, hw=ww))

    mae = pd.DataFrame(mae_rows)
    t = mae.groupby(["fs", "var", "h"])[["ae", "ae_last"]].mean().unstack("h")
    print("\nVALIDATION MAE by horizon ($/gal) and last-value MAE")
    print(t["ae"].round(4).to_string())
    print("last value:", t["ae_last"].iloc[0].round(4).to_dict())
    lam_by_h = mae.groupby(["fs", "h"])["lam"].mean().unstack().round(2)
    print("\nmean lambda by h:\n", lam_by_h.to_string())
    cov = pd.DataFrame(cov_rows)
    print("\nVALIDATION coverage % (target 80) and mean half-width, all horizons")
    c = cov.groupby(["fs", "shrink", "W", "width"]).agg(cov=("hit", "mean"), hw=("hw", "mean"))
    c["cov"] *= 100
    print(c.round(3).to_string())


if __name__ == "__main__":
    main()
