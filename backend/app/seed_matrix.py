"""Second demo organization, shaped like the "Aadi Technology Matrix" workbook (V3): functional DEPARTMENTS (Management, Software Development,
Marketing, Sales), INDUSTRY tags (Education, Security, ...), monthly allocation, and per-project revenue targets.
ALL PEOPLE, CLIENTS AND SALARIES ARE FICTIONAL. Only the structure of the workbook is reused. Demo mode only."""
from datetime import date

from sqlalchemy import select

from . import costing, models as m
from .core import hash_password
from .tenancy import seed_roles_and_modules

SLUG = "aadi-technology-matrix-demo"
NAME = "Aadi Technology Matrix (ILLUSTRATIVE DEMO)"
DOMAIN = "matrix.demo.test"
PASSWORD = "Tracker@Demo26"

# key, name, role, title, department, monthly salary (rupees), manager key, hint
PEOPLE = [
    ("rhea.kulkarni", "Rhea Kulkarni", "owner", "CEO", "Management", 30000, None, "CEO lens: whole organization, cost, margin, bench and department mix"),
    ("anil.deshpande", "Anil Deshpande", "pm", "Project Manager", "Software Development", 30000, "rhea.kulkarni", "Project Manager lens: client projects, staffing and department mix (hours only, no salary)"),
    ("tanvi.joshi", "Tanvi Joshi", "po", "Product Owner", "Software Development", 30000, "rhea.kulkarni", "Product Owner lens: own products by industry, effort and staffing (hours only)"),
    ("kunal.rane", "Kunal Rane", "employee", "Software Engineer", "Software Development", 20000, "anil.deshpande", "Employee"),
    ("neha.gokhale", "Neha Gokhale", "employee", "Software Engineer", "Software Development", 20000, "anil.deshpande", "Employee"),
    ("omkar.pawar", "Omkar Pawar", "employee", "Software Engineer", "Software Development", 10000, "anil.deshpande", "Employee"),
    ("swati.more", "Swati More", "employee", "Software Engineer", "Software Development", 20000, "anil.deshpande", "Employee"),
    ("pallavi.naik", "Pallavi Naik", "employee", "Software Engineer", "Software Development", 10000, "anil.deshpande", "Employee"),
    ("ishaan.dixit", "Ishaan Dixit", "employee", "Software Engineer", "Software Development", 10000, "anil.deshpande", "Employee on bench (no allocation this month)"),
    ("ritu.sharma", "Ritu Sharma", "employee", "QA Engineer", "Software Development", 20000, "anil.deshpande", "Employee on bench (no allocation this month)"),
    ("gauri.patil", "Gauri Patil", "tl", "Marketing Lead", "Marketing", 20000, "rhea.kulkarni", "Team lead: sees her marketing team, hours only"),
    ("meghna.shah", "Meghna Shah", "employee", "Marketing Executive", "Marketing", 10000, "gauri.patil", "Employee"),
    ("jayant.rao", "Jayant Rao", "employee", "Marketing Executive", "Marketing", 10000, "gauri.patil", "Employee"),
    ("pranav.iyer", "Pranav Iyer", "sales", "Sales Lead", "Sales", 20000, "rhea.kulkarni", "Sales: assigned customers only"),
    ("dhruv.menon", "Dhruv Menon", "employee", "Sales Executive", "Sales", 10000, "pranav.iyer", "Employee"),
]
HEADS = {"Management": "rhea.kulkarni", "Software Development": "anil.deshpande", "Marketing": "gauri.patil", "Sales": "pranav.iyer"}
INDUSTRIES = ["Education", "Technology", "Security", "Interior Design", "E-commerce", "Business Consulting", "Manufacturing"]

