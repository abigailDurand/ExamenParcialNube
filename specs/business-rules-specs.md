# Reglas de negocio

## QUÉ HACE
- Autentica al usuario con correo y contraseña y le entrega un token JWT
  (puerta de entrada del sistema, ver specs/login-specs.md)
- Valida que el usuario tenga una sesión activa (JWT válido) antes de cualquier
  acción, excepto la consulta pública de predicciones
- Entrega el catálogo de ubicaciones disponibles para el menú desplegable
  (catálogo inicial: solo la región Tingo María)
- Recibe una ubicación del catálogo seleccionada por el administrador
- Si hay una respuesta en caché de esa ubicación y no ha expirado (TTL) →
  la devuelve desde BD (sin llamar a ningún proveedor externo)
- Si no hay caché o expiró → consulta WeatherAPI; si WeatherAPI falla,
  reintenta con Open-Meteo (ver specs/condicional-api-specs.md); formatea
  los datos del proveedor que haya respondido, guarda la respuesta en
  caché y la devuelve
- Devuelve siempre: Temperatura, Estado (condición) y Humedad
- Registra cada consulta en el historial del usuario (fecha y ubicación)

### Predicción de visitantes (Las Pavas)
- Obtiene el pronóstico diario del clima de Tingo María para los próximos días
  (mismo flujo WeatherAPI → Open-Meteo; el pronóstico se guarda en la tabla
  `clima`, ver specs/condicional-api-specs.md, sección "PRONÓSTICO DIARIO")
- Por cada día calcula las variables: lluvia (mm), temperatura máx. y mín.,
  día de la semana, fin de semana, feriado y temporada de vacaciones
- Aplica el modelo entrenado (Random Forest) y devuelve por cada día:
  fecha, visitantes estimados y nivel de afluencia
- Guarda cada predicción en BD con la versión del modelo que la generó
- Reentrena el modelo una vez por semana con los datos acumulados
  (ver specs/prediccion-specs.md)

## QUÉ NO HACE
- No implementa el registro de usuarios ni recuperación de contraseña:
  los usuarios se cargan/semillan aparte (el login sí está en alcance)
- No permite escribir ubicaciones libres: solo las del catálogo
- No muestra el pronóstico del clima como pantalla propia: el pronóstico
  solo se usa internamente para la predicción de visitantes
- No predice visitantes de otros atractivos ni ubicaciones: solo Las Pavas
- No predice por hora: solo cantidad total por día
- No muestra mapas (por ahora). El único gráfico es el de visitas reales vs.
  predichas del panel del administrador (RF-08)
- No inventa datos del clima: si WeatherAPI falla, reintenta con Open-Meteo.
  - En la consulta del clima actual: si ambos fallan, devuelve un error claro.
  - En la predicción: si ambos fallan, reintenta el flujo completo 3 veces y
    luego predice con el último pronóstico guardado (RNF-07).
  (ver specs/condicional-api-specs.md)

## REGLAS
- El correo se normaliza a minúsculas antes de buscar el usuario
- La contraseña se guarda solo como hash bcrypt; nunca en texto plano, respuestas ni logs
- El error de login es genérico: no revela si falló el correo o la contraseña
- El nombre de la ubicación se compara contra el catálogo antes de llamar a WeatherAPI
- La temperatura se muestra en grados Celsius con el formato "24°C"
- La humedad se muestra con el formato "60%"
- El estado del clima se muestra en español (mapeo desde el proveedor que
  haya respondido — WeatherAPI u Open-Meteo — al mismo vocabulario;
  ver specs/condicional-api-specs.md)
- El TTL del caché por defecto es 10 minutos (configurable por .env)
- Si el token está vencido o ausente, la acción se bloquea y el frontend redirige a login
- NUNCA devuelvas ni registres en logs la contraseña o el password_hash
- Sin JWT válido → responde 401

### Reglas de predicción
- El horizonte de predicción es de 1 a 3 días (máximo configurable por .env
  con PREDICCION_HORIZONTE_DIAS);
  fuera de ese rango → responde 400
- La cantidad de visitantes es un número entero ≥ 0 (nunca negativo ni decimal)
- El nivel de afluencia se asigna así: Baja (< 30), Media (30–60), Alta (> 60)
- Fin de semana = sábado o domingo
- Feriado = la fecha existe en la tabla de feriados de Perú
- Vacaciones = enero, febrero, marzo y julio
- La lluvia se toma en mm diarios; si el proveedor no la informa, se usa 0
  y se marca la predicción como "dato incompleto"
- Los datos de visitas sintéticos solo se usan para entrenar el modelo y se
  marcan con es_sintetico = true; cuando existan registros reales, estos
  tienen prioridad
- Toda respuesta de predicción indica la versión del modelo y si fue
  entrenado con datos sintéticos
- Si el modelo no está entrenado o no carga → responde 503, sin predicción