"""Entrenamiento, versionado y carga del modelo Random Forest."""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from fastapi import HTTPException, status
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from config import get_settings
from repository import feriados_repository, visitas_repository
from services.variables_prediccion import FEATURES, construir_variables

logger = logging.getLogger(__name__)

MENSAJE_MODELO_NO_DISPONIBLE = "Predicción no disponible por el momento"
_PATRON = re.compile(r"^modelo_v(\d+)\.pkl$")
_cache: dict = {"version": None, "modelo": None, "meta": None}


def _dir() -> Path:
    path = get_settings().modelos_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def ultima_version() -> int | None:
    versiones = [int(m.group(1)) for p in _dir().iterdir() if (m := _PATRON.match(p.name))]
    return max(versiones) if versiones else None


def cargar_modelo() -> tuple | None:
    """Devuelve (modelo, meta) de la última versión, o None si no hay modelo."""
    version = ultima_version()
    if version is None:
        return None
    if _cache["version"] != version:
        try:
            modelo = joblib.load(_dir() / f"modelo_v{version}.pkl")
            meta = json.loads((_dir() / f"modelo_v{version}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.error("No se pudo cargar el modelo v%s: %s", version, exc)
            return None
        _cache.update(version=version, modelo=modelo, meta=meta)
    return _cache["modelo"], _cache["meta"]


def exigir_modelo() -> tuple:
    cargado = cargar_modelo()
    if cargado is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=MENSAJE_MODELO_NO_DISPONIBLE)
    return cargado


def _entrenar_sync(datos: list[dict], feriados: set) -> tuple:
    filas = [
        construir_variables(d["fecha"], d["lluvia_mm"], d["temp_max"], d["temp_min"], d["fecha"] in feriados)
        for d in datos
    ]
    x = pd.DataFrame(filas, columns=FEATURES)
    y = [d["cantidad_visitantes"] for d in datos]
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
    modelo = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    modelo.fit(x_train, y_train)
    pred = modelo.predict(x_test)
    return modelo, float(mean_absolute_error(y_test, pred)), float(r2_score(y_test, pred))


async def entrenar() -> dict:
    datos = await visitas_repository.get_datos_entrenamiento()
    if len(datos) < 10:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No hay datos suficientes para entrenar el modelo",
        )
    feriados = await feriados_repository.fechas_feriado(datos[0]["fecha"], datos[-1]["fecha"])
    modelo, mae, r2 = await asyncio.to_thread(_entrenar_sync, datos, feriados)

    version = (ultima_version() or 0) + 1
    meta = {
        "version": version,
        "mae": round(mae, 3),
        "r2": round(r2, 4),
        "entrenado_con_sinteticos": any(d["es_sintetico"] for d in datos),
        "registros": len(datos),
        "entrenado_en": datetime.now(timezone.utc).isoformat(),
    }
    joblib.dump(modelo, _dir() / f"modelo_v{version}.pkl")
    (_dir() / f"modelo_v{version}.json").write_text(json.dumps(meta), encoding="utf-8")
    logger.info("Modelo v%s entrenado: MAE=%.2f R2=%.3f", version, mae, r2)
    return meta


def metricas() -> dict:
    _, meta = exigir_modelo()
    return meta
