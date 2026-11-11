"""The one-time export Identity uses to import Project Tracker's people. Self-contained: its own in-memory database, no PostgreSQL needed."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import core, identity_sync, models as m
from app.main import app
from app.routers import sso

SECRET = "export-test-secret"


@pytest.fixture()
def api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        t = m.Tenant(name="Acme", slug="acme")
        db.add(t)
        db.flush()
        from app import org_kit, people
        roles = org_kit.seed_roles(db, t.id)
        boss = m.User(email="anjali@aadi-live.demo.test", name="Anjali", password_hash="$2b$10$abcdefghijklmnopqrstuv")
        dev = m.User(email="dev@acme.test", name="Dev", password_hash="$2b$10$zzzzzzzzzzzzzzzzzzzzzz")
        admin = m.User(email="platform@acme.test", name="Platform", password_hash="$2b$10$yyyyyyyyyyyyyyyyyyyyyy", is_platform_admin=True)
        db.add_all([boss, dev, admin])
        db.flush()
        people.add_person(db, t.id, boss, "owner")
        people.add_person(db, t.id, dev, "employee")
        db.commit()

    def override():
        with Session() as db:
            yield db

    app.dependency_overrides[core.get_db] = override
    monkeypatch.setattr(identity_sync, "WEBHOOK_SECRET", SECRET)
    yield TestClient(app)  # no "with": start-up (migrations on the real database) is not triggered
    app.dependency_overrides.pop(core.get_db, None)


def export(api, token=SECRET):
    return api.get("/api/auth/identity-export", headers={"Authorization": f"Bearer {token}"})


def test_export_is_off_by_default(api):
    assert export(api).status_code == 404


def test_export_needs_the_switch_and_the_secret(api, monkeypatch):
    monkeypatch.setattr(sso, "EXPORT_ENABLED", True)
    assert export(api, "wrong").status_code == 401
    assert api.get("/api/auth/identity-export").status_code == 401
    monkeypatch.setattr(identity_sync, "WEBHOOK_SECRET", "")
    assert export(api).status_code == 404  # no secret configured: still off


def test_export_gives_identity_what_it_needs_and_never_the_admin_flag(api, monkeypatch):
    monkeypatch.setattr(sso, "EXPORT_ENABLED", True)
    r = export(api)
    assert r.status_code == 200
    body = r.json()
    assert [t["slug"] for t in body["tenants"]] == ["acme"]
    by_email = {u["email"]: u for u in body["users"]}
    assert set(by_email) == {"anjali@aadi-live.demo.test", "dev@acme.test"}  # the platform administrator belongs to no company
    assert by_email["anjali@aadi-live.demo.test"]["password_hash"].startswith("$2")
    assert all("is_platform_admin" not in u for u in body["users"])
    assert {mb["role_key"] for mb in body["memberships"]} == {"owner", "employee"}
    assert {"tenant_id", "user_id", "status", "role_key"} <= set(body["memberships"][0])
