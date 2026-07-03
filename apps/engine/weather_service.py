"""
Weather Service — Open-Meteo Integration
-----------------------------------------
Fetches real-time weather for a lat/lon using Open-Meteo API.
No API key required. Completely free.

API docs: https://open-meteo.com/en/docs

Returns current temperature, humidity, daily min/max temp,
and total precipitation — all used to score crops against
their ideal temperature range from the Excel dataset.

Weather scoring weight: 15 pts (added on top of soil scoring).
Total score breakdown after adding weather:
  pH        : 20 pts
  OC + EC   : 10 pts
  N+P+K+S   : 35 pts
  Micros    : 20 pts
  Weather   : 15 pts
  ─────────────────
  Total     : 100 pts
"""

import json
import urllib.request
import urllib.parse
from typing import Optional

# Open-Meteo base URL (no API key needed)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Weather score weight
WEATHER_WEIGHT = 15.0


def fetch_weather(lat: float, lon: float) -> Optional[dict]:
    """
    Fetch current weather + daily forecast from Open-Meteo.

    Returns:
        {
            "temp_current": float,       # °C
            "temp_min":     float,       # today's min °C
            "temp_max":     float,       # today's max °C
            "humidity":     float,       # %
            "precipitation": float,      # mm today
            "description":  str,         # human-readable summary
        }
        or None if the request fails (graceful degradation).
    """
    params = {
        "latitude":    lat,
        "longitude":   lon,
        "current":     "temperature_2m,relative_humidity_2m,precipitation,weathercode",
        "daily":       "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone":    "Asia/Kolkata",
        "forecast_days": 1,
    }
    url = OPEN_METEO_URL + "?" + urllib.parse.urlencode(params, doseq=True)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgroZone/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        current = data.get("current", {})
        daily   = data.get("daily", {})

        temp_current  = current.get("temperature_2m")
        humidity      = current.get("relative_humidity_2m")
        precip        = current.get("precipitation", 0)
        weathercode   = current.get("weathercode", 0)

        temp_max = (daily.get("temperature_2m_max") or [None])[0]
        temp_min = (daily.get("temperature_2m_min") or [None])[0]
        precip_daily = (daily.get("precipitation_sum") or [0])[0]

        return {
            "temp_current":  round(temp_current, 1) if temp_current is not None else None,
            "temp_min":      round(temp_min, 1)     if temp_min is not None else None,
            "temp_max":      round(temp_max, 1)     if temp_max is not None else None,
            "humidity":      round(humidity, 1)     if humidity is not None else None,
            "precipitation": round(precip_daily, 1) if precip_daily is not None else 0.0,
            "description":  _weather_description(weathercode),
        }

    except Exception as e:
        # Graceful degradation — weather unavailable shouldn't break recommendations
        return None


def _weather_description(code: int) -> str:
    """WMO Weather Code → human-readable string."""
    codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Icy fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
        61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Light snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Rain showers", 81: "Heavy showers", 82: "Violent showers",
        95: "Thunderstorm", 96: "Thunderstorm with hail",
    }
    return codes.get(code, "Unknown")


def score_weather(temp_current: Optional[float], temp_range_str: str) -> dict:
    """
    Score current temperature against a crop's ideal temp range string.
    e.g. temp_range_str = "20-35°C"

    Returns:
        {
            "score": float,      # weighted pts earned
            "max":   float,      # WEATHER_WEIGHT
            "pct":   float,      # 0–100
            "status": str,       # "ok" | "low" | "high" | "missing"
            "ideal_range": str,
        }
    """
    # Parse temp range string like "20-35°C" or "15-30"
    import re
    match = re.search(r"([\d.]+)\s*[-–]\s*([\d.]+)", temp_range_str or "")

    if not match or temp_current is None:
        # No temp data available — neutral score
        return {
            "score": round(WEATHER_WEIGHT * 0.5, 2),
            "max":   WEATHER_WEIGHT,
            "pct":   50.0,
            "status": "missing",
            "ideal_range": temp_range_str or "N/A",
        }

    lo = float(match.group(1))
    hi = float(match.group(2))
    width = hi - lo

    if lo <= temp_current <= hi:
        s = 1.0
        status = "ok"
    else:
        dist = (lo - temp_current) if temp_current < lo else (temp_current - hi)
        s = max(0.0, 1.0 - dist / max(width, 1.0))
        status = "low" if temp_current < lo else "high"

    pts = round(s * WEATHER_WEIGHT, 2)
    return {
        "score":       pts,
        "max":         WEATHER_WEIGHT,
        "pct":         round(s * 100, 1),
        "status":      status,
        "ideal_range": f"{lo}–{hi}°C",
    }