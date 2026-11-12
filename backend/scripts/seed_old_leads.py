"""Seed past customers who went quiet, for the win-back (dead-lead reactivation) demo.

Usage (from backend/): uv run python -m scripts.seed_old_leads [--reset]

Idempotent: skips if win-back leads already exist. --reset removes win-back
leads that have no appointments, then re-seeds. Data lives in
app/services/demo_seed.py (all fictional).
"""

import argparse
import sys

from sqlalchemy import select

from app.db.models import Appointment, Lead
from app.db.session import SessionLocal, init_db
from app.services.demo_seed import OLD_CUSTOMERS, seed_old_leads
from app.services.reactivation import SOURCE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="remove unbooked win-back leads first")
    args = parser.parse_args()
    init_db()

    with SessionLocal() as session:
        if args.reset:
            booked_ids = set(session.scalars(select(Appointment.lead_id)))
            removed = [lead for lead in session.scalars(select(Lead).where(Lead.source == SOURCE))
                       if lead.id not in booked_ids]
            for lead in removed:
                session.delete(lead)
            session.commit()
            print(f"[OK]   Removed {len(removed)} unbooked win-back lead(s).")
        added = seed_old_leads(session)

    if not added:
        print("[SKIP] Win-back leads already exist. Use --reset to re-seed.")
        return 0
    opted_out = sum(status == "do_not_call" for *_, status in OLD_CUSTOMERS)
    print(f"[OK]   Seeded {added} past customers for the win-back campaign ({opted_out} already opted out).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
