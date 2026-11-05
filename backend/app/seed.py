"""Illustrative demo data for Aadi Technology: software development (own products), software services (customer projects),
marketing and sales initiatives. ALL NAMES AND FIGURES ARE FICTIONAL. Demo mode only. Usage: python -m app.seed [--reset]"""
import sys
from datetime import date

from sqlalchemy import select

from . import core, models as m
from .core import hash_password
from .seed_delivery import seed_delivery
from .tenancy import seed_roles_and_modules

DEMO_PASSWORD = "Tracker@Demo26"
DOMAIN = "aadi.demo.test"
TENANT = "Aadi Technology (ILLUSTRATIVE DEMO)"
L = 10_000_000  # one lakh rupees in paise

# key, name, role, title, team, manager, what to try
USERS = [
    ("priya.rao", "Priya Rao", "owner", "CEO", "Leadership", None, "Whole organization: all projects, budgets, audit log, users and roles"),
    ("sameer.joshi", "Sameer Joshi", "finance", "Finance Manager", "Finance", None, "Budgets and contract values; no sprint or performance data"),
    ("vikram.shah", "Vikram Shah", "ops", "Delivery Manager", "Delivery", None, "All projects and delivery; budgets but no contract value"),
    ("asha.kulkarni", "Asha Kulkarni", "pm", "Project Manager (software)", "Delivery", "vikram.shah", "Only her assigned projects; can edit scope and team"),
    ("nisha.verma", "Nisha Verma", "pm", "Project Manager (marketing & services)", "Delivery", "vikram.shah", "Only her assigned projects"),
    ("rohan.mehta", "Rohan Mehta", "tl", "Team Lead, Team A", "Team A", "asha.kulkarni", "Assigned projects, no budgets or money"),
    ("meera.nair", "Meera Nair", "employee", "Software Engineer", "Team A", "rohan.mehta", "Employee: no project list; own work arrives in Sprint 2"),
    ("dev.patel", "Dev Patel", "employee", "Software Engineer", "Team A", "rohan.mehta", "Employee"),
    ("isha.kapoor", "Isha Kapoor", "employee", "Software Engineer", "Team A", "rohan.mehta", "Employee"),
    ("nina.iyer", "Nina Iyer", "employee", "Software Engineer", "Team B", "nisha.verma", "Employee"),
    ("arjun.singh", "Arjun Singh", "employee", "Designer", "Team B", "nisha.verma", "Employee"),
    ("kabir.sethi", "Kabir Sethi", "sales", "Business Development", "Sales", None, "Sees only assigned customers and contract values"),
    ("tara.menon", "Tara Menon", "sales", "Marketing & Sales Lead", "Sales", None, "Sees only assigned customers and contract values"),
]
PLATFORM = ("platform.admin", "Platform Admin", "Tenant lifecycle and entitlements only. No tenant business data.")

CUSTOMERS = [  # key, name, kind, contact, owner
    ("prod", "Aadi Software Products (internal)", "internal", "Priya Rao", "priya.rao"),
    ("mkt", "Aadi Marketing & Sales (internal)", "internal", "Tara Menon", "tara.menon"),
    ("nw", "Northwind Retail", "customer", "Anita Desai", "kabir.sethi"),
    ("lm", "Lumen Academy", "customer", "Rakesh Bhatt", "kabir.sethi"),
    ("hf", "Harbor Foods", "customer", "Sunil Kamath", "tara.menon"),
    ("ol", "Orbit Logistics", "customer", "Deepa Rao", "kabir.sethi"),
    ("sc", "Sunrise Clinics", "customer", "Dr. Farah Khan", "tara.menon"),
]

