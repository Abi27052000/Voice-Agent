"""Handoff tool: receptionist -> emergency dispatcher (native Vapi `handoff` type).

OpenAI models do best with one handoff tool per destination.

Lesson from a real test call: with only an `assistantId` destination, Vapi asks
the model to echo the 36-char UUID as a `destination` argument, and
gpt-4.1-mini mistyped one character -> `assistant-not-found` and a dropped call.
So the destination is addressed by squad member name, and the argument is an
enum with strict schema adherence, so the model can only send the exact value.
"""

from typing import Any

from app.agents import dispatcher

TO_DISPATCHER = "handoff_to_emergency_dispatcher"


def build_to_dispatcher(_ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    return {
        "type": "handoff",
        "function": {
            "name": TO_DISPATCHER,
            "description": "Transfer an emergency caller to the emergency dispatcher.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "enum": [dispatcher.NAME],
                        "description": "Always the emergency dispatcher.",
                    }
                },
                "required": ["destination"],
                "additionalProperties": False,
            },
        },
        "destinations": [
            {
                "type": "assistant",
                # Resolved among the squad's members, so calls must start via the squad.
                "assistantName": dispatcher.NAME,
                "description": (
                    "Hand off when the caller has an emergency: active leak, flooding or burst "
                    "pipe, gas smell, sewage backup, no water at all, no heat in freezing weather, "
                    "or no AC in extreme heat with vulnerable people at home. Give the immediate "
                    "safety step first. Do not hand off routine requests."
                ),
                # Jordan sees what was said, without system prompt or tool noise.
                "contextEngineeringPlan": {"type": "userAndAssistantMessages"},
            }
        ],
        "messages": [
            {
                "type": "request-start",
                "content": "I'm connecting you with our emergency dispatcher right now. Stay on the line.",
            }
        ],
    }
