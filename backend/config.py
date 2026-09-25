"""Lectura de variables de entorno (ver specs/infraestructure-specs.md).

Ningún valor por defecto contiene secretos: si falta una variable
obligatoria, el backend falla al arrancar en vez de inventar un valor.
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# En Docker las variables llegan por env_file; en local se leen de backend/.env
load_dotenv(Path(__file__).resolve().parent / ".env")

ZONA_HORARIA = ZoneInfo("America/Lima")


def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Falta la variable de entorno obligatoria {name}")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    db_pool_min: int
    db_pool_max: int
    weatherapi_key: str
    weatherapi_base_url: str
    open_meteo_base_url: str
    open_meteo_geocoding_url: str
    open_meteo_archive_url: str
    weather_provider_timeout_seconds: float
    weather_cache_ttl_minutes: int
    jwt_secret: str
    jwt_algorithm: str
    jwt_expiration_minutes: int
    cors_origins: list[str]
    prediccion_lat: float
    prediccion_lon: float
    prediccion_horizonte_dias: int
    modelos_dir: Path


@lru_cache
def get_settings() -> Settings:
    cors = os.getenv("CORS_ORIGINS", "")
    return Settings(
        database_url=_required("DATABASE_URL"),
        db_pool_min=int(_required("DB_POOL_MIN")),
        db_pool_max=int(_required("DB_POOL_MAX")),
        weatherapi_key=_required("WEATHERAPI_KEY"),
        weatherapi_base_url=_required("WEATHERAPI_BASE_URL").rstrip("/"),
        open_meteo_base_url=_required("OPEN_METEO_BASE_URL").rstrip("/"),
        open_meteo_geocoding_url=_required("OPEN_METEO_GEOCODING_URL"),
        open_meteo_archive_url=_required("OPEN_METEO_ARCHIVE_URL"),
        weather_provider_timeout_seconds=float(_required("WEATHER_PROVIDER_TIMEOUT_SECONDS")),
        weather_cache_ttl_minutes=int(_required("WEATHER_CACHE_TTL_MINUTES")),
        jwt_secret=_required("JWT_SECRET"),
        jwt_algorithm=_required("JWT_ALGORITHM"),
        jwt_expiration_minutes=int(_required("JWT_EXPIRATION_MINUTES")),
        cors_origins=[o.strip() for o in cors.split(",") if o.strip()],
        prediccion_lat=float(_required("PREDICCION_LAT")),
        prediccion_lon=float(_required("PREDICCION_LON")),
        prediccion_horizonte_dias=int(os.getenv("PREDICCION_HORIZONTE_DIAS") or 3),
        modelos_dir=Path(_required("MODELOS_DIR")),
    )
