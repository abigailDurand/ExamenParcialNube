"""test-specs.md › BACKEND › Pruebas de endpoints (/routes) — integración (API + BD de prueba).

Proveedores de clima siempre simulados.
"""
import time
from datetime import date, timedelta

import httpx
import pytest

from main import app
from repository import clima_repository, locations_repository, users_repository, visitas_repository
from services import open_meteo_client, weatherapi_client
from services.prediccion_service import hoy_lima
from services.security import hash_password
from services.weather_provider_errors import WeatherLocationNotFoundError, WeatherProviderError

EMAIL = "admin@correo.com"
PASSWORD = "Clave-De-Prueba-1"
TINGO = "Tingo María"


@pytest.fixture
async def client(db):
    await users_repository.create_user_if_missing(EMAIL, hash_password(PASSWORD))
    await locations_repository.create_location_if_missing(TINGO, "region", "-9.295,-75.9975")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c


@pytest.fixture
async def auth(client):
    r = await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def proveedores(monkeypatch, weatherapi, open_meteo):
    llamadas = []

    def hacer(nombre, resultado):
        async def fetch(query):
            llamadas.append(nombre)
            if isinstance(resultado, Exception):
                raise resultado
            return resultado

        return fetch

    monkeypatch.setattr(weatherapi_client, "fetch_current_weather", hacer("weatherapi", weatherapi))
    monkeypatch.setattr(open_meteo_client, "fetch_current_weather", hacer("open-meteo", open_meteo))
    return llamadas


DATOS = {"temp_c": 24.0, "humidity": 60, "condition": "Despejado"}


# ---------- Login ----------
async def test_login_valido_200_con_access_token(client):
    """Spec: 'POST /api/v1/auth/login con credenciales válidas → 200 y body con access_token'."""
    r = await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["token_type"] == "bearer" and body["expires_in"] == 3600
    assert PASSWORD not in r.text and "password" not in body


