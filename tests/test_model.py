import numpy as np
import pandas as pd
import pytest

from fuelpulse import model
from fuelpulse.backtest import score
from fuelpulse.features import build_features
from tests.test_features import _panel


@pytest.fixture(scope="module")
def designs():
    return model.make_designs(build_features(_panel(weeks=160)))


def test_training_rows_only_use_published_targets(designs):
    origin = sorted(designs[4]["week"].unique())[120]
    rows = model.trainable(designs[4], origin)
    assert rows["target_week"].max() <= origin
    assert rows["week"].max() <= origin - pd.Timedelta(weeks=4)


def test_baselines_are_what_they_claim(designs):
    weeks = sorted(designs[1]["week"].unique())
    origin = pd.Timestamp(weeks[130])
    fitted = model.fit_all(designs, origin, "pooled", intervals=False)
    fc = model.forecast(fitted, designs, origin)
    assert (fc["pred_last_value"] == fc["origin_price"]).all()
    d = designs[2]
    row = d[(d["week"] == origin) & (d["region"] == "US") & (d["product"] == "gasoline")].iloc[0]
    one = fc[(fc["horizon"] == 2) & (fc["region"] == "US") & (fc["product"] == "gasoline")]
    assert one["pred_seasonal_naive"].iloc[0] == pytest.approx(row["price"] + row["seasonal_chg"])
    assert set(fc["horizon"]) == {1, 2, 3, 4}


def test_conformal_interval_is_positive_and_symmetric(designs):
    origin = pd.Timestamp(sorted(designs[1]["week"].unique())[130])
    fitted = model.fit_all(designs, origin, "pooled", intervals=True)
    fc = model.forecast(fitted, designs, origin)
    assert (fc["hi"] > fc["pred_model"]).all()
    np.testing.assert_allclose(fc["hi"] - fc["pred_model"], fc["pred_model"] - fc["lo"])


def test_score_metrics_by_hand():
    preds = pd.DataFrame({"horizon": [1, 1], "actual": [2.0, 4.0], "pred_model": [3.0, 4.0],
                          "pred_last_value": [2.0, 2.0], "pred_seasonal_naive": [2.0, 4.0]})
    s = score(preds, ["horizon"]).set_index("method")
    assert s.loc["LightGBM", "mae"] == pytest.approx(0.5)
    assert s.loc["LightGBM", "rmse"] == pytest.approx(np.sqrt(0.5))
    assert s.loc["LightGBM", "mape"] == pytest.approx(25.0)
    assert s.loc["Seasonal naive", "mae"] == 0
