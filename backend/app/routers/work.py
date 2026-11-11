"""Customers, projects, scope, milestones, members and the role-aware dashboard.
Scoping and field masking are applied here on the server; the UI never decides what a role may see."""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from .. import models as m
from ..core import Ctx, audit, ctx, err

router = APIRouter(prefix="/api", tags=["work"])
STATUSES = ["Draft", "Planned", "Active", "On Hold", "Completed", "Cancelled"]
TRANSITIONS = {"Draft": {"Planned", "Active", "Cancelled"}, "Planned": {"Active", "On Hold", "Cancelled"},
               "Active": {"On Hold", "Completed", "Cancelled"}, "On Hold": {"Active", "Cancelled"}, "Completed": set(), "Cancelled": set()}
BILLING = {"fixed", "time_and_material", "milestone"}
CATEGORIES = ["Software Development", "Software Services", "Marketing", "Sales"]


# ---------------- scoping ----------------
def assigned_project_ids(c: Ctx) -> set:
    mine = c.db.execute(select(m.ProjectMember.project_id).where(m.ProjectMember.tenant_id == c.tid, m.ProjectMember.user_id == c.user.id)).scalars().all()
    pm = c.db.execute(select(m.Project.id).where(m.Project.tenant_id == c.tid, m.Project.pm_user_id == c.user.id)).scalars().all()
    owned = c.db.execute(select(m.Project.id).join(m.Customer, m.Customer.id == m.Project.customer_id)
                         .where(m.Project.tenant_id == c.tid, m.Customer.owner_user_id == c.user.id)).scalars().all()  # account owner (sales)
    return set(mine) | set(pm) | set(owned)


def project_query(c: Ctx, cap="projects.view"):
    s = c.require(cap)
    q = select(m.Project).where(m.Project.tenant_id == c.tid)
    if s == "all":
        return q
    if s == "assigned":
        ids = assigned_project_ids(c)
        return q.where(m.Project.id.in_(ids or {-1}))
    return q.where(m.Project.id == -1)  # own/team scopes confer no project access


def get_project(c: Ctx, pid: int, cap="projects.view") -> m.Project:
    p = c.db.execute(project_query(c, cap).where(m.Project.id == pid)).scalar_one_or_none()
    if not p:  # same answer for "does not exist" and "not yours": no information leak
        raise err(404, "NOT_FOUND", "Project not found.")
    return p


def customer_query(c: Ctx):
    s = c.require("customers.view")
    q = select(m.Customer).where(m.Customer.tenant_id == c.tid)
    if s == "all":
        return q
    ids = assigned_project_ids(c)
    cust = set(c.db.execute(select(m.Project.customer_id).where(m.Project.id.in_(ids or {-1}))).scalars())
    return q.where(or_(m.Customer.owner_user_id == c.user.id, m.Customer.id.in_(cust or {-1})))


def _tags_of(c: Ctx, pids) -> dict:
    out = {}
    for pt, tg in c.db.execute(select(m.ProjectTag, m.Tag).join(m.Tag, m.Tag.id == m.ProjectTag.tag_id).where(m.ProjectTag.tenant_id == c.tid, m.ProjectTag.project_id.in_(pids or [-1])).order_by(m.ProjectTag.position)).all():
        out.setdefault(pt.project_id, []).append({"id": tg.id, "name": tg.name})
    return out


def _names(c: Ctx) -> dict:
    from .. import people
    return {p.id: p.name for p in people.people(c.db, c.tid, live_only=False).values()}


# ---------------- customers ----------------
class CustomerIn(BaseModel):
    name: str
    kind: str = "customer"
    contact_name: str = ""
    contact_email: str = ""
    billing_details: str = ""
    owner_user_id: int | None = None
    notes: str = ""
    status: str = "active"


def customer_out(x, names, c: Ctx, nproj=0):
    d = {"id": x.id, "name": x.name, "kind": x.kind, "status": x.status, "contact_name": x.contact_name, "contact_email": x.contact_email,
         "owner": names.get(x.owner_user_id), "owner_user_id": x.owner_user_id, "projects": nproj, "notes": x.notes}
    if c.has("customers.manage") or c.has("invoices.view"):
        d["billing_details"] = x.billing_details  # billing data only for roles that manage customers or invoices
    return d


