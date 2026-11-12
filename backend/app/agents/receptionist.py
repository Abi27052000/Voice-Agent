from typing import Any

from app.agents.common import base_assistant, load_prompt, model

KEY = "receptionist"
NAME = "Ridgeway Receptionist"

FIRST_MESSAGE = (
    "Thanks for calling Ridgeway Plumbing and Air, this is Alex, the virtual assistant. "
    "How can I help you today?"
)


def build() -> dict[str, Any]:
    return {
        **base_assistant(KEY),
        "name": NAME,
        "firstMessageMode": "assistant-speaks-first",
        "firstMessage": FIRST_MESSAGE,
        "model": model(load_prompt(KEY), tools=[{"type": "endCall"}]),
    }
