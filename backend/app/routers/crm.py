from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers import crm_controller
from app.core.security import require_dashboard_access
from app.db.session import get_session
from app.schemas.crm import AppointmentOut, CallDetail, CallOut, LeadOut, Stats

router = APIRouter(tags=["crm"], dependencies=[Depends(require_dashboard_access)])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/stats", response_model=Stats)
def stats(session: SessionDep) -> Stats:
    return crm_controller.get_stats(session)


@router.get("/leads", response_model=list[LeadOut])
def leads(session: SessionDep) -> list[LeadOut]:
    return crm_controller.list_leads(session)


@router.get("/appointments", response_model=list[AppointmentOut])
def appointments(session: SessionDep) -> list[AppointmentOut]:
    return crm_controller.list_appointments(session)


@router.get("/calls", response_model=list[CallOut])
def calls(session: SessionDep) -> list[CallOut]:
    return crm_controller.list_calls(session)


@router.get("/calls/{call_id}", response_model=CallDetail)
def call_detail(call_id: str, session: SessionDep) -> CallDetail:
    return crm_controller.get_call(session, call_id)
