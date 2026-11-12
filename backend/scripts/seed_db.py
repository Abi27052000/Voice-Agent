"""Seed the local CRM with a few existing bookings so the schedule looks real.

Usage (from backend/):
    uv run python -m scripts.seed_db            # seed only if the DB is empty
    uv run python -m scripts.seed_db --reset    # wipe all data, then seed

All people and numbers are fictional (555 numbers).
"""

import argparse
import sys
from datetime import timedelta

from sqlalchemy import func, select

from app.db.models import Appointment, Lead
from app.db.session import Base, SessionLocal, engine, init_db
from app.services.scheduling import WEEKLY_SCHEDULE, Slot, business_now, is_offered

SEED_CUSTOMERS = [
    ("Maria Lopez", "5550101", "14 Birch Lane, Ridgeway", "Water heater making popping noises"),
    ("James Carter", "5550102", "88 Oak Street, Ridgeway", "AC not cooling upstairs"),
    ("Priya Nair", "5550103", "302 Hill Road, Ridgeway", "Toilet keeps running"),
    ("Tom Becker", "5550104", "9 Mill Court, Ridgeway", "Furnace tune-up"),
    ("Aisha Khan", "5550105", "51 River Drive, Ridgeway", "Low water pressure in shower"),
    ("David Kim", "5550106", "7 Elm Avenue, Ridgeway", "Garbage disposal jammed"),
]


def upcoming_slots(count: int) -> list[Slot]:
    now = business_now()
    slots: list[Slot] = []
    day = now.date() + timedelta(days=1)
    while len(slots) < count:
        for window in WEEKLY_SCHEDULE[day.weekday()]:
            slot = Slot(day, window)
            if is_offered(slot, now):
                slots.append(slot)
        day += timedelta(days=1)
    return slots[:count]


def seed() -> int:
    with SessionLocal() as session:
        if session.scalar(select(func.count(Lead.id))):
            print("[SKIP] CRM already has data. Use --reset to start over.")
            return 0
        slots = upcoming_slots(4)
        # First upcoming window gets both techs (full); the next three get one booking each.
        plan = [slots[0], slots[0], slots[1], slots[2], slots[3]]
        for (name, phone, address, issue), slot in zip(SEED_CUSTOMERS, plan):
            lead = Lead(name=name, phone=phone, address=address, issue=issue,
                        status="booked", source="seed")
            session.add(Appointment(lead=lead, day=slot.day, window=slot.window, issue=issue))
        name, phone, address, issue = SEED_CUSTOMERS[-1]
        session.add(Lead(name=name, phone=phone, address=address, issue=issue, source="seed"))
        session.commit()
        print(f"[OK]   Seeded {len(plan)} appointments and {len(SEED_CUSTOMERS)} leads.")
        print(f"       Fully booked window: {slots[0].label}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete all data first")
    args = parser.parse_args()
    init_db()
    if args.reset:
        Base.metadata.drop_all(engine)
        init_db()
        print("[OK]   Database reset.")
    return seed()


if __name__ == "__main__":
    sys.exit(main())
