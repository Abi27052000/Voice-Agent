from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.tools import normalize_phone

SERVICES = (
    "Drain or clog",
    "Leak or burst pipe",
    "Water heater",
    "Toilet or faucet",
    "AC repair",
    "AC installation",
    "Heating repair",
    "Maintenance tune-up",
    "Other",
)


class QuoteRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=2, max_length=120)
    phone: str
    address: str | None = Field(default=None, max_length=255)
    service: Literal[SERVICES]  # type: ignore[valid-type]
    details: str = Field(default="", max_length=500)
    # Automated calls need prior express consent (TCPA); the form requires it.
    consent: Literal[True]

    _normalize_phone = field_validator("phone")(normalize_phone)


class QuoteRequestOut(BaseModel):
    lead_id: int
    assistant_id: str
    # Passed to the browser call as assistantOverrides.variableValues.
    variable_values: dict[str, str]
