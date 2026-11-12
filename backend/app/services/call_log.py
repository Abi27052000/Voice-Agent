"""Save Vapi calls (end-of-call reports or GET /call results) into the CRM.

Both sources share the same field names (endedReason, cost, startedAt, endedAt,
analysis, artifact), so one upsert handles webhooks and backfills alike.
"""

import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.agents import call_outcome
from app.db.models import Appointment, Call, Lead
from app.db.session import SessionLocal
from app.services.pricing import estimate_job_value
from app.services.vapi_client import VapiClient, VapiConfigError, VapiError
from app.services.vapi_ids import get_id

log = logging.getLogger(__name__)

# Seconds to wait between checks for a Structured Output that wasn't in the report.
REFRESH_DELAYS = (5, 15, 30, 60)

REPORT_FIELDS = ("endedReason", "cost", "startedAt", "endedAt", "analysis", "artifact")


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_outcome(artifact: dict[str, Any] | None) -> dict[str, Any] | None:
    """Find our Structured Output result by saved ID, falling back to its name."""
    outputs = (artifact or {}).get("structuredOutputs") or {}
    entry = outputs.get(get_id("structured-output", call_outcome.KEY) or "")
    if entry is None:
        entry = next((v for v in outputs.values() if v.get("name") == call_outcome.NAME), None)
    result = (entry or {}).get("result")
    return result if isinstance(result, dict) else None


def _apply_outcome(call: Call, result: dict[str, Any]) -> None:
    # `booked` is NOT taken from the LLM; see _sync_booked().
    call.outcome = result
    call.urgency = result.get("urgency")
    call.job_type = result.get("job_type")
    call.caller_sentiment = result.get("caller_sentiment")
    call.follow_up_needed = result.get("follow_up_needed")
    call.follow_up_reason = result.get("follow_up_reason") or None
    call.outcome_status = "ready"


def _sync_booked(session: Session, call: Call) -> None:
    """A call counts as booked only if an appointment was created during it.

    The CRM is the source of truth. In testing, the LLM extraction marked an
    emergency callback as "booked", which inflated booking rate and revenue.
    """
    call.booked = bool(
        session.scalar(select(exists().where(Appointment.call_id == call.id)))
    )
    call.estimated_value_usd = (
        estimate_job_value(call.job_type) if call.booked and call.outcome_status == "ready" else 0
    )


def _find_lead_id(session: Session, call_id: str, data: dict[str, Any]) -> int | None:
    """The lead a tool touched during this call, else the lead the call was started for."""
    lead_id = session.scalars(
        select(Lead.id).where(Lead.call_id == call_id).order_by(Lead.id.desc())
    ).first()
    if lead_id:
        return lead_id
    # Outbound follow-ups pass the CRM lead ID as a call variable.
    variables = ((data.get("assistantOverrides") or {}).get("variableValues")
                 or (data.get("artifact") or {}).get("variableValues") or {})
    raw = str(variables.get("leadId", ""))
    if raw.isdigit() and session.get(Lead, int(raw)):
        return int(raw)
    return None


def upsert_call(session: Session, data: dict[str, Any]) -> Call:
    """Insert or update a call from a Vapi call object. Commits."""
    call = session.get(Call, data["id"]) or Call(id=data["id"])
    session.add(call)

    artifact = data.get("artifact") or {}
    call.assistant_id = data.get("assistantId") or call.assistant_id
    call.call_type = data.get("type") or call.call_type
    call.ended_reason = data.get("endedReason") or call.ended_reason
    call.started_at = _parse_dt(data.get("startedAt")) or call.started_at
    call.ended_at = _parse_dt(data.get("endedAt")) or call.ended_at
    if call.started_at and call.ended_at:
        call.duration_seconds = round((call.ended_at - call.started_at).total_seconds())
    if data.get("cost") is not None:
        call.cost_usd = float(data["cost"])
    call.summary = (data.get("analysis") or {}).get("summary") or call.summary
    call.transcript = artifact.get("transcript") or call.transcript
    call.recording_url = artifact.get("recordingUrl") or call.recording_url

    if call.lead_id is None:
        call.lead_id = _find_lead_id(session, call.id, data)

    lead = session.get(Lead, call.lead_id) if call.lead_id else None
    # A web-form lead we called back is "contacted" (booking/emergency set their own status).
    # Inbound callback requests stay "new": nobody has called them back yet.
    if lead and lead.source == "web_form" and lead.status == "new" and call.ended_reason:
        lead.status = "contacted"

    result = extract_outcome(artifact)
    if result:
        _apply_outcome(call, result)
    _sync_booked(session, call)

    session.commit()
    return call


def record_end_of_call_report(session: Session, message: dict[str, Any]) -> Call:
    data = {**(message.get("call") or {})}
    data.update({k: message[k] for k in REPORT_FIELDS if k in message})
    return upsert_call(session, data)


def refresh_outcome(call_id: str, delays: tuple[int, ...] = REFRESH_DELAYS) -> None:
    """Background task: poll GET /call until the Structured Output is ready."""
    for delay in delays:
        time.sleep(delay)
        try:
            with VapiClient() as vapi:
                data = vapi.get(f"/call/{call_id}")
        except (VapiConfigError, VapiError) as exc:
            log.warning("Could not refresh call %s: %s", call_id, exc)
            return
        with SessionLocal() as session:
            if upsert_call(session, data).outcome_status == "ready":
                log.info("Call %s outcome ready", call_id)
                return
    log.warning("Call %s outcome still pending after %ss", call_id, sum(delays))
