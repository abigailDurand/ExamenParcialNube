from fastapi import APIRouter, Depends

from models.schemas import LoginRequest, TokenResponse, UserResponse
from routes.deps import current_user
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    return await auth_service.login(body.email, body.password)


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(current_user)):
    return user
