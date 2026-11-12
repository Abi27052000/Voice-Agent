from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class LeadOut(BaseModel):
    id: int
    name: str
    phone: str
    address: str | None
    issue: str | None
    urgency: str
    status: str
    source: str
    created_at: datetime


class AppointmentOut(BaseModel):
    id: int
    reference: str
    day: date
    window: str
    window_label: str
    issue: str | None
    status: str
    is_past: bool
    lead_id: int
    lead_name: str
    lead_phone: str
    lead_address: str | None


class CallOut(BaseModel):
    id: str
    call_type: str | None
    started_at: datetime | None
    duration_seconds: int | None
    cost_usd: float | None
    ended_reason: str | None
    summary: str | None
    outcome_status: str
    booked: bool | None
    urgency: str | None
    job_type: str | None
    caller_sentiment: str | None
    follow_up_needed: bool | None
    follow_up_reason: str | None
    estimated_value_usd: int | None
    lead_id: int | None
    lead_name: str | None


class CallDetail(CallOut):
    transcript: str | None
    outcome: dict[str, Any] | None


class Stats(BaseModel):
    calls_total: int
    calls_with_outcome: int
    calls_booked: int
    booking_rate: float | None  # booked / calls with an outcome
    est_booked_revenue_usd: int
    total_cost_usd: float
    avg_cost_per_call_usd: float | None
    avg_duration_seconds: float | None
    follow_ups_open: int
    emergencies: int
    upcoming_appointments: int
    leads_total: int
