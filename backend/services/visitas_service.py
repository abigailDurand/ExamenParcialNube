"""Registro de visitas reales y gestión de feriados (solo administrador)."""
from datetime import date

from fastapi import HTTPException, status

from repository import feriados_repository, visitas_repository


async def registrar_visita(fecha: date, cantidad: int, user_id: int) -> dict:
    return await visitas_repository.upsert_visita_real(fecha, cantidad, user_id)


async def listar_visitas(desde: date, hasta: date) -> list[dict]:
    if desde > hasta:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="desde no puede ser mayor que hasta")
    return await visitas_repository.list_visitas_con_prediccion(desde, hasta)


async def listar_feriados(anio: int | None) -> list[dict]:
    return await feriados_repository.list_feriados(anio)


async def agregar_feriado(fecha: date, nombre: str) -> dict:
    if not await feriados_repository.insert_feriado(fecha, nombre):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un feriado en esa fecha")
    return {"fecha": fecha, "nombre": nombre}


async def quitar_feriado(fecha: date) -> dict:
    borrado = await feriados_repository.delete_feriado(fecha)
    if borrado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe un feriado en esa fecha")
    return borrado
