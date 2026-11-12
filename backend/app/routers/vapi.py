from fastapi import APIRouter

from app.controllers.vapi_controller import get_public_config
from app.schemas.vapi import VapiPublicConfig

router = APIRouter(prefix="/vapi", tags=["vapi"])


@router.get("/config", response_model=VapiPublicConfig)
def public_config() -> VapiPublicConfig:
    return get_public_config()
