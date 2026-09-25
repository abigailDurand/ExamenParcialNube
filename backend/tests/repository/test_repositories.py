"""test-specs.md › BACKEND › Pruebas de repository — integración con PostgreSQL (BD de prueba)."""
import asyncio
from datetime import date

import asyncpg
import pytest

from repository import (
    clima_repository,
    consultations_repository,
    feriados_repository,
    locations_repository,
    predicciones_repository,
    users_repository,
    visitas_repository,
    weather_cache_repository,
)
from repository import db as db_module


@pytest.fixture
async def tingo(db):
    await locations_repository.create_location_if_missing("Tingo María", "region", "-9.295,-75.9975")
    return await locations_repository.get_location_by_name("Tingo María")


@pytest.fixture
async def usuario(db):
    await users_repository.create_user_if_missing("admin@correo.com", "$2b$12$hashdeprueba")
    return await users_repository.get_user_by_email("admin@correo.com")


async def test_get_user_by_email_devuelve_usuario_con_hash_o_none(usuario):
    """Spec: 'get_user_by_email devuelve el usuario (con su hash) o None'."""
    assert usuario["email"] == "admin@correo.com"
    assert usuario["password_hash"] == "$2b$12$hashdeprueba"
    assert await users_repository.get_user_by_email("nadie@correo.com") is None


async def test_bd_rechaza_correo_con_mayusculas(db):
    """architecture › users: CHECK email = lower(email) (caso de error)."""
    with pytest.raises(asyncpg.CheckViolationError):
        await users_repository.create_user_if_missing("Admin@Correo.com", "x")


async def test_list_locations_devuelve_el_catalogo(tingo):
    """Spec: 'list_locations devuelve el catálogo de ubicaciones (inicialmente solo Tingo María)'."""
    assert await locations_repository.list_locations() == [{"id": tingo["id"], "name": "Tingo María", "type": "region"}]


async def test_get_cached_weather_none_si_no_existe(tingo):
    """Spec: 'get_cached_weather devuelve None si no existe'."""
    assert await weather_cache_repository.get_cached_weather(tingo["id"], 10) is None


async def test_upsert_y_get_cached_weather(tingo):
    """Spec: 'upsert_cached_weather inserta y luego get_cached_weather lo recupera'."""
    await weather_cache_repository.upsert_cached_weather(tingo["id"], 24.4, 60, "Despejado", "weatherapi")
    await weather_cache_repository.upsert_cached_weather(tingo["id"], 21.0, 85, "Lluvia", "open-meteo")
    cache = await weather_cache_repository.get_cached_weather(tingo["id"], 10)
    assert (cache["temp_c"], cache["humidity"], cache["condition"], cache["source"]) == (21.0, 85, "Lluvia", "open-meteo")


async def test_get_cached_weather_none_si_expiro_el_ttl(db, tingo):
    """Spec: 'get_cached_weather devuelve None ... si expiró el TTL' (expiración de caché)."""
    await weather_cache_repository.upsert_cached_weather(tingo["id"], 24.0, 60, "Despejado", "weatherapi")
    await db.execute("UPDATE weather_cache SET fetched_at = now() - interval '11 minutes'")
    assert await weather_cache_repository.get_cached_weather(tingo["id"], 10) is None


async def test_add_consultation_y_list_recent_mas_reciente_primero(db, tingo, usuario):
    """Spec: 'add_consultation registra la consulta y list_recent la devuelve'."""
    await consultations_repository.add_consultation(usuario["id"], tingo["id"])
    await db.execute("UPDATE consultations SET created_at = now() - interval '1 hour'")
    await consultations_repository.add_consultation(usuario["id"], tingo["id"])
    recientes = await consultations_repository.list_recent(usuario["id"], 10)
    assert [r["location"] for r in recientes] == ["Tingo María", "Tingo María"]
    assert recientes[0]["created_at"] > recientes[1]["created_at"]


async def test_usa_el_pool_y_no_abre_una_conexion_por_peticion(db, tingo, monkeypatch):
    """Spec: 'Usa el pool de conexiones (no abre una conexión por petición)'."""
    abiertas = []
    monkeypatch.setattr(asyncpg, "connect", lambda *a, **k: abiertas.append(a))
    await asyncio.gather(*(locations_repository.list_locations() for _ in range(20)))
    assert abiertas == []
    assert db_module.get_pool() is db
    assert db.get_size() <= 5  # DB_POOL_MAX de prueba


# ---------- Tablas de la predicción ----------
async def test_visitas_sinteticas_marcadas_y_registro_real_tiene_prioridad(db, usuario):
    """Spec: 'Los datos sintéticos se marcan con es_sintetico = true; si existe un registro real de la misma fecha, tiene prioridad'."""
    d1, d2 = date(2025, 7, 28), date(2025, 7, 29)
    await visitas_repository.insert_sinteticas([(d1, 100), (d2, 110)])
    real = await visitas_repository.upsert_visita_real(d1, 150, usuario["id"])
    assert real == {"fecha": d1, "cantidad_visitantes": 150, "es_sintetico": False}
    await visitas_repository.insert_sinteticas([(d1, 999)])  # el seed no pisa lo real
    filas = await visitas_repository.list_visitas_con_prediccion(d1, d2)
    assert [(f["cantidad_visitantes"], f["es_sintetico"]) for f in filas] == [(150, False), (110, True)]


async def test_pronostico_no_pisa_clima_observado(db):
    """prediccion-specs › Modelo de datos: el dato observado reemplaza al pronóstico, nunca al revés."""
    dia = {"fecha": date(2026, 9, 26), "temp_max": 30.0, "temp_min": 19.0, "lluvia_mm": 1.0, "humedad": 70}
    await clima_repository.upsert_pronostico([dia])
    await clima_repository.upsert_observado([{**dia, "lluvia_mm": 12.0}])
    await clima_repository.upsert_pronostico([{**dia, "lluvia_mm": 0.0}])
    [guardado] = await clima_repository.get_clima(dia["fecha"], dia["fecha"])
    assert (guardado["lluvia_mm"], guardado["es_pronostico"]) == (12.0, False)


async def test_ultima_prediccion_por_fecha(db):
    """prediccion-specs › Endpoints: para una fecha con varias predicciones se devuelve la más reciente."""
    base = {"fecha": date(2026, 9, 26), "nivel_afluencia": "Media", "version_modelo": 1,
            "entrenado_con_sinteticos": True, "dato_incompleto": False}
    await predicciones_repository.insert_predicciones([{**base, "visitantes_predichos": 40}])
    await db.execute("UPDATE predicciones SET creado_en = now() - interval '1 day'")
    await predicciones_repository.insert_predicciones([{**base, "visitantes_predichos": 55}])
    [ultima] = await predicciones_repository.get_ultimas(base["fecha"], base["fecha"])
    assert ultima["visitantes_predichos"] == 55


async def test_feriados_duplicado_y_borrado_inexistente(db):
    """Caso de error del repository: feriado repetido y borrado de una fecha inexistente."""
    assert await feriados_repository.insert_feriado(date(2026, 10, 15), "Prueba") is True
    assert await feriados_repository.insert_feriado(date(2026, 10, 15), "Otra") is False
    assert await feriados_repository.delete_feriado(date(2026, 10, 15)) is True
    assert await feriados_repository.delete_feriado(date(2026, 10, 15)) is False
