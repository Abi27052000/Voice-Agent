"""Import past receptionist calls from Vapi into the local CRM.

Usage (from backend/):
    uv run python -m scripts.backfill_calls            # import/refresh recent calls (free)
    uv run python -m scripts.backfill_calls --extract  # also run the Call Outcome extraction
                                                       # on calls that don't have it yet
                                                       # (small Vapi LLM cost per call)

Calls made before the Structured Output existed have no outcome; --extract
runs it on them and writes the result to the call in Vapi. Re-run without
--extract a minute later to pull those results in.
"""

import argparse
import sys

from app.agents import call_outcome, receptionist
from app.db.session import SessionLocal, init_db
from app.services.call_log import upsert_call
from app.services.vapi_client import VapiClient, VapiConfigError, VapiError
from app.services.vapi_ids import get_id

MAX_RUN_BATCH = 100  # Vapi's documented max call IDs per run request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=50, help="how many recent calls to fetch")
    parser.add_argument("--extract", action="store_true", help="run Call Outcome on missing calls")
    args = parser.parse_args()

    assistant_id = get_id("assistant", receptionist.KEY)
    if not assistant_id:
        print("[FAIL] No receptionist in vapi/ids.json. Run scripts.sync_vapi first.")
        return 1

    init_db()
    try:
        with VapiClient() as vapi:
            calls = vapi.list("call", limit=args.limit, assistantId=assistant_id)
            calls = [c for c in calls if c.get("status") == "ended"]
            with SessionLocal() as session:
                saved = [upsert_call(session, c) for c in calls]
                pending = [c.id for c in saved if c.outcome_status != "ready"]
            print(f"[OK]   Imported {len(saved)} ended call(s); {len(pending)} without an outcome.")

            if args.extract and pending:
                so_id = get_id("structured-output", call_outcome.KEY)
                if not so_id:
                    print("[FAIL] No Call Outcome in vapi/ids.json. Run scripts.sync_vapi first.")
                    return 1
                for start in range(0, len(pending), MAX_RUN_BATCH):
                    batch = pending[start : start + MAX_RUN_BATCH]
                    vapi.post("/structured-output/run",
                              {"structuredOutputId": so_id, "callIds": batch, "previewEnabled": False})
                print(f"[OK]   Extraction started for {len(pending)} call(s). "
                      "Re-run this script without --extract in about a minute.")
    except (VapiConfigError, VapiError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