# code-key, name, category, customer, pm, status, health, billing, budget L, contract L, est h, scope, members, milestones
PROJECTS = [
    ("Aadi Project Tracker Product", "Software Development", "prod", "asha.kulkarni", "Active", "Green", "fixed", 22, 0, 1400,
     "Multi-tenant business performance and project profitability SaaS: web and mobile apps, role-based access, timesheets, invoices.",
     ["meera.nair", "dev.patel", "isha.kapoor", "rohan.mehta"], [("Foundation and access control", "Done", date(2026, 11, 6)), ("Delivery workflows", "In progress", date(2026, 12, 4)), ("Finance modules", "Planned", date(2027, 1, 15))]),
    ("Aadi SpendOS Expense Platform", "Software Development", "prod", "asha.kulkarni", "Active", "Amber", "fixed", 16, 0, 1100,
     "Configurable personal and business expense management product.",
     ["dev.patel", "isha.kapoor"], [("Production hardening", "In progress", date(2026, 11, 28)), ("Native app decision", "Planned", date(2026, 12, 15))]),
    ("Retail Portal Revamp", "Software Services", "nw", "asha.kulkarni", "Active", "Amber", "milestone", 18, 24, 900,
     "Storefront redesign, checkout, catalogue filters and admin console for Northwind Retail.",
     ["meera.nair", "dev.patel", "isha.kapoor"], [("Design sign-off", "Done", date(2026, 10, 10)), ("Checkout beta", "In progress", date(2026, 11, 20)), ("UAT and go-live", "Planned", date(2026, 12, 20))]),
    ("Learning App Pilot", "Software Services", "lm", "asha.kulkarni", "Active", "Green", "fixed", 9, 12.5, 520,
     "Quiz engine, teacher dashboard and progress reports for Lumen Academy.",
     ["meera.nair", "isha.kapoor"], [("Prototype", "Done", date(2026, 10, 1)), ("Pilot release", "In progress", date(2026, 11, 25))]),
    ("Supply Tracker", "Software Services", "ol", "nisha.verma", "Active", "Red", "time_and_material", 14, 19, 700,
     "Telemetry ingestion, driver app and live map for Orbit Logistics.",
     ["nina.iyer", "arjun.singh"], [("Architecture", "Done", date(2026, 9, 20)), ("Telemetry v1", "In progress", date(2026, 11, 12)), ("Driver app beta", "Planned", date(2026, 12, 10))]),
    ("Clinic Appointment Portal", "Software Services", "sc", "nisha.verma", "Planned", "Green", "fixed", 7, 10, 380,
     "Online appointment booking and reminders for Sunrise Clinics.",
     ["nina.iyer"], [("Discovery workshop", "Planned", date(2026, 11, 18))]),
    ("Aadi Brand and Website Relaunch", "Marketing", "mkt", "nisha.verma", "Active", "Green", "fixed", 6, 0, 320,
     "New aaditechnology.com, product pages and case studies for the three-pillar positioning.",
     ["arjun.singh", "nina.iyer"], [("Messaging and design", "Done", date(2026, 10, 25)), ("Site build", "In progress", date(2026, 11, 30))]),
    ("Harbor Foods Social Campaign", "Marketing", "hf", "nisha.verma", "Active", "Green", "time_and_material", 4, 5.5, 240,
     "Festival-season social media and email campaign for Harbor Foods.",
     ["arjun.singh"], [("Content calendar", "Done", date(2026, 10, 28)), ("Campaign launch", "In progress", date(2026, 11, 15))]),
    ("Q4 Lead-generation Campaign", "Marketing", "mkt", "nisha.verma", "On Hold", "Amber", "fixed", 3, 0, 150,
     "Webinars and LinkedIn outreach to generate qualified leads for Aadi services. On hold pending budget review.",
     ["arjun.singh"], [("Webinar series", "Planned", date(2026, 12, 5))]),
    ("Enterprise Pipeline Build-out", "Sales", "mkt", "nisha.verma", "Active", "Green", "fixed", 2.5, 0, 160,
     "Target-account list, proposal templates and CRM hygiene to reach the annual sales target.",
     ["nina.iyer"], [("Target account list", "Done", date(2026, 10, 15)), ("Proposal kit", "In progress", date(2026, 11, 22))]),
    ("Partner Referral Programme", "Sales", "mkt", "nisha.verma", "Draft", "Green", "fixed", 1.5, 0, 90,
     "Referral partners and commission rules (lightweight; no full CRM without approval).",
     [], []),
]


