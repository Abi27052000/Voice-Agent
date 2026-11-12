from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers import reactivation_controller
from app.core.security import require_dashboard_access
from app.db.session import get_session
from app.schemas.reactivation import WinBackCallOut, WinBackOverview

router = APIRouter(prefix="/win-back", tags=["win-back"],
                   dependencies=[Depends(require_dashboard_access)])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=WinBackOverview)
def overview(session: SessionDep) -> WinBackOverview:
    return reactivation_controller.get_overview(session)


@router.post("/leads/{lead_id}/call", response_model=WinBackCallOut)
def start_call(lead_id: int, session: SessionDep) -> WinBackCallOut:
    return reactivation_controller.start_call(session, lead_id)
