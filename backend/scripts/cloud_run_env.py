"""Write the Cloud Run environment file for the hosted demo from your local config.

Usage (from backend/):
    uv run python -m scripts.cloud_run_env --frontend https://<project>.web.app [--frontend ...]

Reads backend/.env and vapi/ids.json and writes data/deploy/cloud-run.env.yaml
(gitignored: it contains your Vapi keys). Then deploy with:
    gcloud run deploy ridgeway-api --source . --env-vars-file data/deploy/cloud-run.env.yaml ...

Values are plain environment variables, which is fine for a personal demo
project. For a client project, put the two secrets in Secret Manager instead.
"""

import argparse
import json
import sys

from app.core.config import get_settings
from app.services.vapi_ids import IDS_FILE, VAPI_DIR

OUT = VAPI_DIR.parent / "data" / "deploy" / "cloud-run.env.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--frontend", action="append", required=True,
                        help="frontend origin allowed by CORS, e.g. https://my-project.web.app")
    args = parser.parse_args()

    s = get_settings()
    missing = [name for name, value in {
        "VAPI_API_KEY": s.vapi_api_key, "VAPI_PUBLIC_KEY": s.vapi_public_key,
        "VAPI_WEBHOOK_SECRET": s.vapi_webhook_secret,
    }.items() if not value]
    if missing or not IDS_FILE.exists():
        print(f"[FAIL] Missing: {', '.join(missing) or 'vapi/ids.json (run scripts.sync_vapi)'}")
        return 1

    env = {
        "VAPI_API_KEY": s.vapi_api_key.get_secret_value(),
        "VAPI_PUBLIC_KEY": s.vapi_public_key,
        "VAPI_WEBHOOK_SECRET": s.vapi_webhook_secret.get_secret_value(),
        "VAPI_IDS_JSON": json.dumps(json.loads(IDS_FILE.read_text(encoding="utf-8")), separators=(",", ":")),
        "CORS_ORIGINS": json.dumps([o.rstrip("/") for o in args.frontend]),
        "PUBLIC_DEMO": "true",
        "SEED_DEMO_DATA": "true",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # JSON strings are valid YAML scalars, and json.dumps escapes everything safely.
    OUT.write_text("".join(f"{k}: {json.dumps(v)}\n" for k, v in env.items()), encoding="utf-8")
    print(f"[OK]   Wrote {OUT} ({len(env)} variables; keys not printed).")
    print(f"       CORS origins: {env['CORS_ORIGINS']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
