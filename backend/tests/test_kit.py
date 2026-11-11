"""Project Tracker on the shared organisation kit. The kit's tables are the only copy of people, roles and departments; Tracker keeps a
profile row (team, monthly hours) beside them, and Identity is told about people added or suspended."""
import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy import delete, select

from app import core, identity_client, mail, models as m, org_kit, people
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
            db.execute(delete(m.KIT.Member).where(m.KIT.Member.user_id == str(u.id)))
            db.execute(delete(m.User).where(m.User.id == u.id))
        db.execute(delete(m.KIT.Member).where(m.KIT.Member.email.like("kit-test-%")))
        db.execute(delete(m.KIT.Department).where(m.KIT.Department.name.like("Kit Test%")))
        db.execute(delete(m.KIT.Role).where(m.KIT.Role.key.like("kit_test%")))
        db.execute(m.KIT.Member.__table__.update().where(m.KIT.Member.tenant_id == str(t.id)).values(status="active"))
        db.execute(m.User.__table__.update().values(status="active"))
        t.identity_tenant_id = None
        db.commit()
    identity_client.CLIENT.secret = ""


@pytest.fixture()
def sent(monkeypatch):
    box = []
    monkeypatch.setattr(mail, "send", lambda to, subject, body: box.append((to, subject, body)) or True)
    return box


# ---- one copy ---------------------------------------------------------------------------------------------------------------------------
def test_the_old_copies_are_gone_from_the_schema():
    cols = {c["name"] for c in sa.inspect(core.engine).get_columns("memberships")}
    assert cols == {"id", "tenant_id", "user_id", "team", "hours_override", "created_at"}  # only what the kit does not know
    tables = set(sa.inspect(core.engine).get_table_names())
    assert not {"roles", "departments"} & tables and {"org_roles", "org_departments", "org_members"} <= tables


def test_the_owner_sees_everyone_and_both_lists_agree(client, H):
    kit = client.get(f"{KIT}/users", headers=H("priya.rao")).json()
    legacy = client.get("/api/org/users", headers=H("priya.rao")).json()
    assert {p["email"] for p in kit} == {u["email"] for u in legacy} and len(kit) >= 13
    priya = next(p for p in kit if p["email"] == "priya.rao@aadi.demo.test")
    assert priya["role"] == "owner" and priya["status"] == "active"
    asha = next(p for p in kit if p["email"] == "asha.kulkarni@aadi.demo.test")
    assert asha["manager"] == "Vikram Shah"


def test_an_employee_cannot_see_the_people_list_but_can_reach_their_own_account(client, H):
    assert client.get(f"{KIT}/users", headers=H("meera.nair")).status_code == 403
    me = client.get(f"{KIT}/me", headers=H("meera.nair")).json()
    assert me["member"]["email"] == "meera.nair@aadi.demo.test" and "org.users.manage" not in me["caps"]


def test_org_admin_in_trackers_roles_becomes_the_kits_organisation_capabilities_and_back():
    kit = org_kit.to_kit(["org.admin", "projects.view:all"])
    assert {"org.users.manage", "org.roles.manage", "org.departments.manage", "org.users.view", "projects.view:all"} <= set(kit) and "org.admin" not in kit
    assert "org.admin" in org_kit.to_tracker(kit)
    assert "org.admin" not in org_kit.to_tracker(["org.users.manage", "projects.view:all"])
    assert "audit.view" in org_kit.to_kit(["audit.view:all"]) and "audit.view:all" in org_kit.to_tracker(["audit.view"])
    assert org_kit.to_tracker(org_kit.to_kit(["audit.view:all", "projects.view:all"])) == sorted({"audit.view:all", "projects.view:all"})


def test_the_owner_can_see_the_activity_log_in_the_kit(client, H):
    assert "audit.view" in client.get(f"{KIT}/me", headers=H("priya.rao")).json()["caps"]
    assert client.get(f"{KIT}/audit", headers=H("priya.rao")).status_code == 200


