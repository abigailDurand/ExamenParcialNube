"""Login y validación de sesión (ver specs/login-specs.md)."""
from fastapi import HTTPException, status

from repository import users_repository
from services.security import create_access_token, decode_access_token, verify_password

MENSAJE_LOGIN_INVALIDO = "Correo o contraseña incorrectos"
MENSAJE_NO_AUTORIZADO = "No autorizado"


async def login(email: str, password: str) -> dict:
    user = await users_repository.get_user_by_email(email.strip().lower())
    # Mismo mensaje si el correo no existe o si la contraseña no coincide
    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MENSAJE_LOGIN_INVALIDO)
    token, expires_in = create_access_token(user["id"])
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}


async def get_current_user(token: str | None) -> dict:
    user_id = decode_access_token(token) if token else None
    user = await users_repository.get_user_by_id(user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=MENSAJE_NO_AUTORIZADO,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
