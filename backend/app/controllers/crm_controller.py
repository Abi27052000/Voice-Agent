"""Read-only CRM queries for the dashboard."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Appointment, Call, Lead
from app.schemas.crm import AppointmentOut, CallDetail, CallOut, LeadOut, Stats
from app.services.scheduling import Slot, business_now

MAX_ROWS = 200


def list_leads(session: Session) -> list[LeadOut]:
    leads = session.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(MAX_ROWS))
    return [LeadOut.model_validate(lead, from_attributes=True) for lead in leads]


def list_appointments(session: Session) -> list[AppointmentOut]:
    today = business_now().date()
    appointments = session.scalars(
        select(Appointment)
        .options(selectinload(Appointment.lead))
        .order_by(Appointment.day, Appointment.window)
        .limit(MAX_ROWS)
    )
    return [
        AppointmentOut(
            id=a.id,
            reference=a.reference,
            day=a.day,
            window=a.window,
            window_label=Slot(a.day, a.window).label,
            issue=a.issue,
            status=a.status,
            is_past=a.day < today,
            lead_id=a.lead_id,
            lead_name=a.lead.name,
            lead_phone=a.lead.phone,
            lead_address=a.lead.address,
        )
        for a in appointments
    ]


def _call_fields(call: Call) -> dict:
    return {
        **{f: getattr(call, f) for f in CallOut.model_fields if hasattr(call, f)},
        "lead_name": call.lead.name if call.lead else None,
    }


def list_calls(session: Session) -> list[CallOut]:
    calls = session.scalars(
        select(Call)
        .options(selectinload(Call.lead))
        .order_by(Call.started_at.desc().nulls_last())
        .limit(MAX_ROWS)
    )
    return [CallOut(**_call_fields(c)) for c in calls]


def get_call(session: Session, call_id: str) -> CallDetail:
    call = session.get(Call, call_id)
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Call not found")
    return CallDetail(**_call_fields(call), transcript=call.transcript, outcome=call.outcome)


def _speed_to_lead(session: Session) -> tuple[float | None, int]:
    """Average seconds from web-form submission to the first call for that lead."""
    first_call = (
        select(Call.lead_id, func.min(Call.started_at).label("first_call"))
        .where(Call.lead_id.is_not(None), Call.started_at.is_not(None))
        .group_by(Call.lead_id)
        .subquery()
    )
    rows = session.execute(
        select(Lead.created_at, first_call.c.first_call)
        .join(first_call, first_call.c.lead_id == Lead.id)
        .where(Lead.source == "web_form")
    ).all()
    gaps = [(called - created).total_seconds() for created, called in rows if called >= created]
    return (round(sum(gaps) / len(gaps), 1) if gaps else None), len(gaps)


def get_stats(session: Session) -> Stats:
    def scalar(stmt) -> float:
        return session.scalar(stmt) or 0

    calls_total = int(scalar(select(func.count(Call.id))))
    with_outcome = int(scalar(select(func.count(Call.id)).where(Call.outcome_status == "ready")))
    booked = int(scalar(select(func.count(Call.id)).where(Call.booked.is_(True))))
    total_cost = float(scalar(select(func.sum(Call.cost_usd))))
    costed = int(scalar(select(func.count(Call.id)).where(Call.cost_usd.is_not(None))))
    avg_duration = session.scalar(select(func.avg(Call.duration_seconds)))
    speed_to_lead, web_leads_called = _speed_to_lead(session)

    return Stats(
        calls_total=calls_total,
        calls_with_outcome=with_outcome,
        calls_booked=booked,
        booking_rate=(booked / with_outcome) if with_outcome else None,
        est_booked_revenue_usd=int(scalar(select(func.sum(Call.estimated_value_usd)))),
        total_cost_usd=round(total_cost, 4),
        avg_cost_per_call_usd=round(total_cost / costed, 4) if costed else None,
        avg_duration_seconds=round(avg_duration, 1) if avg_duration is not None else None,
        follow_ups_open=int(scalar(select(func.count(Call.id)).where(Call.follow_up_needed.is_(True)))),
        emergencies=int(scalar(select(func.count(Lead.id)).where(Lead.status == "emergency"))),
        upcoming_appointments=int(scalar(
            select(func.count(Appointment.id)).where(
                Appointment.day >= business_now().date(), Appointment.status == "scheduled"
            )
        )),
        leads_total=int(scalar(select(func.count(Lead.id)))),
        speed_to_lead_seconds=speed_to_lead,
        web_leads_called=web_leads_called,
    )
