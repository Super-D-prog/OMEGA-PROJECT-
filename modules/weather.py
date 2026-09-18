"""Deterministic global weather lookup using Open-Meteo."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class WeatherUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class WeatherRequest:
    location: str
    day_offset: int = 0


WEATHER_CODES = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "foggy with frost", 51: "light drizzle",
    53: "drizzle", 55: "heavy drizzle", 56: "light freezing drizzle",
    57: "freezing drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    66: "light freezing rain", 67: "freezing rain", 71: "light snow",
    73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers",
    81: "showers", 82: "heavy showers", 85: "light snow showers",
    86: "heavy snow showers", 95: "thunderstorms",
    96: "thunderstorms with light hail", 99: "thunderstorms with hail",
}


def parse_weather_request(text: str, home: str) -> WeatherRequest | None:
    clean = " ".join(text.strip().rstrip("?.!").split())
    lower = clean.lower()
    if not any(word in lower for word in (
        "weather", "forecast", "rain", "temperature", "wear", "jacket", "hoodie", "coat"
    )):
        return None
    day_offset = 1 if "tomorrow" in lower else 0
    location = None
    patterns = (
        r"(?:weather|forecast|temperature)(?:\s+like)?\s+(?:in|for|at)\s+(.+)",
        r"will it rain\s+(?:in|at)\s+(.+)",
        r"(?:what should i wear|should i wear (?:a )?(?:jacket|hoodie|coat))\s+(?:in|for|at)\s+(.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, clean, flags=re.I)
        if match:
            location = match.group(1)
            break
    if location:
        location = re.sub(r"\s+(?:today|tomorrow)$", "", location, flags=re.I).strip()
    return WeatherRequest(location=location or home, day_offset=day_offset)


def _get_json(url: str, timeout: int = 15) -> dict:
    request = Request(url, headers={"User-Agent": "OMEGA personal assistant"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        # Some macOS Python installations cannot find the system TLS
        # certificates. Fall back to Apple's bundled curl certificate stack.
        try:
            result = subprocess.run(
                [
                    "/usr/bin/curl", "--fail", "--silent", "--show-error",
                    "--max-time", str(timeout), url,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout + 2,
            )
            payload = json.loads(result.stdout)
            if not isinstance(payload, dict):
                raise ValueError("Unexpected weather response")
            return payload
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            OSError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise WeatherUnavailable("I couldn't reach the weather service.") from exc


def clothing_recommendation(
    feels_like: float,
    high: float,
    low: float,
    rain_chance: int,
    condition: str,
    wind: float = 0,
) -> str:
    reference = min(feels_like, low)
    if reference <= 25:
        items = ["a heavy winter coat", "warm layers", "gloves"]
    elif reference <= 40:
        items = ["a warm jacket or coat", "long pants"]
    elif reference <= 55:
        items = ["a hoodie or light jacket", "long pants"]
    elif reference <= 65:
        items = ["a light layer or hoodie"]
    elif high >= 85:
        items = ["light, breathable clothes"]
    else:
        items = ["comfortable light clothing"]

    wet_conditions = any(word in condition for word in ("rain", "drizzle", "shower", "thunder"))
    if rain_chance >= 40 or wet_conditions:
        items.append("an umbrella or waterproof outer layer")
    if wind >= 20:
        items.append("a wind-resistant layer")
    if high >= 85:
        items.append("water")
    return "Wear " + ", ".join(items) + "."


def weather_report(request: WeatherRequest) -> str:
    location_parts = [part.strip() for part in request.location.split(",") if part.strip()]
    search_name = location_parts[0]
    qualifiers = [part.lower() for part in location_parts[1:]]
    geo_query = urlencode({
        "name": search_name,
        "count": 10,
        "language": "en",
        "format": "json",
    })
    geo = _get_json(f"https://geocoding-api.open-meteo.com/v1/search?{geo_query}")
    results = geo.get("results") or []
    if not results:
        raise WeatherUnavailable(f"I couldn't find a place named {request.location}.")
    place = results[0]
    if qualifiers:
        for candidate in results:
            searchable = " ".join(str(candidate.get(field, "")).lower() for field in (
                "name", "admin1", "admin2", "country", "country_code"
            ))
            if all(qualifier in searchable for qualifier in qualifiers):
                place = candidate
                break
    latitude, longitude = place["latitude"], place["longitude"]
    labels = [place.get("name"), place.get("admin1"), place.get("country")]
    resolved = ", ".join(dict.fromkeys(label for label in labels if label))

    forecast_query = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "forecast_days": 3,
        "current": ",".join((
            "temperature_2m", "apparent_temperature", "relative_humidity_2m",
            "precipitation", "weather_code", "wind_speed_10m",
        )),
        "daily": ",".join((
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_probability_max",
        )),
    })
    data = _get_json(f"https://api.open-meteo.com/v1/forecast?{forecast_query}")
    daily = data.get("daily") or {}
    index = request.day_offset
    try:
        date = daily["time"][index]
        condition = WEATHER_CODES.get(daily["weather_code"][index], "unknown conditions")
        high = round(daily["temperature_2m_max"][index])
        low = round(daily["temperature_2m_min"][index])
        rain_chance = daily["precipitation_probability_max"][index]
    except (KeyError, IndexError, TypeError):
        raise WeatherUnavailable("The weather service returned incomplete forecast data.")

    if request.day_offset == 1:
        clothing = clothing_recommendation(low, high, low, rain_chance, condition)
        return (
            f"Tomorrow in {resolved}: {condition}, high {high}°F, low {low}°F, "
            f"with a {rain_chance}% chance of precipitation. {clothing}"
        )

    current = data.get("current") or {}
    try:
        temperature = round(current["temperature_2m"])
        feels = round(current["apparent_temperature"])
        humidity = current["relative_humidity_2m"]
        wind = round(current["wind_speed_10m"])
        current_condition = WEATHER_CODES.get(current["weather_code"], condition)
    except (KeyError, TypeError):
        raise WeatherUnavailable("The weather service returned incomplete current conditions.")
    clothing = clothing_recommendation(
        feels, high, low, rain_chance, current_condition, wind
    )
    return (
        f"In {resolved}, it is {temperature}°F and {current_condition}; it feels like "
        f"{feels}°F. Humidity is {humidity}% and wind is {wind} mph. "
        f"Today's high is {high}°F, the low is {low}°F, and precipitation chance is "
        f"{rain_chance}%. {clothing}"
    )
