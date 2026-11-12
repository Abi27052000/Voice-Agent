"""Vapi function tools. Parameter schemas are generated from app/schemas/tools.py."""

from typing import Any

from pydantic import BaseModel

from app.agents.common import webhook_url
from app.schemas.tools import (
    BookAppointmentArgs,
    CheckAvailabilityArgs,
    CreateLeadArgs,
    UpdateLeadStatusArgs,
)

CHECK_AVAILABILITY = "check_availability"
BOOK_APPOINTMENT = "book_appointment"
CREATE_LEAD = "create_lead"
UPDATE_LEAD_STATUS = "update_lead_status"


def function_parameters(model: type[BaseModel]) -> dict[str, Any]:
    """Pydantic JSON Schema -> compact OpenAI-style function parameters."""

    def clean(node: Any) -> Any:
        if isinstance(node, list):
            return [clean(n) for n in node]
        if not isinstance(node, dict):
            return node
        node = {k: v for k, v in node.items() if k not in ("title", "default")}
        # Optional[X] renders as anyOf [X, null]; models handle plain X better.
        variants = [v for v in node.get("anyOf", []) if v.get("type") != "null"]
        if "anyOf" in node and len(variants) == 1:
            node = {**{k: v for k, v in node.items() if k != "anyOf"}, **variants[0]}
        return {
            k: ({pk: clean(pv) for pk, pv in v.items()} if k == "properties" else clean(v))
            for k, v in node.items()
        }

    return clean(model.model_json_schema())


def _function_tool(
    name: str, description: str, args: type[BaseModel], start_message: str | None, credential_id: str
) -> dict[str, Any]:
    tool: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": function_parameters(args),
        },
        "server": {"url": webhook_url(), "credentialId": credential_id, "timeoutSeconds": 10},
        "messages": [
            {
                "type": "request-failed",
                "content": "Sorry, I'm having trouble with our system right now.",
            }
        ],
    }
    if start_message:
        tool["messages"].insert(0, {"type": "request-start", "content": start_message})
    return tool


def build_check_availability(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    return _function_tool(
        CHECK_AVAILABILITY,
        "List open arrival windows for a service visit. Call after collecting the caller's "
        "details and asking their preferred day. Do not call for emergencies.",
        CheckAvailabilityArgs,
        "Let me check the schedule.",
        ids["credential"]["webhook"],
    )


def build_book_appointment(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    return _function_tool(
        BOOK_APPOINTMENT,
        "Book a service visit in an open window. Call only after the caller confirms the recap "
        "and chose a window returned by check_availability.",
        BookAppointmentArgs,
        "Booking that now.",
        ids["credential"]["webhook"],
    )


def build_create_lead(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    return _function_tool(
        CREATE_LEAD,
        "Log a service request without booking a window: emergencies for the on-call "
        "technician, or callers who want a callback instead of booking now.",
        CreateLeadArgs,
        None,
        ids["credential"]["webhook"],
    )


def build_update_lead_status(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    return _function_tool(
        UPDATE_LEAD_STATUS,
        "Record the outcome of a win-back call with an existing customer when they did not "
        "book: wants a callback later, not interested, asked not to be called, or wrong number. "
        "Do not call after a successful booking.",
        UpdateLeadStatusArgs,
        None,
        ids["credential"]["webhook"],
    )


TOOLS = [
    (CHECK_AVAILABILITY, build_check_availability),
    (BOOK_APPOINTMENT, build_book_appointment),
    (CREATE_LEAD, build_create_lead),
    (UPDATE_LEAD_STATUS, build_update_lead_status),
]
