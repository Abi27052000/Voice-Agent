import json

from sqlalchemy import func, select

from app.agents.tools import function_parameters
from app.db.models import Appointment, Lead
from app.db.session import SessionLocal
from app.schemas.tools import CreateLeadArgs
from app.services.scheduling import open_slots
from tests.conftest import AUTH

CALLER = {
    "full_name": "Jane Doe",
    "phone": "(555) 010-9999",
    "address": "12 Pine Street, Ridgeway",
    "issue": "Kitchen sink draining slowly",
}


def tool_calls(*calls, call_id="call-1"):
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": call_id},
            "toolCallList": [
                {"id": tc_id, "type": "function", "function": {"name": name, "arguments": args}}
                for tc_id, name, args in calls
            ],
        }
    }


def post(client, body, headers=AUTH):
    return client.post("/api/vapi/webhook", json=body, headers=headers)


def first_open_slot_id():
    with SessionLocal() as s:
        return open_slots(s, limit=1)[0].slot_id


def count(model):
    with SessionLocal() as s:
        return s.scalar(select(func.count(model.id)))


def test_rejects_missing_and_wrong_token(client):
    body = tool_calls(("t1", "check_availability", {}))
    assert post(client, body, headers={}).status_code == 401
    assert post(client, body, headers={"Authorization": "Bearer nope"}).status_code == 401


def test_check_availability_lists_slots(client):
    res = post(client, tool_calls(("t1", "check_availability", {}))).json()["results"][0]
    assert res["toolCallId"] == "t1" and res["name"] == "check_availability"
    assert "Open windows" in res["result"]


def test_check_availability_bad_date_returns_error(client):
    res = post(client, tool_calls(("t1", "check_availability", {"preferred_date": "Thursday"})))
    assert "YYYY-MM-DD" in res.json()["results"][0]["error"]


def test_book_appointment_creates_lead_and_appointment(client):
    args = {**CALLER, "slot_id": first_open_slot_id()}
    res = post(client, tool_calls(("t1", "book_appointment", args))).json()["results"][0]
    assert "Booked for" in res["result"] and "Reference number" in res["result"]
    with SessionLocal() as s:
        lead = s.scalars(select(Lead)).one()
        assert lead.phone == "5550109999" and lead.status == "booked"
        assert s.scalars(select(Appointment)).one().call_id == "call-1"


def test_duplicate_tool_call_books_once(client):
    args = {**CALLER, "slot_id": first_open_slot_id()}
    first = post(client, tool_calls(("same-id", "book_appointment", args))).json()["results"][0]
    again = post(client, tool_calls(("same-id", "book_appointment", args))).json()["results"][0]
    assert first["result"] == again["result"]
    assert count(Appointment) == 1


def test_full_window_is_rejected(client):
    slot_id = first_open_slot_id()
    for i in range(2):  # two technicians per window
        post(client, tool_calls((f"t{i}", "book_appointment", {**CALLER, "slot_id": slot_id})))
    res = post(client, tool_calls(("t3", "book_appointment", {**CALLER, "slot_id": slot_id})))
    assert "filled up" in res.json()["results"][0]["error"]
    assert count(Appointment) == 2


def test_invalid_slot_and_missing_fields(client):
    bad_slot = post(client, tool_calls(("t1", "book_appointment", {**CALLER, "slot_id": "soon"})))
    assert "check_availability" in bad_slot.json()["results"][0]["error"]

    missing = post(client, tool_calls(("t2", "book_appointment", {"full_name": "Jane"})))
    error = missing.json()["results"][0]["error"]
    assert "phone" in error and "slot_id" in error
    assert count(Appointment) == 0


def test_create_lead_emergency_with_string_arguments(client):
    args = json.dumps({**CALLER, "urgency": "emergency", "issue": "Burst pipe in basement"})
    res = post(client, tool_calls(("t1", "create_lead", args))).json()["results"][0]
    assert "on-call technician" in res["result"]
    with SessionLocal() as s:
        assert s.scalars(select(Lead)).one().status == "emergency"


def test_multiple_calls_and_unknown_tool(client):
    body = tool_calls(("a", "check_availability", {}), ("b", "delete_everything", {}))
    results = post(client, body).json()["results"]
    assert [r["toolCallId"] for r in results] == ["a", "b"]
    assert "result" in results[0] and "Unknown tool" in results[1]["error"]


def test_other_events_are_acknowledged(client):
    assert post(client, {"message": {"type": "status-update"}}).json() == {}


def test_generated_schema_is_compact():
    schema = function_parameters(CreateLeadArgs)
    assert "title" not in json.dumps(schema)
    assert schema["properties"]["address"]["type"] == "string"  # Optional[str] flattened
    assert schema["properties"]["urgency"]["enum"] == ["routine", "emergency"]
    assert set(schema["required"]) == {"full_name", "phone", "issue", "urgency"}
