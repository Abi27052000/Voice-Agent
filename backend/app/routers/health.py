from fastapi import APIRouter

from app.controllers.health_controller import get_health
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return get_health()
