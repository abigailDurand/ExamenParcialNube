from datetime import date

import asyncpg

from repository.db import get_pool


async def list_feriados(anio: int | None = None) -> list[dict]:
    if anio is None:
        rows = await get_pool().fetch("SELECT fecha, nombre FROM feriados ORDER BY fecha")
    else:
        rows = await get_pool().fetch(
            "SELECT fecha, nombre FROM feriados WHERE extract(year FROM fecha) = $1 ORDER BY fecha",
            anio,
        )
    return [dict(r) for r in rows]


async def fechas_feriado(desde: date, hasta: date) -> set[date]:
    rows = await get_pool().fetch(
        "SELECT fecha FROM feriados WHERE fecha BETWEEN $1 AND $2", desde, hasta
    )
    return {r["fecha"] for r in rows}


async def insert_feriado(fecha: date, nombre: str) -> bool:
    """Devuelve False si la fecha ya existía."""
    try:
        await get_pool().execute("INSERT INTO feriados (fecha, nombre) VALUES ($1, $2)", fecha, nombre)
        return True
    except asyncpg.UniqueViolationError:
        return False


async def insert_feriados_if_missing(feriados: list[tuple[date, str]]) -> None:
    await get_pool().executemany(
        "INSERT INTO feriados (fecha, nombre) VALUES ($1, $2) ON CONFLICT (fecha) DO NOTHING",
        feriados,
    )


async def delete_feriado(fecha: date) -> dict | None:
    """Devuelve el feriado borrado, o None si la fecha no existía."""
    row = await get_pool().fetchrow("DELETE FROM feriados WHERE fecha = $1 RETURNING fecha, nombre", fecha)
    return dict(row) if row else None
