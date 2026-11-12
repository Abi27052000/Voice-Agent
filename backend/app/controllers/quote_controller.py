from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents import follow_up
from app.schemas.quote import QuoteRequestIn, QuoteRequestOut
from app.services.crm import upsert_lead
from app.services.phone import last4_spoken, spoken_phone
from app.services.vapi_ids import get_id


def create_quote_request(session: Session, body: QuoteRequestIn) -> QuoteRequestOut:
    assistant_id = get_id("assistant", follow_up.KEY)
    if not assistant_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Follow-up assistant not synced. Run: uv run python -m scripts.sync_vapi",
        )

    issue = f"{body.service}: {body.details}" if body.details else body.service
    lead = upsert_lead(
        session,
        name=body.full_name,
        phone=body.phone,
        address=body.address,
        issue=issue,
        status="new",
        source="web_form",
    )
    session.commit()

    values = {
        "leadId": str(lead.id),
        "fullName": body.full_name,
        "firstName": body.full_name.split()[0],
        "phone": spoken_phone(body.phone),
        # Reading back a full (possibly international) number is slow and sounds
        # like dead air; confirm the last four digits instead.
        "phoneLast4": last4_spoken(body.phone),
        "service": body.service,
        "details": body.details,
    }
    if body.address:
        values["address"] = body.address
    return QuoteRequestOut(lead_id=lead.id, assistant_id=assistant_id, variable_values=values)
