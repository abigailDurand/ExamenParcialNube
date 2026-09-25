"""Configuración común de las pruebas (specs/test-specs.md, "ENTORNO DE PRUEBAS").

- Nunca se lee backend/.env: todas las variables son valores de prueba propios.
- WeatherAPI y Open-Meteo apuntan a hosts inexistentes (*.test) y siempre se simulan.
- Las pruebas de integración usan TEST_DATABASE_URL (BD de prueba, se limpia entre tests).
"""
import asyncio
import json
import os
import shutil
import sys
import tempfile
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import dotenv  # noqa: E402

dotenv.load_dotenv = lambda *args, **kwargs: False  # jamás cargar el .env real

TEST_DSN = os.environ.get("TEST_DATABASE_URL")
if not TEST_DSN:
    raise RuntimeError("Define TEST_DATABASE_URL apuntando a la BD de prueba (nunca a la de desarrollo)")

_MODELOS_SESION = Path(tempfile.mkdtemp(prefix="modelos_test_"))

os.environ.update(
    {
        "DATABASE_URL": TEST_DSN,
        "DB_POOL_MIN": "1",
        "DB_POOL_MAX": "5",
        "WEATHERAPI_KEY": "clave-de-prueba",
        "WEATHERAPI_BASE_URL": "http://weatherapi.test/v1",
        "OPEN_METEO_BASE_URL": "http://open-meteo.test/v1",
        "OPEN_METEO_GEOCODING_URL": "http://geocoding.open-meteo.test/v1/search",
        "OPEN_METEO_ARCHIVE_URL": "http://archive.open-meteo.test/v1/archive",
        "WEATHER_PROVIDER_TIMEOUT_SECONDS": "2",
        "WEATHER_CACHE_TTL_MINUTES": "10",
        "JWT_SECRET": os.environ.get("TEST_JWT_SECRET", "secreto-solo-para-tests-no-usar-en-produccion"),
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRATION_MINUTES": "60",
        "CORS_ORIGINS": "",
        "PREDICCION_LAT": "-9.295",
        "PREDICCION_LON": "-75.9975",
        "PREDICCION_HORIZONTE_DIAS": "3",
        "MODELOS_DIR": str(_MODELOS_SESION),
    }
)
for _var in ("POSTGRES_USER", "POSTGRES_PASSWORD", "APP_DB_USER", "APP_DB_PASSWORD"):
    os.environ.pop(_var, None)

from config import get_settings  # noqa: E402
from db.migrate import migrate  # noqa: E402
from db.seeds.feriados_peru import feriados as feriados_peru  # noqa: E402
from repository import db as db_module  # noqa: E402
from services import modelo_service  # noqa: E402
from services.sinteticos_service import generar_visitas  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
TABLAS = "users, locations, weather_cache, consultations, clima, visitas, feriados, predicciones"


def pytest_sessionstart(session):
    asyncio.run(migrate(TEST_DSN))


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_MODELOS_SESION, ignore_errors=True)


# ---------- Base de datos ----------
@pytest.fixture
async def db():
    """Pool sobre la BD de prueba, con todas las tablas vacías."""
    pool = await db_module.init_pool(TEST_DSN)
    await pool.execute(f"TRUNCATE {TABLAS} RESTART IDENTITY CASCADE")
    yield pool
    await db_module.close_pool()


# ---------- Datos fijos ----------
@pytest.fixture(scope="session")
def clima_fijo() -> list[dict]:
    """Clima diario real de Tingo María 2023–2025, guardado como archivo fijo."""
    datos = json.loads((FIXTURES_DIR / "clima_tingo_maria_2023_2025.json").read_text(encoding="utf-8"))
    for d in datos:
        d["fecha"] = date.fromisoformat(d["fecha"])
    return datos


@pytest.fixture(scope="session")
def feriados_fijos() -> set[date]:
    return {f for f, _ in feriados_peru(2023, 2026)}


@pytest.fixture(scope="session")
def datos_entrenamiento(clima_fijo, feriados_fijos) -> list[dict]:
    """Mismo formato que visitas_repository.get_datos_entrenamiento()."""
    visitas = dict(generar_visitas(clima_fijo, feriados_fijos))
    return [
        {
            "fecha": c["fecha"],
            "cantidad_visitantes": visitas[c["fecha"]],
            "es_sintetico": True,
            "temp_max": c["temp_max"],
            "temp_min": c["temp_min"],
            "lluvia_mm": c["lluvia_mm"],
        }
        for c in clima_fijo
    ]


# ---------- Modelo ----------
def _usar_dir_modelos(monkeypatch, path: Path):
    settings = replace(get_settings(), modelos_dir=path)
    monkeypatch.setattr(modelo_service, "get_settings", lambda: settings)
    modelo_service._cache.update(version=None, modelo=None, meta=None)


@pytest.fixture(scope="session")
def modelo_v1_sesion(datos_entrenamiento, feriados_fijos) -> Path:
    """Entrena una sola vez por sesión y deja modelo_v1 en una carpeta temporal."""
    carpeta = Path(tempfile.mkdtemp(prefix="modelo_v1_"))
    modelo, mae, r2 = modelo_service._entrenar_sync(datos_entrenamiento, feriados_fijos)
    import joblib

    joblib.dump(modelo, carpeta / "modelo_v1.pkl")
    meta = {
        "version": 1,
        "mae": mae,
        "r2": r2,
        "entrenado_con_sinteticos": True,
        "registros": len(datos_entrenamiento),
        "entrenado_en": "2026-01-01T00:00:00+00:00",
    }
    (carpeta / "modelo_v1.json").write_text(json.dumps(meta), encoding="utf-8")
    yield carpeta
    shutil.rmtree(carpeta, ignore_errors=True)


@pytest.fixture
def sin_modelo(monkeypatch, tmp_path):
    """Carpeta de modelos vacía: el modelo no está entrenado."""
    _usar_dir_modelos(monkeypatch, tmp_path)
    return tmp_path


@pytest.fixture
def con_modelo(monkeypatch, tmp_path, modelo_v1_sesion):
    """Carpeta de modelos con modelo_v1 ya entrenado."""
    for archivo in modelo_v1_sesion.iterdir():
        shutil.copy(archivo, tmp_path / archivo.name)
    _usar_dir_modelos(monkeypatch, tmp_path)
    return tmp_path
