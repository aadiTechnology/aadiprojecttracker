"""The Aadi-Test company in Project Tracker, built from the Aadi Technology Matrix workbook (V4): its 15 people with department and monthly salary,
its 12 projects with tags, planned cost and revenue, and each person's monthly allocation to each project. Titles, roles and managers are not
in the workbook, so they are filled in sensibly (see PEOPLE). ALL NAMES ARE FICTIONAL.

    python -m app.seed_aadi_test            add the company if it is missing (safe to repeat)
    python -m app.seed_aadi_test --reset    ERASES every company and person (platform administrators stay), then adds it. Asks you to type YES

Keep PEOPLE identical to identity/app/test_tenant.py and Media/Academics/backend/app/seed_aadi_test.py (same first names, same company id).
The company is linked to Aadi Identity by IDENTITY_TENANT_ID, and each person by email on their first sign-in."""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select, text

from . import costing, core, models as m, people
from .core import hash_password
from .tenancy import seed_roles_and_modules

DATA = Path(__file__).resolve().parent / "seed_data" / "aadi_matrix.json"
NAME, SLUG = "Aadi-Test", "aadi-test"
IDENTITY_TENANT_ID = "5ca1ab1e-aad1-4e57-8000-000000000001"
DOMAIN = "aadi-test.example.com"
PASSWORD = "AadiTest@2026"

# first name: (title, Tracker role, manager first name)
PEOPLE = {
    "prajakta": ("CEO", "owner", None), "akanksha": ("Project Manager", "pm", "prajakta"), "aarti": ("Product Owner", "po", "prajakta"),
    "kalyani": ("Team Lead", "tl", "akanksha"), "namrata": ("Software Engineer", "employee", "kalyani"), "aman": ("Software Engineer", "employee", "kalyani"),
    "anjali": ("Software Engineer", "employee", "kalyani"), "prital": ("Software Engineer", "employee", "kalyani"), "anushka": ("QA Engineer", "employee", "kalyani"),
    "ankita": ("Software Engineer", "employee", "kalyani"), "manasi": ("Marketing Lead", "tl", "prajakta"), "gayatri": ("Marketing Executive", "employee", "manasi"),
    "jyoti": ("Finance Manager", "finance", "prajakta"), "dhande": ("Delivery Manager", "ops", "prajakta"), "pravin": ("Sales Lead", "sales", "prajakta"),
}
FULL = {"prajakta": "Prajakta Kulkarni", "akanksha": "Akanksha Joshi", "aarti": "Aarti Deshmukh", "kalyani": "Kalyani Patil", "namrata": "Namrata More", "aman": "Aman Shah",
        "anjali": "Anjali Rao", "prital": "Prital Naik", "anushka": "Anushka Iyer", "ankita": "Ankita Sawant", "manasi": "Manasi Gokhale", "gayatri": "Gayatri Pawar",
        "jyoti": "Jyoti Menon", "dhande": "Dhande Kamat", "pravin": "Pravin Dixit"}  # same as identity/app/test_tenant.py
HEADS = {"Management": "prajakta", "Software Development": "akanksha", "Marketing & Sales": "manasi"}
INTERNAL = {"Product", "Internship", "Aadi Technology"}  # projects for the company itself; the rest have a customer
PM_OF = {"Product": "aarti", "Internship": "akanksha"}  # everything else is run by Akanksha
CATEGORY = {"Product": "Own Product", "Internship": "Internal Growth", "Aadi Technology": "Internal Growth"}


def email_of(first: str) -> str:
    return f"{first}@{DOMAIN}"


