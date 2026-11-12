"""Dead-lead reactivation ("win-back") caller.

Built to run unchanged in two places:
- the browser demo, which starts a web call with the lead's variables, and
- a real Vapi Campaign, where each CSV column becomes a variable. That's why
  the variables use snake_case names (lead_id, first_name, ...).
"""

from typing import Any

from app.agents import call_outcome, tools
from app.agents.common import base_assistant, load_prompt, model, server

KEY = "reactivation"
NAME = "Ridgeway Win-back"
PERSONA = "Taylor"

VOICE = {"provider": "vapi", "voiceId": "Neil", "version": 2}

# Campaign-wide offer, passed to every call as variables (easy to change per season).
OFFER = {
    "offer": "winter heating tune-up",
    "offer_price": "seventy-nine dollars",
    "offer_deadline": "December fifteenth",
}

FIRST_MESSAGE = (
    "Hi, is this {{first_name | default: 'the homeowner'}}? This is Taylor from Ridgeway "
    "Plumbing and Air. We helped you with your {{last_service | default: 'home'}} a while back. "
    "Do you have a quick minute?"
)

VOICEMAIL_MESSAGE = (
    "Hi {{first_name | default: 'there'}}, this is Taylor from Ridgeway Plumbing and Air. "
    "We're offering past customers a {{offer}} for {{offer_price}} until {{offer_deadline}}. "
    "Give us a call back if you'd like to book. Have a great day!"
)

TOOL_KEYS = [
    tools.CHECK_AVAILABILITY,
    tools.BOOK_APPOINTMENT,
    tools.UPDATE_LEAD_STATUS,
]


def build(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    llm = model(
        load_prompt(KEY),
        tools=[
            {"type": "endCall"},
            # Real phone campaigns hit voicemail; leave a short message and hang up.
            {"type": "voicemail", "messages": [{"type": "request-start", "content": VOICEMAIL_MESSAGE}]},
        ],
    )
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
