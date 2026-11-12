from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header
from sqlalchemy.orm import Session

from app.controllers.vapi_controller import get_public_config
from app.controllers.vapi_webhook_controller import handle_server_message, verify_authorization
from app.db.session import get_session
from app.schemas.vapi import VapiPublicConfig

router = APIRouter(prefix="/vapi", tags=["vapi"])


@router.get("/config", response_model=VapiPublicConfig)
def public_config() -> VapiPublicConfig:
    return get_public_config()


def require_vapi_auth(authorization: Annotated[str | None, Header()] = None) -> None:
    verify_authorization(authorization)


@router.post("/webhook", dependencies=[Depends(require_vapi_auth)])
def vapi_webhook(
    body: Annotated[dict[str, Any], Body()],
    session: Annotated[Session, Depends(get_session)],
    background: BackgroundTasks,
) -> dict[str, Any]:
    return handle_server_message(session, body, background)
