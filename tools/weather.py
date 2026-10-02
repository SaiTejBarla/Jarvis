"""
tools/weather.py — Weather lookup via wttr.in (no API key required).

Fetches current weather for any city using the free wttr.in JSON API.
"""

import logging
import requests
from .base import BaseTool

logger = logging.getLogger(__name__)

_WTTR_URL = "https://wttr.in/{city}?format=j1"


class WeatherTool(BaseTool):
    name = "weather"
    description = "Get current weather for a city. Query should be the city name."

    def run(self, query: str) -> str:
        city = query.strip()
        if not city:
            return "Please specify a city name."
        try:
            resp = requests.get(
                _WTTR_URL.format(city=city.replace(" ", "+")),
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            current = data["current_condition"][0]
            area = data["nearest_area"][0]

            temp_c = current["temp_C"]
            temp_f = current["temp_F"]
            desc = current["weatherDesc"][0]["value"]
            feels = current["FeelsLikeC"]
            humidity = current["humidity"]
            area_name = area["areaName"][0]["value"]
            country = area["country"][0]["value"]

            return (
                f"Weather in {area_name}, {country}: {desc}. "
                f"Temperature: {temp_c}°C ({temp_f}°F), feels like {feels}°C. "
                f"Humidity: {humidity}%."
            )
        except Exception as exc:
            logger.warning("Weather lookup failed for %r: %s", city, exc)
            return f"Could not fetch weather for '{city}'. Please try again."
