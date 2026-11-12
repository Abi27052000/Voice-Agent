from typing import Any

from app.agents import call_outcome, handoff, tools
from app.agents.common import base_assistant, load_prompt, model, server

KEY = "receptionist"
NAME = "Ridgeway Receptionist"
PERSONA = "Alex"

FIRST_MESSAGE = (
    "Thanks for calling Ridgeway Plumbing and Air, this is Alex, the virtual assistant. "
    "How can I help you today?"
)

TOOL_KEYS = [
    tools.CHECK_AVAILABILITY,
    tools.BOOK_APPOINTMENT,
    tools.CREATE_LEAD,
    handoff.TO_DISPATCHER,
]


def build(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    llm = model(load_prompt(KEY), tools=[{"type": "endCall"}])
    llm["toolIds"] = [ids["tool"][key] for key in TOOL_KEYS]
    return {
        **base_assistant(KEY),
        **server(ids),
        "name": NAME,
        "firstMessageMode": "assistant-speaks-first",
        "firstMessage": FIRST_MESSAGE,
        "model": llm,
        "artifactPlan": {"structuredOutputIds": [ids["structured-output"][call_outcome.KEY]]},
    }
