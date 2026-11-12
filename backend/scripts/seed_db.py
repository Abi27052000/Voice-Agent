"""Seed the local CRM with a few existing bookings so the schedule looks real.

Usage (from backend/):
    uv run python -m scripts.seed_db            # seed only if there are no bookings yet
    uv run python -m scripts.seed_db --reset    # wipe ALL data (calls too), then seed

All people and numbers are fictional. Data lives in app/services/demo_seed.py.
"""

import argparse
import sys

from app.db.session import Base, SessionLocal, engine, init_db
from app.services.demo_seed import BOOKED_CUSTOMERS, seed_bookings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete all data first")
    args = parser.parse_args()
    init_db()
    if args.reset:
        Base.metadata.drop_all(engine)
        init_db()
        print("[OK]   Database reset.")
    with SessionLocal() as session:
        full = seed_bookings(session)
    if full is None:
        print("[SKIP] CRM already has bookings. Use --reset to start over.")
        return 0
    print(f"[OK]   Seeded 5 appointments and {len(BOOKED_CUSTOMERS)} leads.")
    print(f"       Fully booked window: {full.label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
