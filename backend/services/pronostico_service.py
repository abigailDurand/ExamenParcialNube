"""Descarga diaria del pronóstico (WeatherAPI → Open-Meteo, con reintentos) y predicción."""
import asyncio
import logging
from datetime import timedelta

from fastapi import HTTPException

from config import get_settings
from repository import clima_repository
from services import open_meteo_client, prediccion_service, weatherapi_client
from services.weather_provider_errors import WeatherLocationNotFoundError, WeatherProviderError

logger = logging.getLogger(__name__)

REINTENTOS = 3
_ERRORES = (WeatherLocationNotFoundError, WeatherProviderError)


async def _obtener_pronostico(lat: float, lon: float, dias: int) -> list[dict]:
    try:
        return await weatherapi_client.fetch_daily_forecast(lat, lon, dias)
    except _ERRORES as exc:
        logger.warning("WeatherAPI falló en el pronóstico (%s); se intenta con Open-Meteo", exc)
        return await open_meteo_client.fetch_daily_forecast(lat, lon, dias)


async def descargar_pronostico(reintentos: int = REINTENTOS, espera_segundos: float = 10) -> bool:
    """Devuelve False si ambos proveedores fallaron en todos los intentos.

    En ese caso no se guarda nada y la predicción usa el último pronóstico guardado.
    """
    settings = get_settings()
    for intento in range(reintentos + 1):
        try:
            dias = await _obtener_pronostico(
                settings.prediccion_lat, settings.prediccion_lon, settings.prediccion_horizonte_dias
            )
            await clima_repository.upsert_pronostico(dias)
            return True
        except _ERRORES as exc:
            logger.warning("Pronóstico no disponible (intento %s de %s): %s", intento + 1, reintentos + 1, exc)
            if intento < reintentos:
                await asyncio.sleep(espera_segundos)
    logger.error("Ambos proveedores fallaron; se usa el último pronóstico guardado")
    return False


async def flujo_diario() -> None:
    await descargar_pronostico()
    hoy = prediccion_service.hoy_lima()
    hasta = hoy + timedelta(days=get_settings().prediccion_horizonte_dias - 1)
    try:
        predicciones = await prediccion_service.generar_predicciones(hoy, hasta)
        logger.info("Predicciones generadas: %s días", len(predicciones))
    except HTTPException as exc:
        logger.error("No se generaron predicciones: %s", exc.detail)
