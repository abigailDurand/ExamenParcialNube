"""Aplica las migraciones SQL pendientes (python -m db.migrate).

Registra las ya aplicadas en `schema_migrations`, así en cada despliegue solo
corren las nuevas. Se conecta como administrador (POSTGRES_USER) cuando está
disponible y luego da al usuario de la app (APP_DB_USER) solo los permisos
de lectura/escritura sobre las tablas.
"""
import asyncio
import os
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import asyncpg

import config  # noqa: F401  (carga backend/.env)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def admin_dsn() -> str:
    dsn = os.environ["DATABASE_URL"]
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    if not user or not password:
        return dsn
    parts = urlsplit(dsn)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    netloc = f"{quote(user, safe='')}:{quote(password, safe='')}@{host}"
    return urlunsplit(parts._replace(netloc=netloc))


async def migrate(dsn: str | None = None) -> list[str]:
    conn = await asyncpg.connect(dsn or admin_dsn())
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    text PRIMARY KEY,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        applied = {r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations")}
        nuevas = []
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                continue
            async with conn.transaction():
                await conn.execute(path.read_text(encoding="utf-8"))
                await conn.execute("INSERT INTO schema_migrations (version) VALUES ($1)", path.name)
            nuevas.append(path.name)

        app_user = os.getenv("APP_DB_USER")
        current_user = await conn.fetchval("SELECT current_user")
        app_user_existe = app_user and await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", app_user)
        if app_user_existe and app_user != current_user:
            ident = '"' + app_user.replace('"', '""') + '"'
            await conn.execute(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ident}"
            )
            await conn.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ident}")
        return nuevas
    finally:
        await conn.close()


if __name__ == "__main__":
    aplicadas = asyncio.run(migrate())
    print(f"Migraciones aplicadas: {aplicadas or 'ninguna nueva'}")
