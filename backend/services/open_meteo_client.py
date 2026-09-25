"""Cliente de Open-Meteo (fallback de WeatherAPI y fuente del histórico).

Expone la misma firma y las mismas excepciones que weatherapi_client.
"""
from datetime import date

import httpx

from config import get_settings
from services.weather_conditions import translate_open_meteo
from services.weather_provider_errors import WeatherLocationNotFoundError, WeatherProviderError

_DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean"


async def _get(url: str, params: dict) -> dict:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.weather_provider_timeout_seconds) as client:
            response = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        raise WeatherProviderError(f"Open-Meteo no respondió: {type(exc).__name__}") from exc
    if response.status_code != 200:
        raise WeatherProviderError(f"Open-Meteo respondió {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise WeatherProviderError("Open-Meteo devolvió una respuesta inválida") from exc


async def _geocode(name: str) -> tuple[float, float]:
    settings = get_settings()
    data = await _get(settings.open_meteo_geocoding_url, {"name": name, "count": 1})
    results = data.get("results") or []
    if not results:
        raise WeatherLocationNotFoundError("Open-Meteo no encontró la ubicación")
    return float(results[0]["latitude"]), float(results[0]["longitude"])


async def fetch_current_weather(query: str) -> dict:
    """`query` es `locations.name` (Open-Meteo no usa weatherapi_query)."""
    settings = get_settings()
    lat, lon = await _geocode(query)
    data = await _get(
        f"{settings.open_meteo_base_url}/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code",
        },
    )
    try:
        current = data["current"]
        return {
            "temp_c": float(current["temperature_2m"]),
            "humidity": int(current["relative_humidity_2m"]),
            "condition": translate_open_meteo(int(current["weather_code"])),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherProviderError("Open-Meteo devolvió datos incompletos") from exc


def _parse_daily(data: dict) -> list[dict]:
    try:
        daily = data["daily"]
        result = []
        for i, fecha in enumerate(daily["time"]):
            tmax = daily["temperature_2m_max"][i]
            tmin = daily["temperature_2m_min"][i]
            if tmax is None or tmin is None:
                continue
            lluvia = daily["precipitation_sum"][i]
            humedad = daily["relative_humidity_2m_mean"][i]
            result.append(
                {
                    "fecha": date.fromisoformat(fecha),
                    "temp_max": float(tmax),
                    "temp_min": float(tmin),
                    "lluvia_mm": float(lluvia) if lluvia is not None else None,
                    "humedad": int(round(humedad)) if humedad is not None else None,
                }
            )
        return result
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise WeatherProviderError("Open-Meteo devolvió datos diarios incompletos") from exc


async def fetch_daily_forecast(lat: float, lon: float, dias: int) -> list[dict]:
    settings = get_settings()
    data = await _get(
        f"{settings.open_meteo_base_url}/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "daily": _DAILY_VARS,
            "timezone": "America/Lima",
            "forecast_days": dias,
        },
    )
    return _parse_daily(data)


async def fetch_daily_history(lat: float, lon: float, desde: date, hasta: date) -> list[dict]:
    """Clima histórico diario (Open-Meteo Archive), usado solo para entrenar."""
    settings = get_settings()
    data = await _get(
        settings.open_meteo_archive_url,
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": desde.isoformat(),
            "end_date": hasta.isoformat(),
            "daily": _DAILY_VARS,
            "timezone": "America/Lima",
        },
    )
    return _parse_daily(data)
