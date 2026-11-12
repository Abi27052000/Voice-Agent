"""Seed past customers who went quiet, for the win-back (dead-lead reactivation) demo.

Usage (from backend/): uv run python -m scripts.seed_old_leads [--reset]

Idempotent: skips if old_list leads already exist. --reset removes old_list
leads that have no appointments, then re-seeds. All people and numbers are
fictional: 555-0100 to 555-0199 is reserved for fiction in every US area code.
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import Appointment, Lead
from app.db.session import SessionLocal, init_db
from app.services.reactivation import LAST_SERVICE_PREFIX, SOURCE

# name, phone, address, last service, months ago, status
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="remove unbooked old_list leads first")
    args = parser.parse_args()
    init_db()

    with SessionLocal() as session:
        existing = list(session.scalars(select(Lead).where(Lead.source == SOURCE)))
        if args.reset:
            booked_ids = set(session.scalars(select(Appointment.lead_id)))
            removed = [lead for lead in existing if lead.id not in booked_ids]
            for lead in removed:
                session.delete(lead)
            session.commit()
            print(f"[OK]   Removed {len(removed)} unbooked win-back lead(s).")
            existing = [lead for lead in existing if lead.id in booked_ids]
        if existing:
            print(f"[SKIP] {len(existing)} win-back lead(s) already exist. Use --reset to re-seed.")
            return 0

        now = datetime.now(timezone.utc)
        for name, phone, address, service, months, status in OLD_CUSTOMERS:
            session.add(Lead(
                name=name, phone=phone, address=address, source=SOURCE, status=status,
                issue=f"{LAST_SERVICE_PREFIX}{service}",
                created_at=now - timedelta(days=30 * months),
            ))
        session.commit()
        print(f"[OK]   Seeded {len(OLD_CUSTOMERS)} past customers for the win-back campaign "
              f"({sum(s == 'do_not_call' for *_, s in OLD_CUSTOMERS)} already opted out).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
