"""Local store for the IDs of Vapi resources created by scripts/sync_vapi.py.

The file (backend/vapi/ids.json) is account-specific, so it's gitignored.
Shape: {"assistant": {"receptionist": "<id>"}, "tool": {...}, ...}
"""

import json
from pathlib import Path

VAPI_DIR = Path(__file__).resolve().parents[2] / "vapi"
IDS_FILE = VAPI_DIR / "ids.json"


def load_ids() -> dict[str, dict[str, str]]:
    if not IDS_FILE.exists():
        return {}
    return json.loads(IDS_FILE.read_text(encoding="utf-8"))


def save_ids(ids: dict[str, dict[str, str]]) -> None:
    IDS_FILE.write_text(json.dumps(ids, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_id(kind: str, key: str) -> str | None:
    return load_ids().get(kind, {}).get(key)
