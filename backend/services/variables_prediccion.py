"""Variables del modelo y reglas de negocio de la predicción (business-rules-specs.md)."""
from datetime import date

FEATURES = ["lluvia_mm", "temp_max", "temp_min", "dia_semana", "fin_semana", "feriado", "vacaciones", "mes"]

MESES_VACACIONES = {1, 2, 3, 7}


def es_fin_de_semana(fecha: date) -> bool:
    return fecha.weekday() >= 5  # 5 = sábado, 6 = domingo


def es_vacaciones(fecha: date) -> bool:
    return fecha.month in MESES_VACACIONES


def construir_variables(
    fecha: date, lluvia_mm: float | None, temp_max: float, temp_min: float, es_feriado: bool
) -> dict:
    """Si el proveedor no informó la lluvia se usa 0 (y la predicción queda como dato incompleto)."""
    return {
        "lluvia_mm": lluvia_mm if lluvia_mm is not None else 0.0,
        "temp_max": temp_max,
        "temp_min": temp_min,
        "dia_semana": fecha.weekday(),
        "fin_semana": int(es_fin_de_semana(fecha)),
        "feriado": int(es_feriado),
        "vacaciones": int(es_vacaciones(fecha)),
        "mes": fecha.month,
    }


def nivel_afluencia(visitantes: int) -> str:
    if visitantes < 30:
        return "Baja"
    if visitantes <= 60:
        return "Media"
    return "Alta"


def a_entero_no_negativo(valor: float) -> int:
    return max(0, int(round(valor)))
