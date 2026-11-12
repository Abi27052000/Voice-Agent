"""Win-back campaign: which dormant leads to call, and with what variables.

Variable names are snake_case so the same values work as Vapi Campaign CSV
columns (scripts/export_campaign.py) and as browser web-call variables.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.reactivation import OFFER
from app.db.models import Lead
from app.services.phone import last4_spoken, spoken_phone

SOURCE = "old_list"
# Statuses we never dial again.
NOT_CALLABLE = {"do_not_call", "wrong_number", "booked"}
LAST_SERVICE_PREFIX = "Last service: "


def last_service(lead: Lead) -> str:
    issue = lead.issue or ""
    return issue.removeprefix(LAST_SERVICE_PREFIX) if issue.startswith(LAST_SERVICE_PREFIX) else issue


def months_since(lead: Lead) -> int:
    created = lead.created_at
    if created.tzinfo is None:  # SQLite returns naive UTC datetimes
        created = created.replace(tzinfo=timezone.utc)
    return max(0, round((datetime.now(timezone.utc) - created).days / 30))


def is_callable(lead: Lead) -> bool:
    return lead.status not in NOT_CALLABLE


def win_back_leads(session: Session) -> list[Lead]:
    return list(session.scalars(select(Lead).where(Lead.source == SOURCE).order_by(Lead.created_at)))


def call_variables(lead: Lead) -> dict[str, str]:
    values = {
        "lead_id": str(lead.id),
        "full_name": lead.name,
        "first_name": lead.name.split()[0],
        "phone": spoken_phone(lead.phone),
        "phone_last4": last4_spoken(lead.phone),
        "last_service": last_service(lead),
        "months_since": str(months_since(lead)),
        **OFFER,
    }
    if lead.address:
        values["address"] = lead.address
    return values