# ---- adding and changing people ---------------------------------------------------------------------------------------------------------
def test_adding_a_person_in_the_kit_creates_the_tracker_account_and_invites_them(client, H, sent):
    r = client.post(f"{KIT}/users", json={"email": "kit-test-one@example.test", "name": "Kit One", "title": "Analyst"}, headers=H("priya.rao"))
    assert r.status_code == 201 and "integration" not in r.json()  # Identity enrolment is off here
    with core.SessionLocal() as db:
        u = db.execute(select(m.User).where(m.User.email == "kit-test-one@example.test")).scalar_one()
        p = people.person(db, _tenant(db).id, u.id, live_only=False)
        assert u.status == "invited" and p.title == "Analyst" and p.status == "invited" and p.role_key == "employee"  # the least powerful role by default
        assert people.profile(db, _tenant(db).id, u.id) is not None
    assert any(to == "kit-test-one@example.test" and "invited" in s.lower() for to, s, _ in sent)
    legacy = client.get("/api/org/users", headers=H("priya.rao")).json()
    assert any(x["email"] == "kit-test-one@example.test" and x["role_key"] == "employee" for x in legacy)


def test_a_person_invited_through_trackers_own_endpoint_appears_in_the_kit_and_becomes_active_when_they_set_a_password(client, H, sent):
    r = client.post("/api/org/users", json={"email": "kit-test-two@example.test", "name": "Kit Two", "role_key": "employee", "title": "Tester", "team": "QA"}, headers=H("priya.rao"))
    assert r.status_code == 200, r.text
    kit = next(p for p in client.get(f"{KIT}/users", headers=H("priya.rao")).json() if p["email"] == "kit-test-two@example.test")
    assert (kit["status"], kit["title"], kit["role"]) == ("invited", "Tester", "employee")
    with core.SessionLocal() as db:
        u = db.execute(select(m.User).where(m.User.email == "kit-test-two@example.test")).scalar_one()
        assert people.person(db, _tenant(db).id, u.id).team == "QA"
        u.status = "active"
        people.mark_active(db, u)
        db.commit()
    kit = next(p for p in client.get(f"{KIT}/users", headers=H("priya.rao")).json() if p["email"] == "kit-test-two@example.test")
    assert kit["status"] == "active"


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
    assert client.get("/api/org/modules", headers=h).status_code == 200


def test_the_last_owner_cannot_be_suspended_or_demoted(client, H):
    priya = next(p for p in client.get(f"{KIT}/users", headers=H("priya.rao")).json() if p["email"] == "priya.rao@aadi.demo.test")
    assert client.post(f"{KIT}/users/{priya['id']}/suspend", headers=H("priya.rao")).status_code == 409
    emp = next(r for r in client.get(f"{KIT}/roles", headers=H("priya.rao")).json() if r["key"] == "employee")
    assert client.patch(f"{KIT}/users/{priya['id']}", json={"role_id": emp["id"]}, headers=H("priya.rao")).status_code == 409


# ---- departments, roles, hours ---------------------------------------------------------------------------------------------------------
def test_departments_made_in_the_kit_are_the_ones_trackers_screens_use(client, H):
    d = client.post(f"{KIT}/departments", json={"name": "Kit Test Research"}, headers=H("priya.rao"))
    assert d.status_code == 201
    listed = client.get("/api/departments", headers=H("priya.rao")).json()
    assert any(x["id"] == d.json()["id"] and x["name"] == "Kit Test Research" for x in listed)
    dev = next(u["id"] for u in client.get("/api/org/users", headers=H("priya.rao")).json() if u["email"] == "dev.patel@aadi.demo.test")
    before = next(e for e in client.get("/api/employees", headers=H("priya.rao")).json() if e["id"] == dev)["department_id"]
    assert client.patch(f"/api/employees/{dev}", json={"department_id": d.json()["id"]}, headers=H("priya.rao")).status_code == 200
    kit = next(p for p in client.get(f"{KIT}/users", headers=H("priya.rao")).json() if p["email"] == "dev.patel@aadi.demo.test")
    assert kit["department_id"] == d.json()["id"]  # one copy: the kit sees what Tracker's screen set
    client.patch(f"/api/employees/{dev}", json={"department_id": before}, headers=H("priya.rao"))
    assert client.delete(f"{KIT}/departments/{d.json()['id']}", headers=H("priya.rao")).status_code == 204
    assert not any(x["name"] == "Kit Test Research" for x in client.get("/api/departments", headers=H("priya.rao")).json())


def test_a_department_head_set_in_trackers_screen_is_the_kits_head(client, H):
    deps = client.get("/api/departments", headers=H("priya.rao")).json()
    d = next(x for x in deps if x["head_user_id"])
    kit = next(x for x in client.get(f"{KIT}/departments", headers=H("priya.rao")).json() if x["id"] == d["id"])
    assert kit["head_member_id"] is not None and d["head"]


