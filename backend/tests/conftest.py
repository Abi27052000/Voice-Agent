import os
import tempfile

# Must be set before the app (and its DB engine) is imported. Env vars take
# precedence over backend/.env, so tests never touch real data or secrets.
_tmp_dir = tempfile.mkdtemp(prefix="voice-agent-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["VAPI_WEBHOOK_SECRET"] = "test-secret"
os.environ["PUBLIC_BASE_URL"] = "https://example.test"
os.environ["VAPI_API_KEY"] = ""  # tests must never call the real Vapi API

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

AUTH = {"Authorization": "Bearer test-secret"}


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # lifespan creates the tables
        yield c
