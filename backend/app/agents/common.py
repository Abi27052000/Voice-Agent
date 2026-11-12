"""Shared building blocks for every assistant in the demo.

Budget guardrails live here: a small fast model, short replies, and a silence
timeout so a forgotten browser tab can't drain Vapi credit.
"""

from typing import Any

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


def base_assistant(role: str) -> dict[str, Any]:
    """Fields every assistant shares; callers add name, firstMessage and model."""
    return {
        "voice": VOICE,
        "transcriber": TRANSCRIBER,
        "maxDurationSeconds": MAX_CALL_SECONDS,
        "silenceTimeoutSeconds": SILENCE_TIMEOUT_SECONDS,
        "metadata": {"project": PROJECT_TAG, "role": role},
    }
