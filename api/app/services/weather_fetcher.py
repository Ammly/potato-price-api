import requests
from datetime import datetime

OPENWEATHER_URL = "https://api.openweathermap.org/data/3.0/onecall"


def fetch_weather_for(lat: float, lon: float, api_key: str) -> dict:
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
        "exclude": "minutely",  # keep payload small
    }
    r = requests.get(OPENWEATHER_URL, params=params, timeout=10)
    r.raise_for_status()
    payload = r.json()

    current = payload.get("current", {})
    rain_mm = 0.0
    if isinstance(current.get("rain"), dict):
        rain_mm = current["rain"].get("1h", 0.0)
    weather_code = current.get("weather", [{}])[0].get("id")

    # Simple normalization rule: heavy rain > 10mm -> index ~0.6+, extreme > 30mm -> ~1.0
    # Map rain_mm -> [0.0..1.0] with a soft cap
    weather_index = min(1.0, rain_mm / 30.0)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "rain_mm": rain_mm,
        "weather_code": weather_code,
        "weather_index": weather_index,
        "raw": payload,
    }
