from datetime import date

from fastapi import APIRouter, Depends, Query

from config import get_settings
from models.schemas import (
    FeriadoRequest,
    FeriadoResponse,
    MetricasResponse,
    PrediccionResponse,
    VisitaConPrediccionResponse,
    VisitaRequest,
    VisitaResponse,
)
from routes.deps import current_user
from services import modelo_service, prediccion_service, visitas_service

router = APIRouter(tags=["prediccion"])


# --- Públicos ---
@router.get("/predicciones", response_model=list[PrediccionResponse])
async def get_predicciones(dias: int | None = Query(default=None)):
    if dias is None:
        dias = get_settings().prediccion_horizonte_dias
    return await prediccion_service.get_predicciones(dias)


@router.get("/predicciones/{fecha}", response_model=PrediccionResponse)
async def get_prediccion(fecha: date):
    return await prediccion_service.get_prediccion(fecha)


# --- Solo administrador ---
@router.post("/visitas", response_model=VisitaResponse)
async def registrar_visita(body: VisitaRequest, user: dict = Depends(current_user)):
    return await visitas_service.registrar_visita(body.fecha, body.cantidad_visitantes, user["id"])


@router.get("/visitas", response_model=list[VisitaConPrediccionResponse])
async def listar_visitas(desde: date, hasta: date, _: dict = Depends(current_user)):
    return await visitas_service.listar_visitas(desde, hasta)


@router.get("/feriados", response_model=list[FeriadoResponse])
async def listar_feriados(anio: int | None = None, _: dict = Depends(current_user)):
    return await visitas_service.listar_feriados(anio)


@router.post("/feriados", response_model=FeriadoResponse)
async def agregar_feriado(body: FeriadoRequest, _: dict = Depends(current_user)):
    return await visitas_service.agregar_feriado(body.fecha, body.nombre)


@router.delete("/feriados/{fecha}", response_model=FeriadoResponse)
async def quitar_feriado(fecha: date, _: dict = Depends(current_user)):
    return await visitas_service.quitar_feriado(fecha)


@router.post("/modelo/reentrenar", response_model=MetricasResponse)
async def reentrenar(_: dict = Depends(current_user)):
    return await modelo_service.entrenar()


@router.get("/modelo/metricas", response_model=MetricasResponse)
async def metricas(_: dict = Depends(current_user)):
    return modelo_service.metricas()
