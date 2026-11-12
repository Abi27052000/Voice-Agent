from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Lead


def upsert_lead(
    session: Session,
    *,
    name: str,
    phone: str,
    issue: str | None,
    address: str | None = None,
    urgency: str = "routine",
    status: str = "new",
    source: str = "inbound_call",
    call_id: str | None = None,
) -> Lead:
    """Match an existing lead by phone (digits only) or create a new one."""
    lead = session.scalars(
        select(Lead).where(Lead.phone == phone).order_by(Lead.id.desc()).limit(1)
    ).first()
    if lead is None:
        lead = Lead(phone=phone, source=source, name=name)
        session.add(lead)
    elif source == "web_form":
        lead.source = source  # a new web request re-opens the lead as a web lead
    lead.name = name
    lead.issue = issue or lead.issue
    lead.address = address or lead.address
    lead.urgency = urgency
    lead.status = status
    lead.call_id = call_id or lead.call_id
    return lead