# code, name, category (engagement type), industry tag, customer key, pm key, status, target rupees (monthly planning value)
PROJECTS = [
    ("MTX-101", "Greenfield School Platform", "Client Service", "Education", "gf", "anil.deshpande", "Active", 100000),
    ("MTX-102", "Aadi Platform Product", "Own Product", "Technology", "own", "tanvi.joshi", "Active", 80000),
    ("MTX-103", "Campus Growth Suite", "Own Product", "Education", "own", "tanvi.joshi", "Active", 60000),
    ("MTX-104", "Kids Learning Marketing", "Client Service", "Education", "kl", "anil.deshpande", "Active", 20000),
    ("MTX-105", "Internship Programme", "Internal Growth", "Education", "own", "anil.deshpande", "Active", 60000),
    ("MTX-106", "SecureNet Solutions", "Client Service", "Security", "sn", "anil.deshpande", "Active", 40000),
    ("MTX-107", "Interior Studio Consulting", "Client Service", "Interior Design", "is", "anil.deshpande", "Active", 16000),
    ("MTX-108", "Dairy Store E-commerce", "Client Service", "E-commerce", "ds", "anil.deshpande", "Active", 54000),
    ("MTX-109", "E-commerce Starter Kit", "Own Product", "E-commerce", "own", "tanvi.joshi", "Active", 14000),
    ("MTX-110", "Aadi Brand and Website", "Internal Growth", "Technology", "own", "anil.deshpande", "Active", 14000),
    ("MTX-111", "Insurance Portal Services", "Client Service", "Business Consulting", "ip", "anil.deshpande", "Planned", 40000),
    ("MTX-112", "Enterprise Marketing Pilot", "Client Service", "Manufacturing", "em", "anil.deshpande", "Active", 4000),
]
CUSTOMERS = [("own", "Aadi Technology (internal)", "internal", "Rhea Kulkarni", "rhea.kulkarni"), ("gf", "Greenfield Academy", "customer", "Meena Apte", "pranav.iyer"),
             ("kl", "Little Steps Learning", "customer", "Rohit Das", "pranav.iyer"), ("sn", "SecureNet Systems", "customer", "Vikas Rane", "pranav.iyer"),
             ("is", "Studio Aangan", "customer", "Nikita Rao", "pranav.iyer"), ("ds", "Dairy Fresh Store", "customer", "Sandeep Joshi", "pranav.iyer"),
             ("ip", "Shield Insurance Agency", "customer", "Anuja Kale", "pranav.iyer"), ("em", "Precision Parts Works", "customer", "Girish Nene", "pranav.iyer")]
ALLOC = {  # project code: {person key: percent}; per person the total is at most 100
    "MTX-101": {"rhea.kulkarni": 5, "anil.deshpande": 25, "kunal.rane": 50, "neha.gokhale": 75, "swati.more": 100},
    "MTX-102": {"rhea.kulkarni": 5, "kunal.rane": 50, "neha.gokhale": 25, "tanvi.joshi": 100, "pallavi.naik": 25},
    "MTX-103": {"rhea.kulkarni": 5, "jayant.rao": 33, "dhruv.menon": 50, "pranav.iyer": 100},
    "MTX-104": {"rhea.kulkarni": 5, "jayant.rao": 33},
    "MTX-105": {"rhea.kulkarni": 10, "anil.deshpande": 75, "jayant.rao": 33, "dhruv.menon": 50},
    "MTX-106": {"rhea.kulkarni": 15, "meghna.shah": 50, "gauri.patil": 25},
    "MTX-107": {"rhea.kulkarni": 15, "gauri.patil": 25},
    "MTX-108": {"rhea.kulkarni": 10, "meghna.shah": 50, "gauri.patil": 25, "pallavi.naik": 50},
    "MTX-109": {"rhea.kulkarni": 10, "pallavi.naik": 25},
    "MTX-110": {"rhea.kulkarni": 10, "gauri.patil": 25},
    "MTX-112": {"rhea.kulkarni": 10},
}
ORG_TARGET = 500000
TAG_TARGETS = {"Education": 240000, "Technology": 100000, "E-commerce": 70000}


