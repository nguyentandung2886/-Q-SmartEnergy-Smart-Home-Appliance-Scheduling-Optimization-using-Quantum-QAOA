"""Tests cho forecaster.py — mô hình ML cổ điển dự báo thời gian chạy (Vòng Phụ Mức TB)."""
import numpy as np
import pytest

import forecaster
from forecaster import (
    FORECAST_SCHEMA,
    JobDurationForecaster,
    LinearRegression,
    mean_absolute_error,
    model_mae,
    predict_duration,
)


def test_linear_regression_recovers_known_coefficients():
    # y = 3 + 2*x0 - 1*x1 (không nhiễu) -> lstsq phải khôi phục gần đúng.
    rng = np.random.default_rng(0)
    X = rng.uniform(-5, 5, size=(200, 2))
    y = 3.0 + 2.0 * X[:, 0] - 1.0 * X[:, 1]
    model = LinearRegression().fit(X, y)
    assert model.intercept_ == pytest.approx(3.0, abs=1e-6)
    assert model.coef_[0] == pytest.approx(2.0, abs=1e-6)
    assert model.coef_[1] == pytest.approx(-1.0, abs=1e-6)


def test_mean_absolute_error_basic():
    assert mean_absolute_error([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0
    assert mean_absolute_error([1.0, 2.0], [2.0, 4.0]) == pytest.approx(1.5)


def test_each_appliance_model_trains_with_low_error():
    # MAE test phải nhỏ (mô hình học được quan hệ tuyến tính ẩn dưới nhiễu).
    for name in FORECAST_SCHEMA:
        assert model_mae(name) < 0.15, f"{name} MAE quá cao: {model_mae(name)}"


def test_washing_machine_duration_increases_with_load():
    # Đơn điệu tăng theo khối lượng đồ (giữ nguyên chương trình).
    light = predict_duration("Máy giặt", {"load_kg": 2, "program": "normal"})
    heavy = predict_duration("Máy giặt", {"load_kg": 8, "program": "normal"})
    assert heavy > light


def test_washing_machine_duration_increases_with_program_intensity():
    quick = predict_duration("Máy giặt", {"load_kg": 5, "program": "quick"})
    heavy = predict_duration("Máy giặt", {"load_kg": 5, "program": "heavy"})
    assert heavy > quick


def test_water_heater_duration_increases_with_people():
    few = predict_duration("Bình nước nóng gián tiếp", {"people": 1})
    many = predict_duration("Bình nước nóng gián tiếp", {"people": 6})
    assert many > few


def test_predict_duration_clamped_to_minimum():
    # Đặc trưng cực nhỏ vẫn không cho ra duration < 0.25h.
    assert predict_duration("Máy giặt", {"load_kg": 0.1, "program": "quick"}) >= 0.25


def test_unknown_appliance_raises():
    with pytest.raises(KeyError):
        predict_duration("Tủ lạnh", {"load_kg": 1})


def test_invalid_program_raises():
    with pytest.raises(ValueError):
        predict_duration("Máy giặt", {"load_kg": 5, "program": "turbo"})


def test_missing_feature_raises():
    with pytest.raises(ValueError):
        predict_duration("Bình nước nóng gián tiếp", {})


def test_forecaster_deterministic_with_fixed_seed():
    a = JobDurationForecaster("Máy giặt", seed=7)
    b = JobDurationForecaster("Máy giặt", seed=7)
    assert a.test_mae == b.test_mae
    assert np.allclose(a.model.coef_, b.model.coef_)
