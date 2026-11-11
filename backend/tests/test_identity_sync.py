"""Events and reconcile from Aadi Identity. Every test puts back what it changes (the database is shared across the session)."""
import json
import time
import uuid

import pytest
from sqlalchemy import select

from app import core, identity_sync, models as m

SECRET = "test-webhook-secret"
SLUG = "aadi-technology-illustrative-demo"
TENANT = {"id": "11111111-2222-4333-8444-555555555555", "slug": SLUG, "name": "Aadi", "status": "active"}


@pytest.fixture(autouse=True)
def linked(monkeypatch):
    monkeypatch.setattr(identity_sync, "WEBHOOK_SECRET", SECRET)
    with core.SessionLocal() as db:
        t = db.execute(select(m.Tenant).where(m.Tenant.slug == SLUG)).scalar_one()
        t.identity_tenant_id = TENANT["id"]
        u = db.execute(select(m.User).where(m.User.email == "dev.patel@aadi.demo.test")).scalar_one()
        u.identity_id = "user-dev-patel"
        db.commit()
    yield
    with core.SessionLocal() as db:
        db.execute(m.User.__table__.update().values(identity_id=None))
        db.execute(m.Tenant.__table__.update().values(identity_tenant_id=None))
        db.execute(m.Tenant.__table__.update().where(m.Tenant.slug == SLUG).values(status="active"))
        db.execute(m.KIT.Member.__table__.update().values(status="active"))
        db.execute(m.User.__table__.update().values(status="active"))
        db.commit()


DEV = {"id": "user-dev-patel", "email": "dev.patel@aadi.demo.test", "name": "Dev Patel", "status": "active"}


def post(client, ev, secret=SECRET, ts=None, header=None):
    body = json.dumps(ev, separators=(",", ":"))
    ts = ts or int(time.time())
    sig = header or f"t={ts},v1={identity_sync.sign(secret, ts, body)}"
    return client.post("/api/auth/identity-events", content=body, headers={"x-aadi-signature": sig, "content-type": "application/json"})


def event(type, **kw):
    return {"id": str(uuid.uuid4()), "type": type, "at": "2026-11-08T10:00:00+00:00", **kw}


