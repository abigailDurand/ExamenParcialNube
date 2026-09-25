from repository.db import get_pool


async def get_cached_weather(location_id: int, ttl_minutes: int) -> dict | None:
    """Devuelve la caché solo si no expiró el TTL (la comparación se hace en SQL)."""
    row = await get_pool().fetchrow(
        """
        SELECT location_id, temp_c, humidity, condition, source, fetched_at
        FROM weather_cache
        WHERE location_id = $1
          AND fetched_at > now() - make_interval(mins => $2)
        """,
        location_id,
        ttl_minutes,
    )
    if row is None:
        return None
    data = dict(row)
    data["temp_c"] = float(data["temp_c"])
    return data


async def upsert_cached_weather(
    location_id: int, temp_c: float, humidity: int, condition: str, source: str
) -> None:
    await get_pool().execute(
        """
        INSERT INTO weather_cache (location_id, temp_c, humidity, condition, source, fetched_at)
        VALUES ($1, $2, $3, $4, $5, now())
        ON CONFLICT (location_id) DO UPDATE
        SET temp_c = EXCLUDED.temp_c,
            humidity = EXCLUDED.humidity,
            condition = EXCLUDED.condition,
            source = EXCLUDED.source,
            fetched_at = EXCLUDED.fetched_at
        """,
        location_id,
        temp_c,
        humidity,
        condition,
        source,
    )
