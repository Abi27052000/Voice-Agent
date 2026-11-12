"""Hosted-demo settings: public dashboard mode, startup seeding, and IDs from env."""

import json

from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.models import Appointment, Lead
from app.db.session import SessionLocal
from app.services.demo_seed import OLD_CUSTOMERS, seed_demo_data
from app.services.vapi_ids import get_id

PROXIED = {"X-Forwarded-For": "203.0.113.9"}


def test_dashboard_blocked_through_proxy_by_default(client):
    assert client.get("/api/stats", headers=PROXIED).status_code == 403


def test_public_demo_opens_dashboard_behind_cloud_run(client, monkeypatch):
    # Cloud Run adds X-Forwarded-For to every request, so the dev guard must be off here.
    monkeypatch.setattr(get_settings(), "public_demo", True)
    for path in ("/api/stats", "/api/calls", "/api/leads", "/api/win-back"):
        assert client.get(path, headers=PROXIED).status_code == 200, path


def test_webhook_still_requires_secret_in_public_demo(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "public_demo", True)
    res = client.post("/api/vapi/webhook", json={"message": {"type": "status-update"}}, headers=PROXIED)
    assert res.status_code == 401


def test_seed_demo_data_fills_empty_db_once(client):
    with SessionLocal() as s:
        seed_demo_data(s)
        seed_demo_data(s)  # second run must not duplicate anything
        assert s.scalar(select(func.count(Appointment.id))) == 5
        assert s.scalar(select(func.count(Lead.id)).where(Lead.source == "old_list")) == len(OLD_CUSTOMERS)


def test_vapi_ids_can_come_from_env(monkeypatch):
    monkeypatch.setattr(get_settings(), "vapi_ids_json", json.dumps({"assistant": {"receptionist": "asst-env"}}))
    assert get_id("assistant", "receptionist") == "asst-env"
