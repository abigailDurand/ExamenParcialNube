-- Esquema inicial (ver specs/architecture-specs.md y specs/prediccion-specs.md)

CREATE TABLE users (
    id            serial PRIMARY KEY,
    email         text NOT NULL UNIQUE CHECK (email = lower(email)),
    password_hash text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE locations (
    id               serial PRIMARY KEY,
    name             text NOT NULL UNIQUE,
    type             text NOT NULL CHECK (type IN ('country', 'region')),
    weatherapi_query text NOT NULL
);

CREATE TABLE weather_cache (
    location_id integer PRIMARY KEY REFERENCES locations (id),
    temp_c      numeric(5, 2) NOT NULL,
    humidity    integer NOT NULL,
    condition   text NOT NULL,
    source      text NOT NULL CHECK (source IN ('weatherapi', 'open-meteo')),
    fetched_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE consultations (
    id          serial PRIMARY KEY,
    user_id     integer NOT NULL REFERENCES users (id),
    location_id integer NOT NULL REFERENCES locations (id),
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_consultations_user_created ON consultations (user_id, created_at DESC);

-- Predicción de visitantes a Las Pavas
CREATE TABLE clima (
    fecha         date PRIMARY KEY,
    temp_max      numeric(4, 1) NOT NULL,
    temp_min      numeric(4, 1) NOT NULL,
    lluvia_mm     numeric(6, 1),
    humedad       integer,
    es_pronostico boolean NOT NULL
);

CREATE TABLE visitas (
    fecha               date PRIMARY KEY,
    cantidad_visitantes integer NOT NULL CHECK (cantidad_visitantes >= 0),
    es_sintetico        boolean NOT NULL,
    registrado_por      integer REFERENCES users (id)
);

CREATE TABLE feriados (
    fecha  date PRIMARY KEY,
    nombre text NOT NULL
);

CREATE TABLE predicciones (
    id                       serial PRIMARY KEY,
    fecha_objetivo           date NOT NULL,
    visitantes_predichos     integer NOT NULL CHECK (visitantes_predichos >= 0),
    nivel_afluencia          text NOT NULL CHECK (nivel_afluencia IN ('Baja', 'Media', 'Alta')),
    version_modelo           integer NOT NULL,
    entrenado_con_sinteticos boolean NOT NULL,
    dato_incompleto          boolean NOT NULL,
    creado_en                timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_predicciones_fecha ON predicciones (fecha_objetivo, creado_en DESC);
