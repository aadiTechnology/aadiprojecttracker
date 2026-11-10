"""Project Tracker on the shared organisation kit: the two passes keep Tracker's tables and the kit identical, and Identity is told about people."""
import httpx
import pytest
from sqlalchemy import delete, select

from app import core, identity_client, mail, models as m, org_kit
from tests.conftest import login

KIT = "/api/kit/org"
SLUG = "aadi-technology-illustrative-demo"


def _tenant(db):
    return db.execute(select(m.Tenant).where(m.Tenant.slug == SLUG)).scalar_one()


@pytest.fixture(autouse=True)
def clean():
    yield
    with core.SessionLocal() as db:
        t = _tenant(db)
        for u in db.scalars(select(m.User).where(m.User.email.like("kit-test-%"))).all():
            db.execute(delete(m.AuthToken).where(m.AuthToken.user_id == u.id))
            db.execute(delete(m.Membership).where(m.Membership.user_id == u.id))
            db.execute(delete(m.User).where(m.User.id == u.id))
        db.execute(delete(m.Department).where(m.Department.name.like("Kit Test%")))
        db.execute(delete(m.Role).where(m.Role.key.like("kit_test%")))
        db.execute(delete(m.KIT.Member).where(m.KIT.Member.email.like("kit-test-%")))
        db.execute(delete(m.KIT.Department).where(m.KIT.Department.name.like("Kit Test%")))
        db.execute(delete(m.KIT.Role).where(m.KIT.Role.key.like("kit_test%")))
        db.execute(m.Membership.__table__.update().where(m.Membership.tenant_id == t.id).values(status="active"))
        db.execute(m.User.__table__.update().values(status="active"))
        t.identity_tenant_id = None
        db.commit()
    identity_client.CLIENT.secret = ""


@pytest.fixture()
def sent(monkeypatch):
    box = []
    monkeypatch.setattr(mail, "send", lambda to, subject, body: box.append((to, subject, body)) or True)
    return box


def test_the_owner_sees_everyone_and_matches_trackers_own_list(client, H):
    people = client.get(f"{KIT}/users", headers=H("priya.rao")).json()
    legacy = client.get("/api/org/users", headers=H("priya.rao")).json()
    assert {p["email"] for p in people} == {u["email"] for u in legacy} and len(people) >= 13
    priya = next(p for p in people if p["email"] == "priya.rao@aadi.demo.test")
    assert priya["role"] == "owner" and priya["status"] == "active"
    asha = next(p for p in people if p["email"] == "asha.kulkarni@aadi.demo.test")
    assert asha["manager"] == "Vikram Shah"  # reporting lines came across


def test_an_employee_cannot_see_the_people_list_but_can_reach_their_own_account(client, H):
    assert client.get(f"{KIT}/users", headers=H("meera.nair")).status_code == 403
    me = client.get(f"{KIT}/me", headers=H("meera.nair")).json()
    assert me["member"]["email"] == "meera.nair@aadi.demo.test" and "org.users.manage" not in me["caps"]


def test_org_admin_in_trackers_roles_becomes_the_kits_organisation_capabilities_and_back():
    kit = org_kit.to_kit(["org.admin", "projects.view:all"])
    assert {"org.users.manage", "org.roles.manage", "org.departments.manage", "org.users.view", "projects.view:all"} <= set(kit) and "org.admin" not in kit
    assert "org.admin" in org_kit.to_tracker(kit)
    assert "org.admin" not in org_kit.to_tracker(["org.users.manage", "projects.view:all"])  # managing people alone is not Tracker's full admin


def test_the_owner_can_see_the_activity_log_in_the_kit_and_scoped_audit_access_round_trips(client, H):
    assert "audit.view" in client.get(f"{KIT}/me", headers=H("priya.rao")).json()["caps"]  # the screen shows the Activity tab only for this exact capability
    assert client.get(f"{KIT}/audit", headers=H("priya.rao")).status_code == 200
    assert "audit.view" in org_kit.to_kit(["audit.view:all"]) and "audit.view:all" in org_kit.to_tracker(["audit.view"])
    assert org_kit.to_tracker(org_kit.to_kit(["audit.view:all", "projects.view:all"])) == sorted({"audit.view:all", "projects.view:all"})