def test_a_role_made_in_the_kit_works_in_tracker_and_salary_access_stays_with_finance(client, H):
    r = client.post(f"{KIT}/roles", json={"key": "kit_test_lead", "name": "Kit test lead", "caps": ["projects.view:assigned", "org.users.view"]}, headers=H("priya.rao"))
    assert r.status_code == 201, r.text
    assert any(x["key"] == "kit_test_lead" and "projects.view:assigned" in x["perms"] for x in client.get("/api/org/roles", headers=H("priya.rao")).json()["roles"])
    refused = client.put(f"{KIT}/roles/{r.json()['id']}", json={"caps": ["salary.view"]}, headers=H("priya.rao"))
    assert refused.status_code == 422 and "Finance" in refused.json()["detail"]["message"]
    assert client.post(f"{KIT}/roles", json={"key": "kit_test_pay", "name": "Pay", "caps": ["salary.manage"]}, headers=H("priya.rao")).status_code == 422
    assert client.delete(f"{KIT}/roles/{r.json()['id']}", headers=H("priya.rao")).status_code == 204


def test_changing_a_roles_permissions_through_trackers_endpoint_changes_what_its_people_may_do(client, H):
    roles = client.get("/api/org/roles", headers=H("priya.rao")).json()["roles"]
    emp = next(r for r in roles if r["key"] == "employee")
    before = list(emp["perms"])
    assert "customers.view:assigned" not in client.get("/api/me", headers=H("meera.nair")).json()["perms"]
    assert client.put(f"/api/org/roles/{emp['id']}", json={"perms": before + ["customers.view:assigned"]}, headers=H("priya.rao")).status_code == 200
    assert "customers.view:assigned" in client.get("/api/me", headers=H("meera.nair")).json()["perms"]
    client.put(f"/api/org/roles/{emp['id']}", json={"perms": before}, headers=H("priya.rao"))
    assert "customers.view:assigned" not in client.get("/api/me", headers=H("meera.nair")).json()["perms"]


def test_the_hours_override_lives_in_the_profile_and_reaches_the_employee_list(client, H):
    dev = next(u["id"] for u in client.get("/api/org/users", headers=H("priya.rao")).json() if u["email"] == "dev.patel@aadi.demo.test")
    assert client.put(f"/api/costing/employee-hours/{dev}", json={"hours": 120}, headers=H("priya.rao")).status_code == 200
    row = next(e for e in client.get("/api/employees", headers=H("priya.rao")).json() if e["id"] == dev)
    assert (row["hours"], row["hours_override"]) == (120, 120)
    client.put(f"/api/costing/employee-hours/{dev}", json={"hours": None}, headers=H("priya.rao"))


def test_the_catalog_lists_trackers_capabilities_by_module(client, H):
    cat = client.get(f"{KIT}/catalog", headers=H("priya.rao")).json()
    assert cat["admin_role"] == "owner" and {"sprint", "timesheet", "costing"} <= {c["feature"] for c in cat["capabilities"]}


# ---- Identity -----------------------------------------------------------------------------------------------------------------------
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
    r = client.post(f"{KIT}/users", json={"email": "kit-test-three@example.test", "name": "Kit Three"}, headers=H("priya.rao"))
    assert r.status_code == 201 and r.json()["integration"]["ok"] is True
    path, auth, body = calls[-1]
    assert path == "/api/products/enrol" and auth == "Bearer tracker-secret" and b"11111111-2222-4333-8444-555555555555" in body
    assert not any(to == "kit-test-three@example.test" for to, _, _ in sent)
    three = next(p for p in client.get(f"{KIT}/users", headers=H("priya.rao")).json() if p["email"] == "kit-test-three@example.test")
    client.post(f"{KIT}/users/{three['id']}/suspend", headers=H("priya.rao"))
    assert calls[-1][0] == "/api/products/remove"


def test_when_identity_refuses_the_person_is_still_added(client, H, sent):
    identity_client.CLIENT.http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(409, json={"detail": "All 5 seats of Aadi Project Tracker are in use"})))
    identity_client.CLIENT.base, identity_client.CLIENT.secret = "https://id.test", "tracker-secret"
    with core.SessionLocal() as db:
        _tenant(db).identity_tenant_id = "11111111-2222-4333-8444-555555555555"
        db.commit()
    r = client.post(f"{KIT}/users", json={"email": "kit-test-four@example.test", "name": "Kit Four"}, headers=H("priya.rao"))
    assert r.status_code == 201 and r.json()["integration"] == {"ok": False, "message": "All 5 seats of Aadi Project Tracker are in use"}
    with core.SessionLocal() as db:
        assert db.execute(select(m.User).where(m.User.email == "kit-test-four@example.test")).scalar_one_or_none() is not None


