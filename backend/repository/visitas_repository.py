from datetime import date

from repository.db import get_pool


async def upsert_visita_real(fecha: date, cantidad: int, user_id: int) -> dict:
    """El registro real reemplaza al sintético (o real anterior) de la misma fecha."""
    row = await get_pool().fetchrow(
        """
        INSERT INTO visitas (fecha, cantidad_visitantes, es_sintetico, registrado_por)
        VALUES ($1, $2, false, $3)
        ON CONFLICT (fecha) DO UPDATE
        SET cantidad_visitantes = EXCLUDED.cantidad_visitantes,
            es_sintetico = false,
            registrado_por = EXCLUDED.registrado_por
        RETURNING fecha, cantidad_visitantes, es_sintetico
        """,
        fecha,
        cantidad,
        user_id,
    )
    return dict(row)


async def insert_sinteticas(visitas: list[tuple[date, int]]) -> None:
    """Nunca pisa un registro existente (real o sintético)."""
    await get_pool().executemany(
        """
        INSERT INTO visitas (fecha, cantidad_visitantes, es_sintetico, registrado_por)
        VALUES ($1, $2, true, NULL)
        ON CONFLICT (fecha) DO NOTHING
        """,
        visitas,
    )


async def list_visitas_con_prediccion(desde: date, hasta: date) -> list[dict]:
    rows = await get_pool().fetch(
        """
        SELECT v.fecha, v.cantidad_visitantes, v.es_sintetico,
               (SELECT p.visitantes_predichos FROM predicciones p
                WHERE p.fecha_objetivo = v.fecha
                ORDER BY p.creado_en DESC LIMIT 1) AS visitantes_predichos
        FROM visitas v
        WHERE v.fecha BETWEEN $1 AND $2
        ORDER BY v.fecha
        """,
        desde,
        hasta,
    )
    return [dict(r) for r in rows]


async def get_datos_entrenamiento() -> list[dict]:
    """Días que tienen visitas y clima (con temperaturas) para entrenar."""
    rows = await get_pool().fetch(
        """
        SELECT v.fecha, v.cantidad_visitantes, v.es_sintetico,
               c.temp_max, c.temp_min, c.lluvia_mm
        FROM visitas v
        JOIN clima c ON c.fecha = v.fecha
        ORDER BY v.fecha
        """
    )
    data = []
    for r in rows:
        d = dict(r)
        d["temp_max"] = float(d["temp_max"])
        d["temp_min"] = float(d["temp_min"])
        d["lluvia_mm"] = float(d["lluvia_mm"]) if d["lluvia_mm"] is not None else None
        data.append(d)
    return data
