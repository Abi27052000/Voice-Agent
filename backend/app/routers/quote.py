from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.quote_controller import create_quote_request
from app.core.security import require_direct_request
from app.db.session import get_session
from app.schemas.quote import SERVICES, QuoteRequestIn, QuoteRequestOut

# Local-only like the CRM: the demo site runs on this machine, and only Vapi's
# webhook needs to be reachable through the tunnel.
router = APIRouter(prefix="/quote-requests", tags=["quote"],
                   dependencies=[Depends(require_direct_request)])


@router.get("/services")
def services() -> list[str]:
    return list(SERVICES)


@router.post("", response_model=QuoteRequestOut, status_code=status.HTTP_201_CREATED)
def create(
    body: QuoteRequestIn, session: Annotated[Session, Depends(get_session)]
) -> QuoteRequestOut:
    return create_quote_request(session, body)
