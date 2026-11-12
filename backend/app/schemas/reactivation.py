from datetime import datetime

from pydantic import BaseModel


class WinBackLead(BaseModel):
    id: int
    name: str
    phone: str
    address: str | None
    last_service: str
    months_since: int
    status: str
    callable: bool
    created_at: datetime


class WinBackSummary(BaseModel):
    total: int
    callable: int
    contacted: int  # leads with at least one linked call
    booked: int
    callbacks: int
    not_interested: int
    opted_out: int  # do_not_call + wrong_number


class WinBackOverview(BaseModel):
    summary: WinBackSummary
    leads: list[WinBackLead]
    offer: dict[str, str]


class WinBackCallOut(BaseModel):
    assistant_id: str
    # Passed to the browser call as assistantOverrides.variableValues.
    variable_values: dict[str, str]
