"""Speed-to-lead: calls a web-form lead back seconds after they submit.

The quote form's fields arrive as call variables (assistantOverrides.variableValues)
and are injected into the prompt and first message with Liquid templates.
"""

from typing import Any

from app.agents import call_outcome, tools
from app.agents.common import base_assistant, load_prompt, model, server

KEY = "follow_up"
NAME = "Ridgeway Lead Follow-up"
PERSONA = "Sam"

VOICE = {"provider": "vapi", "voiceId": "Savannah", "version": 2}

FIRST_MESSAGE = (
    "Hi {{firstName | default: 'there'}}, this is Sam from Ridgeway Plumbing and Air. "
    "You just asked for a quote about {{service | default: 'a service visit'}}. "
    "Is now a good time for a quick chat?"
)

TOOL_KEYS = [tools.CHECK_AVAILABILITY, tools.BOOK_APPOINTMENT, tools.CREATE_LEAD]


def build(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    llm = model(load_prompt(KEY), tools=[{"type": "endCall"}])
    llm["toolIds"] = [ids["tool"][key] for key in TOOL_KEYS]
    return {
        **base_assistant(KEY),
        **server(ids),
        "name": NAME,
        "voice": VOICE,
        "firstMessageMode": "assistant-speaks-first",
        "firstMessage": FIRST_MESSAGE,
        "model": llm,
        "artifactPlan": {"structuredOutputIds": [ids["structured-output"][call_outcome.KEY]]},
    }
