"""Create or update this project's Vapi resources from the configs in backend/vapi/.

Usage (from the backend/ folder):
    uv run python -m scripts.sync_vapi --check   # verify the API key and local config
    uv run python -m scripts.sync_vapi           # sync assistants/tools/squads (added in later steps)

Sync is idempotent: resources are matched by name, so running it twice
updates instead of creating duplicates. IDs are written to vapi/ids.json.
"""

import argparse
import sys

from app.core.config import get_settings
from app.services.vapi_client import VapiClient, VapiConfigError, VapiError


def check() -> int:
    settings = get_settings()
    try:
        with VapiClient(settings) as vapi:
            assistants = vapi.list("assistant", limit=100)
    except VapiConfigError as exc:
        print(f"[FAIL] {exc}")
        return 1
    except VapiError as exc:
        hint = " Check that it's the PRIVATE key." if exc.status_code in (401, 403) else ""
        print(f"[FAIL] {exc}{hint}")
        return 1

    print(f"[OK]   Vapi private API key works ({len(assistants)} assistant(s) in your org).")

    optional = {
        "VAPI_PUBLIC_KEY": (settings.vapi_public_key, "needed for browser calls (Step 2)"),
        "VAPI_WEBHOOK_SECRET": (settings.vapi_webhook_secret, "needed for tools (Step 3)"),
        "PUBLIC_BASE_URL": (settings.public_base_url, "needed for tools (Step 3)"),
    }
    for name, (value, why) in optional.items():
        status = "[OK]  " if value else "[TODO]"
        print(f"{status} {name} {'is set' if value else 'is not set'} - {why}")
    return 0


def sync() -> int:
    print("Nothing to sync yet. Assistants are added in Step 2.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify API key and config only")
    args = parser.parse_args()
    return check() if args.check else sync()


if __name__ == "__main__":
    sys.exit(main())
