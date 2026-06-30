import os
import httpx
import statistics
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/weather", tags=["weather"])

WEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

class WeatherRequest(BaseModel):
    lat: float
    lon: float

async def fetch_weather_forecast(lat: float, lon: float) -> str:
    """
    Returns "sunny", "cloudy", or "rainy" based on live weather data from OpenWeatherMap.
    If no API key or network error, defaults to "sunny".
    """
    if not WEATHER_API_KEY:
        return "sunny"
    
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            
            # Analyze the first 8 intervals (24 hours, 3h each)
            forecasts = data.get("list", [])[:8]
            if not forecasts:
                return "sunny"
            
            # Simple heuristic
            has_rain = any(
                "rain" in f.get("weather", [{}])[0].get("main", "").lower() 
                for f in forecasts
            )
            if has_rain:
                return "rainy"
                
            avg_clouds = statistics.mean(f.get("clouds", {}).get("all", 0) for f in forecasts)
            if avg_clouds > 40:
                return "cloudy"
                
            return "sunny"
        except Exception:
            return "sunny"

@router.post("")
async def get_live_weather(payload: WeatherRequest):
    condition = await fetch_weather_forecast(payload.lat, payload.lon)
    return {"condition": condition}
