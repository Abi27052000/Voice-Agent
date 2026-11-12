"""Vapi Custom Credential that authenticates Vapi -> our webhook.

Vapi sends "Authorization: Bearer <VAPI_WEBHOOK_SECRET>" on every tool call;
the backend rejects requests without it (see vapi_webhook_controller.py).
"""

from typing import Any

from app.core.config import get_settings

KEY = "webhook"
NAME = "Ridgeway webhook bearer"


def build(_ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    secret = get_settings().vapi_webhook_secret
    if secret is None or not secret.get_secret_value():
        raise SystemExit("[FAIL] VAPI_WEBHOOK_SECRET is not set in backend/.env.")
    return {
        "provider": "custom-credential",
        "name": NAME,
        "authenticationPlan": {"type": "bearer", "token": secret.get_secret_value()},
    }
