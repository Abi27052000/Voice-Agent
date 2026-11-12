from fastapi import APIRouter

from app.routers import crm, health, vapi

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(vapi.router)
api_router.include_router(crm.router)
