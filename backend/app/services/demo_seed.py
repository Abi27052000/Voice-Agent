"""Fictional demo data, shared by the seed scripts and startup seeding (SEED_DEMO_DATA).

All people are fictional. Win-back numbers use 555-0100..0199, which is
reserved for fiction in every US area code.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Appointment, Lead
from app.services.reactivation import LAST_SERVICE_PREFIX, SOURCE
from app.services.scheduling import WEEKLY_SCHEDULE, Slot, business_now, is_offered

log = logging.getLogger(__name__)

# Existing bookings, so the schedule isn't empty and one window is already full.
BOOKED_CUSTOMERS = [
    ("Maria Lopez", "5550101", "14 Birch Lane, Ridgeway", "Water heater making popping noises"),
    ("James Carter", "5550102", "88 Oak Street, Ridgeway", "AC not cooling upstairs"),
    ("Priya Nair", "5550103", "302 Hill Road, Ridgeway", "Toilet keeps running"),
    ("Tom Becker", "5550104", "9 Mill Court, Ridgeway", "Furnace tune-up"),
    ("Aisha Khan", "5550105", "51 River Drive, Ridgeway", "Low water pressure in shower"),
    ("David Kim", "5550106", "7 Elm Avenue, Ridgeway", "Garbage disposal jammed"),
]

# Past customers for the win-back campaign: name, phone, address, last service, months ago, status.
OLD_CUSTOMERS = [
    ("Grace Whitfield", "3125550120", "22 Maple Row, Ridgeway", "furnace repair", 13, "dormant"),
    ("Marcus Bell", "3125550121", "7 Quarry Lane, Ridgeway", "water heater install", 18, "dormant"),
    ("Sofia Romero", "3125550122", "415 Lake View Dr, Ridgeway", "AC tune-up", 11, "dormant"),
    ("Kevin O'Neill", "3125550123", "90 Station Road, Ridgeway", "drain cleaning", 9, "dormant"),
    ("Hannah Park", "3125550124", "3 Cedar Court, Ridgeway", "heating repair", 15, "dormant"),
    ("Daniel Okafor", "3125550125", "128 Elmwood Ave, Ridgeway", "leak repair", 7, "dormant"),
    ("Lucy Tran", "3125550126", "61 Orchard St, Ridgeway", "AC repair", 14, "dormant"),
    ("Robert Shaw", "3125550127", "5 Ferry Road, Ridgeway", "toilet replacement", 20, "dormant"),
    ("Nina Kowalski", "3125550128", "240 Brook Lane, Ridgeway", "furnace tune-up", 12, "dormant"),
    ("Omar Haddad", "3125550129", "17 Willow Way, Ridgeway", "water heater repair", 8, "dormant"),
    ("Ellen Murphy", "3125550130", "88 Pine Ridge Rd, Ridgeway", "AC installation", 16, "dormant"),
    # Already opted out: must never be called or exported.
    ("Victor Lang", "3125550131", "9 Harbor View, Ridgeway", "drain cleaning", 10, "do_not_call"),
]


def _upcoming_slots(count: int) -> list[Slot]:
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


def seed_bookings(session: Session) -> Slot | None:
    """Add 5 bookings (the first upcoming window fully booked) and 1 open lead.

    Skips if any non-win-back lead exists. Returns the fully booked slot, if seeded.
    """
    if session.scalar(select(func.count(Lead.id)).where(Lead.source != SOURCE)):
        return None
    slots = _upcoming_slots(4)
    plan = [slots[0], slots[0], slots[1], slots[2], slots[3]]
    for (name, phone, address, issue), slot in zip(BOOKED_CUSTOMERS, plan):
        lead = Lead(name=name, phone=phone, address=address, issue=issue, status="booked", source="seed")
        session.add(Appointment(lead=lead, day=slot.day, window=slot.window, issue=issue))
    name, phone, address, issue = BOOKED_CUSTOMERS[-1]
    session.add(Lead(name=name, phone=phone, address=address, issue=issue, source="seed"))
    session.commit()
    return slots[0]


def seed_old_leads(session: Session) -> int:
    """Add the win-back past customers. Skips if any exist. Returns how many were added."""
    if session.scalar(select(func.count(Lead.id)).where(Lead.source == SOURCE)):
        return 0
    now = datetime.now(timezone.utc)
    for name, phone, address, service, months, status in OLD_CUSTOMERS:
        session.add(Lead(
            name=name, phone=phone, address=address, source=SOURCE, status=status,
            issue=f"{LAST_SERVICE_PREFIX}{service}", created_at=now - timedelta(days=30 * months),
        ))
    session.commit()
    return len(OLD_CUSTOMERS)


def seed_demo_data(session: Session) -> None:
    """Startup seeding for the hosted demo: fills an empty database, never touches existing data."""
    full = seed_bookings(session)
    added = seed_old_leads(session)
    if full or added:
        log.info("Seeded demo data (bookings: %s, win-back leads: %s)", bool(full), added)
