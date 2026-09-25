"""Generación de visitas sintéticas (prediccion-specs.md, "Datos de visitas sintéticos")."""
import random
from datetime import date

from services.variables_prediccion import a_entero_no_negativo, es_fin_de_semana, es_vacaciones

BASE_VISITANTES = 40
FACTOR_FIN_DE_SEMANA = 1.8
FACTOR_FERIADO = 2.0
FACTOR_VACACIONES = 1.4
RUIDO_MIN = 0.9
RUIDO_MAX = 1.1
SEMILLA = 42


def factor_lluvia(lluvia_mm: float | None) -> float:
    lluvia = lluvia_mm or 0.0
    if lluvia < 5:
        return 1.0
    if lluvia <= 15:
        return 0.75
    return 0.5


def generar_visitas(clima: list[dict], feriados: set[date], semilla: int = SEMILLA) -> list[tuple[date, int]]:
    """Los factores se multiplican; con la misma semilla siempre da los mismos datos."""
    rng = random.Random(semilla)
    visitas = []
    for dia in sorted(clima, key=lambda d: d["fecha"]):
        fecha = dia["fecha"]
        valor = BASE_VISITANTES
        if es_fin_de_semana(fecha):
            valor *= FACTOR_FIN_DE_SEMANA
        if fecha in feriados:
            valor *= FACTOR_FERIADO
        if es_vacaciones(fecha):
            valor *= FACTOR_VACACIONES
        valor *= factor_lluvia(dia.get("lluvia_mm"))
        valor *= rng.uniform(RUIDO_MIN, RUIDO_MAX)
        visitas.append((fecha, a_entero_no_negativo(valor)))
    return visitas
