"""The Aadi-Test company built from the Matrix workbook: people, departments, salaries, tags, projects, allocations, and the one-time maintenance."""
import json

from sqlalchemy import func, select, text

import pytest

from app import core, costing, models as m, seed as demo_seed, seed_aadi_test as st


@pytest.fixture(autouse=True)
def restore_demo_data():
    """These tests erase the database; put the demo data back for the tests that run after them."""
    yield
    demo_seed.run(reset=True)


def fresh(db):
    st.wipe(db)
    db.commit()


def test_seed_matches_the_workbook(client):
    data = json.loads(st.DATA.read_text(encoding="utf-8"))
    with core.SessionLocal() as db:
        fresh(db)
        assert st.seed(db) is True
        db.commit()
        t = db.execute(select(m.Tenant).where(m.Tenant.slug == "aadi-test")).scalar_one()
        assert (t.name, t.monthly_hours, t.hourly_rate_minor, t.identity_tenant_id) == ("Aadi-Test", 160, 25000, st.IDENTITY_TENANT_ID)
        assert db.scalar(select(func.count()).select_from(m.User).where(m.User.is_platform_admin.is_(False))) == 15  # the demo platform admin stays
        sal = {u.email: s for u, s in db.execute(select(m.User, m.EmployeeSalary.amount_minor).join(m.EmployeeSalary, m.EmployeeSalary.user_id == m.User.id))}
        assert sum(sal.values()) == 270000 * 100  # the workbook's total salary
        assert sal["aarti@aadi-test.example.com"] == 30000 * 100 and sal["aman@aadi-test.example.com"] == 10000 * 100
        assert db.scalar(select(func.count()).select_from(m.Project)) == 12 and db.scalar(select(func.count()).select_from(m.Tag)) == 9
        month = costing.month_start()
        alloc = db.execute(select(m.User.email, m.Project.name, m.Allocation.percent).join(m.Allocation, m.Allocation.user_id == m.User.id)
                           .join(m.Project, m.Project.id == m.Allocation.project_id).where(m.Allocation.month == month)).all()
        got = {(e.split("@")[0], p): pct for e, p, pct in alloc}
        assert got[("kalyani", "RITe School")] == 50 and got[("namrata", "RITe School")] == 75 and got[("aman", "Product")] == 100 and got[("aarti", "Technisure")] == 100
        for per in data["projects"]:  # every allocation of the workbook is there
            for first, pct in per["allocation"].items():
                assert got[(first.lower(), per["name"])] == pct, (first, per["name"])
        per_person = {}
        for (f, _), pct in got.items():
            per_person[f] = per_person.get(f, 0) + pct
        assert max(per_person.values()) <= 100  # nobody is over-allocated
        rev = db.scalar(select(func.sum(m.RevenueTarget.amount_minor)).where(m.RevenueTarget.level == "project"))
        assert rev == sum(round(p["revenue"] * 100) for p in data["projects"])
        org = db.scalar(select(m.RevenueTarget.amount_minor).where(m.RevenueTarget.level == "org"))
        assert org == rev


def test_seed_is_repeatable_and_people_can_sign_in(client):
    with core.SessionLocal() as db:
        fresh(db)
        assert st.seed(db) is True
        db.commit()
        assert st.seed(db) is False
    for first in ("prajakta", "pravin", "jyoti"):
        r = client.post("/api/auth/login", json={"email": st.email_of(first), "password": st.PASSWORD})
        assert r.status_code == 200, r.text
    owner = client.post("/api/auth/login", json={"email": st.email_of("prajakta"), "password": st.PASSWORD}).json()["token"]
    projects = client.get("/api/projects", headers={"Authorization": "Bearer " + owner})
    assert projects.status_code == 200 and len(projects.json()) == 12


def test_maintenance_wipes_everything_but_platform_admins_and_runs_once_per_id(client):
    with core.SessionLocal() as db:
        db.add(m.User(email="root@example.com", name="Root", password_hash="x", is_platform_admin=True))
        db.commit()
        first = st.maintenance_once(db, "run-1")
        assert first and first["seeded"] is True
        assert db.scalar(select(func.count()).select_from(m.Tenant)) == 1  # the demo companies are gone
        assert "root@example.com" in db.scalars(select(m.User.email).where(m.User.is_platform_admin.is_(True))).all()  # platform administrators stay
        assert st.maintenance_once(db, "run-1") is None
        db.execute(text("DELETE FROM employee_salaries"))
        db.commit()
        assert st.maintenance_once(db, "run-1") is None and db.scalar(select(func.count()).select_from(m.EmployeeSalary)) == 0
        assert st.maintenance_once(db, "run-2")["seeded"] is True


def test_the_demo_seed_still_runs_when_aadi_test_is_there(client):
    """Production once crashed at start: the start script runs the older demo seed, which touched every demo company, Aadi-Test included."""
    with core.SessionLocal() as db:
        fresh(db)
        assert st.seed(db) is True
        db.commit()
    demo_seed.run()  # must not raise
    with core.SessionLocal() as db:
        names = {t.slug for t in db.execute(select(m.Tenant)).scalars()}
        assert "aadi-test" in names and "aadi-technology-illustrative-demo" in names
