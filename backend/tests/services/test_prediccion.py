"""test-specs.md › BACKEND › Pruebas de la predicción (/services) — unitarias."""
from datetime import date, timedelta

import pandas as pd
import pytest
from fastapi import HTTPException

from repository import clima_repository, feriados_repository, predicciones_repository, visitas_repository
from services import modelo_service, open_meteo_client, prediccion_service, pronostico_service, weatherapi_client
from services.sinteticos_service import factor_lluvia, generar_visitas
from services.variables_prediccion import FEATURES, construir_variables, nivel_afluencia
from services.weather_provider_errors import WeatherProviderError

LUNES = date(2025, 9, 22)
SABADO = date(2025, 9, 27)


# ---------- Reglas ----------
@pytest.mark.parametrize("visitantes, nivel", [(29, "Baja"), (30, "Media"), (60, "Media"), (61, "Alta")])
def test_nivel_de_afluencia_en_los_limites(visitantes, nivel):
    """Spec: 'Nivel de afluencia: 29 → Baja, 30 → Media, 60 → Media, 61 → Alta'."""
    assert nivel_afluencia(visitantes) == nivel


def test_variables_del_modelo():
    """Spec: 'Variables: fin_semana (sáb/dom), feriado, vacaciones (ene–mar y julio), dia_semana (0 = lunes), mes'."""
    lunes_sept = construir_variables(LUNES, 2.0, 30.0, 19.0, es_feriado=False)
    assert (lunes_sept["dia_semana"], lunes_sept["fin_semana"], lunes_sept["vacaciones"], lunes_sept["mes"]) == (0, 0, 0, 9)
    assert construir_variables(SABADO, 0, 30, 19, False)["fin_semana"] == 1
    assert construir_variables(SABADO + timedelta(days=1), 0, 30, 19, False)["fin_semana"] == 1
    assert construir_variables(date(2025, 7, 28), 0, 30, 19, es_feriado=True)["feriado"] == 1
    for mes, esperado in [(1, 1), (2, 1), (3, 1), (4, 0), (6, 0), (7, 1), (8, 0), (12, 0)]:
        assert construir_variables(date(2025, mes, 10), 0, 30, 19, False)["vacaciones"] == esperado


def test_lluvia_ausente_se_usa_cero():
    """Spec: 'Lluvia ausente → se usa 0 y dato_incompleto = true' (parte de las variables)."""
    assert construir_variables(LUNES, None, 30, 19, False)["lluvia_mm"] == 0.0


def test_sinteticos_factores_multiplicados_y_semilla_fija():
    """prediccion-specs › Datos sintéticos: factores que se multiplican, lluvia por tramos, semilla fija."""
    assert (factor_lluvia(4.9), factor_lluvia(5), factor_lluvia(15), factor_lluvia(15.1)) == (1.0, 0.75, 0.75, 0.5)
    clima = [{"fecha": date(2025, 7, 26), "lluvia_mm": 0.0}]  # sábado de julio
    [(_, visitantes)] = generar_visitas(clima, feriados={date(2025, 7, 26)})
    base = 40 * 1.8 * 2.0 * 1.4
    assert round(base * 0.9) <= visitantes <= round(base * 1.1)
    assert generar_visitas(clima, set()) == generar_visitas(clima, set())


# ---------- Modelo entrenado con datos sintéticos ----------
@pytest.fixture(scope="module")
def modelo(datos_entrenamiento, feriados_fijos):
    entrenado, mae, r2 = modelo_service._entrenar_sync(datos_entrenamiento, feriados_fijos)
    return entrenado, mae, r2


def predecir(modelo_rf, fecha, lluvia, feriado=False):
    fila = construir_variables(fecha, lluvia, 30.0, 19.5, feriado)
    return float(modelo_rf.predict(pd.DataFrame([fila], columns=FEATURES))[0])


def test_modelo_cumple_mae_y_r2(modelo):
    """Spec: 'El modelo entrenado con los datos sintéticos cumple MAE < 10 y R² ≥ 0.80 en el 20% de prueba'."""
    _, mae, r2 = modelo
    assert mae < 10, f"MAE={mae:.2f}"
    assert r2 >= 0.80, f"R²={r2:.3f}"


def test_lluvia_mayor_a_15mm_predice_menos_que_dia_seco(modelo):
    """Spec: 'Día con lluvia > 15 mm → predicción menor que un día seco equivalente'."""
    rf, _, _ = modelo
    for fecha in (LUNES, SABADO):
        assert predecir(rf, fecha, 25.0) < predecir(rf, fecha, 0.0)


def test_feriado_o_fin_de_semana_predice_mas_que_laborable(modelo):
    """Spec: 'Feriado o fin de semana → predicción mayor que un día laborable con clima similar'."""
    rf, _, _ = modelo
    laborable = predecir(rf, LUNES, 1.0)
    assert predecir(rf, SABADO, 1.0) > laborable
    assert predecir(rf, LUNES, 1.0, feriado=True) > laborable


# ---------- Servicio de predicción ----------
class ModeloFalso:
    def __init__(self, valores):
        self.valores = valores

    def predict(self, x):
        return self.valores[: len(x)]


