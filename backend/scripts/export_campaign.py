"""Export the win-back audience as a ready-to-launch Vapi Campaign (dry run).

Usage (from backend/): uv run python -m scripts.export_campaign

Writes, under backend/data/campaign/ (gitignored, contains phone numbers):
  - winback_contacts.csv   for the Vapi Dashboard CSV importer: lowercase
                           `number` and `name`; every other column becomes a
                           call variable the win-back assistant already uses.
  - winback_campaign.json  a POST /v2/campaign request body.

Nothing is sent. Launching needs an outbound-capable phone number (free Vapi
numbers can't run campaigns), a consent/opt-out review for every recipient,
and calling-hours checks. Do-not-call, wrong-number, and booked leads are
always excluded.
"""

import csv
import json
import sys
from pathlib import Path

from app.agents import reactivation
from app.db.session import SessionLocal, init_db
from app.services import reactivation as svc
from app.services.phone import to_e164
from app.services.vapi_ids import VAPI_DIR, get_id

OUT_DIR = VAPI_DIR.parent / "data" / "campaign"
PHONE_PLACEHOLDER = "<outbound-phone-number-id>"  # must be replaced before any launch


def main() -> int:
    init_db()
    assistant_id = get_id("assistant", reactivation.KEY)
    if not assistant_id:
        print("[FAIL] Win-back assistant not synced. Run scripts.sync_vapi first.")
        return 1

    with SessionLocal() as session:
        leads = svc.win_back_leads(session)
        audience = [lead for lead in leads if svc.is_callable(lead)]
        excluded = len(leads) - len(audience)
        rows, undialable = [], []
        for lead in audience:
            number = to_e164(lead.phone)
            if number is None:  # never send Vapi an invalid number
                undialable.append(lead.name)
                continue
            rows.append({"number": number, "name": lead.name, **svc.call_variables(lead)})

    if undialable:
        print(f"[WARN] Skipped {len(undialable)} lead(s) without a dialable E.164 number: "
              + ", ".join(undialable))

    if not rows:
        print("[SKIP] No callable win-back leads. Seed them with scripts.seed_old_leads.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    columns = ["number", "name"] + sorted({k for r in rows for k in r} - {"number", "name"})
    csv_path = OUT_DIR / "winback_contacts.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    request = {
        "name": "Ridgeway winter win-back",
        "assistantId": assistant_id,
        "phoneNumberId": PHONE_PLACEHOLDER,
        "maxConcurrency": 2,
        "customers": [
            {
                "number": r["number"],
                "name": r["name"],
                "assistantOverrides": {
                    "variableValues": {k: v for k, v in r.items() if k not in ("number", "name")}
                },
            }
            for r in rows
        ],
    }
    json_path = OUT_DIR / "winback_campaign.json"
    json_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")

    print(f"[OK]   {len(rows)} contacts exported ({excluded} excluded: opted out, wrong number, or booked).")
    print(f"       CSV:  {csv_path}")
    print(f"       JSON: {json_path}")
    print(f"[DRY]  Not launched. Replace {PHONE_PLACEHOLDER} with an outbound-capable number,")
    print("       verify consent and calling hours, then POST it to https://api.vapi.ai/v2/campaign.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
