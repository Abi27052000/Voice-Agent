"""Sync, run, and report the Vapi Simulation regression suites (simulations/definitions.py).

Usage (from backend/):
    uv run python -m scripts.run_simulations sync                 # create/update testers, scenarios, suites (free)
    uv run python -m scripts.run_simulations run --only routine_booking   # one smoke simulation
    uv run python -m scripts.run_simulations run                  # both suites (uses Vapi credit)
    uv run python -m scripts.run_simulations report               # wait for the last runs, write RESULTS.md

Runs use chat transport and one iteration, and every tool is mocked, so a run
never books appointments or edits leads. Sync is idempotent (matched by name).
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.vapi_client import VapiClient, VapiConfigError, VapiError
from app.services.vapi_ids import VAPI_DIR, load_ids, save_ids
from simulations import definitions as d

RUNS_FILE = VAPI_DIR.parent / "data" / "simulations" / "last_runs.json"
RESULTS_FILE = Path(d.__file__).with_name("RESULTS.md")
POLL_SECONDS, TIMEOUT_SECONDS = 10, 15 * 60


def upsert(vapi: VapiClient, ids: dict, path: str, kind: str, key: str, payload: dict) -> str:
    remote = vapi.list(path, limit=100)
    saved = ids.get(kind, {}).get(key)
    existing = saved if any(r["id"] == saved for r in remote) else next(
        (r["id"] for r in remote if r.get("name") == payload["name"]), None)
    result = vapi.patch(f"/{path}/{existing}", payload) if existing else vapi.post(f"/{path}", payload)
    ids.setdefault(kind, {})[key] = result["id"]
    print(f"[OK]   {'updated' if existing else 'created'} {kind} '{payload['name']}'")
    return result["id"]


def personality_id(ids: dict, key: str) -> str:
    return d.COOPERATIVE_CASEY_ID if key == "casey" else ids["sim-personality"][key]


def target(ids: dict, suite_key: str) -> dict[str, str]:
    kind, key = d.SUITES[suite_key]["target"]
    if kind == "squad":
        return {"type": "squad", "squadId": ids["squad"][key]}
    return {"type": "assistant", "assistantId": ids["assistant"][key]}


def sync(vapi: VapiClient) -> None:
    ids = load_ids()
    try:
        for key, payload in d.PERSONALITIES.items():
            upsert(vapi, ids, "eval/simulation/personality", "sim-personality", key, payload)
        for s in d.SCENARIOS:
            upsert(vapi, ids, "eval/simulation/scenario", "sim-scenario", s.key, s.payload())
            upsert(vapi, ids, "eval/simulation", "simulation", s.key, {
                "name": f"{s.name} [{s.personality}]",
                "scenarioId": ids["sim-scenario"][s.key],
                "personalityId": personality_id(ids, s.personality),
            })
        for suite_key, suite in d.SUITES.items():
            t = target(ids, suite_key)
            upsert(vapi, ids, "eval/simulation/suite", "sim-suite", suite_key, {
                "name": suite["name"],
                "simulationIds": [ids["simulation"][s.key] for s in d.SCENARIOS if s.suite == suite_key],
                "targetAssignments": [{"targetType": t["type"], "targetId": next(iter(v for k, v in t.items() if k != "type"))}],
            })
    finally:
        save_ids(ids)


def run(vapi: VapiClient, only: str | None) -> None:
    ids = load_ids()
    runs = []
    if only:
        scenario = next(s for s in d.SCENARIOS if s.key == only)
        groups = [(scenario.suite, [{"type": "simulation", "simulationId": ids["simulation"][only]}])]
    else:
        groups = [(k, [{"type": "simulationSuite", "simulationSuiteId": ids["sim-suite"][k]}]) for k in d.SUITES]

    for suite_key, simulations in groups:
        body = {"simulations": simulations, "target": target(ids, suite_key), "iterations": 1,
                "transport": {"provider": "vapi.webchat"}}
        result = vapi.post("/eval/simulation/run", body)
        runs.append({"id": result["id"], "suite": suite_key, "only": only})
        print(f"[OK]   started run {result['id']} ({only or d.SUITES[suite_key]['name']}, chat, 1 iteration)")
        if result.get("url"):
            print(f"       {result['url']}")
    RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUNS_FILE.write_text(json.dumps(runs, indent=2), encoding="utf-8")


def wait_for(vapi: VapiClient, run_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while True:
        group = vapi.get(f"/eval/simulation/run/{run_id}")
        if group.get("status") == "ended" or time.monotonic() > deadline:
            return group
        print(f"       run {run_id[:8]}: {group.get('status')} {group.get('itemCounts', '')}")
        time.sleep(POLL_SECONDS)


def scenario_name(ids: dict, item: dict) -> str:
    by_sim = {v: k for k, v in ids.get("simulation", {}).items()}
    key = by_sim.get(item.get("simulationId", ""))
    scenario = next((s for s in d.SCENARIOS if s.key == key), None)
    return scenario.name if scenario else (item.get("simulationId") or item.get("id", "?"))


def report(vapi: VapiClient) -> int:
    ids = load_ids()
    runs = json.loads(RUNS_FILE.read_text(encoding="utf-8")) if RUNS_FILE.exists() else []
    if not runs:
        print("[FAIL] No runs recorded. Use: run")
        return 1

    lines = ["# Simulation results", "",
             f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · chat transport · 1 iteration · all tools mocked", ""]
    all_passed = True
    for r in runs:
        group = wait_for(vapi, r["id"])
        items = vapi.list(f"eval/simulation/run/{r['id']}/item", limit=100)
        counts = group.get("itemCounts") or {}
        title = d.SUITES[r["suite"]]["name"] + (f" (only: {r['only']})" if r.get("only") else "")
        lines += [f"## {title}", "", f"Run `{r['id']}` · status `{group.get('status')}` · items {counts}", "",
                  "| Scenario | Result | Checks |", "|---|---|---|"]
        print(f"\n== {title}: {group.get('status')} {counts}")
        if not items:
            all_passed = False
        for item in items:
            results = item.get("results") or {}
            passed = bool(results.get("passed")) and item.get("status") not in ("failed", "canceled")
            all_passed &= passed
            checks = []
            for ev in results.get("evaluations") or []:
                ok = "✅" if ev.get("passed") else ("⏭️" if ev.get("isSkipped") else "❌")
                checks.append(f"{ok} {ev.get('name')}: got `{ev.get('extractedValue')}`, "
                              f"want {ev.get('comparator', '=')} `{ev.get('expectedValue')}`"
                              + (f" ({ev.get('error') or ev.get('skipReason')})" if ev.get("error") or ev.get("skipReason") else ""))
            if item.get("failureReason"):
                checks.append(f"⚠️ {item['failureReason']}")
            name = scenario_name(ids, item)
            lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {'<br>'.join(checks) or '—'} |")
            print(f"  {'PASS' if passed else 'FAIL'}  {name}")
            for c in checks:
                print(f"        {c}")
        lines.append("")

    RESULTS_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[{'OK' if all_passed else 'FAIL'}]   Report written to {RESULTS_FILE}")
    return 0 if all_passed else 1


def main() -> int:
    # Windows consoles default to cp1252, which can't print the report's status icons.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync")
    p_run = sub.add_parser("run")
    p_run.add_argument("--only", choices=[s.key for s in d.SCENARIOS], help="run one simulation")
    sub.add_parser("report")
    args = parser.parse_args()
    try:
        with VapiClient() as vapi:
            if args.cmd == "sync":
                sync(vapi)
            elif args.cmd == "run":
                run(vapi, args.only)
            else:
                return report(vapi)
    except (VapiConfigError, VapiError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
