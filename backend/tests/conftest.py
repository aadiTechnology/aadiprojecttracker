import os

os.environ["APP_ENV"] = "demo"
os.environ["LIVE_SPRINT"] = "2"  # tests cover the Sprint 2 API
os.environ["DATABASE_URL"] = "postgresql+psycopg://tracker:tracker_dev@localhost:15434/tracker_test"
import pytest
from fastapi.testclient import TestClient

from app import seed
from app.main import app


@pytest.fixture(scope="session")
def client():
    seed.run(reset=True)
    with TestClient(app) as c:
        yield c


def login(client, key, pw=seed.DEMO_PASSWORD):
    r = client.post("/api/auth/login", json={"email": f"{key}@{seed.DOMAIN}", "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture(scope="session")
def H(client):
    cache = {}

    def get(key):
        if key not in cache:
            cache[key] = login(client, key)
        return cache[key]

    return get
