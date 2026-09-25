from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services import auth_service

_bearer = HTTPBearer(auto_error=False)


async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    """Exige un JWT válido del administrador; si no, 401."""
    return await auth_service.get_current_user(credentials.credentials if credentials else None)
