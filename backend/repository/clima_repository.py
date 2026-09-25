from datetime import date

from repository.db import get_pool


def _row(row) -> dict:
    data = dict(row)
    for key in ("temp_max", "temp_min", "lluvia_mm"):
        if data.get(key) is not None:
            data[key] = float(data[key])
    return data


async def upsert_pronostico(dias: list[dict]) -> None:
    """Guarda pronósticos. Nunca pisa un dato observado con un pronóstico."""
    await get_pool().executemany(
        """
        INSERT INTO clima (fecha, temp_max, temp_min, lluvia_mm, humedad, es_pronostico)
        VALUES ($1, $2, $3, $4, $5, true)
        ON CONFLICT (fecha) DO UPDATE
        SET temp_max = EXCLUDED.temp_max,
            temp_min = EXCLUDED.temp_min,
            lluvia_mm = EXCLUDED.lluvia_mm,
            humedad = EXCLUDED.humedad
        WHERE clima.es_pronostico
        """,
        [(d["fecha"], d["temp_max"], d["temp_min"], d["lluvia_mm"], d["humedad"]) for d in dias],
    )


async def upsert_observado(dias: list[dict]) -> None:
    """Guarda clima observado; reemplaza al pronóstico de la misma fecha."""
    await get_pool().executemany(
        """
        INSERT INTO clima (fecha, temp_max, temp_min, lluvia_mm, humedad, es_pronostico)
        VALUES ($1, $2, $3, $4, $5, false)
        ON CONFLICT (fecha) DO UPDATE
        SET temp_max = EXCLUDED.temp_max,
            temp_min = EXCLUDED.temp_min,
            lluvia_mm = EXCLUDED.lluvia_mm,
            humedad = EXCLUDED.humedad,
            es_pronostico = false
        """,
        [(d["fecha"], d["temp_max"], d["temp_min"], d["lluvia_mm"], d["humedad"]) for d in dias],
    )


async def get_clima(desde: date, hasta: date) -> list[dict]:
    rows = await get_pool().fetch(
        """
        SELECT fecha, temp_max, temp_min, lluvia_mm, humedad, es_pronostico
        FROM clima WHERE fecha BETWEEN $1 AND $2 ORDER BY fecha
        """,
        desde,
        hasta,
    )
    return [_row(r) for r in rows]


async def count_observado(desde: date, hasta: date) -> int:
    return await get_pool().fetchval(
        "SELECT count(*) FROM clima WHERE fecha BETWEEN $1 AND $2 AND NOT es_pronostico",
        desde,
        hasta,
    )
