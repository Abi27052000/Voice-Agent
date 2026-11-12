"""Handles server messages Vapi posts to /api/vapi/webhook."""

import hmac
import json
import logging
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.tool_handlers import TOOL_HANDLERS, ToolContext, ToolError

log = logging.getLogger(__name__)

FALLBACK_ERROR = "System error. Apologize and tell the caller the office will follow up."


def verify_authorization(authorization: str | None) -> None:
    secret = get_settings().vapi_webhook_secret
    if secret is None or not secret.get_secret_value():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook secret not configured")
    expected = f"Bearer {secret.get_secret_value()}".encode()
    if not authorization or not hmac.compare_digest(authorization.encode(), expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, str):
        raw = json.loads(raw) if raw.strip() else {}
    if not isinstance(raw, dict):
        raise ValueError("arguments must be an object")
    return raw


def _format_validation_error(exc: ValidationError) -> str:
    problems = [
        f"{'.'.join(str(p) for p in err['loc']) or 'arguments'}: {err['msg']}"
        for err in exc.errors()
    ]
    return "Invalid or missing details - " + "; ".join(problems) + ". Ask the caller and retry."


def run_tool_call(session: Session, tool_call: dict[str, Any], call_id: str | None) -> dict[str, Any]:
    tool_call_id = str(tool_call.get("id", ""))
    function = tool_call.get("function") or {}
    name = function.get("name") or tool_call.get("name") or ""
    result: dict[str, Any] = {"name": name, "toolCallId": tool_call_id}

    entry = TOOL_HANDLERS.get(name)
    if entry is None:
        result["error"] = f"Unknown tool '{name}'."
        return result
    args_model, handler = entry

    raw = function.get("arguments", tool_call.get("arguments", tool_call.get("parameters")))
    try:
        args = args_model.model_validate(_parse_arguments(raw))
    except ValidationError as exc:  # subclass of ValueError, so it must come first
        result["error"] = _format_validation_error(exc)
        return result
    except ValueError:  # includes json.JSONDecodeError
        result["error"] = "Arguments were not a valid JSON object. Retry the tool call."
        return result

    try:
        ctx = ToolContext(tool_call_id=tool_call_id, call_id=call_id)
        result["result"] = handler(session, args, ctx)
    except ToolError as exc:
        session.rollback()
        result["error"] = str(exc)
    except Exception:
        session.rollback()
        log.exception("Tool %s failed (toolCallId=%s, callId=%s)", name, tool_call_id, call_id)
        result["error"] = FALLBACK_ERROR

    log.info("tool=%s toolCallId=%s ok=%s", name, tool_call_id, "result" in result)
    return result


def handle_server_message(session: Session, body: dict[str, Any]) -> dict[str, Any]:
    message = body.get("message") or {}
    message_type = message.get("type")
    call_id = (message.get("call") or {}).get("id")

    if message_type == "tool-calls":
        tool_calls = message.get("toolCallList") or []
        return {"results": [run_tool_call(session, tc, call_id) for tc in tool_calls]}

    # Other events (status-update, end-of-call-report, ...) are acknowledged.
    # end-of-call-report handling is added in Step 4.
    return {}
