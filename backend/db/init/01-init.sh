#!/bin/bash
# Se ejecuta solo la primera vez que se crea el volumen de PostgreSQL
# (/docker-entrypoint-initdb.d). Crea el usuario de la app y la BD de prueba.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE "$APP_DB_USER" LOGIN PASSWORD '$APP_DB_PASSWORD';
    GRANT CONNECT ON DATABASE "$POSTGRES_DB" TO "$APP_DB_USER";
    GRANT USAGE ON SCHEMA public TO "$APP_DB_USER";
    CREATE DATABASE "${POSTGRES_DB}_test" OWNER "$APP_DB_USER";
EOSQL
