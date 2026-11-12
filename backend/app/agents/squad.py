from typing import Any

from app.agents import dispatcher, receptionist

KEY = "front_desk"
NAME = "Ridgeway Front Desk Squad"


def build(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    # The first member answers the call.
    return {
        "name": NAME,
        "members": [
            {"assistantId": ids["assistant"][receptionist.KEY]},
            {"assistantId": ids["assistant"][dispatcher.KEY]},
        ],
    }
