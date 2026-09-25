"""Cliente de WeatherAPI (proveedor principal). No conoce a FastAPI."""
from datetime import date

import httpx

from config import get_settings
from services.weather_conditions import translate_weatherapi
from services.weather_provider_errors import WeatherLocationNotFoundError, WeatherProviderError

# WeatherAPI responde 400 con este código cuando no encuentra la ubicación
_LOCATION_NOT_FOUND_CODE = 1006


async def _get(path: str, params: dict) -> dict:
    settings = get_settings()
    params = {"key": settings.weatherapi_key, **params}
    try:
        async with httpx.AsyncClient(timeout=settings.weather_provider_timeout_seconds) as client:
            response = await client.get(f"{settings.weatherapi_base_url}/{path}", params=params)
    except httpx.HTTPError as exc:
        raise WeatherProviderError(f"WeatherAPI no respondió: {type(exc).__name__}") from exc

    if response.status_code == 400:
        try:
            code = response.json().get("error", {}).get("code")
        except ValueError:
            code = None
        if code == _LOCATION_NOT_FOUND_CODE:
            raise WeatherLocationNotFoundError("WeatherAPI no encontró la ubicación")
    if response.status_code != 200:
        raise WeatherProviderError(f"WeatherAPI respondió {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise WeatherProviderError("WeatherAPI devolvió una respuesta inválida") from exc


async def fetch_current_weather(query: str) -> dict:
    data = await _get("current.json", {"q": query})
    try:
        current = data["current"]
        return {
            "temp_c": float(current["temp_c"]),
            "humidity": int(current["humidity"]),
            "condition": translate_weatherapi(current["condition"]["text"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherProviderError("WeatherAPI devolvió datos incompletos") from exc


async def fetch_daily_forecast(lat: float, lon: float, dias: int) -> list[dict]:
    data = await _get("forecast.json", {"q": f"{lat},{lon}", "days": dias})
    try:
        result = []
        for item in data["forecast"]["forecastday"]:
            day = item["day"]
            lluvia = day.get("totalprecip_mm")
            result.append(
                {
                    "fecha": date.fromisoformat(item["date"]),
                    "temp_max": float(day["maxtemp_c"]),
                    "temp_min": float(day["mintemp_c"]),
                    "lluvia_mm": float(lluvia) if lluvia is not None else None,
                    "humedad": int(day["avghumidity"]) if day.get("avghumidity") is not None else None,
                }
            )
        return result
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherProviderError("WeatherAPI devolvió un pronóstico incompleto") from exc
