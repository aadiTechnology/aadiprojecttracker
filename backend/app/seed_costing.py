"""Sprint 3 demo data: departments, salaries, tags, monthly allocation and revenue targets. ALL FICTIONAL (illustrative salaries).
Idempotent: does nothing when the organization already has departments."""
from datetime import date

from sqlalchemy import select

from . import costing, models as m

DEPTS = {"Leadership": "priya.rao", "Finance": "sameer.joshi", "Delivery": "vikram.shah", "Engineering": "rohan.mehta", "Design & Marketing": "arjun.singh", "Sales": "kabir.sethi"}
PEOPLE = {  # user key: (department, monthly salary in rupees)
    "priya.rao": ("Leadership", 30000), "sameer.joshi": ("Finance", 20000), "vikram.shah": ("Delivery", 30000), "asha.kulkarni": ("Delivery", 30000),
    "nisha.verma": ("Delivery", 20000), "rohan.mehta": ("Engineering", 30000), "meera.nair": ("Engineering", 20000), "dev.patel": ("Engineering", 20000),
    "isha.kapoor": ("Engineering", 10000), "nina.iyer": ("Engineering", 10000), "arjun.singh": ("Design & Marketing", 10000),
    "kabir.sethi": ("Sales", 20000), "tara.menon": ("Sales", 20000)}
TAGS = ["Software", "Marketing", "Sales", "Education", "Retail", "Logistics", "Healthcare", "Internal", "Customer"]
PROJECT_TAGS = {"PRJ-101": ["Software", "Internal"], "PRJ-102": ["Software", "Internal"], "PRJ-103": ["Retail", "Customer"], "PRJ-104": ["Education", "Customer"],
                "PRJ-105": ["Logistics", "Customer"], "PRJ-106": ["Healthcare", "Customer"], "PRJ-107": ["Marketing", "Internal"], "PRJ-108": ["Marketing", "Customer"],
                "PRJ-109": ["Marketing", "Internal"], "PRJ-110": ["Sales", "Internal"], "PRJ-111": ["Sales", "Internal"]}
ALLOC = {  # user key: {project code: percent}; every row totals at most 100
    "asha.kulkarni": {"PRJ-101": 25, "PRJ-102": 25, "PRJ-103": 25, "PRJ-104": 25}, "nisha.verma": {"PRJ-105": 25, "PRJ-106": 25, "PRJ-107": 25, "PRJ-108": 25},
    "rohan.mehta": {"PRJ-101": 50, "PRJ-102": 50}, "meera.nair": {"PRJ-101": 50, "PRJ-103": 25, "PRJ-104": 25}, "dev.patel": {"PRJ-102": 50, "PRJ-103": 50},
    "isha.kapoor": {"PRJ-102": 25, "PRJ-103": 25, "PRJ-104": 50}, "nina.iyer": {"PRJ-105": 50, "PRJ-107": 25, "PRJ-110": 25},
    "arjun.singh": {"PRJ-105": 25, "PRJ-107": 50, "PRJ-108": 25}, "kabir.sethi": {"PRJ-110": 50}, "tara.menon": {"PRJ-108": 25, "PRJ-109": 25, "PRJ-110": 25},
    "priya.rao": {"PRJ-101": 25, "PRJ-107": 25}, "vikram.shah": {"PRJ-103": 25, "PRJ-105": 25}}
TARGETS = {"PRJ-103": 75000, "PRJ-104": 30000, "PRJ-105": 50000, "PRJ-108": 20000}  # rupees per month (planning targets)


def seed_costing(db, t) -> bool:
    if db.execute(select(m.Department).where(m.Department.tenant_id == t.id)).first():
        return False
    uid = {u.email.split("@")[0]: u.id for u in db.execute(select(m.User)).scalars()}
    proj = {p.code: p.id for p in db.execute(select(m.Project).where(m.Project.tenant_id == t.id)).scalars()}
    dep = {}
    for name in DEPTS:
        d = m.Department(tenant_id=t.id, name=name)
        db.add(d)
        db.flush()
        dep[name] = d
    for key, (dname, rupees) in PEOPLE.items():
        mem = db.execute(select(m.Membership).where(m.Membership.tenant_id == t.id, m.Membership.user_id == uid[key])).scalar_one()
        mem.department_id = dep[dname].id
        db.add(m.EmployeeSalary(tenant_id=t.id, user_id=uid[key], amount_minor=rupees * 100, effective_from=date(2026, 1, 1), created_by=uid["priya.rao"]))
    for name, head in DEPTS.items():
        dep[name].head_user_id = uid[head]
    tag = {}
    for name in TAGS:
        x = m.Tag(tenant_id=t.id, name=name)
        db.add(x)
        db.flush()
        tag[name] = x.id
    for code, names in PROJECT_TAGS.items():
        for i, n in enumerate(names):
            db.add(m.ProjectTag(tenant_id=t.id, project_id=proj[code], tag_id=tag[n], position=i))
    month = costing.month_start()
    for key, rows in ALLOC.items():
        for code, pct in rows.items():
            db.add(m.Allocation(tenant_id=t.id, user_id=uid[key], project_id=proj[code], month=month, percent=pct))
            if not db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == proj[code], m.ProjectMember.user_id == uid[key])).first():
                db.add(m.ProjectMember(tenant_id=t.id, project_id=proj[code], user_id=uid[key], allocation_pct=pct, role_label="Contributor"))
    for code, rupees in TARGETS.items():
        db.add(m.RevenueTarget(tenant_id=t.id, level="project", project_id=proj[code], month=month, amount_minor=rupees * 100, updated_by=uid["priya.rao"]))
    db.add(m.RevenueTarget(tenant_id=t.id, level="org", month=month, amount_minor=250000 * 100, updated_by=uid["priya.rao"]))
    return True