@router.get("/customers")
def customers(q: str = "", c: Ctx = Depends(ctx)):
    qq = customer_query(c)
    if q:
        qq = qq.where(m.Customer.name.ilike(f"%{q}%"))
    rows = c.db.execute(qq.order_by(m.Customer.name)).scalars().all()
    counts = dict(c.db.execute(select(m.Project.customer_id, func.count()).where(m.Project.tenant_id == c.tid).group_by(m.Project.customer_id)).all())
    n = _names(c)
    return [customer_out(x, n, c, counts.get(x.id, 0)) for x in rows]


@router.post("/customers")
def add_customer(b: CustomerIn, c: Ctx = Depends(ctx)):
    c.require("customers.manage")
    if not b.name.strip() or b.kind not in ("customer", "internal"):
        raise err(422, "VALIDATION", "Enter a name; type must be customer or internal business unit.")
    dup = c.db.execute(select(m.Customer).where(m.Customer.tenant_id == c.tid, func.lower(m.Customer.name) == b.name.strip().lower())).scalar_one_or_none()
    if dup:
        raise err(409, "DUPLICATE", "A customer with this name already exists.")
    x = m.Customer(tenant_id=c.tid, **{**b.model_dump(), "name": b.name.strip()})
    c.db.add(x)
    c.db.flush()
    audit(c.db, c.tid, c.user.id, "customer.create", "customer", x.id, name=x.name)
    c.db.commit()
    return customer_out(x, _names(c), c)


@router.patch("/customers/{cid}")
def edit_customer(cid: int, b: CustomerIn, c: Ctx = Depends(ctx)):
    c.require("customers.manage")
    x = c.db.get(m.Customer, cid)
    if not x or x.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Customer not found.")
    before = {"name": x.name, "status": x.status}
    for k, v in b.model_dump().items():
        setattr(x, k, v.strip() if isinstance(v, str) and k == "name" else v)
    audit(c.db, c.tid, c.user.id, "customer.update", "customer", x.id, before=before)
    c.db.commit()
    return customer_out(x, _names(c), c)


# ---------------- projects ----------------
def project_out(c: Ctx, p: m.Project, names: dict, cust: dict, detail=False, tagmap=None):
    d = {"id": p.id, "code": p.code, "name": p.name, "customer_id": p.customer_id, "customer": cust.get(p.customer_id, ""),
         "pm": names.get(p.pm_user_id), "pm_user_id": p.pm_user_id, "status": p.status, "category": p.category}
    delivery = c.has("projects.view") and not (c.has("projects.contract") and not c.has("projects.budget") and not c.has("projects.finance"))
    if delivery:
        d.update(health=p.health, billing_model=p.billing_model, start_date=p.start_date, end_date=p.end_date, est_hours=p.est_hours)
    if c.has("projects.budget"):
        d["budget_minor"] = p.budget_minor
    if c.has("projects.finance") or c.has("projects.contract"):
        d["contract_value_minor"] = p.contract_value_minor  # expected revenue, not recognized revenue
    d["tags"] = (tagmap or {}).get(p.id, [])
    if detail:
        d["scope"] = p.scope
    return d


class ProjectIn(BaseModel):
    name: str
    customer_id: int
    pm_user_id: int | None = None
    category: str = "Software Services"
    billing_model: str = "fixed"
    start_date: date | None = None
    end_date: date | None = None
    scope: str = ""
    budget_minor: int = 0
    contract_value_minor: int = 0
    est_hours: float = 0


def _validate_project(c: Ctx, b: ProjectIn):
    if not b.name.strip():
        raise err(422, "VALIDATION", "Enter a project name.")
    if b.category not in CATEGORIES:
        raise err(422, "VALIDATION", "Unknown project category.")
    if b.billing_model not in BILLING:
        raise err(422, "VALIDATION", "Unknown billing model.")
    if b.start_date and b.end_date and b.end_date < b.start_date:
        raise err(422, "VALIDATION", "The end date cannot be before the start date.")
    if min(b.budget_minor, b.contract_value_minor, b.est_hours) < 0:
        raise err(422, "VALIDATION", "Amounts and hours cannot be negative.")
    if not c.db.execute(select(m.Customer).where(m.Customer.id == b.customer_id, m.Customer.tenant_id == c.tid)).scalar_one_or_none():
        raise err(422, "VALIDATION", "Choose a customer or internal business unit (every project needs one).")
    from .. import people
    if b.pm_user_id and not people.is_live(c.db, c.tid, b.pm_user_id):
        raise err(422, "VALIDATION", "The project manager is not an active member of this organization.")


