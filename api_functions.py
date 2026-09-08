import os
from datetime import datetime, timezone
from typing import Any

import requests


BASE_URL = "https://api.openweathermap.org/data/2.5"

POLLUTANT_KEYS = {
    "PM2.5": "pm2_5",
    "PM10": "pm10",
    "NO2": "no2",
    "SO2": "so2",
    "CO": "co",
    "O3": "o3",
    "NH3": "nh3",
}


def _get_api_key(api_key: str | None = None) -> str:
    """Return the supplied API key or read it from OWM_API_KEY."""
    key = api_key or os.getenv("OWM_API_KEY")

    if not key:
        raise ValueError(
            "OpenWeatherMap API key is missing. "
            "Set OWM_API_KEY or pass api_key."
        )

    return key


def _request_json(
    endpoint: str,
    lat: float,
    lon: float,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Call an OpenWeatherMap endpoint and return JSON with readable errors."""

    key = _get_api_key(api_key)

    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params={
                "lat": lat,
                "lon": lon,
                "appid": key,
            },
            timeout=15,
        )

    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "The pollution API request timed out."
        ) from exc

    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "No internet connection or the pollution API is unreachable."
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"The pollution API request failed: {exc}"
        ) from exc

    if response.status_code == 401:
        raise RuntimeError(
            "The API key was rejected. Check the key and wait for a newly "
            "created key to activate."
        )

    if response.status_code == 404:
        raise RuntimeError(
            "No pollution data was found for these coordinates."
        )

    if response.status_code == 429:
        raise RuntimeError(
            "The API request limit has been reached. Try again later."
        )

    try:
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"The pollution API returned HTTP {response.status_code}."
        ) from exc

    except ValueError as exc:
        raise RuntimeError(
            "The pollution API returned invalid JSON."
        ) from exc


def _extract_pollutants(
    record: dict[str, Any],
) -> dict[str, float]:
    """Convert API component names into our seven pollutant names."""

    components = record.get("components", {})

    missing = [
        api_name
        for api_name in POLLUTANT_KEYS.values()
        if api_name not in components
    ]

    if missing:
        raise RuntimeError(
            f"The API response is missing pollutant fields: {missing}"
        )

    return {
        feature_name: float(components[api_name])
        for feature_name, api_name in POLLUTANT_KEYS.items()
    }


def get_pollution(
    lat: float,
    lon: float,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Return current pollution data for a latitude and longitude.

    Returns:
        timestamp_utc
        latitude
        longitude
        seven pollutant values
    """

    data = _request_json(
        "air_pollution",
        lat,
        lon,
        api_key,
    )

    records = data.get("list", [])

    if not records:
        raise RuntimeError(
            "The API returned no current pollution record for this location."
        )

    record = records[0]

    return {
        "timestamp_utc": datetime.fromtimestamp(
            record["dt"],
            tz=timezone.utc,
        ).isoformat(),

        "lat": float(
            data.get("coord", {}).get("lat", lat)
        ),

        "lon": float(
            data.get("coord", {}).get("lon", lon)
        ),

        "pollutants": _extract_pollutants(record),
    }


def get_pollution_forecast(
    lat: float,
    lon: float,
    api_key: str | None = None,
    hours: int = 24,
) -> list[dict[str, Any]]:
    """
    Return up to the requested number of forecast pollution records.
    """

    if hours < 1:
        raise ValueError("hours must be at least 1")

    data = _request_json(
        "air_pollution/forecast",
        lat,
        lon,
        api_key,
    )

    records = data.get("list", [])

    if not records:
        raise RuntimeError(
            "The API returned no forecast records for this location."
        )

    output = []

    for record in records[:hours]:
        output.append(
            {
                "timestamp_utc": datetime.fromtimestamp(
                    record["dt"],
                    tz=timezone.utc,
                ).isoformat(),

                "pollutants": _extract_pollutants(record),
            }
        )

    return output