def seed(db) -> bool:
    """Adds the company if it is missing. Returns True when something was added."""
    if db.execute(select(m.Tenant).where(m.Tenant.slug == SLUG)).scalar_one_or_none():
        return False
    data = json.loads(DATA.read_text(encoding="utf-8"))
    t = m.Tenant(name=NAME, slug=SLUG, plan="growth", is_demo=True, identity_tenant_id=os.environ.get("AADI_TEST_IDENTITY_TENANT_ID", IDENTITY_TENANT_ID),
                 monthly_hours=int(data["monthly_hours"]), hourly_rate_minor=int(data["hourly_rate"] * 100))
    db.add(t)
    db.flush()
    seed_roles_and_modules(db, t)
    pw = hash_password(PASSWORD)
    by_first = {p["name"].lower(): p for p in data["people"]}
    uid = {}
    for first, (title, role, mgr) in PEOPLE.items():
        u = m.User(email=email_of(first), name=FULL[first], password_hash=pw, status="active")
        db.add(u)
        db.flush()
        uid[first] = u.id
    dep = {d: people.create_department(db, t.id, d) for d in data["departments"]}
    for first, (title, role, mgr) in PEOPLE.items():
        p = by_first[first]
        people.add_person(db, t.id, db.get(m.User, uid[first]), role, title=title, team=p["department"], manager_user_id=uid.get(mgr),
                          department_id=dep[p["department"]].id, actor="seed")
        db.add(m.EmployeeSalary(tenant_id=t.id, user_id=uid[first], amount_minor=int(p["salary"] * 100), effective_from=date(2026, 1, 1), created_by=uid["prajakta"]))
    for dname, head in HEADS.items():
        people.set_head(db, dep[dname], uid[head])
    tag = {}
    for name in data["tags"]:
        x = m.Tag(tenant_id=t.id, name=name)
        db.add(x)
        db.flush()
        tag[name] = x.id
    cust = {}
    own = m.Customer(tenant_id=t.id, name="Aadi Technology (internal)", kind="internal", contact_name="Prajakta", contact_email=email_of("prajakta"),
                     owner_user_id=uid["prajakta"], billing_details="Internal")
    db.add(own)
    db.flush()
    month = costing.month_start()
    total_revenue = 0.0
    for i, pr in enumerate(data["projects"]):
        name = pr["name"]
        if name in INTERNAL:
            cid = own.id
        else:
            c = cust.get(name) or m.Customer(tenant_id=t.id, name=name, kind="customer", contact_name="Contact", contact_email=f"contact@{name.lower().replace(' ', '')}.example.com",
                                             owner_user_id=uid["pravin"], billing_details="Sample billing details (illustrative)")
            if name not in cust:
                db.add(c)
                db.flush()
                cust[name] = c
            cid = c.id
        pm = PM_OF.get(name, "akanksha")
        p = m.Project(tenant_id=t.id, code=f"AT-{101 + i}", name=name, category=CATEGORY.get(name, "Client Service"), customer_id=cid, pm_user_id=uid[pm], status="Active",
                      health="Green", billing_model="fixed", budget_minor=int(pr["cost"] * 100), contract_value_minor=int(pr["revenue"] * 100),
                      scope=f"{', '.join(pr['tags'])} (from the Matrix workbook; illustrative).", start_date=date(2026, 9, 1), end_date=date(2027, 3, 31))
        db.add(p)
        db.flush()
        for pos, tg in enumerate(pr["tags"]):
            db.add(m.ProjectTag(tenant_id=t.id, project_id=p.id, tag_id=tag[tg], position=pos))
        db.add(m.ProjectMember(tenant_id=t.id, project_id=p.id, user_id=uid[pm], role_label="Product Owner" if pm == "aarti" else "Project Manager"))
        db.add(m.RevenueTarget(tenant_id=t.id, level="project", project_id=p.id, month=month, amount_minor=int(round(pr["revenue"] * 100)), updated_by=uid["prajakta"]))
        total_revenue += pr["revenue"]
        for first_cap, pct in pr["allocation"].items():
            first = first_cap.lower()
            db.add(m.Allocation(tenant_id=t.id, user_id=uid[first], project_id=p.id, month=month, percent=int(pct)))
            if not db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == p.id, m.ProjectMember.user_id == uid[first])).first():
                db.add(m.ProjectMember(tenant_id=t.id, project_id=p.id, user_id=uid[first], allocation_pct=int(pct), role_label="Contributor"))
    db.add(m.RevenueTarget(tenant_id=t.id, level="org", month=month, amount_minor=int(round(total_revenue * 100)), updated_by=uid["prajakta"]))
    db.add(m.AuditEvent(tenant_id=t.id, action="seed.aadi_test", detail={"note": "Aadi-Test loaded from the Matrix workbook V4 (fictional)"}))
    return True


def wipe(db) -> dict:
    """Deletes every row of every table except the platform administrators' accounts, the migration marker and the maintenance log."""
    from sqlalchemy import delete

    counts = {}
    for table in reversed(m.Base.metadata.sorted_tables):
        if table.name in ("alembic_version", "maintenance_runs"):
            continue
        if table.name == "users":
            counts["users"] = db.execute(delete(table).where(table.c.is_platform_admin.is_(False))).rowcount
        else:
            counts[table.name] = db.execute(delete(table)).rowcount
    return {k: v for k, v in counts.items() if v}


def maintenance_once(db, maintenance_id: str) -> dict | None:
    """Wipe and seed once per id (restarting with the same id does nothing). Returns what was done, or None when this id already ran."""
    db.execute(text("CREATE TABLE IF NOT EXISTS maintenance_runs (id VARCHAR(80) PRIMARY KEY, at TIMESTAMPTZ DEFAULT now(), note TEXT)"))
    if db.execute(text("SELECT 1 FROM maintenance_runs WHERE id = :i"), {"i": maintenance_id}).first():
        db.rollback()
        return None
    counts = wipe(db)
    seeded = seed(db)
    db.execute(text("INSERT INTO maintenance_runs (id, note) VALUES (:i, :n)"), {"i": maintenance_id, "n": json.dumps({"wiped": counts, "seeded": seeded})})
    db.commit()
    return {"wiped": counts, "seeded": seeded}


def run(reset: bool = False, yes: bool = False) -> None:
    if core.ENV == "production" and os.environ.get("APP_ALLOW_TEST_SEED") != "yes":
        raise SystemExit("Refusing to seed in production. Set APP_ALLOW_TEST_SEED=yes only on purpose.")
    from .main import migrate

    migrate()
    with core.SessionLocal() as db:
        if reset:
            if not yes and input("This ERASES all companies and people in this database. Type YES to continue: ").strip() != "YES":
                raise SystemExit("Cancelled. Nothing was changed.")
            print("Erased:", wipe(db))
        added = seed(db)
        db.commit()
    print("Aadi-Test added." if added else "Aadi-Test is already there; nothing to do.", "Everyone signs in with the password", PASSWORD)


if __name__ == "__main__":
    run(reset="--reset" in sys.argv, yes="--yes" in sys.argv)
