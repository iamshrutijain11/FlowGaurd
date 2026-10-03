import os
import tempfile

# Must be set before the app is imported
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only-32-bytes-minimum-hs256"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="flowguard-test-uploads-")
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["AUTO_CREATE_TABLES"] = "false"

import pytest
from fastapi.testclient import TestClient

import app.models  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


def register_and_login(client, email="investor@flowguard.app", name="Test Investor"):
    r = client.post("/api/v1/auth/register", json={"name": name, "email": email, "password": "Passw0rd!x"})
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!x"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


@pytest.fixture
def auth(client):
    return register_and_login(client)


GRIEVANCE = {
    "complaint_id": "CMP-2026-001",
    "entity_name": "Demo Brokerage Pvt Ltd",
    "issue_type": "Transaction related issue",
    "issue_description": "Trade not settled",
    "submission_date": "2026-09-20T10:00:00Z",
}


@pytest.fixture
def grievance(client, auth):
    r = client.post("/api/v1/grievances", json=GRIEVANCE, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()["data"]
