# Infraestructura

## ENTORNOS
- Desarrollo: local (con Docker)
- Producción: instancia EC2 de AWS, desplegada por GitHub Actions
  (ver specs/ci-specs.md)
- Base de datos: PostgreSQL en su propio contenedor (en ambos entornos)

## VERSIONES
- Python 3.13 (dependencias en `backend/requirements.txt`, instaladas con pip)
- Node 22 LTS (gestor: npm, con `package-lock.json` versionado)
- Vite como bundler del frontend
- PostgreSQL 16 (imagen `postgres:16`)
- nginx (imagen oficial `nginx:stable`)
- Docker Compose v5.x (versión de referencia: v5.5.1, la instalada en la EC2)
  - Se usa como plugin: `docker compose` (con espacio), nunca `docker-compose`
  - El `docker-compose.yml` **no** lleva la clave `version:` (obsoleta)
  - En desarrollo local se usa la misma versión mayor (v5.x) que en la EC2;
    se comprueba con `docker compose version`
  - En GitHub Actions el job `docker-build` usa la versión que traiga el
    runner; solo construye imágenes, así que no depende de la versión exacta

## VARIABLES DE ENTORNO
> Los valores reales viven **solo** en los archivos `.env`. Esta spec solo
> nombra las variables; nunca se escriben valores, claves ni secretos aquí,
> en el código, en el docker-compose ni en los workflows de GitHub Actions.
> Los `.env` no se suben al repositorio; se versionan `backend/.env.example`
> y `frontend/.env.example` con los nombres de las variables sin valores.

### Backend (`backend/.env`)
- DATABASE_URL → conexión de la app a PostgreSQL (dentro de Docker el host es `db`)
- TEST_DATABASE_URL → conexión a la BD de prueba (ver specs/test-specs.md)
- DB_POOL_MIN → mínimo de conexiones del pool
- DB_POOL_MAX → máximo de conexiones del pool
- POSTGRES_USER → usuario administrador del contenedor de PostgreSQL
- POSTGRES_PASSWORD → contraseña del administrador de PostgreSQL
- POSTGRES_DB → nombre de la BD principal
- APP_DB_USER → usuario de BD que usa el backend (permisos mínimos)
- APP_DB_PASSWORD → contraseña de ese usuario
- SEED_USER_EMAIL → correo del usuario inicial que crea el seed
- SEED_USER_PASSWORD → contraseña del usuario inicial (el seed guarda solo su hash bcrypt)
- WEATHERAPI_KEY → API key de weatherapi.com
- WEATHERAPI_BASE_URL → URL base de WeatherAPI
- OPEN_METEO_BASE_URL → URL base del forecast de Open-Meteo
- OPEN_METEO_GEOCODING_URL → URL del geocoding de Open-Meteo
- OPEN_METEO_ARCHIVE_URL → URL del clima histórico de Open-Meteo (entrenamiento)
- PREDICCION_LAT → latitud de Tingo María
- PREDICCION_LON → longitud de Tingo María
- PREDICCION_HORIZONTE_DIAS → máximo de días a predecir (por defecto 3)
- MODELOS_DIR → carpeta del volumen `modelos` donde se guardan los `.pkl`
- TZ → zona horaria de los contenedores (America/Lima)
- WEATHER_PROVIDER_TIMEOUT_SECONDS → tiempo máximo de espera a cada proveedor;
  si se supera, cuenta como falla y dispara el fallback
- WEATHER_CACHE_TTL_MINUTES → TTL de la caché del clima
- JWT_SECRET → secreto para firmar los JWT
- JWT_ALGORITHM → algoritmo de firma de los JWT
- JWT_EXPIRATION_MINUTES → minutos de vida del JWT
- CORS_ORIGINS → orígenes permitidos, separados por coma (en desarrollo el
  del servidor de Vite; en producción no hace falta porque nginx sirve
  frontend y API desde el mismo origen)
- BACKEND_URL → URL pública del backend

### Frontend (`frontend/.env`)
- VITE_BACKEND_URL → URL del backend que consume el frontend
  - En producción (EC2) va **vacía**: nginx sirve el frontend y la API desde
    el mismo origen, así que las llamadas van a `/api/v1` sin conocer la IP
  - Solo en desarrollo con `npm run dev` (puerto 5173) se usa `http://localhost:80`
- VITE_DEMO_ADMIN_EMAIL / VITE_DEMO_ADMIN_PASSWORD → opcionales; si tienen
  valor, la vista pública y el login muestran esas credenciales de
  demostración. Quedan visibles para cualquiera: se vacían al terminar la
  revisión (y conviene cambiar entonces la contraseña del administrador)

> Vite incrusta las variables `VITE_*` en el código **al hacer el build**, no
> al arrancar el contenedor. Por eso el Dockerfile del frontend hace
> `npm run build` con `frontend/.env` presente en el contexto de build; el
> contenedor de nginx no usa `env_file`.

