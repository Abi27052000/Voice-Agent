from datetime import datetime, timedelta, timezone

import pytest

from app.db.models import Call, Lead
from app.db.session import SessionLocal
from tests.test_call_log import OUTCOME, report
from tests.test_webhook import post

FORM = {
    "full_name": "Maria Lopez",
    "phone": "(555) 010-1234",
    "address": "14 Birch Lane, Ridgeway",
    "service": "Water heater",
    "details": "Popping noises when heating",
    "consent": True,
}


@pytest.fixture()
def quote_client(client, monkeypatch):
    monkeypatch.setattr("app.controllers.quote_controller.get_id", lambda kind, key: "asst-follow")
    monkeypatch.setattr("app.controllers.vapi_webhook_controller.refresh_outcome", lambda _id: None)
    return client


def submit(client, **overrides):
    return client.post("/api/quote-requests", json={**FORM, **overrides})


def test_quote_request_creates_web_lead_and_call_variables(quote_client):
    res = submit(quote_client)
    assert res.status_code == 201
    body = res.json()
    assert body["assistant_id"] == "asst-follow"
    values = body["variable_values"]
    assert values["firstName"] == "Maria" and values["phone"] == "555 010 1234"
    assert values["phoneLast4"] == "1 2 3 4"
    assert values["leadId"] == str(body["lead_id"]) and values["service"] == "Water heater"
    with SessionLocal() as s:
        lead = s.get(Lead, body["lead_id"])
        assert lead.source == "web_form" and lead.status == "new" and lead.phone == "5550101234"
        assert lead.issue == "Water heater: Popping noises when heating"


@pytest.mark.parametrize(
    "overrides",
    [{"consent": False}, {"service": "Roof repair"}, {"phone": "12"}, {"full_name": ""}, {"extra": 1}],
)
def test_quote_request_validation(quote_client, overrides):
    assert submit(quote_client, **overrides).status_code == 422


def test_follow_up_call_links_lead_and_marks_contacted(quote_client):
    lead_id = submit(quote_client).json()["lead_id"]
    started = datetime.now(timezone.utc) + timedelta(seconds=3)
    body = report("c-follow", outcome={**OUTCOME, "booked": False})
    body["message"]["startedAt"] = started.isoformat()
    body["message"]["endedAt"] = (started + timedelta(seconds=60)).isoformat()
    body["message"]["call"]["assistantOverrides"] = {"variableValues": {"leadId": str(lead_id)}}
    post(quote_client, body)

    with SessionLocal() as s:
        assert s.get(Call, "c-follow").lead_id == lead_id
        assert s.get(Lead, lead_id).status == "contacted"

    stats = quote_client.get("/api/stats").json()
    assert stats["web_leads_called"] == 1
    assert 2 <= stats["speed_to_lead_seconds"] <= 10


def test_inbound_callback_lead_is_not_marked_contacted(quote_client):
    from tests.test_webhook import CALLER, tool_calls

    post(quote_client, tool_calls(("t1", "create_lead", {**CALLER, "urgency": "routine"}), call_id="c-in"))
    post(quote_client, report("c-in"))
    with SessionLocal() as s:
        assert s.get(Call, "c-in").lead.status == "new"


def test_quote_api_blocked_through_tunnel(quote_client):
    res = quote_client.post("/api/quote-requests", json=FORM, headers={"X-Forwarded-For": "203.0.113.9"})
    assert res.status_code == 403
