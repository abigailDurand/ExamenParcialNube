# Lógica condicional de fallback (WeatherAPI → Open-Meteo)

> Este spec asume ya leído `architecture-specs.md` (contrato de API, capas,
> modelo de datos) y `business-rules-specs.md`. Aquí solo se detalla la
> lógica condicional del clima: cuándo se dispara el fallback, cómo se
> normaliza cada proveedor y qué código HTTP corresponde a cada falla.

## POR QUÉ
- WeatherAPI es el proveedor principal, pero si no responde o falla, el
  usuario no debe quedarse sin clima: se reintenta automáticamente con
  Open-Meteo antes de devolver un error.

## CUÁNDO SE DISPARA EL FALLBACK
Se reintenta con Open-Meteo ante **cualquier** falla de WeatherAPI:
- No encuentra la ubicación
- Error de red / timeout (no se pudo contactar al proveedor)
- Responde con un status distinto de 200 (error del proveedor)

No hay distinción de "reintentar solo en ciertos casos": toda falla de
WeatherAPI dispara el intento con Open-Meteo.

## FLUJO
1. `GET /api/v1/weather?location=...` revisa primero la caché (sin cambios
   respecto a lo descrito en `business-rules-specs.md`).
2. Si no hay caché, se llama a WeatherAPI.
   - Si responde bien → se usa esa respuesta, `source = "weatherapi"`.
   - Si falla (cualquier motivo de la sección anterior) → se reintenta
     automáticamente con Open-Meteo.
3. Con Open-Meteo:
   - Primero se geocodifica el nombre de la ubicación (lat/long) contra
     `OPEN_METEO_GEOCODING_URL` usando `locations.name` (el mismo nombre
     del catálogo; Open-Meteo no usa `weatherapi_query`, que es específico
     de WeatherAPI).
   - Con lat/long se pide el clima actual a `OPEN_METEO_BASE_URL`.
   - Si responde bien → se usa esa respuesta, `source = "open-meteo"`.
4. Si ambos proveedores fallan, ver "CÓDIGOS DE ERROR" abajo.
5. La respuesta exitosa (de cualquiera de los dos proveedores) se cachea
   con el mismo TTL y se registra en el historial igual que hoy — no hay
   distinción de TTL ni de registro de historial según qué proveedor
   respondió.

## CÓDIGOS DE ERROR (cuando ambos proveedores fallan)
- **404** → los dos proveedores fallaron específicamente porque **ninguno
  encontró la ubicación** (WeatherAPI con status 400 / Open-Meteo con
  geocoding sin resultados).
- **503** → cualquier otra combinación de fallas (red, timeout, error del
  proveedor), sin importar si uno de los dos falló por "no encontrado" y
  el otro por error de proveedor. No se distingue 502 de 503: siempre 503.

## CONTRATO COMPARTIDO ENTRE CLIENTES (/backend/services)
- `weatherapi_client.fetch_current_weather(query)` y
  `open_meteo_client.fetch_current_weather(query)` exponen la misma firma y
  devuelven la misma forma: `{"temp_c": float, "humidity": int, "condition": str}`,
  con `condition` ya traducido al mismo vocabulario en español.
- Ambos levantan las mismas excepciones (`backend/services/weather_provider_errors.py`):
  - `WeatherLocationNotFoundError` → el proveedor no encontró la ubicación
  - `WeatherProviderError` → cualquier otro fallo (red, timeout, error 5xx)
- `weather_service` es el único que decide el código HTTP final y hace el
  fallback; los clientes no conocen a FastAPI ni devuelven HTTPException.

## RESPUESTA CRUDA DE OPEN-METEO Y SU MAPEO
- Geocoding (`GET {OPEN_METEO_GEOCODING_URL}?name={location}&count=1`):
  - `results[0].latitude` / `results[0].longitude` → coordenadas a usar
  - `results` vacío o ausente → `WeatherLocationNotFoundError`
- Forecast (`GET {OPEN_METEO_BASE_URL}/forecast?latitude=..&longitude=..&current=temperature_2m,relative_humidity_2m,weather_code`):
  - `current.temperature_2m` → `temp_c`
  - `current.relative_humidity_2m` → `humidity`
  - `current.weather_code` (código numérico WMO) → `condition`, mapeado con
    `OPEN_METEO_CODE_TRANSLATIONS` en `backend/services/weather_conditions.py`
    al mismo vocabulario en español que usa WeatherAPI (Despejado, Nublado,
    Lluvia, etc.)
- WeatherAPI: texto en inglés (`current.condition.text`) → traducido con
  `WEATHERAPI_CONDITION_TRANSLATIONS` en el mismo archivo.

## RESPUESTA DE /api/v1/weather
- Se agrega el campo `source` ("weatherapi" u "open-meteo"). Es
  informativo/para logs; el frontend no cambia su comportamiento según
  este campo (ver `ui-design-specs.md`, que no lo muestra en pantalla).

## PRONÓSTICO DIARIO (usado por la predicción de visitantes)
> La predicción (ver specs/prediccion-specs.md) usa el mismo orden
> WeatherAPI → Open-Meteo y las mismas excepciones, pero con datos diarios.

- Ambos clientes exponen además `fetch_daily_forecast(lat, lon, dias)` con la
  misma firma, que devuelve una lista de
  `{"fecha": date, "temp_max": float, "temp_min": float, "lluvia_mm": float | None, "humedad": int}`.
- WeatherAPI (`GET {WEATHERAPI_BASE_URL}/forecast.json?q={lat},{lon}&days={dias}`):
  - `forecast.forecastday[].date` → `fecha`
  - `day.maxtemp_c` / `day.mintemp_c` → `temp_max` / `temp_min`
  - `day.totalprecip_mm` → `lluvia_mm`
  - `day.avghumidity` → `humedad`
- Open-Meteo (`GET {OPEN_METEO_BASE_URL}/forecast?latitude=..&longitude=..&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean&timezone=America/Lima&forecast_days={dias}`):
  - `daily.time[]` → `fecha`
  - `daily.temperature_2m_max[]` / `daily.temperature_2m_min[]` → `temp_max` / `temp_min`
  - `daily.precipitation_sum[]` → `lluvia_mm`
  - `daily.relative_humidity_2m_mean[]` → `humedad`
- Si falta la lluvia (`None`), la predicción usa 0 y marca `dato_incompleto`.
- Diferencias con la consulta del clima actual:
  - No usa `weather_cache`: el pronóstico se guarda en la tabla `clima`.
  - Si ambos fallan no se responde 404/503 al usuario (lo ejecuta el
    scheduler): se reintenta el flujo completo 3 veces y luego se usa el
    último pronóstico guardado (RNF-07 de specs/prediccion-specs.md).
