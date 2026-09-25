"""Tareas programadas (python -m jobs.scheduler), hora de Lima.

- Todos los días 06:00: descarga del pronóstico y predicción del horizonte.
- Lunes 03:00: reentrenamiento del modelo.
Solo llaman a /services, igual que las rutas.
"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import HTTPException

from config import ZONA_HORARIA
from repository.db import init_pool
from services import modelo_service, pronostico_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scheduler")


async def reentrenar() -> None:
    try:
        await modelo_service.entrenar()
    except HTTPException as exc:
        logger.error("Reentrenamiento omitido: %s", exc.detail)


async def flujo_al_iniciar() -> None:
    """Si el contenedor arranca después de las 06:00 (reinicio, despliegue), no se pierde el día."""
    try:
        await pronostico_service.flujo_diario()
    except Exception as exc:  # p. ej. en el primer despliegue aún no hay tablas
        logger.warning("Flujo diario al iniciar omitido: %s", exc)


async def main() -> None:
    await init_pool()
    await flujo_al_iniciar()
    scheduler = AsyncIOScheduler(timezone=ZONA_HORARIA)
    scheduler.add_job(pronostico_service.flujo_diario, CronTrigger(hour=6, minute=0, timezone=ZONA_HORARIA))
    scheduler.add_job(
        reentrenar, CronTrigger(day_of_week="mon", hour=3, minute=0, timezone=ZONA_HORARIA)
    )
    scheduler.start()
    logger.info("Scheduler iniciado (diario 06:00, reentrenamiento lunes 03:00, hora de Lima)")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
