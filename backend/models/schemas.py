"""Esquemas de entrada y salida de la API (Pydantic)."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# --- Login ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int


class UserResponse(BaseModel):
    id: int
    email: str


# --- Consulta del clima actual ---
class LocationResponse(BaseModel):
    id: int
    name: str
    type: Literal["country", "region"]


class WeatherResponse(BaseModel):
    location: str
    temperature: str
    condition: str
    humidity: str
    source: Literal["weatherapi", "open-meteo"]


class ConsultationResponse(BaseModel):
    location: str
    created_at: datetime


# --- Predicción de visitantes ---
class PrediccionResponse(BaseModel):
    fecha: date
    visitantes_predichos: int
    nivel_afluencia: Literal["Baja", "Media", "Alta"]
    lluvia_mm: float | None
    temp_max: float | None
    version_modelo: int
    entrenado_con_sinteticos: bool
    dato_incompleto: bool


class VisitaRequest(BaseModel):
    fecha: date
    cantidad_visitantes: int = Field(ge=0)


class VisitaResponse(BaseModel):
    fecha: date
    cantidad_visitantes: int
    es_sintetico: bool


class VisitaConPrediccionResponse(VisitaResponse):
    visitantes_predichos: int | None


class FeriadoRequest(BaseModel):
    fecha: date
    nombre: str = Field(min_length=1)


class FeriadoResponse(BaseModel):
    fecha: date
    nombre: str


class MetricasResponse(BaseModel):
    version: int
    mae: float
    r2: float
    entrenado_con_sinteticos: bool
    registros: int
    entrenado_en: datetime