def test_adding_a_person_in_the_kit_creates_the_tracker_account_and_invites_them(client, H, sent):
    r = client.post(f"{KIT}/users", json={"email": "kit-test-one@example.test", "name": "Kit One", "title": "Analyst"}, headers=H("priya.rao"))
    assert r.status_code == 201 and "integration" not in r.json()  # Identity enrolment is off here
    with core.SessionLocal() as db:
        u = db.execute(select(m.User).where(m.User.email == "kit-test-one@example.test")).scalar_one()
        mem = db.execute(select(m.Membership).where(m.Membership.user_id == u.id)).scalar_one()
        assert u.status == "invited" and mem.title == "Analyst" and mem.status == "active"
        assert db.get(m.Role, mem.role_id).key == "employee"  # the least powerful role by default
    assert any(to == "kit-test-one@example.test" and "invited" in s.lower() for to, s, _ in sent)  # Tracker's own invitation
    legacy = client.get("/api/org/users", headers=H("priya.rao")).json()
    assert any(x["email"] == "kit-test-one@example.test" and x["role_key"] == "employee" for x in legacy)


def test_a_change_made_through_trackers_own_screens_shows_in_the_kit(client, H):
    uid = next(u["id"] for u in client.get("/api/org/users", headers=H("priya.rao")).json() if u["email"] == "dev.patel@aadi.demo.test")
    assert client.patch(f"/api/org/users/{uid}", json={"title": "Staff Engineer"}, headers=H("priya.rao")).status_code == 200
    kit = next(p for p in client.get(f"{KIT}/users", headers=H("priya.rao")).json() if p["email"] == "dev.patel@aadi.demo.test")
    assert kit["title"] == "Staff Engineer"
    client.patch(f"/api/org/users/{uid}", json={"title": "Software Engineer"}, headers=H("priya.rao"))


def test_suspending_through_the_kit_signs_the_person_out_at_once(client, H):
    h = login(client, "isha.kapoor")
    assert client.get("/api/org/modules", headers=h).status_code == 200
    isha = next(p for p in client.get(f"{KIT}/users", headers=H("priya.rao")).json() if p["email"] == "isha.kapoor@aadi.demo.test")
    assert client.post(f"{KIT}/users/{isha['id']}/suspend", headers=H("priya.rao")).status_code == 200
    assert client.get("/api/org/modules", headers=h).status_code in (401, 403)
    assert client.post(f"{KIT}/users/{isha['id']}/reactivate", headers=H("priya.rao")).status_code == 200
    with core.SessionLocal() as db:
        u = db.execute(select(m.User).where(m.User.email == "isha.kapoor@aadi.demo.test")).scalar_one()
        assert db.execute(select(m.Membership).where(m.Membership.user_id == u.id)).scalar_one().status == "active"


def test_the_last_owner_cannot_be_suspended_or_demoted(client, H):
    priya = next(p for p in client.get(f"{KIT}/users", headers=H("priya.rao")).json() if p["email"] == "priya.rao@aadi.demo.test")
    assert client.post(f"{KIT}/users/{priya['id']}/suspend", headers=H("priya.rao")).status_code == 409
    emp = next(r for r in client.get(f"{KIT}/roles", headers=H("priya.rao")).json() if r["key"] == "employee")
    assert client.patch(f"{KIT}/users/{priya['id']}", json={"role_id": emp["id"]}, headers=H("priya.rao")).status_code == 409


def test_departments_made_in_the_kit_exist_in_tracker_and_deleting_one_unassigns_people(client, H):
    d = client.post(f"{KIT}/departments", json={"name": "Kit Test Research"}, headers=H("priya.rao"))
    assert d.status_code == 201
    with core.SessionLocal() as db:
        assert db.execute(select(m.Department).where(m.Department.name == "Kit Test Research")).scalar_one().kit_id == d.json()["id"]
    assert any(x["name"] == "Kit Test Research" for x in client.get("/api/departments", headers=H("priya.rao")).json())
    assert client.delete(f"{KIT}/departments/{d.json()['id']}", headers=H("priya.rao")).status_code == 204
    with core.SessionLocal() as db:
        assert db.execute(select(m.Department).where(m.Department.name == "Kit Test Research")).scalar_one_or_none() is None


