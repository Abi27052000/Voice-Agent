"""Arguments for each Vapi function tool.

These models are the single source of truth: they validate incoming tool calls
AND generate the JSON Schema sent to Vapi (see app/agents/tools.py), so the
model-facing contract and the server-side validation can't drift apart.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if not 7 <= len(digits) <= 15:
        raise ValueError("phone must contain 7 to 15 digits")
    return digits


class CheckAvailabilityArgs(ToolArgs):
    preferred_date: str | None = Field(
        default=None,
        description=(
            "Earliest date the caller wants, as YYYY-MM-DD. "
            "Omit to get the next available windows."
        ),
    )


class CallerDetails(ToolArgs):
    full_name: str = Field(min_length=2, max_length=120, description="Caller's full name.")
    phone: str = Field(description="Callback phone number, digits as spoken by the caller.")
    issue: str = Field(min_length=3, max_length=1000, description="Short description of the problem.")

    _normalize_phone = field_validator("phone")(normalize_phone)


class BookAppointmentArgs(CallerDetails):
    slot_id: str = Field(
        description="Exact slot_id of the chosen window from check_availability, e.g. 2026-11-14-AM."
    )
    address: str = Field(min_length=5, max_length=255, description="Service street address and town.")


class CreateLeadArgs(CallerDetails):
    address: str | None = Field(
        default=None, max_length=255, description="Service street address and town, if given."
    )
    urgency: Literal["routine", "emergency"] = Field(
        description="emergency for active leaks, flooding, gas smell, no heat in freezing weather, "
        "sewage backup or no water; otherwise routine."
    )
