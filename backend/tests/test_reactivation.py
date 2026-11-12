from datetime import datetime, timedelta, timezone

import pytest

from app.agents import reactivation, tools
from app.db.models import Lead
from app.db.session import SessionLocal
from tests.test_agents import IDS
from tests.test_call_log import report
from tests.test_webhook import first_open_slot_id, post


def add_lead(name, phone, status="dormant", source="old_list", months=12):
    with SessionLocal() as s:
        lead = Lead(name=name, phone=phone, status=status, source=source,
                    address="1 Test St, Ridgeway", issue="Last service: furnace repair",
                    created_at=datetime.now(timezone.utc) - timedelta(days=30 * months))
        s.add(lead)
        s.commit()
        return lead.id


def lead_status(lead_id):
    with SessionLocal() as s:
        return s.get(Lead, lead_id).status


def win_back_tool_call(name, args, lead_id, call_id="c-wb"):
    variables = {"lead_id": str(lead_id)} if lead_id is not None else {}
    return {"message": {
        "type": "tool-calls",
        "call": {"id": call_id, "assistantOverrides": {"variableValues": variables}},
        "toolCallList": [{"id": "t1", "type": "function", "function": {"name": name, "arguments": args}}],
    }}


@pytest.fixture()
def wb(client, monkeypatch):
    monkeypatch.setattr("app.controllers.reactivation_controller.get_id", lambda kind, key: "asst-wb")
    monkeypatch.setattr("app.controllers.vapi_webhook_controller.refresh_outcome", lambda _id: None)
    return client


def test_overview_counts_and_callability(wb):
    add_lead("Grace Whitfield", "5550120")
    add_lead("Victor Lang", "5550131", status="do_not_call")
    add_lead("Inbound Person", "5550199", source="inbound_call", status="new")  # not in campaign
    body = wb.get("/api/win-back").json()
    assert body["summary"]["total"] == 2 and body["summary"]["callable"] == 1
    assert body["summary"]["opted_out"] == 1 and body["offer"] == reactivation.OFFER
    assert body["summary"]["contacted"] == 0  # regression: an imported opt-out was never called
    grace = next(lead for lead in body["leads"] if lead["name"] == "Grace Whitfield")
    assert grace["last_service"] == "furnace repair" and grace["months_since"] == 12


def test_start_call_returns_campaign_style_variables(wb):
    lead_id = add_lead("Grace Whitfield", "5550120")
    res = wb.post(f"/api/win-back/leads/{lead_id}/call").json()
    v = res["variable_values"]
    assert res["assistant_id"] == "asst-wb"
    assert v["lead_id"] == str(lead_id) and v["first_name"] == "Grace"
    assert v["phone_last4"] == "0 1 2 0" and v["last_service"] == "furnace repair"
    assert v["offer_price"] == reactivation.OFFER["offer_price"]


def test_never_calls_opted_out_or_unknown_leads(wb):
    dnc = add_lead("Victor Lang", "5550131", status="do_not_call")
    inbound = add_lead("Inbound Person", "5550199", source="inbound_call", status="new")
    assert wb.post(f"/api/win-back/leads/{dnc}/call").status_code == 409
    assert wb.post(f"/api/win-back/leads/{inbound}/call").status_code == 404


@pytest.mark.parametrize("outcome, status", [
    ("callback_requested", "callback"), ("not_interested", "not_interested"),
    ("do_not_call", "do_not_call"), ("wrong_number", "wrong_number"),
])
def test_update_lead_status_uses_call_variables(wb, outcome, status):
    lead_id = add_lead("Grace Whitfield", "5550120")
    res = post(wb, win_back_tool_call("update_lead_status", {"outcome": outcome}, lead_id)).json()
    assert "result" in res["results"][0]
    assert lead_status(lead_id) == status


def test_model_cannot_target_another_lead(wb):
    # Trust boundary: a lead_id in the model's arguments is ignored; only the call's variables count.
    mine = add_lead("Grace Whitfield", "5550120")
    other = add_lead("Marcus Bell", "5550121")
    post(wb, win_back_tool_call("update_lead_status", {"outcome": "do_not_call", "lead_id": other}, mine))
    assert lead_status(mine) == "do_not_call" and lead_status(other) == "dormant"


def test_update_lead_status_without_linked_lead_fails_safely(wb):
    res = post(wb, win_back_tool_call("update_lead_status", {"outcome": "not_interested"}, None)).json()
    assert "isn't linked" in res["results"][0]["error"]


def test_booking_reactivates_the_same_lead(wb):
    lead_id = add_lead("Grace Whitfield", "5550120")
    args = {"slot_id": first_open_slot_id(), "full_name": "Grace Whitfield", "phone": "555 012 0",
            "address": "1 Test St, Ridgeway", "issue": "Winter heating tune-up"}
    post(wb, win_back_tool_call("book_appointment", args, lead_id))
    assert lead_status(lead_id) == "booked"
    assert wb.post(f"/api/win-back/leads/{lead_id}/call").status_code == 409  # no re-dial


def test_call_without_outcome_marks_contacted(wb):
    lead_id = add_lead("Grace Whitfield", "5550120")
    body = report("c-wb-2", outcome=None)
    body["message"]["call"]["assistantOverrides"] = {"variableValues": {"lead_id": str(lead_id)}}
    post(wb, body)
    assert lead_status(lead_id) == "contacted"
    assert wb.get("/api/win-back").json()["summary"]["contacted"] == 1


def test_win_back_assistant_wiring():
    ids = {**IDS, "tool": {**IDS["tool"], tools.UPDATE_LEAD_STATUS: "tool-status"}}
    payload = reactivation.build(ids)
    assert payload["model"]["toolIds"] == ["tool-avail", "tool-book", "tool-status"]
    inline = {t["type"]: t for t in payload["model"]["tools"]}
    assert set(inline) == {"endCall", "voicemail"}
    assert "{{first_name" in inline["voicemail"]["messages"][0]["content"]


def test_win_back_api_blocked_through_tunnel(wb):
    assert wb.get("/api/win-back", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 403