@router.get("/projects")
def projects(q: str = "", status: str = "", category: str = "", tags: str = "", c: Ctx = Depends(ctx)):
    qq = project_query(c)
    for tid in [int(x) for x in tags.split(",") if x.strip().isdigit()]:  # every selected tag must be on the project
        qq = qq.where(m.Project.id.in_(select(m.ProjectTag.project_id).where(m.ProjectTag.tenant_id == c.tid, m.ProjectTag.tag_id == tid)))
    if q:
        qq = qq.where(or_(m.Project.name.ilike(f"%{q}%"), m.Project.code.ilike(f"%{q}%")))
    if status:
        qq = qq.where(m.Project.status == status)
    if category:
        qq = qq.where(m.Project.category == category)
    rows = c.db.execute(qq.order_by(m.Project.code)).scalars().all()
    n = _names(c)
    cust = {x.id: x.name for x in c.db.execute(select(m.Customer).where(m.Customer.tenant_id == c.tid)).scalars()}
    return [project_out(c, p, n, cust, tagmap=_tags_of(c, [p.id for p in rows])) for p in rows]


@router.post("/projects")
def add_project(b: ProjectIn, c: Ctx = Depends(ctx)):
    if c.require("projects.manage") != "all":
        raise err(403, "FORBIDDEN", "Only roles with organization-wide project management can create projects.")
    _validate_project(c, b)
    last = c.db.execute(select(func.max(m.Project.id)).where(m.Project.tenant_id == c.tid)).scalar() or 0
    n = c.db.execute(select(func.count()).select_from(m.Project).where(m.Project.tenant_id == c.tid)).scalar()
    p = m.Project(tenant_id=c.tid, code=f"PRJ-{101 + n}", status="Draft", currency=c.tenant.currency, **{**b.model_dump(), "name": b.name.strip()})
    c.db.add(p)
    c.db.flush()
    if p.pm_user_id:
        c.db.add(m.ProjectMember(tenant_id=c.tid, project_id=p.id, user_id=p.pm_user_id, role_label="Project Manager"))
    audit(c.db, c.tid, c.user.id, "project.create", "project", p.id, code=p.code)
    c.db.commit()
    return project_out(c, p, _names(c), {x.id: x.name for x in c.db.execute(select(m.Customer).where(m.Customer.tenant_id == c.tid)).scalars()}, True)


@router.get("/projects/{pid}")
def project_detail(pid: int, c: Ctx = Depends(ctx)):
    p = get_project(c, pid)
    n = _names(c)
    cust = {x.id: x.name for x in c.db.execute(select(m.Customer).where(m.Customer.tenant_id == c.tid)).scalars()}
    d = project_out(c, p, n, cust, True, _tags_of(c, [p.id]))
    d["members"] = [{"user_id": x.user_id, "name": n.get(x.user_id), "allocation_pct": x.allocation_pct, "role_label": x.role_label}
                    for x in c.db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == p.id)).scalars()]
    d["milestones"] = [{"id": x.id, "name": x.name, "due_date": x.due_date, "status": x.status,
                        **({"amount_minor": x.amount_minor} if c.has("projects.finance") or c.has("projects.budget") else {})}
                       for x in c.db.execute(select(m.Milestone).where(m.Milestone.project_id == p.id).order_by(m.Milestone.due_date)).scalars()]
    d["scope_changes"] = [{"id": x.id, "description": x.description, "reason": x.reason, "requested_by": n.get(x.requested_by),
                           "approved_by": n.get(x.approved_by), "status": x.status, "at": x.at.isoformat()}
                          for x in c.db.execute(select(m.ScopeChange).where(m.ScopeChange.project_id == p.id).order_by(m.ScopeChange.id.desc())).scalars()]
    d["can_manage"] = c.has("projects.manage") and (c.scope("projects.manage") == "all" or p.id in assigned_project_ids(c))
    d["transitions"] = sorted(TRANSITIONS[p.status]) if d["can_manage"] else []
    return d


def _manage(c: Ctx, pid: int) -> m.Project:
    c.require("projects.manage")
    return get_project(c, pid, "projects.manage")


