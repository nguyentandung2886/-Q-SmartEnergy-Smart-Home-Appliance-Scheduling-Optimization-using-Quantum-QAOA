import os
import httpx
import statistics
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_user
from db.models import User

router = APIRouter(prefix="/weather", tags=["weather"])

WEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

# OpenWeatherMap free tier: /forecast returns 3-hour intervals covering 5 days (40 intervals).
# Each day is one block of 8 intervals (8 * 3h = 24h). days_ahead selects which block to read.
INTERVALS_PER_DAY = 8
MAX_DAYS_AHEAD = 5


class WeatherRequest(BaseModel):
    lat: float
    lon: float
    # 0 = today, 1 = tomorrow, … Days beyond the free-tier horizon fall back to a sunny assumption.
    days_ahead: int = 0


def _select_cluster(forecast_list: list, days_ahead: int) -> list:
    """The 8 three-hour intervals (~24h) for the requested day offset. Empty if the requested
    day lies beyond the data returned (free tier only reaches ~5 days out)."""
    start = days_ahead * INTERVALS_PER_DAY
    return forecast_list[start:start + INTERVALS_PER_DAY]


def _classify(forecasts: list) -> str:
    """Reduce a block of 3h forecast intervals to "sunny"/"cloudy"/"rainy". Any rain in the block
    wins; otherwise a mostly-clouded day is "cloudy"; else "sunny". Empty block → "sunny"."""
    if not forecasts:
        return "sunny"
    has_rain = any(
        "rain" in f.get("weather", [{}])[0].get("main", "").lower()
        for f in forecasts
    )
    if has_rain:
        return "rainy"
    avg_clouds = statistics.mean(f.get("clouds", {}).get("all", 0) for f in forecasts)
    return "cloudy" if avg_clouds > 40 else "sunny"


async def fetch_weather_forecast(lat: float, lon: float, days_ahead: int = 0) -> tuple[str, bool]:
    """Returns (condition, forecast_available). condition is "sunny"/"cloudy"/"rainy".
    forecast_available is True only when a real forecast block was read for the requested day;
    it is False when the day is beyond the free-tier horizon, no API key is set, the network
    fails, or the returned data doesn't reach that day — in all those cases condition is "sunny"
    so the caller can warn instead of optimizing on a silent, possibly-wrong assumption."""
    if days_ahead > MAX_DAYS_AHEAD or not WEATHER_API_KEY:
        return "sunny", False

    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()

            cluster = _select_cluster(data.get("list", []), days_ahead)
            if not cluster:
                return "sunny", False
            return _classify(cluster), True
        except Exception:
            return "sunny", False


@router.post("")
async def get_live_weather(
    payload: WeatherRequest,
    current_user: User = Depends(get_current_user),
):
    # Yêu cầu đăng nhập: endpoint gọi OpenWeatherMap (API trả phí, tốn quota key) nên không để
    # public — tránh bị gọi ẩn danh làm cạn quota (B-M2).
    condition, forecast_available = await fetch_weather_forecast(
        payload.lat, payload.lon, payload.days_ahead
    )
    return {"condition": condition, "forecast_available": forecast_available}