# ---- the retiring migration ---------------------------------------------------------------------------------------------------------
def test_the_migration_brings_the_shared_tables_up_to_date_from_the_old_ones():
    import importlib.util
    from pathlib import Path
    from datetime import datetime, timezone

    spec = importlib.util.spec_from_file_location("mig0009", Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0009_retire_old_people_tables.py")
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    eng = sa.create_engine("sqlite://")
    md = sa.MetaData()
    sa.Table("users", md, sa.Column("id", sa.Integer, primary_key=True), sa.Column("email", sa.String), sa.Column("name", sa.String), sa.Column("status", sa.String), sa.Column("identity_id", sa.String))
    sa.Table("roles", md, sa.Column("id", sa.Integer, primary_key=True), sa.Column("tenant_id", sa.Integer), sa.Column("key", sa.String), sa.Column("name", sa.String),
             sa.Column("perms", sa.JSON), sa.Column("is_system", sa.Boolean), sa.Column("kit_id", sa.Integer))
    sa.Table("departments", md, sa.Column("id", sa.Integer, primary_key=True), sa.Column("tenant_id", sa.Integer), sa.Column("name", sa.String), sa.Column("head_user_id", sa.Integer), sa.Column("kit_id", sa.Integer))
    sa.Table("memberships", md, sa.Column("id", sa.Integer, primary_key=True), sa.Column("tenant_id", sa.Integer), sa.Column("user_id", sa.Integer), sa.Column("role_id", sa.Integer),
             sa.Column("title", sa.String), sa.Column("team", sa.String), sa.Column("manager_user_id", sa.Integer), sa.Column("department_id", sa.Integer), sa.Column("status", sa.String), sa.Column("kit_id", sa.Integer))
    m.Base.metadata.create_all(eng, tables=[t for n, t in m.Base.metadata.tables.items() if n.startswith("org_")])
    md.create_all(eng)
    with eng.begin() as c:
        c.execute(sa.text("INSERT INTO users VALUES (1,'boss@x.test','Boss','active',NULL),(2,'dev@x.test','Dev','active','idp-2'),(3,'new@x.test','New','invited',NULL),(4,'gone@x.test','Gone','active',NULL)"))
        c.execute(sa.text("INSERT INTO roles (id,tenant_id,key,name,perms,is_system,kit_id) VALUES (1,7,'owner','Owner','[\"org.admin\",\"projects.view:all\"]',1,NULL),(2,7,'employee','Employee','[\"sprint.view:own\"]',1,NULL)"))
        c.execute(sa.text("INSERT INTO departments VALUES (1,7,'Eng',2,NULL)"))
        c.execute(sa.text("INSERT INTO memberships VALUES (1,7,1,1,'CEO','Lead',NULL,NULL,'active',NULL),(2,7,2,2,'Dev','A',1,1,'active',NULL),(3,7,3,2,'',  '',1,NULL,'active',NULL),(4,7,4,2,'','',NULL,NULL,'suspended',NULL)"))
        mig._bring_shared_tables_up_to_date(c)
        mig._bring_shared_tables_up_to_date(c)  # running it again changes nothing
    with eng.connect() as c:
        roles = {r.key: r for r in c.execute(sa.text("SELECT * FROM org_roles")).mappings()}
        mems = {r.email: r for r in c.execute(sa.text("SELECT * FROM org_members")).mappings()}
        depts = list(c.execute(sa.text("SELECT * FROM org_departments")).mappings())
    assert set(roles) == {"owner", "employee"} and len(mems) == 4 and len(depts) == 1
    import json
    assert "org.users.manage" in json.loads(roles["owner"].caps) and "org.admin" not in json.loads(roles["owner"].caps)
    assert (mems["dev@x.test"].title, mems["dev@x.test"].status, mems["dev@x.test"].identity_id) == ("Dev", "active", "idp-2")
    assert mems["new@x.test"].status == "invited" and mems["gone@x.test"].status == "suspended"
    assert mems["dev@x.test"].manager_id == mems["boss@x.test"].id and mems["dev@x.test"].department_id == depts[0].id
    assert depts[0].head_member_id == mems["dev@x.test"].id
    assert mems["boss@x.test"].role_id == roles["owner"].id and mems["dev@x.test"].user_id == "2"


def test_the_pinned_kit_copy_is_exactly_the_recorded_version():
    from pathlib import Path

    from aadi_org import vendoring
    assert vendoring.verify(Path(__file__).resolve().parents[1] / "aadi_org", "0.3.0") == []
