"""Catálogo de ubicaciones e historial de consultas."""
from repository import consultations_repository, locations_repository

# La spec no fija cuántas consultas recientes devolver
CONSULTAS_RECIENTES_LIMITE = 10


async def list_locations() -> list[dict]:
    return await locations_repository.list_locations()


async def list_recent_consultations(user_id: int) -> list[dict]:
    return await consultations_repository.list_recent(user_id, CONSULTAS_RECIENTES_LIMITE)
