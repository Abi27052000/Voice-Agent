"""Shared building blocks for every assistant in the demo.

Budget guardrails live here: a small fast model, short replies, and a silence
timeout so a forgotten browser tab can't drain Vapi credit.
"""

from typing import Any

from app.core.config import get_settings
from app.services.vapi_ids import VAPI_DIR

PROMPTS_DIR = VAPI_DIR / "prompts"
PROJECT_TAG = "ridgeway-demo"

# Vapi's own default. Set explicitly because an omitted field is not reset on
# update (PATCH keeps the previous value).
MAX_CALL_SECONDS = 600
SILENCE_TIMEOUT_SECONDS = 20


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def model(system_prompt: str, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "temperature": 0.3,
        "maxTokens": 250,
        "messages": [{"role": "system", "content": system_prompt}],
        "tools": tools or [],
    }


VOICE: dict[str, Any] = {"provider": "vapi", "voiceId": "Elliot", "version": 2}

TRANSCRIBER: dict[str, Any] = {"provider": "deepgram", "model": "nova-3", "language": "en"}


def webhook_url() -> str:
    url = get_settings().webhook_url
    if not url:
        raise SystemExit("[FAIL] PUBLIC_BASE_URL is not set in backend/.env (needed for webhooks).")
    return url


def server(ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Send this assistant's call events to our webhook (bearer-authenticated).

    Only the events we handle are subscribed, to keep webhook traffic low.
    Tool calls still go to each tool's own server URL.
    """
    return {
        "server": {
            "url": webhook_url(),
            "credentialId": ids["credential"]["webhook"],
            "timeoutSeconds": 10,
        },
        "serverMessages": ["end-of-call-report", "tool-calls"],
    }


# Every client message type Vapi offers. Listed explicitly (instead of relying on
# defaults) so `assistant.started` reaches the browser and the UI can show handoffs.
CLIENT_MESSAGES = [
    "conversation-update", "assistant.speechStarted", "function-call", "function-call-result",
    "hang", "language-changed", "metadata", "model-output", "speech-update", "status-update",
    "transcript", "tool-calls", "tool-calls-result", "tool.completed", "transfer-update",
    "user-interrupted", "voice-input", "workflow.node.started", "assistant.started",
]


def base_assistant(role: str) -> dict[str, Any]:
    """Fields every assistant shares; callers add name, firstMessage and model."""
    return {
        "voice": VOICE,
        "transcriber": TRANSCRIBER,
        "maxDurationSeconds": MAX_CALL_SECONDS,
        "silenceTimeoutSeconds": SILENCE_TIMEOUT_SECONDS,
        "analysisPlan": {"summaryPlan": {"enabled": True}},
        "clientMessages": CLIENT_MESSAGES,
        "metadata": {"project": PROJECT_TAG, "role": role},
    }
