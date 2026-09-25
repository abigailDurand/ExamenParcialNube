"""condicional-api-specs.md — contrato y mapeo de los clientes (proveedores simulados con httpx.MockTransport).

Cubre la parte de 'traduce el estado a español (desde el proveedor que haya respondido)'
de test-specs.md y las excepciones compartidas.
"""
import httpx
import pytest

from services import open_meteo_client, weatherapi_client
from services.weather_provider_errors import WeatherLocationNotFoundError, WeatherProviderError


def simular_http(monkeypatch, modulo, manejador):
    """Reemplaza httpx.AsyncClient del módulo por uno con transporte simulado (sin red)."""
    original = httpx.AsyncClient

    def cliente(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(manejador)
        return original(*args, **kwargs)

    monkeypatch.setattr(modulo.httpx, "AsyncClient", cliente)


async def test_weatherapi_mapea_y_traduce(monkeypatch):
    def manejador(request):
        return httpx.Response(200, json={"current": {"temp_c": 24.3, "humidity": 60,
                                                     "condition": {"text": "Partly cloudy"}}})

    simular_http(monkeypatch, weatherapi_client, manejador)
    assert await weatherapi_client.fetch_current_weather("q") == {
        "temp_c": 24.3, "humidity": 60, "condition": "Parcialmente nublado"}


async def test_weatherapi_400_codigo_1006_es_ubicacion_no_encontrada(monkeypatch):
    simular_http(monkeypatch, weatherapi_client,
                 lambda r: httpx.Response(400, json={"error": {"code": 1006, "message": "No location found"}}))
    with pytest.raises(WeatherLocationNotFoundError):
        await weatherapi_client.fetch_current_weather("q")


@pytest.mark.parametrize("status", [401, 500, 503])
async def test_weatherapi_otro_status_es_error_de_proveedor(monkeypatch, status):
    simular_http(monkeypatch, weatherapi_client, lambda r: httpx.Response(status, json={}))
    with pytest.raises(WeatherProviderError):
        await weatherapi_client.fetch_current_weather("q")


async def test_weatherapi_error_de_red_es_error_de_proveedor(monkeypatch):
    def manejador(request):
        raise httpx.ConnectError("sin red", request=request)

    simular_http(monkeypatch, weatherapi_client, manejador)
    with pytest.raises(WeatherProviderError):
        await weatherapi_client.fetch_current_weather("q")


async def test_open_meteo_geocodifica_y_traduce_codigo_wmo(monkeypatch):
    def manejador(request):
        if "geocoding" in request.url.host:
            assert request.url.params["name"] == "Tingo María"
            return httpx.Response(200, json={"results": [{"latitude": -9.29, "longitude": -75.99}]})
        return httpx.Response(200, json={"current": {"temperature_2m": 27.1, "relative_humidity_2m": 75,
                                                     "weather_code": 63}})

    simular_http(monkeypatch, open_meteo_client, manejador)
    assert await open_meteo_client.fetch_current_weather("Tingo María") == {
        "temp_c": 27.1, "humidity": 75, "condition": "Lluvia"}


async def test_open_meteo_geocoding_vacio_es_ubicacion_no_encontrada(monkeypatch):
    simular_http(monkeypatch, open_meteo_client, lambda r: httpx.Response(200, json={}))
    with pytest.raises(WeatherLocationNotFoundError):
        await open_meteo_client.fetch_current_weather("Inexistente")


async def test_pronostico_diario_misma_forma_en_ambos_clientes(monkeypatch):
    """condicional-api-specs › PRONÓSTICO DIARIO: misma firma y misma forma de salida."""
    def manejador(request):
        # Ambos clientes comparten el módulo httpx: un solo simulador que responde según el host
        if request.url.host == "weatherapi.test":
            return httpx.Response(200, json={"forecast": {"forecastday": [
                {"date": "2026-09-26", "day": {"maxtemp_c": 31.3, "mintemp_c": 19.0, "totalprecip_mm": 0.4,
                                               "avghumidity": 62}}]}})
        return httpx.Response(200, json={"daily": {
            "time": ["2026-09-26"], "temperature_2m_max": [31.3], "temperature_2m_min": [19.0],
            "precipitation_sum": [None], "relative_humidity_2m_mean": [62.4]}})

    simular_http(monkeypatch, weatherapi_client, manejador)
    wa = await weatherapi_client.fetch_daily_forecast(-9.3, -76.0, 1)
    om = await open_meteo_client.fetch_daily_forecast(-9.3, -76.0, 1)
    assert set(wa[0]) == set(om[0]) == {"fecha", "temp_max", "temp_min", "lluvia_mm", "humedad"}
    assert om[0]["lluvia_mm"] is None  # lluvia no informada → None (luego dato_incompleto)
