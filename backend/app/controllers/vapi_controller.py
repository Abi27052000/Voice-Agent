from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.vapi import VapiPublicConfig
from app.services.vapi_ids import load_ids


def get_public_config() -> VapiPublicConfig:
    settings = get_settings()
    if not settings.vapi_public_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "VAPI_PUBLIC_KEY is not set on the server."
        )
    assistants = load_ids().get("assistant", {})
    if not assistants:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "No assistants synced yet. Run: uv run python -m scripts.sync_vapi",
        )
    return VapiPublicConfig(public_key=settings.vapi_public_key, assistants=assistants)
