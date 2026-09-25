# Especificación de Pruebas

## CRITERIOS DE ACEPTACIÓN (BDD / Gherkin)

### Escenario 0: Login (puerta de entrada — ver specs/login-specs.md)
```
Dado que un usuario registrado ingresa su correo y contraseña correctos
Cuando presiona "Iniciar sesión"
Entonces el sistema responde 200 con un token JWT
  y el frontend lo guarda y lo lleva al panel del administrador

Dado que un usuario ingresa una contraseña incorrecta o un correo no registrado
Cuando presiona "Iniciar sesión"
Entonces el sistema responde 401 con un mensaje genérico
  y no revela si falló el correo o la contraseña

Dado que un campo está vacío o el correo no tiene formato válido
Cuando el usuario intenta enviar el formulario
Entonces el frontend muestra el error y no llama a la API
```

### Escenario 1: Consulta exitosa del clima para una región seleccionada
```
Dado que el usuario está logueado en el sistema
  y se encuentra en la sección Consulta Meteorológica del panel
Cuando selecciona una región del catálogo
  y presiona el botón "Consultar"
Entonces el sistema realiza la búsqueda
  y muestra correctamente Temperatura, Estado y Humedad de la ubicación seleccionada
```

### Escenario 2: Intento de consulta sin sesión activa
```
Dado que un usuario sin autenticar intenta acceder a la funcionalidad
Cuando intenta realizar una consulta
Entonces el sistema bloquea la acción (401)
  y lo redirige a la pantalla de inicio de sesión
```

### Escenario 3: Segunda consulta de la misma ubicación (caché)
```
Dado que un usuario ya consultó el clima de "Tingo María" hace menos del TTL
Cuando vuelve a consultar "Tingo María"
Entonces el sistema responde con los datos guardados en BD en menos de 100 ms
  y no llama a WeatherAPI
```

### Escenario 4: WeatherAPI no disponible pero Open-Meteo responde (fallback)
```
Dado que un usuario logueado selecciona una ubicación válida
  y WeatherAPI no responde
Cuando presiona "Consultar"
Entonces el sistema reintenta automáticamente con Open-Meteo
  y muestra correctamente Temperatura, Estado y Humedad de la ubicación
  y la respuesta se guarda en caché igual que si hubiera respondido WeatherAPI
```

### Escenario 5: Ambos proveedores fallan
```
Dado que un usuario logueado selecciona una ubicación válida
  y WeatherAPI no responde
  y Open-Meteo tampoco responde
Cuando presiona "Consultar"
Entonces el sistema muestra un mensaje de error claro
  y no guarda datos en caché

Dado que un usuario logueado selecciona una ubicación válida
  y ni WeatherAPI ni Open-Meteo encuentran esa ubicación
Cuando presiona "Consultar"
Entonces el sistema responde 404 con un mensaje de error claro
  y no guarda datos en caché
```

### Escenario 6: Predicción pública de visitantes
```
Dado que el modelo está entrenado y hay pronóstico guardado
Cuando un turista sin sesión consulta /api/v1/predicciones?dias=3
Entonces recibe 3 predicciones con fecha, visitantes, nivel de afluencia,
  version_modelo, entrenado_con_sinteticos y dato_incompleto

Dado que alguien pide /api/v1/predicciones?dias=0 o un valor mayor que
  PREDICCION_HORIZONTE_DIAS
Entonces el sistema responde 400

Dado que el modelo no está entrenado
Cuando se consulta una predicción
Entonces el sistema responde 503
```

### Escenario 7: Pronóstico con fallos del proveedor
```
Dado que WeatherAPI falla en la descarga diaria
Entonces el pronóstico se obtiene de Open-Meteo

Dado que WeatherAPI y Open-Meteo fallan en los 3 reintentos
Entonces la predicción se genera con el último pronóstico guardado
```

### Escenario 8: Acciones del administrador
```
Dado que un usuario sin sesión intenta registrar visitas, gestionar feriados,
  reentrenar o ver métricas
Entonces el sistema responde 401
```

