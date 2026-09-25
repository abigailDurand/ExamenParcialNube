# SPEC: Login

> Este spec es la **puerta de entrada del administrador**. Solo el administrador
> tiene cuenta (todos los usuarios de `users` son administradores; no hay roles
> por ahora). Sin sesión solo se puede ver la predicción pública de visitantes
> (ver `specs/prediccion-specs.md`); todo lo demás (consulta del clima, registro
> de visitas, feriados, métricas y reentrenamiento) exige una sesión iniciada aquí.
> El login entrega un **token JWT** que el frontend guarda y envía en el header
> `Authorization: Bearer <token>` en las peticiones a los endpoints protegidos.

## 1. Objetivo → qué construir
Sistema de inicio de sesión mediante correo y contraseña que autentica al usuario
y le entrega un token JWT para acceder al resto de la aplicación.

## 2. Requisitos → qué debe hacer y cómo debe ser
- Ingresar correo y contraseña.
- Validar el formato de los datos.
- Verificar las credenciales contra la BD.
- Mostrar un mensaje de error claro si son incorrectas.
- Si son válidas: devolver un token JWT e iniciar sesión.
- El frontend guarda el token en `sessionStorage` y redirige al panel del administrador.
- Si un endpoint responde 401 (token ausente/vencido), el frontend vuelve al login.

## 3. Reglas → qué condiciones debe respetar
- Ambos campos son obligatorios.
- El correo debe tener formato válido.
- Solo usuarios registrados pueden acceder (los usuarios se cargan/semillan aparte;
  el registro no es parte de este spec por ahora).
- La contraseña nunca se almacena en texto plano: se guarda su hash (bcrypt).
- La contraseña nunca aparece en respuestas de la API ni en logs.
- El mismo mensaje de error para "correo no existe" y "contraseña incorrecta"
  (no revelar cuál de los dos falló).
- El token JWT tiene expiración (configurable por `.env`).

## 4. Flujo → cómo funciona paso a paso
1. Usuario ingresa correo y contraseña en la vista de login.
2. Frontend valida que ambos campos estén llenos y el correo tenga formato válido.
3. Frontend envía `POST /api/v1/auth/login` con `{ email, password }`.
4. Backend busca el usuario por correo (normalizado a minúsculas).
5. Backend compara la contraseña con el hash guardado (bcrypt).
6. Si coinciden → backend genera un JWT (HS256, con expiración) y lo devuelve.
7. Frontend guarda el token en `sessionStorage` y redirige al panel del administrador.
8. Si no coinciden o el usuario no existe → backend responde 401 y el frontend
   muestra el mensaje de error.

## 5. Criterios de aceptación → cómo comprobar que funciona
- ✅ Login correcto devuelve 200 con un token y permite acceder.
- ✅ Contraseña incorrecta responde 401 y rechaza el acceso.
- ✅ Campos vacíos: el frontend muestra error y no llama a la API.
- ✅ Correo con formato inválido: el frontend muestra error y no llama a la API.
- ✅ Usuario inexistente responde 401 con el mismo mensaje genérico.
- ✅ La respuesta y los logs nunca incluyen la contraseña ni el hash.
- ✅ Un token vencido o inválido en otro endpoint responde 401 y redirige al login.

## 6. Restricciones → qué tecnologías/condiciones debe usar
- API REST sobre FastAPI (Python 3.13).
- PostgreSQL para la tabla de usuarios (Repository Pattern, igual que el resto).
- Hash de contraseñas con bcrypt (passlib).
- Token JWT firmado con `JWT_SECRET` / `JWT_ALGORITHM` del `.env`.
- No exponer contraseñas ni hashes en respuestas o logs.
- El código del backend va en `/backend` (routes, services, repository, models);
  el del frontend en `/frontend` (components, services).

## 7. Diseño de API

### POST /api/v1/auth/login
- Body:
  ```json
  { "email": "user@correo.com", "password": "secreto" }
  ```
- Respuesta 200:
  ```json
  { "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600 }
  ```
- Respuesta 401 (credenciales inválidas o usuario inexistente):
  ```json
  { "detail": "Correo o contraseña incorrectos" }
  ```
- Respuesta 422: falta un campo o el correo no tiene formato válido.

### GET /api/v1/auth/me  (opcional, para validar la sesión al cargar la app)
- Headers: `Authorization: Bearer <jwt>`
- Respuesta 200: `{ "id": 1, "email": "user@correo.com" }`
- Respuesta 401: token ausente, inválido o vencido.

## 8. Modelo de datos (tabla `users`)
- `id` (PK)
- `email` (único, en minúsculas: `CHECK email = lower(email)`)
- `password_hash` (bcrypt)
- `created_at` (`timestamptz`)
