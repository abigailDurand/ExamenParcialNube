# SISTEMA: Predicción de visitantes a Las Pavas (Tingo María) y consulta meteorológica

> El objetivo principal del sistema es predecir cuántos visitantes tendrá la
> Cueva de Las Pavas cada día según el clima (ver specs/prediccion-specs.md).
> La consulta del clima actual es un módulo de apoyo para el administrador.

# INFORMACIÓN GENERAL:
- Módulo 1: Predicción de visitantes (público + panel del administrador)
  → specs/prediccion-specs.md
- Módulo 2: Consulta Meteorológica (solo administrador)
- Actores: administrador (con login), turista y municipalidad (sin login)
- Catálogo inicial de ubicaciones: solo la región Tingo María
- Objetivo del módulo 2: permitir al administrador visualizar el estado del
  clima actual de una ubicación del catálogo



# DECISIONES TÉCNICAS:
- El login es la puerta de entrada del administrador (ver specs/login-specs.md):
  inicia sesión con correo y contraseña y recibe un token JWT. Sin token solo
  se puede consultar la predicción pública de visitantes.
- El módulo de consulta meteorológica requiere sesión activa: cada petición lleva
  Authorization: Bearer <token_jwt> y el backend lo valida antes de responder
  (si no hay token válido → 401 y el frontend redirige a login)
- El endpoint de clima es GET /api/v1/weather?location={country_or_region_name}
  (la ubicación no es un dato sensible; va como query param)
- El catálogo de ubicaciones (por ahora solo regiones) vive en BD y se expone en
  GET /api/v1/locations para llenar el menú desplegable
- Las respuestas del proveedor climático (WeatherAPI u Open-Meteo) se guardan
  en BD como caché con TTL corto (por defecto 10 minutos) para no llamar al
  proveedor externo en cada petición ni superar su límite de uso
- Si WeatherAPI falla, se reintenta automáticamente con Open-Meteo antes de
  devolver un error (ver specs/condicional-api-specs.md)
- La conexión a BD usa pool de conexiones



# CRITERIOS DE VALIDACIÓN:
- Sin JWT válido: el sistema bloquea la acción (401) y el frontend redirige a login
- La respuesta muestra siempre: Temperatura, Estado y Humedad
- Segunda consulta de la misma ubicación dentro del TTL: responde desde BD (< 100 ms,
  sin llamar a WeatherAPI)
- Si WeatherAPI falla, el sistema reintenta con Open-Meteo automáticamente;
  si ambos fallan o ninguno encuentra la ubicación, el usuario ve un error
  claro (nunca una pantalla en blanco)

FLUJOS PRINCIPALES:
0. Administrador inicia sesión (POST /api/v1/auth/login) → recibe el token JWT →
   el frontend lo guarda y entra al panel del administrador
   (el turista no inicia sesión: ve la predicción pública directamente)
1. Usuario entra a la vista → frontend pide GET /api/v1/locations → llena el menú desplegable
2. Usuario selecciona ubicación y presiona "Consultar" → GET /api/v1/weather →
   backend valida JWT → busca en caché BD → si no hay o expiró → WeatherAPI
   (con fallback a Open-Meteo si falla, ver specs/condicional-api-specs.md) →
   guarda en caché → devuelve Temperatura, Estado y Humedad
3. Usuario sin sesión activa → backend responde 401 → frontend redirige a login

# AGENTES:
- Agente frontend: construye la vista pública de predicciones, la vista de
  login, el panel del administrador (consulta del clima, registro de visitas,
  feriados, métricas y gráfico real vs. predicho) y el guardado del token
- Agente backend: construye la API (login, clima y predicción), el hash de
  contraseñas, la emisión y validación del JWT, la lógica de caché, la
  integración con WeatherAPI y Open-Meteo (fallback), el modelo predictivo y
  las tareas programadas
- Agente de test: verifica todo lo anterior según specs/test-specs.md
