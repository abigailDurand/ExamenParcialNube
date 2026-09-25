"""test-specs.md › BACKEND › Pruebas de servicios — consulta del clima con caché y fallback.

WeatherAPI y Open-Meteo siempre simulados; repositorios reemplazados por dobles en memoria.
"""
import pytest
from fastapi import HTTPException

from repository import consultations_repository, locations_repository, weather_cache_repository
from services import open_meteo_client, weather_service, weatherapi_client
from services.weather_provider_errors import WeatherLocationNotFoundError, WeatherProviderError

TINGO = {"id": 1, "name": "Tingo María", "type": "region", "weatherapi_query": "-9.295,-75.9975"}
DATOS = {"temp_c": 24.0, "humidity": 60, "condition": "Despejado"}


class Estado:
    def __init__(self):
        self.cache = None
        self.upserts = []
        self.consultas = []
        self.llamadas = {"weatherapi": [], "open-meteo": []}


@pytest.fixture
def estado(monkeypatch):
    e = Estado()

    async def get_location_by_name(name):
        return TINGO if name == TINGO["name"] else None

    async def get_cached_weather(location_id, ttl):
        return e.cache

    async def upsert_cached_weather(*args):
        e.upserts.append(args)

    async def add_consultation(user_id, location_id):
        e.consultas.append((user_id, location_id))

    monkeypatch.setattr(locations_repository, "get_location_by_name", get_location_by_name)
    monkeypatch.setattr(weather_cache_repository, "get_cached_weather", get_cached_weather)
    monkeypatch.setattr(weather_cache_repository, "upsert_cached_weather", upsert_cached_weather)
    monkeypatch.setattr(consultations_repository, "add_consultation", add_consultation)
    return e


def simular_proveedores(monkeypatch, estado, weatherapi, open_meteo):
    """Cada proveedor es un dict de datos o una excepción a levantar."""

    def hacer(nombre, resultado):
        async def fetch(query):
            estado.llamadas[nombre].append(query)
            if isinstance(resultado, Exception):
                raise resultado
            return resultado

        return fetch

    monkeypatch.setattr(weatherapi_client, "fetch_current_weather", hacer("weatherapi", weatherapi))
    monkeypatch.setattr(open_meteo_client, "fetch_current_weather", hacer("open-meteo", open_meteo))


@pytest.mark.parametrize("location", [None, ""], ids=["ausente", "vacia"])
async def test_sin_ubicacion_levanta_400(estado, location):
    """Spec (architecture › Códigos de error): 400 si falta el query param location."""
    with pytest.raises(HTTPException) as exc:
        await weather_service.get_weather(location, user_id=1)
    assert exc.value.status_code == 400


async def test_ubicacion_fuera_del_catalogo_levanta_400(estado, monkeypatch):
    """Spec: 'Rechaza la ubicación si no pertenece al catálogo (levanta 400)'."""
    simular_proveedores(monkeypatch, estado, DATOS, DATOS)
    with pytest.raises(HTTPException) as exc:
        await weather_service.get_weather("Peru", user_id=1)
    assert exc.value.status_code == 400
    assert estado.llamadas == {"weatherapi": [], "open-meteo": []}


async def test_cache_vigente_devuelve_bd_sin_llamar_proveedores(estado, monkeypatch):
    """Spec: 'Ubicación en caché y dentro del TTL → devuelve BD, no llama a ningún proveedor'."""
    estado.cache = {"temp_c": 20.4, "humidity": 80, "condition": "Nublado", "source": "open-meteo"}
    simular_proveedores(monkeypatch, estado, DATOS, DATOS)
    resultado = await weather_service.get_weather("Tingo María", user_id=1)
    assert estado.llamadas == {"weatherapi": [], "open-meteo": []}
    assert resultado == {
        "location": "Tingo María",
        "temperature": "20°C",
        "condition": "Nublado",
        "humidity": "80%",
        "source": "open-meteo",
    }


