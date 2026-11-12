from typing import Any

from app.agents import call_outcome, tools
from app.agents.common import base_assistant, load_prompt, model, server

KEY = "dispatcher"
NAME = "Ridgeway Emergency Dispatcher"
PERSONA = "Jordan"

# A different voice from the receptionist, so callers can hear the handoff.
VOICE = {"provider": "vapi", "voiceId": "Clara", "version": 2}


def build(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    llm = model(load_prompt(KEY), tools=[{"type": "endCall"}])
    llm["toolIds"] = [ids["tool"][tools.CREATE_LEAD]]
    return {
        **base_assistant(KEY),
        **server(ids),
        "name": NAME,
        "voice": VOICE,
        # Generated from the conversation so far, so Jordan picks up where Alex left off.
        "firstMessageMode": "assistant-speaks-first-with-model-generated-message",
        "model": llm,
        "artifactPlan": {"structuredOutputIds": [ids["structured-output"][call_outcome.KEY]]},
    }