@router.patch("/projects/{pid}")
def edit_project(pid: int, b: ProjectIn, c: Ctx = Depends(ctx)):
    p = _manage(c, pid)
    _validate_project(c, b)
    before = {"name": p.name, "budget_minor": p.budget_minor, "pm": p.pm_user_id}
    for k, v in b.model_dump().items():
        if (k == "budget_minor" and not c.has("projects.budget")) or (k == "contract_value_minor" and not (c.has("projects.finance") or c.scope("projects.manage") == "all")):
            continue  # roles that cannot see a figure cannot overwrite it blind
        setattr(p, k, v)
    if p.pm_user_id and not c.db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == p.id, m.ProjectMember.user_id == p.pm_user_id)).scalar_one_or_none():
        c.db.add(m.ProjectMember(tenant_id=c.tid, project_id=p.id, user_id=p.pm_user_id, role_label="Project Manager"))
    audit(c.db, c.tid, c.user.id, "project.update", "project", p.id, before=before)
    c.db.commit()
    return {"ok": True}


class StatusIn(BaseModel):
    status: str
    health: str | None = None


@router.post("/projects/{pid}/status")
def project_status(pid: int, b: StatusIn, c: Ctx = Depends(ctx)):
    p = _manage(c, pid)
    if b.health:
        if b.health not in ("Green", "Amber", "Red"):
            raise err(422, "VALIDATION", "Health must be Green, Amber or Red.")
        p.health = b.health
    if b.status != p.status:
        if b.status not in TRANSITIONS[p.status]:
            raise err(409, "BAD_TRANSITION", f"A {p.status} project cannot move to {b.status}.")
        if b.status == "Active" and not (p.pm_user_id and p.scope.strip()):
            raise err(409, "NOT_READY", "Before activating, assign a project manager and define the scope.")
        audit(c.db, c.tid, c.user.id, "project.status", "project", p.id, before=p.status, after=b.status)
        p.status = b.status
    c.db.commit()
    return {"ok": True, "status": p.status}


class MemberIn(BaseModel):
    user_id: int
    allocation_pct: int = 100
    role_label: str = ""


@router.post("/projects/{pid}/members")
def add_member(pid: int, b: MemberIn, c: Ctx = Depends(ctx)):
    p = _manage(c, pid)
    if not 1 <= b.allocation_pct <= 100:
        raise err(422, "VALIDATION", "Allocation must be between 1 and 100 percent.")
    from .. import people
    if not people.is_live(c.db, c.tid, b.user_id):
        raise err(422, "VALIDATION", "That person is not an active member of this organization.")
    if c.db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == p.id, m.ProjectMember.user_id == b.user_id)).scalar_one_or_none():
        raise err(409, "DUPLICATE", "Already on this project.")
    c.db.add(m.ProjectMember(tenant_id=c.tid, project_id=p.id, **b.model_dump()))
    audit(c.db, c.tid, c.user.id, "project.member_add", "project", p.id, user_id=b.user_id)
    c.db.commit()
    return {"ok": True}


@router.delete("/projects/{pid}/members/{uid}")
def remove_member(pid: int, uid: int, c: Ctx = Depends(ctx)):
    p = _manage(c, pid)
    if uid == p.pm_user_id:
        raise err(409, "PM_REQUIRED", "Change the project manager before removing them from the team.")
    row = c.db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == p.id, m.ProjectMember.user_id == uid)).scalar_one_or_none()
    if row:
        c.db.delete(row)
        audit(c.db, c.tid, c.user.id, "project.member_remove", "project", p.id, user_id=uid)
        c.db.commit()
    return {"ok": True}


class MilestoneIn(BaseModel):
    name: str
    due_date: date | None = None
    status: str = "Planned"
    amount_minor: int = 0


@router.post("/projects/{pid}/milestones")
def add_milestone(pid: int, b: MilestoneIn, c: Ctx = Depends(ctx)):
    p = _manage(c, pid)
    if not b.name.strip() or b.status not in ("Planned", "In progress", "Done") or b.amount_minor < 0:
        raise err(422, "VALIDATION", "Enter a name and a valid status.")
    c.db.add(m.Milestone(tenant_id=c.tid, project_id=p.id, name=b.name.strip(), due_date=b.due_date, status=b.status,
                         amount_minor=b.amount_minor if c.has("projects.budget") else 0))
    audit(c.db, c.tid, c.user.id, "project.milestone_add", "project", p.id, name=b.name)
    c.db.commit()
    return {"ok": True}


