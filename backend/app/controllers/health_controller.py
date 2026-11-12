from datetime import datetime, timezone

from app.core.config import get_settings
from app.schemas.health import HealthResponse


def get_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
    )
