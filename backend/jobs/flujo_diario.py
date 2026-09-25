"""Ejecuta una sola vez el flujo diario (python -m jobs.flujo_diario).

Descarga el pronóstico (WeatherAPI → Open-Meteo) y genera las predicciones del
horizonte. Lo usa el despliegue para no esperar a las 06:00.
"""
import asyncio
import logging

from repository.db import close_pool, init_pool
from services import pronostico_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    await init_pool()
    try:
        await pronostico_service.flujo_diario()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
