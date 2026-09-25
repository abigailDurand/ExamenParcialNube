"""Carga de datos iniciales (python -m db.seed). Es idempotente.

Orden: catálogo → usuario inicial → feriados → clima histórico → visitas
sintéticas → primer modelo (solo si todavía no existe ninguno).
"""
import asyncio
import logging
import os
from datetime import date

from config import get_settings
from db.seeds.feriados_peru import feriados
from repository import clima_repository, feriados_repository, locations_repository, users_repository, visitas_repository
from repository.db import close_pool, init_pool
from services import modelo_service, open_meteo_client
from services.security import hash_password
from services.sinteticos_service import generar_visitas

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("seed")

HISTORICO_DESDE = date(2023, 1, 1)
HISTORICO_HASTA = date(2025, 12, 31)


async def seed() -> None:
    settings = get_settings()

    await locations_repository.create_location_if_missing(
        "Tingo María", "region", f"{settings.prediccion_lat},{settings.prediccion_lon}"
    )

    email = os.getenv("SEED_USER_EMAIL")
    password = os.getenv("SEED_USER_PASSWORD")
    if email and password:
        await users_repository.create_user_if_missing(email.strip().lower(), hash_password(password))
    else:
        logger.warning("SEED_USER_EMAIL / SEED_USER_PASSWORD no definidos: no se crea el usuario inicial")

    await feriados_repository.insert_feriados_if_missing(feriados(2023, 2026))

    dias_esperados = (HISTORICO_HASTA - HISTORICO_DESDE).days + 1
    if await clima_repository.count_observado(HISTORICO_DESDE, HISTORICO_HASTA) < dias_esperados:
        logger.info("Descargando clima histórico 2023–2025 de Open-Meteo Archive...")
        historico = await open_meteo_client.fetch_daily_history(
            settings.prediccion_lat, settings.prediccion_lon, HISTORICO_DESDE, HISTORICO_HASTA
        )
        await clima_repository.upsert_observado(historico)
        logger.info("Clima histórico guardado: %s días", len(historico))

    clima = await clima_repository.get_clima(HISTORICO_DESDE, HISTORICO_HASTA)
    fechas_feriado = await feriados_repository.fechas_feriado(HISTORICO_DESDE, HISTORICO_HASTA)
    await visitas_repository.insert_sinteticas(generar_visitas(clima, fechas_feriado))

    if modelo_service.ultima_version() is None:
        meta = await modelo_service.entrenar()
        logger.info("Primer modelo entrenado: %s", meta)
    logger.info("Seeds completados")


async def main() -> None:
    await init_pool()
    try:
        await seed()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
