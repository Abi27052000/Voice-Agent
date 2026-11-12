from collections import Counter

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import reactivation
from app.db.models import Call, Lead
from app.schemas.reactivation import WinBackCallOut, WinBackLead, WinBackOverview, WinBackSummary
from app.services import reactivation as svc
from app.services.vapi_ids import get_id


def get_overview(session: Session) -> WinBackOverview:
    leads = svc.win_back_leads(session)
    counts = Counter(lead.status for lead in leads)
    # "Reached" is evidence-based: a call is linked to the lead. (A lead imported
    # as do-not-call has a non-dormant status but was never called.)
    called_ids = set(session.scalars(
        select(Call.lead_id).where(Call.lead_id.in_([lead.id for lead in leads]))
    ))
    summary = WinBackSummary(
        total=len(leads),
        callable=sum(svc.is_callable(lead) for lead in leads),
        contacted=len(called_ids),
        booked=counts["booked"],
        callbacks=counts["callback"],
        not_interested=counts["not_interested"],
        opted_out=counts["do_not_call"] + counts["wrong_number"],
    )
    rows = [
        WinBackLead(
            id=lead.id,
            name=lead.name,
            phone=lead.phone,
            address=lead.address,
            last_service=svc.last_service(lead),
            months_since=svc.months_since(lead),
            status=lead.status,
            callable=svc.is_callable(lead),
            created_at=lead.created_at,
        )
        for lead in leads
    ]
    return WinBackOverview(summary=summary, leads=rows, offer=reactivation.OFFER)


def start_call(session: Session, lead_id: int) -> WinBackCallOut:
    assistant_id = get_id("assistant", reactivation.KEY)
    if not assistant_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Win-back assistant not synced. Run: uv run python -m scripts.sync_vapi",
        )
    lead = session.get(Lead, lead_id)
    if lead is None or lead.source != svc.SOURCE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Win-back lead not found")
    if not svc.is_callable(lead):
        # Never re-dial opt-outs, wrong numbers, or customers who already booked.
        raise HTTPException(status.HTTP_409_CONFLICT, f"Lead is '{lead.status}' and must not be called")
    return WinBackCallOut(assistant_id=assistant_id, variable_values=svc.call_variables(lead))
