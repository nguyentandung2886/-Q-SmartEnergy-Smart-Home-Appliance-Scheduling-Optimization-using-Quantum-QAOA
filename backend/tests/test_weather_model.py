"""
Tests for weather_model.py — the classical weather-forecast layer of the Hybrid
Quantum-Classical architecture (Vòng Phụ Mức Khó, +25đ).
"""

import pytest

from core.weather_model import WEATHER_MULTIPLIERS, solar_multiplier


def test_sunny_multiplier_is_one():
    assert solar_multiplier("sunny") == 1.0


def test_cloudy_multiplier_is_zero_point_six():
    assert solar_multiplier("cloudy") == 0.6


def test_rainy_multiplier_is_zero_point_two_five():
    assert solar_multiplier("rainy") == 0.25


def test_invalid_weather_condition_raises_value_error():
    with pytest.raises(ValueError):
        solar_multiplier("snowy")


def test_all_multipliers_in_valid_range():
    for condition, multiplier in WEATHER_MULTIPLIERS.items():
        assert 0 < multiplier <= 1.0, f"{condition} multiplier {multiplier} out of (0,1] range"


def test_exactly_three_weather_conditions_defined():
    assert set(WEATHER_MULTIPLIERS.keys()) == {"sunny", "cloudy", "rainy"}
