"""Predicción de visitantes a Las Pavas (prediccion-specs.md)."""
from datetime import date, datetime, timedelta

import pandas as pd
from fastapi import HTTPException, status

from config import ZONA_HORARIA, get_settings
from repository import clima_repository, feriados_repository, predicciones_repository
from services import modelo_service
from services.variables_prediccion import FEATURES, a_entero_no_negativo, construir_variables, nivel_afluencia


def hoy_lima() -> date:
    return datetime.now(ZONA_HORARIA).date()


async def generar_predicciones(desde: date, hasta: date) -> list[dict]:
    """Predice con la última versión del modelo los días del rango que tengan clima guardado."""
    modelo, meta = modelo_service.exigir_modelo()
    clima = await clima_repository.get_clima(desde, hasta)
    if not clima:
        return []
    feriados = await feriados_repository.fechas_feriado(desde, hasta)
    filas = [
        construir_variables(c["fecha"], c["lluvia_mm"], c["temp_max"], c["temp_min"], c["fecha"] in feriados)
        for c in clima
    ]
    valores = modelo.predict(pd.DataFrame(filas, columns=FEATURES))
    predicciones = []
    for dia, valor in zip(clima, valores):
        visitantes = a_entero_no_negativo(valor)
        predicciones.append(
            {
                "fecha": dia["fecha"],
                "visitantes_predichos": visitantes,
                "nivel_afluencia": nivel_afluencia(visitantes),
                "version_modelo": meta["version"],
                "entrenado_con_sinteticos": meta["entrenado_con_sinteticos"],
                "dato_incompleto": dia["lluvia_mm"] is None,
            }
        )
    await predicciones_repository.insert_predicciones(predicciones)
    return predicciones


async def get_predicciones(dias: int) -> list[dict]:
    horizonte = get_settings().prediccion_horizonte_dias
    if dias < 1 or dias > horizonte:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El parámetro dias debe estar entre 1 y {horizonte}",
        )
    modelo_service.exigir_modelo()
    desde = hoy_lima()
    hasta = desde + timedelta(days=dias - 1)
    existentes = await predicciones_repository.get_ultimas(desde, hasta)
    if len(existentes) < dias:
        # Si la tarea diaria aún no generó alguna fecha, se predice con el pronóstico guardado
        await generar_predicciones(desde, hasta)
        existentes = await predicciones_repository.get_ultimas(desde, hasta)
    return existentes


async def get_prediccion(fecha: date) -> dict:
    modelo_service.exigir_modelo()
    resultado = await predicciones_repository.get_ultimas(fecha, fecha)
    if not resultado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay predicción para esa fecha")
    return resultado[0]
