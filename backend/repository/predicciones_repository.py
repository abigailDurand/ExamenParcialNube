from datetime import date

from repository.db import get_pool

_SELECT_ULTIMA = """
    SELECT DISTINCT ON (p.fecha_objetivo)
           p.fecha_objetivo AS fecha, p.visitantes_predichos, p.nivel_afluencia,
           p.version_modelo, p.entrenado_con_sinteticos, p.dato_incompleto,
           c.lluvia_mm, c.temp_max
    FROM predicciones p
    LEFT JOIN clima c ON c.fecha = p.fecha_objetivo
"""


def _row(row) -> dict:
    data = dict(row)
    for key in ("lluvia_mm", "temp_max"):
        if data.get(key) is not None:
            data[key] = float(data[key])
    return data


async def insert_predicciones(predicciones: list[dict]) -> None:
    await get_pool().executemany(
        """
        INSERT INTO predicciones (fecha_objetivo, visitantes_predichos, nivel_afluencia,
                                  version_modelo, entrenado_con_sinteticos, dato_incompleto)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        [
            (
                p["fecha"],
                p["visitantes_predichos"],
                p["nivel_afluencia"],
                p["version_modelo"],
                p["entrenado_con_sinteticos"],
                p["dato_incompleto"],
            )
            for p in predicciones
        ],
    )


async def get_ultimas(desde: date, hasta: date) -> list[dict]:
    """Última predicción (mayor creado_en) de cada fecha del rango."""
    rows = await get_pool().fetch(
        _SELECT_ULTIMA
        + """
        WHERE p.fecha_objetivo BETWEEN $1 AND $2
        ORDER BY p.fecha_objetivo, p.creado_en DESC
        """,
        desde,
        hasta,
    )
    return [_row(r) for r in rows]
