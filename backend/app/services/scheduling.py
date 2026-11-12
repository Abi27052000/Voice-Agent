"""Service windows for the fictional business.

Customers book an arrival *window*, not an exact time, like most home-service
companies. Each window has a fixed capacity (number of technicians).
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Appointment

TECHS_PER_WINDOW = 2
LOOKAHEAD_DAYS = 14

# window code -> (start hour, end hour, spoken label)
WINDOWS = {
    "AM": (8, 12, "between 8 a.m. and noon"),
    "PM": (12, 16, "between noon and 4 p.m."),
}
# weekday() -> windows offered that day (Mon=0 ... Sun=6)
WEEKLY_SCHEDULE = {0: ("AM", "PM"), 1: ("AM", "PM"), 2: ("AM", "PM"), 3: ("AM", "PM"),
                   4: ("AM", "PM"), 5: ("AM",), 6: ()}


@dataclass(frozen=True)
class Slot:
    day: date
    window: str

    @property
    def slot_id(self) -> str:
        return f"{self.day.isoformat()}-{self.window}"

    @property
    def label(self) -> str:
        return f"{self.day.strftime('%A, %B')} {self.day.day}, {WINDOWS[self.window][2]}"

    @classmethod
    def parse(cls, slot_id: str) -> "Slot":
        """Parse 'YYYY-MM-DD-AM'. Raises ValueError if malformed."""
        day_part, _, window = slot_id.strip().upper().rpartition("-")
        if window not in WINDOWS:
            raise ValueError(f"unknown window '{window}'")
        return cls(date.fromisoformat(day_part), window)


def business_now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().business_timezone))


def is_offered(slot: Slot, now: datetime | None = None) -> bool:
    """True if the business works that window and it hasn't started yet."""
    now = now or business_now()
    if slot.window not in WEEKLY_SCHEDULE[slot.day.weekday()]:
        return False
    if not now.date() <= slot.day <= now.date() + timedelta(days=LOOKAHEAD_DAYS):
        return False
    start_hour = WINDOWS[slot.window][0]
    return slot.day > now.date() or now.hour < start_hour


def booked_count(session: Session, slot: Slot) -> int:
    return session.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.day == slot.day,
            Appointment.window == slot.window,
            Appointment.status == "scheduled",
        )
    ) or 0


def has_capacity(session: Session, slot: Slot) -> bool:
    return booked_count(session, slot) < TECHS_PER_WINDOW


def open_slots(session: Session, start: date | None = None, limit: int = 4) -> list[Slot]:
    now = business_now()
    day = max(start or now.date(), now.date())
    found: list[Slot] = []
    while day <= now.date() + timedelta(days=LOOKAHEAD_DAYS) and len(found) < limit:
        for window in WEEKLY_SCHEDULE[day.weekday()]:
            slot = Slot(day, window)
            if is_offered(slot, now) and has_capacity(session, slot):
                found.append(slot)
        day += timedelta(days=1)
    return found[:limit]
