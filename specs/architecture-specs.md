# Arquitectura

## TECNOLOGÍA
- Frontend: React + JavaScript (corre en el navegador)
- Backend: Python 3.13 + FastAPI
- Base de datos: PostgreSQL
- Proveedor externo del clima: WeatherAPI (https://www.weatherapi.com), con
  fallback a Open-Meteo (ver specs/condicional-api-specs.md)
- Autenticación: login con correo + contraseña (hash bcrypt) que emite un JWT
  (Bearer token) usado en el header Authorization de los endpoints protegidos
  (ver specs/login-specs.md). Solo el administrador tiene cuenta.
- Predicción de visitantes a Las Pavas: Random Forest (scikit-learn) con
  pronóstico diario WeatherAPI → Open-Meteo e histórico de Open-Meteo Archive
  (ver specs/prediccion-specs.md)

## TIPO DE APLICACIÓN
- Web (corre en el navegador)

## PATRÓN DE ARQUITECTURA
- Patrón: Repository Pattern
- Los endpoints solo reciben, delegan y devuelven
- La lógica de negocio va en una capa de servicios
- La conexión a BD va en una capa separada (repository)
- La integración con WeatherAPI va en su propio cliente dentro de /services y es
  condicional: si falla, se usa el cliente de Open-Meteo, que también vive en /services
  (ver specs/condicional-api-specs.md para el detalle completo de esta lógica)

## ESTRUCTURA DE CARPETAS BACKEND
- /routes     → endpoints FastAPI
- /services   → lógica de negocio + clientes de WeatherAPI/Open-Meteo + validación de JWT
                + entrenamiento, predicción y generación de datos sintéticos
- /jobs       → tareas programadas (descarga diaria del clima, predicción,
                reentrenamiento semanal) que ejecuta el servicio `scheduler`;
                solo llaman a /services, igual que las rutas
- /repository → conexión y queries a PostgreSQL
- /models     → esquemas de datos (Pydantic)

## ESTRUCTURA DE CARPETAS FRONTEND
- /components → componentes React (menú desplegable, botón, tarjeta de resultado,
                vista pública de predicciones, panel del administrador)
- /services   → llamadas a la API del backend

## STACK Y DEPENDENCIAS TÉCNICAS

### Backend
- python-jose (o PyJWT) → emisión y verificación de JWT; el secreto va en .env
- passlib[bcrypt] → hash y verificación de contraseñas
- python-dotenv → lectura de variables de entorno
- asyncpg → conexión a PostgreSQL (con pool de conexiones)
- httpx → llamadas HTTP a WeatherAPI y a Open-Meteo
- scikit-learn → modelo Random Forest de regresión
- pandas → preparación de datos para entrenar
- joblib → guardar y cargar el modelo `.pkl`
- APScheduler → tareas programadas (zona horaria America/Lima)

### Frontend
- react-router → rutas (vista pública, login, panel del administrador)
- Librería de gráficos para visitas reales vs. predichas (RF-08): Recharts

### Proveedores climáticos
- WeatherAPI (weatherapi.com) → proveedor principal; key va en .env
- Open-Meteo (open-meteo.com) → proveedor de fallback; NO requiere API key
  - Geocoding: https://geocoding-api.open-meteo.com/v1/search?name={location}
  - Forecast: https://api.open-meteo.com/v1/forecast
  - Ver specs/condicional-api-specs.md para el detalle de esta integración
  - Archive (clima histórico, predicción): https://archive-api.open-meteo.com/v1/archive
  - La predicción usa el pronóstico diario WeatherAPI → Open-Meteo y, para
    entrenar, el histórico de Open-Meteo Archive (ver specs/prediccion-specs.md)

## DISEÑO DE API

> Endpoints públicos (sin token): POST /api/v1/auth/login, GET /api/v1/predicciones
> y GET /api/v1/predicciones/{fecha}. Todos los demás exigen
> Authorization: Bearer <token_jwt> del administrador (ver specs/login-specs.md).
> Los endpoints de predicción están en specs/prediccion-specs.md (sección 10).

### POST /api/v1/auth/login
- Body: { "email": "...", "password": "..." }
- Respuesta 200: { "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600 }
- Respuesta 401: credenciales inválidas o usuario inexistente (mensaje genérico)
- Respuesta 422: falta un campo o el correo no tiene formato válido

### GET /api/v1/auth/me  (opcional)
- Headers: Authorization: Bearer <token_jwt>
- Respuesta 200: { "id": 1, "email": "..." }
- Respuesta 401: token ausente, inválido o vencido

### GET /api/v1/locations
- Headers: Authorization: Bearer <token_jwt>
- Devuelve el catálogo de ubicaciones para el menú desplegable
  (catálogo inicial: solo la región Tingo María)
- Respuesta 200:
  [
    { "id": 1, "name": "Tingo María", "type": "region" }
  ]

### GET /api/v1/weather
- Query params: ?location={country_or_region_name}
- Headers: Authorization: Bearer <token_jwt>
- Respuesta 200:
  {
    "location": "Tingo María",
    "temperature": "24°C",
    "condition": "Despejado",
    "humidity": "60%",
    "source": "weatherapi"
  }
  > "source" indica qué proveedor respondió: "weatherapi" (caso normal)
  > u "open-meteo" (si WeatherAPI falló y se usó el fallback). El frontend
  > no cambia su comportamiento según este campo, es solo informativo/para logs.
  > Ver specs/condicional-api-specs.md para el detalle completo de esta lógica.

### Códigos de error
- 401 → sin token / token inválido o expirado (el frontend redirige a login)
- 400 → falta el query param `location` o no pertenece al catálogo
- 404 → ninguno de los dos proveedores (WeatherAPI ni Open-Meteo) encuentra la ubicación
- 503 → ambos proveedores fallan por cualquier otro motivo (no responden o
  devuelven error). Ver specs/condicional-api-specs.md para el detalle.

### GET /api/v1/consultations/recent
- Headers: Authorization: Bearer <token_jwt>
- Devuelve el historial de consultas del usuario autenticado (las más
  recientes primero), para el sidebar "Consultas recientes" (ver
  ui-design-specs.md)
- Respuesta 200:
  [
    { "location": "Tingo María", "created_at": "2026-09-22T10:00:00Z" }
  ]
- Respuesta 401: sin token / token inválido o expirado

## MODELO DE DATOS (PostgreSQL)
> Las marcas de tiempo son `timestamptz`; las fechas de calendario, `date`. El esquema se crea con las migraciones
> SQL descritas en `infraestructure-specs.md`.

- users
  - id (PK)
  - email (UNIQUE, CHECK email = lower(email))
  - password_hash (bcrypt)
  - created_at
- locations
  - id (PK)
  - name (UNIQUE)
  - type (CHECK type IN ('country', 'region'))
  - weatherapi_query (query específica de WeatherAPI; Open-Meteo geocodifica
    usando directamente `name`, ver specs/condicional-api-specs.md)
- weather_cache  (una fila por ubicación)
  - location_id (PK, FK → locations.id)
  - temp_c (numeric)
  - humidity (int)
  - condition (texto ya traducido al español)
  - source ('weatherapi' | 'open-meteo')
  - fetched_at
  - Se guardan los datos ya normalizados (no la respuesta cruda del proveedor).
  - Se escribe con `INSERT ... ON CONFLICT (location_id) DO UPDATE`.
  - Se sirve mientras `fetched_at > now() - WEATHER_CACHE_TTL_MINUTES`; al
    servir desde caché se devuelve el `source` guardado.
- consultations  (historial)
  - id (PK)
  - user_id (FK → users.id)
  - location_id (FK → locations.id)
  - created_at
  - Índice (user_id, created_at DESC) para GET /api/v1/consultations/recent,
    que devuelve `locations.name` como `location`.
- Tablas de la predicción: clima, visitas, feriados, predicciones
  (ver specs/prediccion-specs.md, sección 7)
