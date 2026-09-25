from repository.db import get_pool


async def get_user_by_email(email: str) -> dict | None:
    row = await get_pool().fetchrow(
        "SELECT id, email, password_hash FROM users WHERE email = $1", email
    )
    return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict | None:
    row = await get_pool().fetchrow("SELECT id, email FROM users WHERE id = $1", user_id)
    return dict(row) if row else None


async def create_user_if_missing(email: str, password_hash: str) -> None:
    await get_pool().execute(
        "INSERT INTO users (email, password_hash) VALUES ($1, $2) ON CONFLICT (email) DO NOTHING",
        email,
        password_hash,
    )