def seed_matrix(db) -> bool:
    """Adds the second demo organization if it is missing. Returns True when something was added."""
    if db.execute(select(m.Tenant).where(m.Tenant.slug == SLUG)).scalar_one_or_none():
        return False
    t = m.Tenant(name=NAME, slug=SLUG, plan="growth", is_demo=True)
    db.add(t)
    db.flush()
    roles = seed_roles_and_modules(db, t)
    pw = hash_password(PASSWORD)
    uid = {}
    for key, name, *_ in PEOPLE:
        u = m.User(email=f"{key}@{DOMAIN}", name=name, password_hash=pw)
        db.add(u)
        db.flush()
        uid[key] = u.id
    dep = {}
    for dname in HEADS:
        d = m.Department(tenant_id=t.id, name=dname)
        db.add(d)
        db.flush()
        dep[dname] = d
    for key, name, role, title, dname, salary, mgr, _ in PEOPLE:
        db.add(m.Membership(tenant_id=t.id, user_id=uid[key], role_id=roles[role].id, title=title, team=dname, manager_user_id=uid.get(mgr), department_id=dep[dname].id))
        db.add(m.EmployeeSalary(tenant_id=t.id, user_id=uid[key], amount_minor=salary * 100, effective_from=date(2026, 1, 1), created_by=uid["rhea.kulkarni"]))
    for dname, head in HEADS.items():
        dep[dname].head_user_id = uid[head]
    tag = {}
    for n in INDUSTRIES:
        x = m.Tag(tenant_id=t.id, name=n)
        db.add(x)
        db.flush()
        tag[n] = x.id
    cid = {}
    for key, name, kind, contact, owner in CUSTOMERS:
        c = m.Customer(tenant_id=t.id, name=name, kind=kind, contact_name=contact, contact_email=f"{contact.lower().replace(' ', '.')}@example.test",
                       owner_user_id=uid[owner], billing_details="Sample billing details (illustrative)")
        db.add(c)
        db.flush()
        cid[key] = c.id
    month = costing.month_start()
    pid = {}
    for code, name, cat, industry, cust, pm, status, target in PROJECTS:
        p = m.Project(tenant_id=t.id, code=code, name=name, category=cat, customer_id=cid[cust], pm_user_id=uid[pm], status=status, health="Green",
                      billing_model="fixed", scope=f"{cat} in {industry} (illustrative).", start_date=date(2026, 9, 1), end_date=date(2027, 3, 31))
        db.add(p)
        db.flush()
        pid[code] = p.id
        db.add(m.ProjectTag(tenant_id=t.id, project_id=p.id, tag_id=tag[industry], position=0))
        db.add(m.ProjectMember(tenant_id=t.id, project_id=p.id, user_id=uid[pm], role_label="Project Manager" if pm != "tanvi.joshi" else "Product Owner"))
        db.add(m.RevenueTarget(tenant_id=t.id, level="project", project_id=p.id, month=month, amount_minor=target * 100, updated_by=uid["rhea.kulkarni"]))
    for code, rows in ALLOC.items():
        for key, pct in rows.items():
            db.add(m.Allocation(tenant_id=t.id, user_id=uid[key], project_id=pid[code], month=month, percent=pct))
            if not db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == pid[code], m.ProjectMember.user_id == uid[key])).first():
                db.add(m.ProjectMember(tenant_id=t.id, project_id=pid[code], user_id=uid[key], allocation_pct=pct, role_label="Contributor"))
    db.add(m.RevenueTarget(tenant_id=t.id, level="org", month=month, amount_minor=ORG_TARGET * 100, updated_by=uid["rhea.kulkarni"]))
    for n, amount in TAG_TARGETS.items():
        db.add(m.RevenueTarget(tenant_id=t.id, level="tag", tag_id=tag[n], month=month, amount_minor=amount * 100, updated_by=uid["rhea.kulkarni"]))
    db.add(m.AuditEvent(tenant_id=t.id, action="demo.seed", detail={"note": "Illustrative matrix demo organization loaded"}))
    return True
