from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.quote_controller import create_quote_request
from app.core.security import require_dashboard_access
from app.db.session import get_session
from app.schemas.quote import SERVICES, QuoteRequestIn, QuoteRequestOut

# Same access rule as the CRM: open in the hosted public demo, local-only in development.
router = APIRouter(prefix="/quote-requests", tags=["quote"],
                   dependencies=[Depends(require_dashboard_access)])


@router.get("/services")
def services() -> list[str]:
    return list(SERVICES)


@router.post("", response_model=QuoteRequestOut, status_code=status.HTTP_201_CREATED)
def create(
    body: QuoteRequestIn, session: Annotated[Session, Depends(get_session)]
) -> QuoteRequestOut:
    return create_quote_request(session, body)
