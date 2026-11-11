from datetime import date

import numpy as np
import pandas as pd
import pytest

from fuelpulse.features import (
    BASE_FEATURES,
    HORIZON_FEATURES,
    HORIZONS,
    build_features,
    design,
    holidays,
    is_holiday_week,
)


def _panel(weeks=140, seed=0):
    rng = np.random.default_rng(seed)
    frames = []
    for region in ("US", "PADD5"):
        for product in ("gasoline", "diesel"):
            frames.append(pd.DataFrame({
                "region": region,
                "product": product,
                "week": pd.date_range("2022-01-03", periods=weeks, freq="7D"),
                "price": 3 + rng.normal(0, 0.05, weeks).cumsum(),
                "wti": 70 + rng.normal(0, 2, weeks).cumsum(),
                "brent": 75 + rng.normal(0, 2, weeks).cumsum(),
            }))
    return pd.concat(frames, ignore_index=True)


NUMERIC = BASE_FEATURES + HORIZON_FEATURES


@pytest.mark.parametrize("h", HORIZONS)
def test_no_future_information_in_features(h):
    """Features at week t are identical whether or not later weeks exist."""
    panel = _panel()
    cutoff = panel["week"].unique()[100]
    full = design(build_features(panel), h)
    truncated = design(build_features(panel[panel["week"] <= cutoff]), h)
    a = full[full["week"] <= cutoff].reset_index(drop=True)[NUMERIC]
    b = truncated.reset_index(drop=True)[NUMERIC]
    pd.testing.assert_frame_equal(a, b)


@pytest.mark.parametrize("h", HORIZONS)
def test_changing_the_future_does_not_change_features(h):
    panel = _panel()
    cutoff = panel["week"].unique()[100]
    shocked = panel.copy()
    later = shocked["week"] > cutoff
    shocked.loc[later, ["price", "wti", "brent"]] *= 3
    a = design(build_features(panel), h)
    b = design(build_features(shocked), h)
    keep = a["week"] <= cutoff
    pd.testing.assert_frame_equal(a.loc[keep, NUMERIC], b.loc[keep, NUMERIC])


def test_target_is_the_future_price_change():
    panel = _panel()
    d = design(build_features(panel), 2)
    one = d[(d["region"] == "US") & (d["product"] == "gasoline")].reset_index(drop=True)
    assert one["y"].iloc[10] == pytest.approx(one["price"].iloc[12] - one["price"].iloc[10])
    assert one["y"].iloc[-2:].isna().all()


def test_holiday_dates_2025():
    assert holidays(2025) == [date(2025, 5, 26), date(2025, 7, 4), date(2025, 9, 1),
                              date(2025, 11, 27)]


def test_holiday_week_flag():
    weeks = pd.Series(pd.to_datetime(["2025-06-30", "2025-07-07", "2025-11-24", "2025-05-26"]))
    assert list(is_holiday_week(weeks)) == [1, 0, 1, 1]
