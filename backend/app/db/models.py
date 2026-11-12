from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
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
