# CI/CD con GitHub Actions

> Este spec asume ya leídos `infraestructure-specs.md` (Docker, AWS,
> variables) y `test-specs.md` (qué se prueba y con qué herramientas).

## OBJETIVO
Cada cambio que llega a `main` se prueba automáticamente y, si todo pasa,
se despliega en la instancia EC2 de AWS. Nada llega a producción sin haber
pasado los tests.

## ARCHIVOS
- `.github/workflows/ci-cd.yml` → orquestador: es el único que se dispara con
  push / pull_request; llama a los dos reutilizables, construye las imágenes
  y despliega
- `.github/workflows/backend-ci.yml` → reutilizable (`workflow_call`): job backend-tests
- `.github/workflows/frontend-ci.yml` → reutilizable (`workflow_call`): job frontend-tests
- Los secretos llegan a los reutilizables con `secrets: inherit`

## CUÁNDO CORRE
- `pull_request` hacia `main` → solo los jobs de prueba y build (no despliega)
- `push` a `main` → prueba, build y, si todo pasa, despliega

## JOBS (en este orden)

### 1. backend-tests
- Runner: `ubuntu-latest`
- Python 3.13, dependencias desde `backend/requirements.txt` y
  `backend/requirements-dev.txt` (pytest, pytest-asyncio, pytest-cov), con caché de pip
- Servicio: contenedor `postgres:16` como BD de prueba (`clima_test`), con healthcheck
- La BD de prueba es desechable y solo existe dentro del runner: arranca con
  `POSTGRES_HOST_AUTH_METHOD=trust`, sin contraseña
- Variables del job: `TEST_DATABASE_URL` (`postgresql://postgres@localhost:5432/clima_test`)
  y `TEST_JWT_SECRET` (si el secreto no existe, los tests usan su valor de prueba)
- Aplica las migraciones sobre la BD de prueba antes de los tests
  (`python -m db.migrate` desde `backend/`, con `DATABASE_URL` apuntando a
  la BD de prueba del runner)
- Ejecuta `pytest --cov=services --cov-fail-under=80`: **falla si la cobertura
  de `/services` baja del 80%** (ver specs/test-specs.md)
- WeatherAPI y Open-Meteo nunca se llaman: están simulados en los tests

### 2. frontend-tests
- Runner: `ubuntu-latest`
- Node 22, `npm ci` (con caché de npm)
- Ejecuta Vitest
- Ejecuta `npm run build` para comprobar que el build no se rompe

### 3. docker-build
- Depende de: backend-tests y frontend-tests
- Como en el runner no existen los `.env`, antes del build copia
  `backend/.env.example` → `backend/.env` y `frontend/.env.example` →
  `frontend/.env` (sin valores; solo para que el build encuentre los archivos)
- Ejecuta `docker compose build` para comprobar que las imágenes se construyen

### 4. deploy
- Depende de: docker-build
- Solo corre en `push` a `main` (nunca en pull requests)
- Se conecta por SSH (cliente `ssh` del runner, sin acciones de terceros) a la
  instancia EC2 y ejecuta, en `DEPLOY_PATH`:
  1. `git pull` de `main`
  2. `docker compose up -d --build`
  3. `docker compose exec -T backend python -m db.migrate` (solo aplica
     las nuevas, ver infraestructure-specs.md)
  4. `docker compose exec -T backend python -m db.seed` (idempotentes)
- Nunca ejecuta `docker compose down -v`
- Si algún paso falla, el job falla y se ve en rojo en GitHub

## SECRETOS (GitHub → Settings → Secrets and variables → Actions)
> Ningún secreto se escribe en el YAML. Los `.env` de producción ya viven en la
> instancia (ver infraestructure-specs.md); el workflow no los crea ni los lee.

### Para desplegar
- `EC2_HOST` → IP o DNS público de la instancia
- `EC2_USER` → usuario SSH (ej. el de la AMI)
- `EC2_SSH_KEY` → clave privada SSH para entrar a la instancia
- `DEPLOY_PATH` → ruta del repositorio clonado en la instancia
- Si el repositorio es privado, la instancia necesita una *deploy key* de
  solo lectura de GitHub para poder hacer `git pull`

### Para los tests
- `TEST_JWT_SECRET` → secreto JWT solo para tests
- El resto de variables de prueba (TTL, algoritmo, URLs de proveedores
  simulados, etc.) no son secretas y se definen en el `env:` del job con
  valores de prueba.

## REGLAS
- Un job que falla detiene los siguientes: no se despliega con tests en rojo.
- No se desactivan ni se saltan tests para que el pipeline pase.
- Sin lint por ahora (ni ruff ni eslint).