async def test_sin_cache_llama_weatherapi_formatea_y_guarda(estado, monkeypatch):
    """Spec: 'Ubicación sin caché o expirada → llama a WeatherAPI, formatea y guarda en caché con source weatherapi'."""
    simular_proveedores(monkeypatch, estado, DATOS, WeatherProviderError("no debería llamarse"))
    resultado = await weather_service.get_weather("Tingo María", user_id=1)
    assert estado.llamadas["weatherapi"] == [TINGO["weatherapi_query"]]
    assert estado.llamadas["open-meteo"] == []
    assert resultado["source"] == "weatherapi"
    assert estado.upserts == [(1, 24.0, 60, "Despejado", "weatherapi")]


@pytest.mark.parametrize(
    "falla",
    [WeatherProviderError("red"), WeatherProviderError("error 500"), WeatherLocationNotFoundError("no existe")],
    ids=["red", "error-proveedor", "ubicacion-no-encontrada"],
)
async def test_weatherapi_falla_reintenta_con_open_meteo(estado, monkeypatch, falla):
    """Spec: 'Si WeatherAPI falla (red, error del proveedor o ubicación no encontrada) → reintenta con Open-Meteo'."""
    simular_proveedores(monkeypatch, estado, falla, {"temp_c": 26.6, "humidity": 70, "condition": "Lluvia"})
    resultado = await weather_service.get_weather("Tingo María", user_id=1)
    assert estado.llamadas["open-meteo"] == ["Tingo María"]  # Open-Meteo usa locations.name
    assert resultado["source"] == "open-meteo"
    assert estado.upserts == [(1, 26.6, 70, "Lluvia", "open-meteo")]


async def test_ninguno_encuentra_la_ubicacion_404(estado, monkeypatch):
    """Spec: 'Si WeatherAPI y Open-Meteo fallan porque ninguno encuentra la ubicación → 404'."""
    simular_proveedores(monkeypatch, estado, WeatherLocationNotFoundError("x"), WeatherLocationNotFoundError("y"))
    with pytest.raises(HTTPException) as exc:
        await weather_service.get_weather("Tingo María", user_id=1)
    assert exc.value.status_code == 404
    assert exc.value.detail == "No se pudo obtener el clima de esta ubicación"
    assert estado.upserts == [] and estado.consultas == []


@pytest.mark.parametrize(
    "weatherapi, open_meteo",
    [
        (WeatherProviderError("red"), WeatherProviderError("timeout")),
        (WeatherLocationNotFoundError("x"), WeatherProviderError("500")),
        (WeatherProviderError("500"), WeatherLocationNotFoundError("y")),
    ],
    ids=["ambos-error", "notfound+error", "error+notfound"],
)
async def test_ambos_fallan_por_otro_motivo_503_sin_cache_ni_historial(estado, monkeypatch, weatherapi, open_meteo):
    """Spec: 'fallan por cualquier otro motivo → 503, y no se guarda nada en caché ni se registra en el historial'."""
    simular_proveedores(monkeypatch, estado, weatherapi, open_meteo)
    with pytest.raises(HTTPException) as exc:
        await weather_service.get_weather("Tingo María", user_id=1)
    assert exc.value.status_code == 503
    assert estado.upserts == [] and estado.consultas == []


async def test_formato_temperatura_humedad_y_estado_en_espanol(estado, monkeypatch):
    """Spec: 'Formatea temperatura "24°C", humedad "60%" y traduce el estado a español'."""
    simular_proveedores(monkeypatch, estado, DATOS, DATOS)
    resultado = await weather_service.get_weather("Tingo María", user_id=1)
    assert resultado["temperature"] == "24°C"
    assert resultado["humidity"] == "60%"
    assert resultado["condition"] == "Despejado"


async def test_registra_la_consulta_en_el_historial(estado, monkeypatch):
    """Spec: 'Registra la consulta en el historial del usuario'."""
    simular_proveedores(monkeypatch, estado, DATOS, DATOS)
    await weather_service.get_weather("Tingo María", user_id=5)
    assert estado.consultas == [(5, 1)]