def token_for(client, key):
    return {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": f"{key}@aadi.demo.test", "password": "Tracker@Demo26"}).json()["token"]}


def test_unsigned_or_wrongly_signed_events_are_refused(client):
    ev = event("user.revoked", user=DEV)
    assert post(client, ev, header="t=1,v1=bad").status_code == 401
    assert post(client, ev, secret="another-secret").status_code == 401
    assert post(client, ev, ts=int(time.time()) - 3600).status_code == 401  # replayed old delivery
    assert client.post("/api/auth/identity-events", content="{}").status_code == 401


def test_endpoint_is_off_without_a_secret(client, monkeypatch):
    monkeypatch.setattr(identity_sync, "WEBHOOK_SECRET", "")
    assert post(client, event("user.revoked", user=DEV)).status_code == 404


def test_suspended_membership_signs_the_person_out_at_once_and_reactivation_restores(client):
    h = token_for(client, "dev.patel")
    assert client.get("/api/me", headers=h).status_code == 200
    r = post(client, event("membership.suspended", tenant=TENANT, user=DEV))
    assert r.status_code == 200 and r.json()["result"] == "applied"
    refused = client.get("/api/me", headers=h)
    assert refused.status_code == 403 and refused.json()["detail"]["code"] == "NO_ACCESS"
    assert post(client, event("membership.reactivated", tenant=TENANT, user=DEV)).json()["result"] == "applied"
    assert client.get("/api/me", headers=h).status_code == 200


def test_the_same_event_twice_is_harmless(client):
    ev = event("membership.suspended", tenant=TENANT, user=DEV)
    assert post(client, ev).json()["result"] == "applied"
    assert post(client, ev).json()["result"] == "duplicate"
    post(client, event("membership.reactivated", tenant=TENANT, user=DEV))


def test_removed_member_is_suspended_not_deleted(client):
    post(client, event("membership.removed", tenant=TENANT, user=DEV))
    with core.SessionLocal() as db:
        u = db.execute(select(m.User).where(m.User.email == DEV["email"])).scalar_one()
        mem = db.execute(select(m.KIT.Member).where(m.KIT.Member.user_id == str(u.id))).scalar_one()
        assert mem.status == "suspended"  # the record, and the person's work history, stay


def test_suspended_person_loses_every_session(client):
    h = token_for(client, "dev.patel")
    assert post(client, event("user.suspended", user=DEV)).json()["result"] == "applied"
    r = client.get("/api/me", headers=h)
    assert r.status_code == 401  # token epoch moved on
    assert client.post("/api/auth/login", json={"email": DEV["email"], "password": "Tracker@Demo26"}).status_code == 401
    assert post(client, event("user.reactivated", user=DEV)).json()["result"] == "applied"
    assert client.post("/api/auth/login", json={"email": DEV["email"], "password": "Tracker@Demo26"}).status_code == 200


def test_ended_subscription_closes_the_company_and_a_new_one_reopens_it(client):
    h = token_for(client, "priya.rao")
    assert client.get("/api/me", headers=h).status_code == 200
    r = post(client, event("subscription.changed", tenant=TENANT, subscription={"product": "tracker", "status": "cancelled"}))
    assert r.json()["result"] == "applied"
    assert client.get("/api/me", headers=h).status_code == 403
    post(client, event("subscription.changed", tenant=TENANT, subscription={"product": "tracker", "status": "active"}))
    assert client.get("/api/me", headers=h).status_code == 200


def test_other_products_subscriptions_are_ignored(client):
    r = post(client, event("subscription.changed", tenant=TENANT, subscription={"product": "dms", "status": "cancelled"}))
    assert r.json()["result"] == "no change"


def test_unlinked_person_can_still_be_restricted_but_never_restored_by_email(client):
    with core.SessionLocal() as db:
        db.execute(m.User.__table__.update().values(identity_id=None))
        db.commit()
    stranger = {**DEV, "id": "not-linked-yet"}
    assert post(client, event("user.suspended", user=stranger)).json()["result"] == "applied"  # matched by e-mail: a restriction is safe
    assert post(client, event("user.reactivated", user=stranger)).json()["result"] == "no change"  # a restore needs a proven link


def test_membership_added_never_creates_a_role(client):
    r = post(client, event("membership.added", tenant=TENANT, user={"id": "x", "email": "new@aadi.demo.test", "name": "New", "status": "invited"}))
    assert r.json()["result"] == "noted"
    with core.SessionLocal() as db:
        assert db.execute(select(m.User).where(m.User.email == "new@aadi.demo.test")).first() is None


def test_reconcile_restricts_but_never_reactivates(client):
    snap = {"tenants": [{**TENANT, "subscription_status": "active", "members": [
        {"user_id": "user-dev-patel", "email": DEV["email"], "user_status": "active", "membership_status": "removed"}]}]}
    h = token_for(client, "dev.patel")
    with core.SessionLocal() as db:
        assert identity_sync.reconcile(db, snap) == {"tenants": 0, "memberships": 1, "users": 0}
    assert client.get("/api/me", headers=h).status_code == 403
    # a later snapshot that says "active" must not undo it: only an explicit reactivation event restores
    snap["tenants"][0]["members"][0]["membership_status"] = "active"
    with core.SessionLocal() as db:
        assert identity_sync.reconcile(db, snap)["memberships"] == 0
    assert client.get("/api/me", headers=h).status_code == 403
    post(client, event("membership.reactivated", tenant=TENANT, user=DEV))
    assert client.get("/api/me", headers=h).status_code == 200


def test_reconcile_suspends_company_with_ended_subscription(client):
    snap = {"tenants": [{**TENANT, "subscription_status": "cancelled", "members": []}]}
    h = token_for(client, "priya.rao")
    with core.SessionLocal() as db:
        assert identity_sync.reconcile(db, snap)["tenants"] == 1
    assert client.get("/api/me", headers=h).status_code == 403