@pytest.fixture
def repos_prediccion(monkeypatch):
    guardadas = []
    clima = [
        {"fecha": date(2026, 9, 26), "lluvia_mm": None, "temp_max": 30.0, "temp_min": 19.0},
        {"fecha": date(2026, 9, 27), "lluvia_mm": 3.0, "temp_max": 31.0, "temp_min": 19.0},
    ]

    async def get_clima(desde, hasta):
        return clima

    async def fechas_feriado(desde, hasta):
        return set()

    async def insert_predicciones(p):
        guardadas.extend(p)

    monkeypatch.setattr(clima_repository, "get_clima", get_clima)
    monkeypatch.setattr(feriados_repository, "fechas_feriado", fechas_feriado)
    monkeypatch.setattr(predicciones_repository, "insert_predicciones", insert_predicciones)
    return guardadas


async def test_visitantes_predichos_enteros_no_negativos_y_dato_incompleto(monkeypatch, repos_prediccion):
    """Spec: 'Visitantes predichos siempre enteros ≥ 0' y 'Lluvia ausente → dato_incompleto = true'."""
    meta = {"version": 4, "entrenado_con_sinteticos": True}
    monkeypatch.setattr(modelo_service, "exigir_modelo", lambda: (ModeloFalso([-3.7, 45.6]), meta))
    predicciones = await prediccion_service.generar_predicciones(date(2026, 9, 26), date(2026, 9, 27))
    assert [p["visitantes_predichos"] for p in predicciones] == [0, 46]
    assert all(isinstance(p["visitantes_predichos"], int) for p in predicciones)
    assert [p["dato_incompleto"] for p in predicciones] == [True, False]
    assert all(p["version_modelo"] == 4 and p["entrenado_con_sinteticos"] for p in predicciones)
    assert repos_prediccion == predicciones


async def test_modelo_no_entrenado_503(sin_modelo):
    """Spec: 'Modelo no entrenado → 503'."""
    for llamada in (lambda: prediccion_service.get_predicciones(3),
                    lambda: prediccion_service.get_prediccion(date(2026, 9, 26))):
        with pytest.raises(HTTPException) as exc:
            await llamada()
        assert exc.value.status_code == 503


@pytest.mark.parametrize("dias", [0, 4, -1])
async def test_dias_fuera_de_rango_400(con_modelo, dias):
    """business-rules › Reglas de predicción: horizonte 1 a PREDICCION_HORIZONTE_DIAS; fuera → 400."""
    with pytest.raises(HTTPException) as exc:
        await prediccion_service.get_predicciones(dias)
    assert exc.value.status_code == 400


async def test_reentrenar_guarda_nueva_version_con_metricas(monkeypatch, con_modelo, datos_entrenamiento, feriados_fijos):
    """Spec: 'Reentrenar guarda una nueva versión del .pkl con sus métricas'."""
    async def get_datos():
        return datos_entrenamiento

    async def fechas_feriado(desde, hasta):
        return feriados_fijos

    monkeypatch.setattr(visitas_repository, "get_datos_entrenamiento", get_datos)
    monkeypatch.setattr(feriados_repository, "fechas_feriado", fechas_feriado)
    meta = await modelo_service.entrenar()
    assert meta["version"] == 2
    assert (con_modelo / "modelo_v2.pkl").exists() and (con_modelo / "modelo_v2.json").exists()
    assert {"mae", "r2", "entrenado_con_sinteticos"} <= set(meta)
    assert modelo_service.metricas()["version"] == 2


# ---------- Pronóstico con fallos del proveedor ----------
@pytest.fixture
def pronostico_guardado(monkeypatch):
    guardados = []

    async def upsert_pronostico(dias):
        guardados.append(dias)

    monkeypatch.setattr(clima_repository, "upsert_pronostico", upsert_pronostico)
    return guardados


async def test_pronostico_weatherapi_falla_usa_open_meteo(monkeypatch, pronostico_guardado):
    """Spec: 'Pronóstico: WeatherAPI falla → usa Open-Meteo'."""
    dia = {"fecha": date(2026, 9, 26), "temp_max": 30.0, "temp_min": 19.0, "lluvia_mm": 1.0, "humedad": 70}

    async def weatherapi_falla(*args):
        raise WeatherProviderError("caído")

    async def open_meteo_ok(*args):
        return [dia]

    monkeypatch.setattr(weatherapi_client, "fetch_daily_forecast", weatherapi_falla)
    monkeypatch.setattr(open_meteo_client, "fetch_daily_forecast", open_meteo_ok)
    assert await pronostico_service.descargar_pronostico(espera_segundos=0) is True
    assert pronostico_guardado == [[dia]]


async def test_pronostico_ambos_fallan_3_reintentos_usa_el_guardado(monkeypatch, pronostico_guardado):
    """Spec: 'ambos fallan 3 veces → usa el último pronóstico guardado' (no se sobrescribe nada)."""
    intentos = {"weatherapi": 0, "open-meteo": 0}

    def falla(nombre):
        async def fetch(*args):
            intentos[nombre] += 1
            raise WeatherProviderError("caído")

        return fetch

    monkeypatch.setattr(weatherapi_client, "fetch_daily_forecast", falla("weatherapi"))
    monkeypatch.setattr(open_meteo_client, "fetch_daily_forecast", falla("open-meteo"))
    assert await pronostico_service.descargar_pronostico(espera_segundos=0) is False
    assert intentos == {"weatherapi": 4, "open-meteo": 4}  # intento inicial + 3 reintentos
    assert pronostico_guardado == []
