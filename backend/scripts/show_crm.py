"""Print the latest leads and appointments (a quick check until the Step 5 dashboard).

Usage (from backend/): uv run python -m scripts.show_crm
"""

from sqlalchemy import select

from app.db.models import Appointment, Lead
from app.db.session import SessionLocal, init_db
from app.services.scheduling import Slot


def main() -> None:
    init_db()
    with SessionLocal() as session:
        print("LEADS (newest first)")
        for lead in session.scalars(select(Lead).order_by(Lead.id.desc()).limit(10)):
            print(f"  #{lead.id:<3} {lead.status:<9} {lead.urgency:<9} {lead.name:<18} "
                  f"{lead.phone:<12} {lead.source:<12} {(lead.issue or '')[:40]}")
        print("\nAPPOINTMENTS (newest first)")
        for appt in session.scalars(select(Appointment).order_by(Appointment.id.desc()).limit(10)):
            print(f"  ref {appt.reference}  {Slot(appt.day, appt.window).label:<45} "
                  f"{appt.lead.name:<18} {appt.status}")


if __name__ == "__main__":
    main()