class ScopeIn(BaseModel):
    description: str
    reason: str = ""


@router.post("/projects/{pid}/scope-changes")
def request_scope_change(pid: int, b: ScopeIn, c: Ctx = Depends(ctx)):
    p = _manage(c, pid)
    if not b.description.strip():
        raise err(422, "VALIDATION", "Describe the change in scope.")
    x = m.ScopeChange(tenant_id=c.tid, project_id=p.id, description=b.description.strip(), reason=b.reason.strip(), requested_by=c.user.id)
    c.db.add(x)
    c.db.flush()
    audit(c.db, c.tid, c.user.id, "scope.request", "project", p.id, change_id=x.id)
    c.db.commit()
    return {"id": x.id}


class Decision(BaseModel):
    approve: bool


@router.post("/projects/{pid}/scope-changes/{sid}/decision")
def decide_scope_change(pid: int, sid: int, b: Decision, c: Ctx = Depends(ctx)):
    p = _manage(c, pid)
    x = c.db.get(m.ScopeChange, sid)
    if not x or x.project_id != p.id or x.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Scope change not found.")
    if x.status != "Requested":
        raise err(409, "DECIDED", "This scope change was already decided.")
    if x.requested_by == c.user.id and c.scope("projects.manage") != "all":
        raise err(403, "FORBIDDEN", "A scope change must be approved by someone other than the requester.")
    x.status, x.approved_by = ("Approved" if b.approve else "Rejected"), c.user.id
    if b.approve:
        p.scope = (p.scope + "\n" if p.scope else "") + f"[Change {date.today().isoformat()}] {x.description}"
    audit(c.db, c.tid, c.user.id, "scope.decision", "project", p.id, change_id=x.id, status=x.status)
    c.db.commit()
    return {"status": x.status}


# ---------------- dashboard ----------------
@router.get("/dashboard")
def dashboard(c: Ctx = Depends(ctx)):
    out = {"role": c.role.name, "scope": {"all": "Whole organization", "assigned": "Assigned projects only", "team": "Your team", "own": "Your own work"}.get(
        c.scope("projects.view") or c.scope("sprint.view") or "own", "Your own work")}
    if c.can("projects.view"):
        rows = c.db.execute(project_query(c)).scalars().all()
        out["projects"] = {"total": len(rows), "by_status": {s: sum(1 for p in rows if p.status == s) for s in STATUSES if any(p.status == s for p in rows)},
                           "health": {h: sum(1 for p in rows if p.health == h and p.status == "Active") for h in ("Green", "Amber", "Red")}}
        out["project_list"] = [{"id": p.id, "code": p.code, "name": p.name, "status": p.status, "health": p.health} for p in rows[:6]]
        if c.has("projects.budget"):
            out["budget_minor"] = sum(p.budget_minor for p in rows)
        if c.has("projects.finance") or c.has("projects.contract"):
            out["contract_value_minor"] = sum(p.contract_value_minor for p in rows)
    if c.can("customers.view"):
        out["customers"] = c.db.execute(select(func.count()).select_from(customer_query(c).subquery())).scalar()
    if c.has("org.admin") or c.has("org.users.view"):
        from .. import people
        out["people"] = people.count_live(c.db, c.tid)
    from .delivery import delivery_summary  # imported here: delivery builds on this module
    out["delivery"] = delivery_summary(c)
    from .costing import org_summary
    out["costing"] = org_summary(c)
    out["open_decisions"] = [d for d in ["Revenue basis not yet decided" if not c.tenant.revenue_basis else None,
                                         "Meaning of the S/H planning markers not yet defined" if not c.tenant.planning_markers else None] if d] if c.has("org.admin") else []
    return out


@router.get("/people")
def people(c: Ctx = Depends(ctx)):
    """Minimal directory (id, name, title) for pickers. Needs a project/customer management capability; no emails or pay data."""
    if not (c.has("projects.manage") or c.has("customers.manage") or c.has("org.admin")):
        raise err(403, "FORBIDDEN", "Your role does not allow this action.")
    from .. import people
    rows = sorted(people.people(c.db, c.tid).values(), key=lambda p: p.name)
    return [{"id": p.id, "name": p.name, "title": p.title, "team": p.team} for p in rows]