## BACKEND

### Pruebas de servicios (/services) — unitarias
- Login: con correo y contraseña correctos devuelve un JWT válido y con expiración
- Login: contraseña incorrecta o usuario inexistente levanta 401 (mensaje genérico)
- Login: el correo se normaliza a minúsculas antes de buscar el usuario
- Login: la respuesta y los logs nunca incluyen la contraseña ni el hash
- El JWT emitido se valida correctamente (firma y expiración)
- Rechaza la consulta si el JWT es inválido o expiró (levanta 401)
- Rechaza la ubicación si no pertenece al catálogo (levanta 400)
- Ubicación en caché y dentro del TTL → devuelve BD, no llama a ningún proveedor
- Ubicación sin caché o expirada → llama a WeatherAPI, formatea y guarda en caché
  con `source: "weatherapi"`
- Si WeatherAPI falla (red, error del proveedor o ubicación no encontrada) →
  reintenta con Open-Meteo; si responde, formatea y guarda en caché con
  `source: "open-meteo"`
- Si WeatherAPI y Open-Meteo fallan porque ninguno encuentra la ubicación → 404
- Si WeatherAPI y Open-Meteo fallan por cualquier otro motivo → 503, y no se
  guarda nada en caché ni se registra en el historial
- Formatea temperatura "24°C", humedad "60%" y traduce el estado a español
  (desde el proveedor que haya respondido)
- Registra la consulta en el historial del usuario

### Pruebas de la predicción (/services) — unitarias
- Nivel de afluencia: 29 → Baja, 30 → Media, 60 → Media, 61 → Alta
- Variables: fin_semana (sáb/dom), feriado (según tabla feriados),
  vacaciones (ene–mar y julio), dia_semana (0 = lunes), mes
- Visitantes predichos siempre enteros ≥ 0
- Lluvia ausente → se usa 0 y dato_incompleto = true
- Día con lluvia > 15 mm → predicción menor que un día seco equivalente
- Feriado o fin de semana → predicción mayor que un día laborable con clima similar
- El modelo entrenado con los datos sintéticos cumple MAE < 10 y R² ≥ 0.80
  en el 20% de prueba
- Reentrenar guarda una nueva versión del .pkl con sus métricas
- Modelo no entrenado → 503
- Pronóstico: WeatherAPI falla → usa Open-Meteo; ambos fallan 3 veces →
  usa el último pronóstico guardado
- Los datos sintéticos se marcan con es_sintetico = true; si existe un
  registro real de la misma fecha, tiene prioridad

### Pruebas de repository (/repository) — integración con PostgreSQL
- get_user_by_email devuelve el usuario (con su hash) o None
- list_locations devuelve el catálogo de ubicaciones (inicialmente solo Tingo María)
- get_cached_weather devuelve None si no existe o si expiró el TTL
- upsert_cached_weather inserta y luego get_cached_weather lo recupera
- add_consultation registra la consulta y list_recent la devuelve
- Usa el pool de conexiones (no abre una conexión por petición)

### Pruebas de endpoints (/routes) — integración
- POST /api/v1/auth/login con credenciales válidas → 200 y body con access_token
- POST /api/v1/auth/login con credenciales inválidas → 401
- POST /api/v1/auth/login sin email o sin password → 422
- GET /api/v1/auth/me con token válido → 200; sin token o token vencido → 401
- GET /api/v1/locations sin Authorization → 401
- GET /api/v1/weather sin Authorization → 401
- GET /api/v1/weather sin query param `location` → 400
- GET /api/v1/weather?location=Tingo María con token válido → 200 y body con
  location, temperature, condition, humidity, source
- Si WeatherAPI falla y Open-Meteo responde → 200 con source: "open-meteo"
- Si ninguno de los dos encuentra la ubicación → 404
- Si ambos fallan por cualquier otro motivo → 503
- Segunda consulta de la misma ubicación responde en < 100 ms
- GET /api/v1/consultations/recent sin Authorization → 401
- GET /api/v1/consultations/recent con token válido → 200 y lista de
  consultas del usuario, más reciente primero
