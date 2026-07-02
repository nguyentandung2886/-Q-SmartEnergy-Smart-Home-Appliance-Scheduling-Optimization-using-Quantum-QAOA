"""
Tests for weather_router.py pure helpers.

Verifies:
1. _select_cluster() picks the correct 8-interval (24h) block for a given days_ahead.
2. _select_cluster() returns an empty list when days_ahead is beyond the available data.
3. _classify() maps a block of 3h forecast intervals to sunny/cloudy/rainy (rain wins).
4. fetch_weather_forecast() returns ("sunny", False) for days_ahead > 5 without any network call.
"""
import asyncio

from api.weather_router import _select_cluster, _classify, fetch_weather_forecast


def _make_list(n):
    """n synthetic 3h intervals, tagged with their index so slices are identifiable."""
    return [{"idx": i, "weather": [{"main": "Clear"}], "clouds": {"all": 0}} for i in range(n)]


class TestSelectCluster:
    def test_today_is_first_eight(self):
        data = _make_list(40)
        cluster = _select_cluster(data, days_ahead=0)
        assert [f["idx"] for f in cluster] == list(range(0, 8))

    def test_tomorrow_is_second_eight(self):
        data = _make_list(40)
        cluster = _select_cluster(data, days_ahead=1)
        assert [f["idx"] for f in cluster] == list(range(8, 16))

    def test_beyond_available_data_is_empty(self):
        # Free tier = 40 intervals (indices 0..39); days_ahead=5 needs 40..47 → empty.
        data = _make_list(40)
        assert _select_cluster(data, days_ahead=5) == []


class TestClassify:
    def test_empty_defaults_sunny(self):
        assert _classify([]) == "sunny"

    def test_rain_wins(self):
        block = [
            {"weather": [{"main": "Clear"}], "clouds": {"all": 10}},
            {"weather": [{"main": "Rain"}], "clouds": {"all": 90}},
        ]
        assert _classify(block) == "rainy"

    def test_cloudy_when_avg_clouds_high(self):
        block = [{"weather": [{"main": "Clouds"}], "clouds": {"all": 80}} for _ in range(8)]
        assert _classify(block) == "cloudy"

    def test_sunny_when_clear(self):
        block = [{"weather": [{"main": "Clear"}], "clouds": {"all": 5}} for _ in range(8)]
        assert _classify(block) == "sunny"


class TestFetchBeyondRange:
    def test_days_ahead_over_five_is_sunny_unavailable(self):
        # Beyond the free-tier horizon: assumed sunny, flagged unavailable, no network call.
        condition, available = asyncio.run(fetch_weather_forecast(21.0, 105.8, days_ahead=6))
        assert condition == "sunny"
        assert available is False
