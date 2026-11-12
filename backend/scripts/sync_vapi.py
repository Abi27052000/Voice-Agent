"""Create or update this project's Vapi resources from the definitions in app/agents/.

Usage (from the backend/ folder):
    uv run python -m scripts.sync_vapi --check     # verify the API key and local config
    uv run python -m scripts.sync_vapi --dry-run   # show what would be created/updated
    uv run python -m scripts.sync_vapi             # create/update resources in Vapi

Sync is idempotent: a resource is matched by its saved ID (vapi/ids.json), then
by name, so running it twice updates instead of creating duplicates.
Syncing does not use Vapi credit; only calls do.
"""

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.agents import call_outcome, credential, receptionist, tools
from app.core.config import get_settings
from app.services.vapi_client import VapiClient, VapiConfigError, VapiError
from app.services.vapi_ids import load_ids, save_ids

Ids = dict[str, dict[str, str]]


@dataclass(frozen=True)
class Resource:
    kind: str  # Vapi API path segment: credential | tool | structured-output | assistant
    key: str  # local key in ids.json
    name: str  # unique name used to find it in Vapi
    build: Callable[[Ids], dict[str, Any]]


def remote_name(kind: str, item: dict[str, Any]) -> str | None:
    if kind == "tool":
        return (item.get("function") or {}).get("name")
    return item.get("name")


# Order matters: each resource may reference IDs of the ones before it.
RESOURCES: list[Resource] = [
    Resource("credential", credential.KEY, credential.NAME, credential.build),
    *[Resource("tool", key, key, build) for key, build in tools.TOOLS],
    Resource("structured-output", call_outcome.KEY, call_outcome.NAME, call_outcome.build),
    Resource("assistant", receptionist.KEY, receptionist.NAME, receptionist.build),
]


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
    if settings.webhook_url:
        print(f"       Tools will call: {settings.webhook_url}")
    return 0


def find_existing(vapi: VapiClient, res: Resource, saved_id: str | None) -> str | None:
    remote = vapi.list(res.kind, limit=1000)
    if saved_id and any(r["id"] == saved_id for r in remote):
        return saved_id
    matches = [r["id"] for r in remote if remote_name(res.kind, r) == res.name]
    if len(matches) > 1:
        raise SystemExit(f"[FAIL] {len(matches)} {res.kind}s are named '{res.name}'. Delete extras.")
    return matches[0] if matches else None


def sync(dry_run: bool) -> int:
    ids = load_ids()
    try:
        with VapiClient() as vapi:
            for res in RESOURCES:
                existing_id = find_existing(vapi, res, ids.get(res.kind, {}).get(res.key))
                action = "update" if existing_id else "create"
                if dry_run:
                    print(f"[DRY]  would {action} {res.kind} '{res.name}'")
                    if existing_id:  # later builders may need this ID
                        ids.setdefault(res.kind, {})[res.key] = existing_id
                    continue
                payload = res.build(ids)
                if existing_id:
                    result = vapi.patch(f"/{res.kind}/{existing_id}", payload)
                else:
                    result = vapi.post(f"/{res.kind}", payload)
                ids.setdefault(res.kind, {})[res.key] = result["id"]
                print(f"[OK]   {action}d {res.kind} '{res.name}' -> {result['id']}")
    except (VapiConfigError, VapiError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    finally:
        if not dry_run:
            save_ids(ids)  # keep IDs of anything created before a failure
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="verify API key and config only")
    group.add_argument("--dry-run", action="store_true", help="show changes without applying")
    args = parser.parse_args()
    return check() if args.check else sync(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
