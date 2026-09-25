from repository.db import get_pool


async def list_locations() -> list[dict]:
    rows = await get_pool().fetch("SELECT id, name, type FROM locations ORDER BY name")
    return [dict(r) for r in rows]


async def get_location_by_name(name: str) -> dict | None:
    row = await get_pool().fetchrow(
        "SELECT id, name, type, weatherapi_query FROM locations WHERE name = $1", name
    )
    return dict(row) if row else None


async def create_location_if_missing(name: str, type_: str, weatherapi_query: str) -> None:
    await get_pool().execute(
        """
        INSERT INTO locations (name, type, weatherapi_query) VALUES ($1, $2, $3)
        ON CONFLICT (name) DO NOTHING
        """,
        name,
        type_,
        weatherapi_query,
    )
