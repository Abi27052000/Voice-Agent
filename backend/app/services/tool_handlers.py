"""Business logic behind each Vapi function tool.

Each handler returns a short plain-text result written for the voice model to
read, and raises ToolError with a message that tells the model how to recover.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Appointment, Lead
from app.schemas.tools import (
    BookAppointmentArgs,
    CheckAvailabilityArgs,
    CreateLeadArgs,
    UpdateLeadStatusArgs,
)
from app.services import scheduling
from app.services.crm import upsert_lead


class ToolError(Exception):
    """An expected failure; the message is returned to the model."""


@dataclass(frozen=True)
class ToolContext:
    tool_call_id: str
    call_id: str | None
    # The call's variableValues (set when the call was started, not by the model).
    variables: dict[str, Any] = field(default_factory=dict)


def _spoken_reference(appointment: Appointment) -> str:
    return " ".join(appointment.reference)


def _booking_confirmation(appointment: Appointment) -> str:
    slot = scheduling.Slot(appointment.day, appointment.window)
    return (
        f"Booked for {slot.label}. Reference number {_spoken_reference(appointment)}. "
        "The office will call ahead when the technician is on the way."
    )


def check_availability(session: Session, args: CheckAvailabilityArgs, ctx: ToolContext) -> str:
    start = None
    if args.preferred_date:
        try:
            start = date.fromisoformat(args.preferred_date)
        except ValueError as exc:
            raise ToolError("preferred_date must be YYYY-MM-DD. Retry with a valid date.") from exc

    slots = scheduling.open_slots(session, start)
    if not slots:
        return (
            "No open windows in the next two weeks from that date. "
            "Offer to log a callback request instead."
        )
    listed = "; ".join(f"{s.slot_id} = {s.label}" for s in slots)
    return f"Open windows (slot_id = label): {listed}. Offer the caller one or two that fit."


def book_appointment(session: Session, args: BookAppointmentArgs, ctx: ToolContext) -> str:
    existing = session.scalars(
        select(Appointment).where(Appointment.tool_call_id == ctx.tool_call_id)
    ).first()
    if existing:  # duplicate delivery of the same tool call
        return _booking_confirmation(existing)

    try:
        slot = scheduling.Slot.parse(args.slot_id)
    except ValueError as exc:
        raise ToolError(
            "Invalid slot_id. Call check_availability and use a slot_id from its result."
        ) from exc
    if not scheduling.is_offered(slot):
        raise ToolError("That window isn't offered. Call check_availability for current openings.")
    if not scheduling.has_capacity(session, slot):
        raise ToolError(
            "That window just filled up. Call check_availability and offer the next openings."
        )

    lead = upsert_lead(
        session,
        name=args.full_name,
        phone=args.phone,
        address=args.address,
        issue=args.issue,
        status="booked",
        call_id=ctx.call_id,
    )
    appointment = Appointment(
        lead=lead,
        day=slot.day,
        window=slot.window,
        issue=args.issue,
        call_id=ctx.call_id,
        tool_call_id=ctx.tool_call_id,
    )
    session.add(appointment)
    session.commit()
    return _booking_confirmation(appointment)


def create_lead(session: Session, args: CreateLeadArgs, ctx: ToolContext) -> str:
    emergency = args.urgency == "emergency"
    upsert_lead(
        session,
        name=args.full_name,
        phone=args.phone,
        address=args.address,
        issue=args.issue,
        urgency=args.urgency,
        status="emergency" if emergency else "new",
        call_id=ctx.call_id,
    )
    session.commit()
    if emergency:
        return "Emergency logged. The on-call technician has been notified and will call back shortly."
    return "Request logged. The office will follow up during business hours."


LEAD_STATUS_FOR_OUTCOME = {
    "callback_requested": "callback",
    "not_interested": "not_interested",
    "do_not_call": "do_not_call",
    "wrong_number": "wrong_number",
}


def update_lead_status(session: Session, args: UpdateLeadStatusArgs, ctx: ToolContext) -> str:
    # Trust boundary: the lead comes from the call's variables (set by our backend
    # when the call was started), so the model can't touch a different customer.
    raw = str(ctx.variables.get("lead_id", ""))
    lead = session.get(Lead, int(raw)) if raw.isdigit() else None
    if lead is None:
        raise ToolError("This call isn't linked to a customer record. Don't retry; continue the call.")
    lead.status = LEAD_STATUS_FOR_OUTCOME[args.outcome]
    lead.call_id = ctx.call_id or lead.call_id
    session.commit()
    if args.outcome == "do_not_call":
        return "Saved. They are on the do-not-call list. Confirm they won't be called again, then end the call."
    return "Saved."


Handler = Callable[[Session, BaseModel, ToolContext], str]

# Allowlist: function name -> (argument model, handler)
TOOL_HANDLERS: dict[str, tuple[type[BaseModel], Handler]] = {
    "check_availability": (CheckAvailabilityArgs, check_availability),
    "book_appointment": (BookAppointmentArgs, book_appointment),
    "create_lead": (CreateLeadArgs, create_lead),
    "update_lead_status": (UpdateLeadStatusArgs, update_lead_status),
}
