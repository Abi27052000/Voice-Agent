from fastapi import APIRouter

from app.routers import health, vapi

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(vapi.router)