- GET /api/v1/predicciones?dias=3 sin token → 200 (público)
- GET /api/v1/predicciones?dias=0 o mayor al máximo → 400
- GET /api/v1/predicciones/{fecha} sin token → 200 (público)
- POST /api/v1/visitas, GET /api/v1/visitas, GET/POST/DELETE /api/v1/feriados,
  POST /api/v1/modelo/reentrenar y GET /api/v1/modelo/metricas sin token → 401;
  con token → 200
- GET /api/v1/predicciones/{fecha} sin predicción para esa fecha → 404
- POST /api/v1/feriados con fecha existente → 409; DELETE de una fecha
  inexistente → 404
- POST /api/v1/visitas sobre una fecha sintética la reemplaza con
  es_sintetico = false

## FRONTEND

### Pruebas de componentes (/components)
- Vista de login: campos vacíos o correo mal formado → muestra error, no llama a la API
- Vista de login: credenciales inválidas → muestra el mensaje de error del backend
- Vista de login: login correcto → guarda el token y redirige al panel del administrador
- Rutas protegidas: sin token guardado → redirige a la vista de login
- El menú desplegable se llena con los datos de GET /api/v1/locations
- El botón "Consultar" está deshabilitado si no hay ubicación seleccionada
- Estado cargando: se muestra el spinner mientras espera la respuesta
- Estado éxito: la tarjeta muestra Temperatura, Estado y Humedad
- Estado error: se muestra "No se pudo obtener el clima de esta ubicación"
- Respuesta 401: se redirige a la pantalla de inicio de sesión

- Vista pública: muestra las tarjetas de predicción sin sesión, con el color
  del nivel de afluencia; muestra la nota de dato incompleto y el mensaje de 503
- Panel del administrador: solo accesible con token; "Cerrar sesión" borra
  el token y vuelve a la vista pública
- Gráfico de visitas reales vs. predichas se dibuja con los datos de la API

### Pruebas de servicios (/services)
- Las llamadas usan VITE_BACKEND_URL del .env (no URL hardcodeada)
- Se envía el header Authorization: Bearer <token> en cada llamada
- Maneja respuestas de error del backend sin romper la UI

## COBERTURA MÍNIMA
- Servicios backend: 80%
- Repository backend: happy path + expiración de caché + error
- Componentes frontend: los estados cargando, éxito, error y 401

## ENTORNO DE PRUEBAS

### Herramientas
- Backend: pytest + pytest-asyncio (pruebas async) + pytest-cov (cobertura);
  los endpoints se prueban con el cliente de pruebas de FastAPI / httpx
- Frontend: Vitest + React Testing Library

### Ubicación de los tests
- Backend: /backend/tests, separados por capa:
  - /backend/tests/services
  - /backend/tests/repository
  - /backend/tests/routes
- Frontend: /frontend/tests, separados por capa:
  - /frontend/tests/components
  - /frontend/tests/services
- Los tests nunca modifican código de producción, specs ni docker-compose

### Reglas de las pruebas
- Nunca se llama a WeatherAPI ni a Open-Meteo reales: se simulan (mock) para
  forzar éxito, fallo de red, "ubicación no encontrada" y error del proveedor
- Las pruebas del modelo (MAE / R²) usan un archivo fijo de clima de prueba
  en `/backend/tests/fixtures` y las visitas sintéticas generadas con la
  misma semilla fija; nunca descargan el histórico real
- Las pruebas de integración usan una BD PostgreSQL de prueba, distinta de la
  de desarrollo, que se limpia entre tests
- Las variables de entorno de prueba (DATABASE_URL, JWT_SECRET, etc.) son
  valores de prueba propios; nunca se usan keys ni secretos reales
- Cada test es independiente: no depende del orden ni del estado de otro test
- Cada test indica en su nombre o docstring qué punto de esta spec cubre
