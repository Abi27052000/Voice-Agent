import pytest

from tests.test_call_log import OUTCOME, report
from tests.test_webhook import CALLER, first_open_slot_id, post, tool_calls


@pytest.fixture()
def data(client, monkeypatch):
    """One booked call, one abandoned call needing follow-up, one emergency lead."""
    monkeypatch.setattr("app.controllers.vapi_webhook_controller.refresh_outcome", lambda _id: None)
    post(client, tool_calls(("t1", "book_appointment", {**CALLER, "slot_id": first_open_slot_id()}),
                            call_id="c-booked"))
    post(client, report("c-booked"))
    post(client, report("c-abandoned", outcome={**OUTCOME, "booked": False, "job_type": "ac_repair",
                                                "follow_up_needed": True,
                                                "follow_up_reason": "Call back to book."}))
    post(client, tool_calls(("t2", "create_lead", {**CALLER, "phone": "5550199", "urgency": "emergency",
                                                   "issue": "Burst pipe"}), call_id="c-emergency"))
    return client


def test_stats(data):
    s = data.get("/api/stats").json()
    assert s["calls_total"] == 2 and s["calls_booked"] == 1
    assert s["booking_rate"] == pytest.approx(0.5)
    assert s["est_booked_revenue_usd"] == 1800  # water_heater, booked only
    assert s["total_cost_usd"] == pytest.approx(0.2468)
    assert s["avg_cost_per_call_usd"] == pytest.approx(0.1234)
    assert s["follow_ups_open"] == 1 and s["emergencies"] == 1
    assert s["upcoming_appointments"] == 1 and s["leads_total"] == 2


def test_lists(data):
    calls = data.get("/api/calls").json()
    assert {c["id"] for c in calls} == {"c-booked", "c-abandoned"}
    booked = next(c for c in calls if c["id"] == "c-booked")
    assert booked["lead_name"] == "Jane Doe" and "transcript" not in booked

    appts = data.get("/api/appointments").json()
    assert appts[0]["lead_name"] == "Jane Doe" and appts[0]["reference"] == "1001"
    assert appts[0]["is_past"] is False and "between" in appts[0]["window_label"]

    statuses = {lead["status"] for lead in data.get("/api/leads").json()}
    assert statuses == {"booked", "emergency"}


def test_call_detail_and_404(data):
    detail = data.get("/api/calls/c-booked").json()
    assert detail["transcript"].startswith("AI:") and detail["outcome"]["job_type"] == "water_heater"
    assert data.get("/api/calls/nope").status_code == 404


def test_empty_stats(client):
    s = client.get("/api/stats").json()
    assert s["calls_total"] == 0 and s["booking_rate"] is None and s["avg_cost_per_call_usd"] is None


@pytest.mark.parametrize("path", ["/api/stats", "/api/leads", "/api/calls", "/api/appointments"])
def test_crm_blocked_through_tunnel(client, path):
    assert client.get(path, headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 403