## ESTRUCTURA DE CARPETAS
practica3/
├── .claude/
│   ├── backend-agente.md
│   ├── frontend-agente.md
│   └── test-agentte.md
├── .github/
│   └── workflows/
│       └── ci-cd.yml    ← ver specs/ci-specs.md
├── specs/
│   ├── login-specs.md   ← puerta de entrada (login)
│   └── *-specs.md
├── backend/         ← FastAPI (routes, services, repository, models)
│   ├── jobs/         ← tareas programadas (las ejecuta el servicio scheduler)
│   ├── db/
│   │   ├── init/         ← crea APP_DB_USER y la BD de prueba (solo la 1.ª vez)
│   │   ├── migrations/   ← scripts SQL numerados (001_init.sql, 002_...)
│   │   └── seeds/        ← catálogo, usuario inicial, feriados, clima histórico
│   │                       y visitas sintéticas
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
├── frontend/        ← React (JavaScript) para navegador
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── .env
│   └── .env.example
├── .gitignore       ← incluye **/.env
└── docker-compose.yml

## BASE DE DATOS
- Init (`backend/db/init`): se ejecuta solo al crear el volumen por primera
  vez (`/docker-entrypoint-initdb.d`); crea `APP_DB_USER` con permisos mínimos
  y la BD de prueba.
- Migraciones (`backend/db/migrations`): scripts SQL numerados. El script
  `backend/db/migrate.py` (se ejecuta con `python -m db.migrate`) las aplica en orden y registra las ya aplicadas en la tabla
  `schema_migrations`, para que en cada despliegue solo se ejecuten las
  nuevas (el init de Docker no vuelve a correr si el volumen ya existe).
  No se usa ORM (la conexión es con asyncpg).
- Seeds (`backend/db/seeds`), ejecutados con `python -m db.seed`,
  idempotentes (`ON CONFLICT DO NOTHING`): correrlos dos veces no duplica
  datos. El clima histórico solo se descarga si la tabla `clima` no tiene
  datos de 2023–2025 (no se vuelve a descargar en cada deploy). Cargan:
  - Catálogo de `locations`: solo regiones; inicialmente una sola fila,
    `name = "Tingo María"`, `type = "region"`,
    `weatherapi_query = "{PREDICCION_LAT},{PREDICCION_LON}"`.
  - Usuario inicial (administrador): `SEED_USER_EMAIL` / `SEED_USER_PASSWORD`,
    guardando solo el hash bcrypt.
  - Feriados nacionales de Perú de 2023 a 2026 (calendario oficial).
  - Clima histórico 2023–2025 de Tingo María desde Open-Meteo Archive.
  - Visitas sintéticas 2023–2025 (`es_sintetico = true`) con las reglas de
    specs/prediccion-specs.md, usando una semilla aleatoria fija para que
    siempre se generen los mismos datos.
  - Después de los seeds, si todavía no existe ningún `.pkl` en `MODELOS_DIR`,
    se entrena la primera versión del modelo (si ya existe, no se reentrena).
- Persistencia: volumen con nombre (`pgdata`). Nunca se ejecuta
  `docker compose down -v` en producción (borraría la BD).
- Healthcheck: `pg_isready`; el backend arranca solo cuando la BD está sana
  (`depends_on: condition: service_healthy`).
- Usuario de la app: el backend se conecta con `APP_DB_USER`, nunca con el
  superusuario.
- Las marcas de tiempo se guardan como `timestamptz`; las fechas de calendario
  (clima, visitas, feriados, fecha_objetivo) como `date`.

## PUERTOS
- Backend corre en: puerto 80 (uvicorn `--host 0.0.0.0 --port 80`)
- Frontend (dev) corre en: puerto 5173
- Frontend consume: VITE_BACKEND_URL del .env

## CONTAINERIZACIÓN
- Usar Docker
- Crear docker-compose.yml con:
  - Servicio backend (FastAPI, puerto 80 dentro de la red de Docker; no se
    publica al host). Lee `backend/.env` con `env_file`.
  - Servicio base de datos `db` (PostgreSQL 16, puerto 5432 solo dentro de la
    red de Docker; no se publica al host). Lee `backend/.env` con `env_file`.
  - Servicio `scheduler` (misma imagen del backend, sin puertos): ejecuta
    las tareas de `backend/jobs` con APScheduler en hora de Lima (descarga
    diaria del pronóstico a las 06:00 y reentrenamiento semanal los lunes
    a las 03:00). Lee
    `backend/.env` con `env_file`.
  - Servicio frontend (build de React servido por nginx, puerto 80): es el
    único puerto publicado al host.
- Volúmenes con nombre: `pgdata` (BD) y `modelos` (archivos `.pkl`,
  montado en backend y scheduler en `MODELOS_DIR`).
- `frontend/nginx.conf`:
  - `location /api/` → `proxy_pass` al servicio backend
  - `location /` → sirve el build y, si la ruta no existe, devuelve
    `index.html` (`try_files $uri /index.html`) para que recargar una ruta
    del frontend no dé 404
- Ningún valor de variable se escribe en el compose ni en el código

## AWS (producción)
- Una instancia EC2 con Docker y el plugin `docker compose` instalados.
- El repositorio clonado en la instancia, en la ruta indicada por el secreto
  `DEPLOY_PATH` (ver specs/ci-specs.md).
- `backend/.env` y `frontend/.env` de producción se crean a mano **una sola
  vez** en la instancia y viven solo ahí.
- Security Group:
  - Puerto 80 abierto al público.
  - Puerto 22 (SSH) abierto para que GitHub Actions pueda desplegar.
  - El 5432 nunca se abre.
