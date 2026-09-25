from repository.db import get_pool


async def add_consultation(user_id: int, location_id: int) -> None:
    await get_pool().execute(
        "INSERT INTO consultations (user_id, location_id) VALUES ($1, $2)", user_id, location_id
    )


async def list_recent(user_id: int, limit: int) -> list[dict]:
    rows = await get_pool().fetch(
        """
        SELECT l.name AS location, c.created_at
        FROM consultations c
        JOIN locations l ON l.id = c.location_id
        WHERE c.user_id = $1
        ORDER BY c.created_at DESC
        LIMIT $2
        """,
        user_id,
        limit,
    )
    return [dict(r) for r in rows]
