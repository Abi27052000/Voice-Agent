from datetime import date, datetime, timezone

from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), index=True)  # digits only
    address: Mapped[str | None] = mapped_column(String(255))
    issue: Mapped[str | None] = mapped_column(Text)
    urgency: Mapped[str] = mapped_column(String(20), default="routine")  # routine | emergency
    status: Mapped[str] = mapped_column(String(20), default="new")  # new | booked | emergency
    source: Mapped[str] = mapped_column(String(30), default="inbound_call")
    call_id: Mapped[str | None] = mapped_column(String(64))  # Vapi call that last touched it
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="lead")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    day: Mapped[date] = mapped_column(Date, index=True)
    window: Mapped[str] = mapped_column(String(2))  # AM | PM
    issue: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    call_id: Mapped[str | None] = mapped_column(String(64))
    # Vapi may retry a tool call; the same toolCallId must never book twice.
    tool_call_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lead: Mapped[Lead] = relationship(back_populates="appointments")

    @property
    def reference(self) -> str:
        return str(1000 + self.id)


class Call(Base):
    """One Vapi call, saved from the end-of-call report (or backfilled via the API)."""

    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Vapi call ID
    assistant_id: Mapped[str | None] = mapped_column(String(64))
    call_type: Mapped[str | None] = mapped_column(String(30))  # webCall, outboundPhoneCall, ...
    ended_reason: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text)
    recording_url: Mapped[str | None] = mapped_column(String(500))
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"))

    # Structured Output ("Ridgeway Call Outcome"); pending until Vapi finishes extraction.
    outcome_status: Mapped[str] = mapped_column(String(10), default="pending")  # pending | ready
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    booked: Mapped[bool | None] = mapped_column(Boolean)
    urgency: Mapped[str | None] = mapped_column(String(20))
    job_type: Mapped[str | None] = mapped_column(String(40))
    caller_sentiment: Mapped[str | None] = mapped_column(String(20))
    follow_up_needed: Mapped[bool | None] = mapped_column(Boolean)
    follow_up_reason: Mapped[str | None] = mapped_column(Text)
    estimated_value_usd: Mapped[int | None] = mapped_column(Integer)  # derived from job_type

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    lead: Mapped[Lead | None] = relationship()