def run(reset=False):
    if core.ENV != "demo":
        raise SystemExit("Demo data is loaded only when APP_ENV=demo.")
    if reset:
        m.Base.metadata.drop_all(core.engine)
        with core.engine.begin() as c:
            c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        from .main import migrate
        migrate()
    with core.SessionLocal() as db:
        if db.execute(select(m.Tenant).where(m.Tenant.slug == "aadi-technology-illustrative-demo")).scalar_one_or_none():
            tt = db.execute(select(m.Tenant).where(m.Tenant.slug == "aadi-technology-illustrative-demo")).scalar_one()
            if seed_delivery(db, tt):
                db.commit()
                print("Sprint 2 demo data added to the existing demo organization.")
            else:
                print("Demo data already present; nothing to do.")
            return
        t = m.Tenant(name=TENANT, slug="aadi-technology-illustrative-demo", plan="growth", is_demo=True)
        db.add(t)
        db.flush()
        roles = seed_roles_and_modules(db, t)
        pw = hash_password(DEMO_PASSWORD)
        uid, mem = {}, {}
        for key, name, role, title, team, mgr, _ in USERS:
            u = m.User(email=f"{key}@{DOMAIN}", name=name, password_hash=pw)
            db.add(u)
            db.flush()
            uid[key] = u.id
        for key, name, role, title, team, mgr, _ in USERS:
            db.add(m.Membership(tenant_id=t.id, user_id=uid[key], role_id=roles[role].id, title=title, team=team, manager_user_id=uid.get(mgr)))
        db.add(m.User(email=f"{PLATFORM[0]}@{DOMAIN}", name=PLATFORM[1], password_hash=pw, is_platform_admin=True))
        cid = {}
        for key, name, kind, contact, owner in CUSTOMERS:
            c = m.Customer(tenant_id=t.id, name=name, kind=kind, contact_name=contact, contact_email=f"{contact.lower().replace(' ', '.').replace('dr..', '')}@example.test",
                           owner_user_id=uid[owner], billing_details="Sample billing details (illustrative)")
            db.add(c)
            db.flush()
            cid[key] = c.id
        for i, (name, cat, cust, pm, status, health, billing, bud, contract, est, scope, members, miles) in enumerate(PROJECTS):
            p = m.Project(tenant_id=t.id, code=f"PRJ-{101 + i}", name=name, category=cat, customer_id=cid[cust], pm_user_id=uid[pm], status=status, health=health,
                          billing_model=billing, scope=scope, budget_minor=int(bud * L), contract_value_minor=int(contract * L), est_hours=est,
                          start_date=date(2026, 9, 1), end_date=date(2027, 1, 31))
            db.add(p)
            db.flush()
            db.add(m.ProjectMember(tenant_id=t.id, project_id=p.id, user_id=uid[pm], role_label="Project Manager"))
            for mk in members:
                db.add(m.ProjectMember(tenant_id=t.id, project_id=p.id, user_id=uid[mk], allocation_pct=60 if len(members) > 2 else 100, role_label="Team Lead" if mk == "rohan.mehta" else "Contributor"))
            for mn, ms, due in miles:
                db.add(m.Milestone(tenant_id=t.id, project_id=p.id, name=mn, status=ms, due_date=due, amount_minor=int(contract * L / max(len(miles), 1))))
            if name == "Supply Tracker":
                db.add(m.ScopeChange(tenant_id=t.id, project_id=p.id, description="Add geofence alerts to the driver app", reason="Requested by customer after the pilot", requested_by=uid["nisha.verma"]))
        db.add(m.AuditEvent(tenant_id=t.id, action="demo.seed", detail={"note": "Illustrative demo data loaded"}))
        db.flush()
        seed_delivery(db, t)
        db.commit()
        print("Demo data loaded:", len(USERS), "users,", len(CUSTOMERS), "customers,", len(PROJECTS), "projects")


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
