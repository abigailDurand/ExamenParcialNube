"""Consulta del clima actual con caché y fallback WeatherAPI → Open-Meteo.

Es el único que decide el código HTTP final (ver condicional-api-specs.md).
"""
import logging

from fastapi import HTTPException, status

from config import get_settings
from repository import consultations_repository, locations_repository, weather_cache_repository
from services import open_meteo_client, weatherapi_client
from services.weather_provider_errors import WeatherLocationNotFoundError, WeatherProviderError

logger = logging.getLogger(__name__)

MENSAJE_ERROR_CLIMA = "No se pudo obtener el clima de esta ubicación"


def _format(location_name: str, temp_c: float, humidity: int, condition: str, source: str) -> dict:
    return {
        "location": location_name,
        "temperature": f"{round(temp_c)}°C",
        "condition": condition,
        "humidity": f"{humidity}%",
        "source": source,
    }


async def get_weather(location_name: str | None, user_id: int) -> dict:
    if not location_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Falta el parámetro location")
    location = await locations_repository.get_location_by_name(location_name)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="La ubicación no pertenece al catálogo"
        )

    settings = get_settings()
    cached = await weather_cache_repository.get_cached_weather(
        location["id"], settings.weather_cache_ttl_minutes
    )
    if cached is not None:
        await consultations_repository.add_consultation(user_id, location["id"])
        return _format(
            location["name"], cached["temp_c"], cached["humidity"], cached["condition"], cached["source"]
        )

    try:
        data = await weatherapi_client.fetch_current_weather(location["weatherapi_query"])
        source = "weatherapi"
    except (WeatherLocationNotFoundError, WeatherProviderError) as weatherapi_error:
        logger.warning("WeatherAPI falló (%s); se intenta con Open-Meteo", weatherapi_error)
        try:
            data = await open_meteo_client.fetch_current_weather(location["name"])
            source = "open-meteo"
        except (WeatherLocationNotFoundError, WeatherProviderError) as open_meteo_error:
            logger.warning("Open-Meteo también falló (%s)", open_meteo_error)
            ninguno_encontro = isinstance(weatherapi_error, WeatherLocationNotFoundError) and isinstance(
                open_meteo_error, WeatherLocationNotFoundError
            )
            code = status.HTTP_404_NOT_FOUND if ninguno_encontro else status.HTTP_503_SERVICE_UNAVAILABLE
            raise HTTPException(status_code=code, detail=MENSAJE_ERROR_CLIMA)

    await weather_cache_repository.upsert_cached_weather(
        location["id"], data["temp_c"], data["humidity"], data["condition"], source
    )
    await consultations_repository.add_consultation(user_id, location["id"])
    return _format(location["name"], data["temp_c"], data["humidity"], data["condition"], source)
