import pytest
from sqlalchemy import func, select

from app.agents import call_outcome
from app.db.models import Call
from app.db.session import SessionLocal
from tests.conftest import AUTH
from tests.test_webhook import CALLER, first_open_slot_id, post, tool_calls

OUTCOME = {
    "booked": True,
    "urgency": "routine",
    "job_type": "water_heater",
    "caller_sentiment": "positive",
    "follow_up_needed": False,
    "follow_up_reason": "",
}


def report(call_id="call-1", outcome=OUTCOME):
    artifact = {"transcript": "AI: Thanks for calling...\nUser: My water heater...",
                "recordingUrl": "https://storage.example/rec.wav"}
    if outcome is not None:
        artifact["structuredOutputs"] = {"so-123": {"name": call_outcome.NAME, "result": outcome}}
    return {
        "message": {
            "type": "end-of-call-report",
            "endedReason": "customer-ended-call",
            "cost": 0.1234,
            "startedAt": "2026-11-12T10:00:00.000Z",
            "endedAt": "2026-11-12T10:02:05.000Z",
            "analysis": {"summary": "Caller booked a water heater repair."},
            "artifact": artifact,
            "call": {"id": call_id, "type": "webCall", "assistantId": "asst-1"},
        }
    }


@pytest.fixture()
def refreshes(monkeypatch):
    scheduled = []
    monkeypatch.setattr(
        "app.controllers.vapi_webhook_controller.refresh_outcome", scheduled.append
    )
    return scheduled


def get_call(call_id="call-1") -> Call:
    with SessionLocal() as s:
        return s.get(Call, call_id)


def test_report_saves_call_with_outcome_and_links_lead(client, refreshes):
    post(client, tool_calls(("t1", "book_appointment", {**CALLER, "slot_id": first_open_slot_id()})))
    assert post(client, report()).status_code == 200

    call = get_call()
    assert call.ended_reason == "customer-ended-call" and call.cost_usd == pytest.approx(0.1234)
    assert call.duration_seconds == 125
    assert call.summary.startswith("Caller booked")
    assert call.outcome_status == "ready" and call.job_type == "water_heater"
    assert call.estimated_value_usd == 1800
    assert call.lead_id is not None  # linked to the lead booked during this call
    assert refreshes == []


def test_booked_comes_from_crm_not_llm(client, refreshes):
    # Regression: the LLM said booked=True for an emergency callback with no appointment.
    post(client, report(outcome={**OUTCOME, "booked": True, "urgency": "emergency"}))
    call = get_call()
    assert call.booked is False and call.estimated_value_usd == 0
    assert call.outcome["booked"] is True  # raw extraction kept for reference


def test_report_without_outcome_schedules_refresh(client, refreshes):
    post(client, report(outcome=None))
    assert get_call().outcome_status == "pending"
    assert refreshes == ["call-1"]


def test_unbooked_call_has_no_estimated_value(client, refreshes):
    post(client, report(outcome={**OUTCOME, "booked": False, "follow_up_needed": True,
                                 "follow_up_reason": "Call back with a quote."}))
    call = get_call()
    assert call.estimated_value_usd == 0 and call.follow_up_needed is True


def test_duplicate_report_updates_single_row(client, refreshes):
    post(client, report(outcome=None))
    post(client, report())
    with SessionLocal() as s:
        assert s.scalar(select(func.count(Call.id))) == 1
    assert get_call().outcome_status == "ready"


def test_report_requires_auth(client):
    assert client.post("/api/vapi/webhook", json=report()).status_code == 401
    assert client.post("/api/vapi/webhook", json=report(), headers=AUTH).status_code == 200
