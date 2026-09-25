from fastapi import APIRouter, Depends, Query

from models.schemas import ConsultationResponse, LocationResponse, WeatherResponse
from routes.deps import current_user
from services import catalog_service, weather_service

router = APIRouter(tags=["clima"])


@router.get("/locations", response_model=list[LocationResponse])
async def list_locations(_: dict = Depends(current_user)):
    return await catalog_service.list_locations()


@router.get("/weather", response_model=WeatherResponse)
async def get_weather(location: str | None = Query(default=None), user: dict = Depends(current_user)):
    return await weather_service.get_weather(location, user["id"])


@router.get("/consultations/recent", response_model=list[ConsultationResponse])
async def recent_consultations(user: dict = Depends(current_user)):
    return await catalog_service.list_recent_consultations(user["id"])