async def test_login_invalido_401(client):
    """Spec: 'POST /api/v1/auth/login con credenciales inválidas → 401'."""
    r = await client.post("/auth/login", json={"email": EMAIL, "password": "mala"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Correo o contraseña incorrectos"}


@pytest.mark.parametrize("body", [{"password": "x"}, {"email": EMAIL}, {"email": "no-es-correo", "password": "x"}],
                         ids=["sin-email", "sin-password", "correo-invalido"])
async def test_login_campos_faltantes_o_invalidos_422(client, body):
    """Spec: 'POST /api/v1/auth/login sin email o sin password → 422'."""
    r = await client.post("/auth/login", json=body)
    assert r.status_code == 422


async def test_auth_me(client, auth):
    """Spec: 'GET /api/v1/auth/me con token válido → 200; sin token o token vencido → 401'."""
    r = await client.get("/auth/me", headers=auth)
    assert r.status_code == 200 and r.json()["email"] == EMAIL
    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.get("/auth/me", headers={"Authorization": "Bearer vencido.o.falso"})).status_code == 401


# ---------- Consulta del clima ----------
@pytest.mark.parametrize("ruta", ["/locations", f"/weather?location={TINGO}", "/consultations/recent"])
async def test_endpoints_del_clima_sin_authorization_401(client, ruta):
    """Spec: GET locations / weather / consultations/recent sin Authorization → 401."""
    assert (await client.get(ruta)).status_code == 401


async def test_weather_sin_location_400(client, auth):
    """Spec: 'GET /api/v1/weather sin query param location → 400'."""
    assert (await client.get("/weather", headers=auth)).status_code == 400


async def test_weather_valido_200(client, auth, monkeypatch):
    """Spec: 'GET /api/v1/weather?location=Tingo María con token válido → 200 y body con location, temperature, condition, humidity, source'."""
    proveedores(monkeypatch, DATOS, DATOS)
    r = await client.get("/weather", params={"location": TINGO}, headers=auth)
    assert r.status_code == 200
    assert r.json() == {"location": TINGO, "temperature": "24°C", "condition": "Despejado",
                        "humidity": "60%", "source": "weatherapi"}


async def test_weather_fallback_open_meteo_200(client, auth, monkeypatch):
    """Spec: 'Si WeatherAPI falla y Open-Meteo responde → 200 con source: "open-meteo"'."""
    proveedores(monkeypatch, WeatherProviderError("caído"), DATOS)
    r = await client.get("/weather", params={"location": TINGO}, headers=auth)
    assert r.status_code == 200 and r.json()["source"] == "open-meteo"


async def test_weather_ninguno_encuentra_404(client, auth, monkeypatch):
    """Spec: 'Si ninguno de los dos encuentra la ubicación → 404'."""
    proveedores(monkeypatch, WeatherLocationNotFoundError("x"), WeatherLocationNotFoundError("y"))
    assert (await client.get("/weather", params={"location": TINGO}, headers=auth)).status_code == 404


async def test_weather_ambos_fallan_503(client, auth, monkeypatch):
    """Spec: 'Si ambos fallan por cualquier otro motivo → 503'."""
    proveedores(monkeypatch, WeatherProviderError("x"), WeatherProviderError("y"))
    assert (await client.get("/weather", params={"location": TINGO}, headers=auth)).status_code == 503


async def test_segunda_consulta_desde_cache_en_menos_de_100ms(client, auth, monkeypatch):
    """Spec: 'Segunda consulta de la misma ubicación responde en < 100 ms' (y sin llamar a WeatherAPI)."""
    llamadas = proveedores(monkeypatch, DATOS, DATOS)
    await client.get("/weather", params={"location": TINGO}, headers=auth)
    inicio = time.perf_counter()
    r = await client.get("/weather", params={"location": TINGO}, headers=auth)
    duracion_ms = (time.perf_counter() - inicio) * 1000
    assert r.status_code == 200
    assert duracion_ms < 100, f"{duracion_ms:.1f} ms"
    assert llamadas == ["weatherapi"]


async def test_consultations_recent_mas_reciente_primero(client, auth, db, monkeypatch):
    """Spec: 'GET /api/v1/consultations/recent con token válido → 200 y lista de consultas, más reciente primero'."""
    proveedores(monkeypatch, DATOS, DATOS)
    await client.get("/weather", params={"location": TINGO}, headers=auth)
    await db.execute("UPDATE consultations SET created_at = now() - interval '1 hour'")
    await client.get("/weather", params={"location": TINGO}, headers=auth)
    r = await client.get("/consultations/recent", headers=auth)
    assert r.status_code == 200
    fechas = [c["created_at"] for c in r.json()]
    assert len(fechas) == 2 and fechas == sorted(fechas, reverse=True)


# ---------- Predicción ----------
@pytest.fixture
async def pronostico_3_dias(db):
    hoy = hoy_lima()
    await clima_repository.upsert_pronostico([
        {"fecha": hoy + timedelta(days=i), "temp_max": 30.0, "temp_min": 19.0,
         "lluvia_mm": None if i == 2 else 2.0, "humedad": 70}
        for i in range(3)
    ])
    return hoy


async def test_predicciones_publicas_3_dias_200(client, con_modelo, pronostico_3_dias):
    """Spec: 'GET /api/v1/predicciones?dias=3 sin token → 200 (público)' + campos del Escenario 6."""
    r = await client.get("/predicciones", params={"dias": 3})
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 3
    campos = {"fecha", "visitantes_predichos", "nivel_afluencia", "version_modelo",
              "entrenado_con_sinteticos", "dato_incompleto"}
    assert all(campos <= set(p) for p in datos)
    assert [p["dato_incompleto"] for p in datos] == [False, False, True]


@pytest.mark.parametrize("dias", [0, 4])
async def test_predicciones_dias_fuera_de_rango_400(client, con_modelo, dias):
    """Spec: 'GET /api/v1/predicciones?dias=0 o mayor al máximo → 400'."""
    assert (await client.get("/predicciones", params={"dias": dias})).status_code == 400


async def test_prediccion_por_fecha_publica_200_y_404(client, con_modelo, pronostico_3_dias):
    """Spec: '/predicciones/{fecha} sin token → 200 (público)' y 'sin predicción para esa fecha → 404'."""
    await client.get("/predicciones", params={"dias": 3})
    assert (await client.get(f"/predicciones/{pronostico_3_dias.isoformat()}")).status_code == 200
    assert (await client.get("/predicciones/2030-01-01")).status_code == 404


async def test_prediccion_modelo_no_entrenado_503(client, sin_modelo):
    """Escenario 6: 'Dado que el modelo no está entrenado ... responde 503'."""
    assert (await client.get("/predicciones", params={"dias": 3})).status_code == 503


# ---------- Acciones del administrador ----------
ACCIONES_ADMIN = [
    ("POST", "/visitas", {"fecha": "2025-07-28", "cantidad_visitantes": 150}),
    ("GET", "/visitas?desde=2025-07-01&hasta=2025-07-31", None),
    ("GET", "/feriados?anio=2026", None),
    ("POST", "/feriados", {"fecha": "2026-10-15", "nombre": "Aniversario de Tingo María"}),
    ("DELETE", "/feriados/2026-10-15", None),
    ("POST", "/modelo/reentrenar", None),
    ("GET", "/modelo/metricas", None),
]


@pytest.mark.parametrize("metodo, ruta, body", ACCIONES_ADMIN, ids=[f"{m} {r}" for m, r, _ in ACCIONES_ADMIN])
async def test_acciones_admin_sin_token_401(client, metodo, ruta, body):
    """Spec (Escenario 8): sin token → 401."""
    assert (await client.request(metodo, ruta, json=body)).status_code == 401


@pytest.mark.parametrize("metodo, ruta, body", ACCIONES_ADMIN, ids=[f"{m} {r}" for m, r, _ in ACCIONES_ADMIN])
async def test_acciones_admin_con_token_200(client, auth, con_modelo, db, metodo, ruta, body,
                                            datos_entrenamiento):
    """Spec: '... sin token → 401; con token → 200' (literal: todas las acciones responden 200)."""
    if ruta.startswith("/feriados/"):
        await client.post("/feriados", json={"fecha": "2026-10-15", "nombre": "Prueba"}, headers=auth)
    if ruta == "/modelo/reentrenar":
        await clima_repository.upsert_observado([
            {k: d[k] for k in ("fecha", "temp_max", "temp_min", "lluvia_mm")} | {"humedad": 80}
            for d in datos_entrenamiento[:60]])
        await visitas_repository.insert_sinteticas([(d["fecha"], d["cantidad_visitantes"])
                                                    for d in datos_entrenamiento[:60]])
    r = await client.request(metodo, ruta, json=body, headers=auth)
    assert r.status_code == 200, f"{metodo} {ruta} respondió {r.status_code}"


async def test_feriado_repetido_409_y_borrado_inexistente_404(client, auth):
    """Spec: 'POST /api/v1/feriados con fecha existente → 409; DELETE de una fecha inexistente → 404'."""
    body = {"fecha": "2026-10-15", "nombre": "Aniversario de Tingo María"}
    assert (await client.post("/feriados", json=body, headers=auth)).status_code == 200
    assert (await client.post("/feriados", json=body, headers=auth)).status_code == 409
    assert (await client.delete("/feriados/2030-01-01", headers=auth)).status_code == 404


async def test_visita_real_reemplaza_la_sintetica(client, auth):
    """Spec: 'POST /api/v1/visitas sobre una fecha sintética la reemplaza con es_sintetico = false'."""
    await visitas_repository.insert_sinteticas([(date(2025, 7, 28), 100)])
    r = await client.post("/visitas", json={"fecha": "2025-07-28", "cantidad_visitantes": 150}, headers=auth)
    assert r.json() == {"fecha": "2025-07-28", "cantidad_visitantes": 150, "es_sintetico": False}