def test_a_role_made_in_the_kit_works_in_tracker_and_salary_access_stays_with_finance(client, H):
    r = client.post(f"{KIT}/roles", json={"key": "kit_test_lead", "name": "Kit test lead", "caps": ["projects.view:assigned", "org.users.view"]}, headers=H("priya.rao"))
    assert r.status_code == 201, r.text
    with core.SessionLocal() as db:
        role = db.execute(select(m.Role).where(m.Role.key == "kit_test_lead")).scalar_one()
        assert "projects.view:assigned" in role.perms and role.kit_id == r.json()["id"]
    refused = client.put(f"{KIT}/roles/{r.json()['id']}", json={"caps": ["salary.view"]}, headers=H("priya.rao"))
    assert refused.status_code == 422 and "Finance" in refused.json()["detail"]["message"]
    assert client.post(f"{KIT}/roles", json={"key": "kit_test_pay", "name": "Pay", "caps": ["salary.manage"]}, headers=H("priya.rao")).status_code == 422
    assert client.delete(f"{KIT}/roles/{r.json()['id']}", headers=H("priya.rao")).status_code == 204
    with core.SessionLocal() as db:
        assert db.execute(select(m.Role).where(m.Role.key == "kit_test_lead")).scalar_one_or_none() is None


def test_the_roles_screen_lists_trackers_capabilities_by_module(client, H):
    cat = client.get(f"{KIT}/catalog", headers=H("priya.rao")).json()
    assert cat["admin_role"] == "owner" and {"sprint", "timesheet", "costing"} <= {c["feature"] for c in cat["capabilities"]}
    assert any(c["key"] == "projects.view" and c["scopes"] for c in cat["capabilities"])


def test_with_identity_on_the_person_is_enrolled_and_trackers_own_invitation_is_not_sent(client, H, sent):
    calls = []

    def fake(request: httpx.Request):
        calls.append((request.url.path, request.headers["authorization"], request.read()))
        return httpx.Response(200, json={"invited": True, "created": True})

    identity_client.CLIENT.http = httpx.Client(transport=httpx.MockTransport(fake))
    identity_client.CLIENT.base, identity_client.CLIENT.secret = "https://id.test", "tracker-secret"
    with core.SessionLocal() as db:
        _tenant(db).identity_tenant_id = "11111111-2222-4333-8444-555555555555"
        db.commit()
    r = client.post(f"{KIT}/users", json={"email": "kit-test-two@example.test", "name": "Kit Two"}, headers=H("priya.rao"))
    assert r.status_code == 201 and r.json()["integration"]["ok"] is True
    path, auth, body = calls[-1]
    assert path == "/api/products/enrol" and auth == "Bearer tracker-secret" and b"11111111-2222-4333-8444-555555555555" in body
    assert not any(to == "kit-test-two@example.test" for to, _, _ in sent)  # Identity sends the invitation
    two = next(p for p in client.get(f"{KIT}/users", headers=H("priya.rao")).json() if p["email"] == "kit-test-two@example.test")
    client.post(f"{KIT}/users/{two['id']}/suspend", headers=H("priya.rao"))
    assert calls[-1][0] == "/api/products/remove"


def test_when_identity_refuses_the_person_is_still_added(client, H, sent):
    identity_client.CLIENT.http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(409, json={"detail": "All 5 seats of Aadi Project Tracker are in use"})))
    identity_client.CLIENT.base, identity_client.CLIENT.secret = "https://id.test", "tracker-secret"
    with core.SessionLocal() as db:
        _tenant(db).identity_tenant_id = "11111111-2222-4333-8444-555555555555"
        db.commit()
    r = client.post(f"{KIT}/users", json={"email": "kit-test-three@example.test", "name": "Kit Three"}, headers=H("priya.rao"))
    assert r.status_code == 201 and r.json()["integration"] == {"ok": False, "message": "All 5 seats of Aadi Project Tracker are in use"}
    with core.SessionLocal() as db:
        assert db.execute(select(m.User).where(m.User.email == "kit-test-three@example.test")).scalar_one_or_none() is not None


def test_both_passes_can_run_again_without_changing_anything(client, H):
    client.get(f"{KIT}/users", headers=H("priya.rao"))
    with core.SessionLocal() as db:
        t = _tenant(db)
        before = sorted((x.email, x.role_id, x.department_id, x.manager_id, x.status, x.title) for x in db.scalars(select(m.KIT.Member).where(m.KIT.Member.tenant_id == str(t.id))))
        org_kit.push(db, t.id)
        org_kit.pull(db, t.id)
        db.commit()
        after = sorted((x.email, x.role_id, x.department_id, x.manager_id, x.status, x.title) for x in db.scalars(select(m.KIT.Member).where(m.KIT.Member.tenant_id == str(t.id))))
    assert before == after


def test_the_pinned_kit_copy_is_exactly_the_recorded_version():
    from pathlib import Path

    from aadi_org import vendoring
    assert vendoring.verify(Path(__file__).resolve().parents[1] / "aadi_org", "0.3.0") == []
