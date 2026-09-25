import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from repository.db import close_pool, init_pool
from routes import auth_routes, prediccion_routes, weather_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="Las Pavas — Predicción de visitantes y clima", lifespan=lifespan)

settings = get_settings()
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

for router in (auth_routes.router, weather_routes.router, prediccion_routes.router):
    app.include_router(router, prefix="/api/v1")
