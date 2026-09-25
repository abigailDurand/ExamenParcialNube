# Diseño de Interfaz

## VISTA DE LOGIN (puerta de entrada — ver specs/login-specs.md)
- Tarjeta centrada con:
  - Campo "Correo"
  - Campo "Contraseña" (texto oculto)
  - Botón "Iniciar sesión"
- Validación en el cliente: ambos campos obligatorios y correo con formato válido
- Botón deshabilitado mientras la petición está en curso
- Error: mensaje bajo el formulario ("Correo o contraseña incorrectos")
- Login correcto: se guarda el token y se redirige al panel del administrador
- Diseño redondeado y colores pasteles, igual que el resto

## VISTA PÚBLICA DE PREDICCIONES (página de inicio, sin login)
- Título "Visitantes a Las Pavas"
- Una tarjeta por día del horizonte (hasta 3) con: fecha, visitantes
  predichos, nivel de afluencia (Baja / Media / Alta), lluvia (mm) y
  temperatura máxima
- Color pastel por nivel de afluencia (Baja, Media, Alta)
- Si la predicción tiene `dato_incompleto`, la tarjeta muestra la nota
  "Pronóstico de lluvia no disponible"
- Si la API responde 503 (modelo no entrenado): mensaje
  "Predicción no disponible por el momento"
- Enlace discreto "Ingresar como administrador" que lleva al login
- Debajo, el recuadro "Acceso de demostración (administrador)" con el correo y
  la contraseña de `VITE_DEMO_ADMIN_EMAIL` / `VITE_DEMO_ADMIN_PASSWORD`
  (para la revisión del profesor). Si esas variables están vacías, no se
  muestra nada. El mismo recuadro aparece debajo del formulario de login.
- Funciona en celular (RNF-06): las tarjetas se apilan en una columna

## PANEL DEL ADMINISTRADOR (solo con sesión activa)
- Menú con las secciones:
  1. Consulta Meteorológica (layout descrito abajo)
  2. Registrar visitas: fecha + cantidad de visitantes → POST /api/v1/visitas
  3. Feriados: lista, agregar y quitar feriados (RF-09)
  4. Modelo: métricas (MAE, R², versión, si fue entrenado con datos
     sintéticos) y botón "Reentrenar"
  5. Gráfico de visitas reales vs. predichas (RF-08)
- Botón "Cerrar sesión": borra el token y vuelve a la vista pública
- Funciona en celular (RNF-06)

## LAYOUT PRINCIPAL (sección Consulta Meteorológica)
- Vista "Consulta Meteorológica", visible solo con sesión activa
- Bloque de consulta arriba:
  1. Menú desplegable de países y regiones
  2. Botón "Consultar"
- Debajo, la tarjeta de resultado con los datos del clima
- Sidebar derecho opcional: "Consultas recientes" (historial del usuario)

## SECCIÓN CONSULTA
- Menú desplegable (select) etiquetado "País o región"
  - Placeholder: "Selecciona un país o región..."
  - Se llena con GET /api/v1/locations al abrir la vista
- Botón "Consultar"
  - Deshabilitado mientras no haya una ubicación seleccionada
  - Deshabilitado mientras hay una consulta en curso

## SECCIÓN RESULTADO
- Tarjeta con border redondeado que muestra:
  - Ubicación (título)
  - Temperatura (ej. "24°C")
  - Estado / condición (ej. "Despejado")
  - Humedad (ej. "60%")
- Colores pasteles según el estado del clima (soleado, nublado, lluvia)

## SECCIÓN CONSULTAS RECIENTES (sidebar, opcional)
- Lista de tarjetas con la ubicación y la fecha de la última consulta
- Al hacer clic en una tarjeta se vuelve a consultar esa ubicación
- Diseño redondeado y colores pasteles

## ESTILO GENERAL
- Diseño redondeado en todos los componentes
- Colores pasteles
- Sin modo oscuro por ahora
- Imagenes referente al contexto.

## ESTADOS DE LA UI
- Cargando: spinner en la tarjeta de resultado mientras espera la respuesta
- Éxito: tarjeta con Temperatura, Estado y Humedad
- Error de datos: mensaje claro "No se pudo obtener el clima de esta ubicación"
- Sin sesión (401): redirección automática a la pantalla de inicio de sesión
