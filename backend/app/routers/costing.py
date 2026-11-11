"""Sprint 3 (Revision 2): employees and departments, salary (restricted), project tags, costing settings, monthly allocation,
effort and cost by employee / project / tag / workbook-style matrix, revenue targets and project profitability.
Scope and masking are applied here on the server. Salary, cost, value and profit exist in a response only for roles holding
`salary.view` / `costing.cost`; everyone else never receives those numbers."""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from .. import costing as k, models as m, people
from ..core import Ctx, audit, ctx, err
from .work import assigned_project_ids

router = APIRouter(prefix="/api", tags=["costing"])
OPEN_STATUSES = ("Draft", "Planned", "Active", "On Hold")
MAX_MONEY = 10**11  # paise


def _month(s):
    try:
        return k.parse_month(s)
    except ValueError as e:
        raise err(422, "VALIDATION", str(e))


def _member(c: Ctx, uid: int) -> "people.Person":
    p = people.person(c.db, c.tid, uid)
    if not p:
        raise err(404, "NOT_FOUND", "Employee not found.")
    return p


def _project(c: Ctx, pid: int) -> m.Project:
    p = c.db.get(m.Project, pid)
    if not p or p.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Project not found.")
    return p


def visible(c: Ctx, cap: str, d: dict):
    """(employee ids, project ids, partial) the caller may see under `cap`. partial=True: totals cover only part of the picture."""
    s = c.require(cap)
    if s == "all":
        return set(d["emps"]), set(d["projects"]), False
    if s == "team":
        team = c.team_user_ids() & set(d["emps"])
        return team, {p for (u, p) in d["alloc"] if u in team}, False
    pids = assigned_project_ids(c) & set(d["projects"])
    return {u for (u, p) in d["alloc"] if p in pids}, pids, True


def _money(c: Ctx, v):
    return v if c.can("costing.cost") else None


# ---------------- departments and employees ----------------
class DeptIn(BaseModel):
    name: str
    head_user_id: int | None = None


def _check_head(c: Ctx, dept_id: int, uid: int | None):
    if uid is None:
        return
    p = people.person(c.db, c.tid, uid)
    if not p or p.department_id != dept_id:
        raise err(422, "VALIDATION", "The Head of Department must be an active employee of that department.")


@router.get("/departments")
def departments(c: Ctx = Depends(ctx)):
    c.require("employees.view")
    team = people.people(c.db, c.tid)
    counts: dict[int, int] = {}
    for p in team.values():
        counts[p.department_id] = counts.get(p.department_id, 0) + 1
    out = []
    for x in people.departments(c.db, c.tid):
        head = people.head_user_id(c.db, x)
        out.append({"id": x.id, "name": x.name, "head_user_id": head, "head": team[head].name if head in team else None, "employees": counts.get(x.id, 0)})
    return out


@router.post("/departments")
def add_department(b: DeptIn, c: Ctx = Depends(ctx)):
    c.require("departments.manage")
    name = b.name.strip()
    if not 1 <= len(name) <= 80:
        raise err(422, "VALIDATION", "Enter a department name of 1 to 80 characters.")
    if any(d.name.lower() == name.lower() for d in people.departments(c.db, c.tid)):
        raise err(409, "DUPLICATE", "A department with this name already exists.")
    x = people.create_department(c.db, c.tid, name)
    audit(c.db, c.tid, c.user.id, "department.create", "department", x.id, name=name)
    c.db.commit()
    return {"id": x.id}


@router.patch("/departments/{did}")
def edit_department(did: int, b: DeptIn, c: Ctx = Depends(ctx)):
    c.require("departments.manage")
    x = people.department(c.db, c.tid, did)
    if not x:
        raise err(404, "NOT_FOUND", "Department not found.")
    name = b.name.strip()
    if not 1 <= len(name) <= 80:
        raise err(422, "VALIDATION", "Enter a department name of 1 to 80 characters.")
    if any(d.name.lower() == name.lower() and d.id != did for d in people.departments(c.db, c.tid)):
        raise err(409, "DUPLICATE", "A department with this name already exists.")
    _check_head(c, did, b.head_user_id)
    before = {"name": x.name, "head_user_id": people.head_user_id(c.db, x)}
    x.name = name
    people.set_head(c.db, x, b.head_user_id)
    audit(c.db, c.tid, c.user.id, "department.update", "department", x.id, before=before, head_user_id=b.head_user_id)
    c.db.commit()
    return {"ok": True}


@router.get("/employees")
def employees(c: Ctx = Depends(ctx)):
    s = c.require("employees.view")
    month = k.month_start()
    d = k.load(c, month)
    emp_ids = set(d["emps"])
    if s == "team":
        emp_ids &= c.team_user_ids()
    elif s == "assigned":
        pids = assigned_project_ids(c)
        emp_ids = {u for (u, p) in d["alloc"] if p in pids} | set(c.db.execute(select(m.ProjectMember.user_id).where(m.ProjectMember.project_id.in_(pids or {-1}))).scalars())
        emp_ids &= set(d["emps"])
    depts = {x.id: x for x in people.departments(c.db, c.tid)}
    heads = people.department_heads(c.db, c.tid)
    r = k.compute(d)
    show_alloc = c.can("allocation.view") and c.scope("allocation.view") == "all"
    show_sal = c.can("salary.view")
    out = []
    for uid in sorted(emp_ids, key=lambda i: d["emps"][i]["name"]):
        e = d["emps"][uid]
        dep = depts.get(e["dept_id"])
        row = {"id": uid, "name": e["name"], "title": e["title"], "team": e["team"], "department_id": e["dept_id"], "department": dep.name if dep else None,
               "is_head": bool(dep and heads.get(dep.id) == uid), "hours": e["hours"], "hours_override": e["hours_override"]}
        if show_alloc:
            row.update(allocated_pct=r["emp"][uid]["pct"], bench_pct=r["emp"][uid]["bench_pct"])
        if show_sal:
            row.update(salary_minor=e["salary"], cost_per_hour_minor=None if e["salary"] is None else k.half_up(e["salary"], e["hours"]))
        out.append(row)
    return out


class EmpPatch(BaseModel):
    department_id: int | None = None


@router.patch("/employees/{uid}")
def edit_employee(uid: int, b: EmpPatch, c: Ctx = Depends(ctx)):
    c.require("employees.manage")
    mem = _member(c, uid)
    if b.department_id is not None and not people.department(c.db, c.tid, b.department_id):
        raise err(422, "VALIDATION", "Choose an existing department.")
    old = people.department(c.db, c.tid, mem.department_id)
    if old and people.head_user_id(c.db, old) == uid and old.id != b.department_id:
        raise err(409, "IS_HEAD", f"This person heads {old.name}. Choose another Head of Department first.")
    people.set_department(c.db, c.tid, uid, b.department_id)
    audit(c.db, c.tid, c.user.id, "employee.department", "user", uid, department_id=b.department_id)
    c.db.commit()
    return {"ok": True}


class SalaryIn(BaseModel):
    amount_minor: int
    effective_from: date


@router.put("/employees/{uid}/salary")
def set_salary(uid: int, b: SalaryIn, c: Ctx = Depends(ctx)):
    c.require("salary.manage")
    _member(c, uid)
    if not 0 < b.amount_minor <= MAX_MONEY:
        raise err(422, "VALIDATION", "Enter a monthly salary above zero.")
    existing = c.db.execute(select(m.EmployeeSalary).where(m.EmployeeSalary.tenant_id == c.tid, m.EmployeeSalary.user_id == uid, m.EmployeeSalary.effective_from == b.effective_from)).scalar_one_or_none()
    if existing:
        existing.amount_minor, existing.created_by = b.amount_minor, c.user.id
    else:
        c.db.add(m.EmployeeSalary(tenant_id=c.tid, user_id=uid, amount_minor=b.amount_minor, effective_from=b.effective_from, created_by=c.user.id))
    audit(c.db, c.tid, c.user.id, "salary.set", "user", uid, effective_from=b.effective_from.isoformat())  # the amount is deliberately not written to the audit log
    c.db.commit()
    return {"ok": True}


@router.get("/employees/{uid}/salary")
def salary_history(uid: int, c: Ctx = Depends(ctx)):
    c.require("salary.view")
    _member(c, uid)
    rows = c.db.execute(select(m.EmployeeSalary).where(m.EmployeeSalary.tenant_id == c.tid, m.EmployeeSalary.user_id == uid).order_by(m.EmployeeSalary.effective_from.desc())).scalars().all()
    return [{"effective_from": r.effective_from, "amount_minor": r.amount_minor} for r in rows]


# ---------------- tags ----------------
class TagIn(BaseModel):
    name: str | None = None
    archived: bool | None = None


@router.get("/tags")
def tags(c: Ctx = Depends(ctx)):
    if not (c.has("tags.manage") or c.has("projects.tag") or c.has("projects.view")):
        raise err(403, "FORBIDDEN", "Your role does not allow this action.")
    counts = dict(c.db.execute(select(m.ProjectTag.tag_id, func.count()).where(m.ProjectTag.tenant_id == c.tid).group_by(m.ProjectTag.tag_id)).all())
    rows = c.db.execute(select(m.Tag).where(m.Tag.tenant_id == c.tid).order_by(m.Tag.name)).scalars().all()
    return [{"id": t.id, "name": t.name, "archived": t.archived, "projects": counts.get(t.id, 0)} for t in rows]


@router.post("/tags")
def add_tag(b: TagIn, c: Ctx = Depends(ctx)):
    c.require("tags.manage")
    name = (b.name or "").strip()
    if not 1 <= len(name) <= 40:
        raise err(422, "VALIDATION", "A tag name needs 1 to 40 characters.")
    if c.db.execute(select(m.Tag).where(m.Tag.tenant_id == c.tid, func.lower(m.Tag.name) == name.lower())).first():
        raise err(409, "DUPLICATE", "A tag with this name already exists.")
    t = m.Tag(tenant_id=c.tid, name=name)
    c.db.add(t)
    c.db.flush()
    audit(c.db, c.tid, c.user.id, "tag.create", "tag", t.id, name=name)
    c.db.commit()
    return {"id": t.id}


@router.patch("/tags/{tid}")
def edit_tag(tid: int, b: TagIn, c: Ctx = Depends(ctx)):
    c.require("tags.manage")
    t = c.db.get(m.Tag, tid)
    if not t or t.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Tag not found.")
    if b.name is not None:
        name = b.name.strip()
        if not 1 <= len(name) <= 40:
            raise err(422, "VALIDATION", "A tag name needs 1 to 40 characters.")
        if c.db.execute(select(m.Tag).where(m.Tag.tenant_id == c.tid, func.lower(m.Tag.name) == name.lower(), m.Tag.id != tid)).first():
            raise err(409, "DUPLICATE", "A tag with this name already exists.")
        t.name = name
    if b.archived is not None:
        t.archived = b.archived
    audit(c.db, c.tid, c.user.id, "tag.update", "tag", t.id)
    c.db.commit()
    return {"ok": True}


class ProjectTagsIn(BaseModel):
    tag_ids: list[int]


@router.put("/projects/{pid}/tags")
def set_project_tags(pid: int, b: ProjectTagsIn, c: Ctx = Depends(ctx)):
    s = c.require("projects.tag")
    p = _project(c, pid)
    if s != "all" and pid not in assigned_project_ids(c):
        raise err(404, "NOT_FOUND", "Project not found.")
    ids = list(dict.fromkeys(b.tag_ids))
    found = {t.id for t in c.db.execute(select(m.Tag).where(m.Tag.tenant_id == c.tid, m.Tag.id.in_(ids or [-1]), m.Tag.archived.is_(False))).scalars()}
    if found != set(ids):
        raise err(422, "VALIDATION", "Every tag must be an existing, active tag.")
    for pt in c.db.execute(select(m.ProjectTag).where(m.ProjectTag.project_id == pid)).scalars():
        c.db.delete(pt)
    c.db.flush()
    for i, tid in enumerate(ids):  # first tag is the primary tag
        c.db.add(m.ProjectTag(tenant_id=c.tid, project_id=pid, tag_id=tid, position=i))
    audit(c.db, c.tid, c.user.id, "project.tags", "project", p.id, tag_ids=ids)
    c.db.commit()
    return {"ok": True}


# ---------------- settings ----------------
class SettingsIn(BaseModel):
    monthly_hours: int
    hourly_rate_minor: int


@router.get("/costing/settings")
def get_settings(c: Ctx = Depends(ctx)):
    if not (c.can("costing.settings") or c.can("costing.effort")):
        c.require("costing.effort")
    t = c.tenant
    out = {"monthly_hours": t.monthly_hours, "currency": t.currency, "can_edit": c.can("costing.settings")}
    if c.can("costing.cost") or c.can("costing.settings"):
        out["hourly_rate_minor"] = t.hourly_rate_minor
    if c.can("costing.settings"):
        d = k.load(c, k.month_start())
        out["project_rates"] = [{"project_id": p["id"], "code": p["code"], "name": p["name"], "rate_override_minor": p["rate_override"]} for p in d["projects"].values()]
        out["employee_hours"] = [{"user_id": e["id"], "name": e["name"], "hours_override": e["hours_override"]} for e in sorted(d["emps"].values(), key=lambda x: x["name"])]
    return out


@router.patch("/costing/settings")
def patch_settings(b: SettingsIn, c: Ctx = Depends(ctx)):
    c.require("costing.settings")
    if not 1 <= b.monthly_hours <= 300:
        raise err(422, "VALIDATION", "Monthly working hours must be between 1 and 300.")
    if not 0 < b.hourly_rate_minor <= MAX_MONEY:
        raise err(422, "VALIDATION", "The hourly rate must be above zero.")
    before = {"monthly_hours": c.tenant.monthly_hours, "hourly_rate_minor": c.tenant.hourly_rate_minor}
    c.tenant.monthly_hours, c.tenant.hourly_rate_minor = b.monthly_hours, b.hourly_rate_minor
    audit(c.db, c.tid, c.user.id, "costing.settings", "tenant", c.tid, before=before, after=b.model_dump())
    c.db.commit()
    return {"ok": True}


class RateIn(BaseModel):
    rate_minor: int | None = None


@router.put("/costing/project-rate/{pid}")
def project_rate(pid: int, b: RateIn, c: Ctx = Depends(ctx)):
    c.require("costing.settings")
    p = _project(c, pid)
    if b.rate_minor is not None and not 0 < b.rate_minor <= MAX_MONEY:
        raise err(422, "VALIDATION", "The hourly rate must be above zero (or empty to inherit).")
    p.rate_override_minor = b.rate_minor
    audit(c.db, c.tid, c.user.id, "costing.project_rate", "project", pid, override=b.rate_minor is not None)
    c.db.commit()
    return {"ok": True}


class HoursIn(BaseModel):
    hours: int | None = None


@router.put("/costing/employee-hours/{uid}")
def employee_hours(uid: int, b: HoursIn, c: Ctx = Depends(ctx)):
    c.require("costing.settings")
    mem = _member(c, uid)
    if b.hours is not None and not 1 <= b.hours <= 300:
        raise err(422, "VALIDATION", "Monthly hours must be between 1 and 300 (or empty to inherit).")
    people.set_hours(c.db, c.tid, uid, b.hours)
    audit(c.db, c.tid, c.user.id, "costing.employee_hours", "user", uid, override=b.hours is not None)
    c.db.commit()
    return {"ok": True}


# ---------------- allocation ----------------
class AllocIn(BaseModel):
    user_id: int
    project_id: int
    month: str | None = None
    percent: int


def _total_other(c: Ctx, uid: int, month: date, pid: int) -> int:
    return int(c.db.execute(select(func.coalesce(func.sum(m.Allocation.percent), 0)).where(
        m.Allocation.tenant_id == c.tid, m.Allocation.user_id == uid, m.Allocation.month == month, m.Allocation.project_id != pid)).scalar())


def _manage_scope_ok(c: Ctx, pid: int):
    if c.require("allocation.manage") != "all" and pid not in assigned_project_ids(c):
        raise err(404, "NOT_FOUND", "Project not found.")


@router.get("/allocations")
def allocations(month: str | None = None, c: Ctx = Depends(ctx)):
    s = c.require("allocation.view")
    mo = _month(month)
    d = k.load(c, mo)
    can_manage = c.can("allocation.manage")
    emp_ids, proj_ids, partial = visible(c, "allocation.view", d)
    if can_manage:  # people who can allocate need the whole list to see headroom
        emp_ids = set(d["emps"])
    res = k.compute(d)
    projects = [p for p in d["projects"].values() if p["status"] in OPEN_STATUSES and (s == "all" or p["id"] in proj_ids)]
    manage_ids = {p["id"] for p in projects} if c.scope("allocation.manage") == "all" else (assigned_project_ids(c) if can_manage else set())
    depts = people.department_names(c.db, c.tid)
    return {"month": mo.isoformat()[:7], "can_manage": can_manage, "partial": partial,
            "employees": [{"id": u, "name": d["emps"][u]["name"], "department": depts.get(d["emps"][u]["dept_id"]), "total_pct": res["emp"][u]["pct"],
                           "hours": round(res["emp"][u]["hours"], 2)} for u in sorted(emp_ids, key=lambda i: d["emps"][i]["name"])],
            "projects": [{"id": p["id"], "code": p["code"], "name": p["name"], "status": p["status"], "can_edit": p["id"] in manage_ids} for p in projects],
            "cells": [{"user_id": u, "project_id": p, "percent": v["pct"]} for (u, p), v in res["cells"].items() if u in emp_ids and p in {x["id"] for x in projects}]}


@router.put("/allocations")
def set_allocation(b: AllocIn, c: Ctx = Depends(ctx)):
    mo = _month(b.month)
    _manage_scope_ok(c, b.project_id)
    p = _project(c, b.project_id)
    mem = _member(c, b.user_id)
    if not isinstance(b.percent, int) or not 0 <= b.percent <= 100:
        raise err(422, "VALIDATION", "Allocation must be a whole number between 0 and 100 percent.")
    if p.status not in OPEN_STATUSES:
        raise err(409, "PROJECT_CLOSED", "This project is closed; allocation cannot change.")
    others = _total_other(c, b.user_id, mo, b.project_id)
    if others + b.percent > 100:
        name = c.db.get(m.User, b.user_id).name
        raise err(409, "OVER_ALLOCATED", f"{name} would be at {others + b.percent}% in {mo.isoformat()[:7]}. An employee cannot be allocated above 100%.")
    row = c.db.execute(select(m.Allocation).where(m.Allocation.user_id == b.user_id, m.Allocation.project_id == b.project_id, m.Allocation.month == mo)).scalar_one_or_none()
    if b.percent == 0:
        if row:
            c.db.delete(row)
    elif row:
        row.percent = b.percent
    else:
        c.db.add(m.Allocation(tenant_id=c.tid, user_id=b.user_id, project_id=b.project_id, month=mo, percent=b.percent))
    if b.percent > 0:  # allocation requires membership of the project team (BR-016)
        pm = c.db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == b.project_id, m.ProjectMember.user_id == b.user_id)).scalar_one_or_none()
        if not pm:
            c.db.add(m.ProjectMember(tenant_id=c.tid, project_id=b.project_id, user_id=b.user_id, allocation_pct=b.percent, role_label="Contributor"))
        elif mo == k.month_start():
            pm.allocation_pct = b.percent
    audit(c.db, c.tid, c.user.id, "allocation.set", "project", b.project_id, user_id=b.user_id, month=mo.isoformat()[:7], percent=b.percent)
    c.db.commit()
    return {"ok": True, "total_pct": others + b.percent}


class CopyIn(BaseModel):
    from_month: str
    to_month: str


@router.post("/allocations/copy")
def copy_allocations(b: CopyIn, c: Ctx = Depends(ctx)):
    if c.require("allocation.manage") != "all":
        raise err(403, "FORBIDDEN", "Copying a whole month needs organization-wide allocation management.")
    a, z = _month(b.from_month), _month(b.to_month)
    if a == z:
        raise err(422, "VALIDATION", "Choose two different months.")
    src = c.db.execute(select(m.Allocation).where(m.Allocation.tenant_id == c.tid, m.Allocation.month == a)).scalars().all()
    have = {(x.user_id, x.project_id) for x in c.db.execute(select(m.Allocation).where(m.Allocation.tenant_id == c.tid, m.Allocation.month == z)).scalars()}
    open_p = {p.id for p in c.db.execute(select(m.Project).where(m.Project.tenant_id == c.tid, m.Project.status.in_(OPEN_STATUSES))).scalars()}
    added = skipped = 0
    for x in src:
        if (x.user_id, x.project_id) in have or x.project_id not in open_p:
            skipped += 1
            continue
        c.db.add(m.Allocation(tenant_id=c.tid, user_id=x.user_id, project_id=x.project_id, month=z, percent=x.percent))
        added += 1
    audit(c.db, c.tid, c.user.id, "allocation.copy", "allocation", "", from_month=a.isoformat()[:7], to_month=z.isoformat()[:7], added=added)
    c.db.commit()
    return {"added": added, "skipped": skipped}


# ---------------- effort and cost reports ----------------
def _filters(d: dict, tag_ids):
    if not tag_ids:
        return None
    want = {int(x) for x in tag_ids.split(",") if x.strip().isdigit()}
    return {pid for pid, p in d["projects"].items() if want and want <= {t["id"] for t in p["tags"]}}


def _proj_row(c: Ctx, p: dict, r: dict, cost_ok: bool, tags_filter=None):
    x = r["proj"][p["id"]]
    row = {"id": p["id"], "code": p["code"], "name": p["name"], "status": p["status"], "tags": p["tags"], "people": x["people"], "hours": round(x["hours"], 2),
           "rate_overridden": p["rate_override"] is not None}
    if cost_ok:
        row.update(rate_minor=p["rate"], value_minor=x["value"], cost_minor=x["cost"], missing_salary=x["missing_salary"])
    return row


@router.get("/costing/summary")
def summary(month: str | None = None, tags: str | None = None, c: Ctx = Depends(ctx)):
    c.require("costing.effort")
    mo = _month(month)
    d = k.load(c, mo)
    emp_ids, proj_ids, partial = visible(c, "costing.effort", d)
    only = _filters(d, tags)
    if only is not None:
        proj_ids = proj_ids & only
    r = k.compute(d, emp_ids, proj_ids)
    cost_ok = c.can("costing.cost")
    out = {"month": mo.isoformat()[:7], "partial": partial, "hours": round(sum(p["hours"] for p in r["proj"].values()), 2), "projects": len(proj_ids),
           "rate_note": "Value = hours x hourly rate. It is a standard value of effort, not invoiced revenue."}
    if cost_ok and not partial:
        t = k.org_totals(d, r) if only is None else None
        if t:
            out.update(value_minor=t["value"], cost_minor=t["cost"], bench_cost_minor=t["bench_cost"], salary_pool_minor=t["salary_pool"], margin_minor=t["margin"],
                       reconciles=t["reconciles"], missing_salary=t["missing_salary"])
        else:
            out.update(value_minor=sum(p["value"] for p in r["proj"].values()), cost_minor=sum(p["cost"] for p in r["proj"].values()))
            out["margin_minor"] = out["value_minor"] - out["cost_minor"]
    return out


@router.get("/costing/employees")
def by_employee(month: str | None = None, c: Ctx = Depends(ctx)):
    c.require("costing.effort")
    mo = _month(month)
    d = k.load(c, mo)
    emp_ids, proj_ids, partial = visible(c, "costing.effort", d)
    r = k.compute(d, emp_ids, proj_ids)
    cost_ok = c.can("costing.cost") and not partial
    depts = people.department_names(c.db, c.tid)
    rows = []
    for uid in sorted(emp_ids, key=lambda i: d["emps"][i]["name"]):
        e, x = d["emps"][uid], r["emp"][uid]
        row = {"id": uid, "name": e["name"], "department": depts.get(e["dept_id"]), "hours": round(x["hours"], 2), "monthly_hours": e["hours"]}
        if not partial:
            row.update(allocated_pct=x["pct"], bench_pct=x["bench_pct"], bench_hours=round(x["bench_hours"], 2),
                       status="Over-allocated" if x["pct"] > 100 else "Fully allocated" if x["pct"] == 100 else "Bench" if x["pct"] == 0 else "Partly allocated")
        if cost_ok:
            row.update(salary_minor=e["salary"], cost_minor=x["cost"], bench_cost_minor=x["bench_cost"],
                       cost_per_hour_minor=None if e["salary"] is None else k.half_up(e["salary"], e["hours"]), missing_salary=e["salary"] is None)
        rows.append(row)
    return {"month": mo.isoformat()[:7], "partial": partial, "rows": rows}


@router.get("/costing/projects")
def by_project(month: str | None = None, tags: str | None = None, c: Ctx = Depends(ctx)):
    c.require("costing.effort")
    mo = _month(month)
    d = k.load(c, mo)
    emp_ids, proj_ids, partial = visible(c, "costing.effort", d)
    only = _filters(d, tags)
    if only is not None:
        proj_ids = proj_ids & only
    r = k.compute(d, emp_ids, proj_ids)
    cost_ok = c.can("costing.cost") and not partial
    rows = [_proj_row(c, d["projects"][p], r, cost_ok) for p in sorted(proj_ids, key=lambda i: d["projects"][i]["code"])]
    return {"month": mo.isoformat()[:7], "partial": partial, "rows": rows}


@router.get("/costing/tags")
def by_tag(month: str | None = None, primary: bool = False, c: Ctx = Depends(ctx)):
    c.require("costing.effort")
    mo = _month(month)
    d = k.load(c, mo)
    emp_ids, proj_ids, partial = visible(c, "costing.effort", d)
    r = k.compute(d, emp_ids, proj_ids)
    cost_ok = c.can("costing.cost") and not partial
    rows = []
    for tid, g in sorted(k.tag_groups(d, primary).items(), key=lambda kv: kv[1]["name"]):
        pids = [p for p in g["projects"] if p in proj_ids]
        if not pids:
            continue
        row = {"tag_id": tid, "tag": g["name"], "projects": len(pids), "hours": round(sum(r["proj"][p]["hours"] for p in pids), 2),
               "project_list": [{"id": p, "code": d["projects"][p]["code"], "name": d["projects"][p]["name"], "hours": round(r["proj"][p]["hours"], 2)} for p in pids]}
        if cost_ok:
            v, cst = sum(r["proj"][p]["value"] for p in pids), sum(r["proj"][p]["cost"] for p in pids)
            row.update(value_minor=v, cost_minor=cst, margin_minor=v - cst)
            for pl in row["project_list"]:
                pl.update(value_minor=r["proj"][pl["id"]]["value"], cost_minor=r["proj"][pl["id"]]["cost"])
        rows.append(row)
    return {"month": mo.isoformat()[:7], "partial": partial, "additive": primary, "rows": rows,
            "note": "Each project is counted once, under its first tag, so rows add up." if primary else "Projects can carry several tags, so tag rows overlap and must not be added together."}


@router.get("/costing/matrix")
def matrix(month: str | None = None, c: Ctx = Depends(ctx)):
    """Workbook-style view: per project an Allocation, Efforts and Cost row, employees across, with reconciliation."""
    c.require("costing.effort")
    mo = _month(month)
    d = k.load(c, mo)
    emp_ids, proj_ids, partial = visible(c, "costing.effort", d)
    r = k.compute(d, emp_ids, proj_ids)
    cost_ok = c.can("costing.cost") and not partial
    dn = people.department_names(c.db, c.tid)
    order = sorted(emp_ids, key=lambda i: (dn.get(d["emps"][i]["dept_id"], "~"), d["emps"][i]["name"]))  # grouped by department, like the workbook header
    projects = []
    for pid in sorted(proj_ids, key=lambda i: d["projects"][i]["code"]):
        p = d["projects"][pid]
        cells = {u: r["cells"][(u, pid)] for u in order if (u, pid) in r["cells"]}
        row = {"id": pid, "code": p["code"], "name": p["name"], "tags": [t["name"] for t in p["tags"]], "allocation": {u: v["pct"] for u, v in cells.items()}, "effort": {u: round(v["hours"], 2) for u, v in cells.items()},
               "hours": round(r["proj"][pid]["hours"], 2)}
        if cost_ok:
            row.update(cost={u: v["cost"] for u, v in cells.items()}, cost_minor=r["proj"][pid]["cost"], value_minor=r["proj"][pid]["value"])
        projects.append(row)
    emps = []
    for u in order:
        e, x = d["emps"][u], r["emp"][u]
        row = {"id": u, "name": e["name"], "department": dn.get(e["dept_id"]), "monthly_hours": e["hours"]}
        if not partial:
            row.update(allocated_pct=x["pct"], hours=round(x["hours"], 2), status="OVER" if x["pct"] > 100 else "Full" if x["pct"] == 100 else "Bench" if x["pct"] == 0 else "Part")
        if cost_ok:
            row.update(salary_minor=e["salary"], cost_minor=x["cost"], bench_cost_minor=x["bench_cost"])
        emps.append(row)
    out = {"month": mo.isoformat()[:7], "partial": partial, "employees": emps, "projects": projects}
    if cost_ok:
        t = k.org_totals(d, r)
        out["reconciliation"] = {"salary_pool_minor": t["salary_pool"], "allocated_cost_minor": t["cost"], "bench_cost_minor": t["bench_cost"],
                                 "value_minor": t["value"], "hours": round(t["hours"], 2),
                                 "check": "OVER-ALLOCATED" if any(e["allocated_pct"] > 100 for e in emps if "allocated_pct" in e) else "OK: salary = allocated cost + bench" if t["reconciles"] else "CHECK"}
    return out


# ---------------- revenue targets and profitability ----------------
class TargetIn(BaseModel):
    level: str = "project"
    project_id: int | None = None
    tag_id: int | None = None
    month: str | None = None
    amount_minor: int | None = None


def _target_row(c, level, mo, pid=None, tid=None):
    q = select(m.RevenueTarget).where(m.RevenueTarget.tenant_id == c.tid, m.RevenueTarget.level == level, m.RevenueTarget.month == mo)
    q = q.where(m.RevenueTarget.project_id == pid) if pid else q.where(m.RevenueTarget.project_id.is_(None))
    q = q.where(m.RevenueTarget.tag_id == tid) if tid else q.where(m.RevenueTarget.tag_id.is_(None))
    return c.db.execute(q).scalar_one_or_none()


@router.get("/targets")
def targets(month: str | None = None, c: Ctx = Depends(ctx)):
    s = c.require("targets.view")
    mo = _month(month)
    d = k.load(c, mo)
    pids = set(d["projects"]) if s == "all" else assigned_project_ids(c) & set(d["projects"])
    rows = {(t.level, t.project_id, t.tag_id): t.amount_minor for t in c.db.execute(select(m.RevenueTarget).where(m.RevenueTarget.tenant_id == c.tid, m.RevenueTarget.month == mo)).scalars()}
    cost_ok = c.can("costing.cost") and c.can("costing.effort") and c.scope("costing.effort") == "all"
    r = k.compute(d) if cost_ok else None
    out_p = []
    for pid in sorted(pids, key=lambda i: d["projects"][i]["code"]):
        p = d["projects"][pid]
        if p["status"] not in OPEN_STATUSES:
            continue
        row = {"project_id": pid, "code": p["code"], "name": p["name"], "tags": p["tags"], "target_minor": rows.get(("project", pid, None))}
        if cost_ok:
            row.update(value_minor=r["proj"][pid]["value"], cost_minor=r["proj"][pid]["cost"], hours=round(r["proj"][pid]["hours"], 2))
        out_p.append(row)
    out = {"month": mo.isoformat()[:7], "can_manage": c.can("targets.manage"), "projects": out_p,
           "note": "Targets are planning values. Actual (invoiced or collected) revenue is added when invoicing exists; the revenue basis is an open decision."}
    if s == "all":
        out["org_target_minor"] = rows.get(("org", None, None))
        out["tags"] = [{"tag_id": t["id"], "tag": t["name"], "target_minor": rows.get(("tag", None, t["id"]))}
                       for t in sorted({x["id"]: x for p in d["projects"].values() for x in p["tags"]}.values(), key=lambda x: x["name"])]
    return out


@router.put("/targets")
def set_target(b: TargetIn, c: Ctx = Depends(ctx)):
    c.require("targets.manage")
    mo = _month(b.month)
    if b.level not in ("project", "tag", "org"):
        raise err(422, "VALIDATION", "Level must be project, tag or org.")
    pid = tid = None
    if b.level == "project":
        pid = _project(c, b.project_id or -1).id
    if b.level == "tag":
        t = c.db.get(m.Tag, b.tag_id or -1)
        if not t or t.tenant_id != c.tid:
            raise err(404, "NOT_FOUND", "Tag not found.")
        tid = t.id
    if b.amount_minor is not None and not 0 <= b.amount_minor <= MAX_MONEY:
        raise err(422, "VALIDATION", "A target cannot be negative.")
    row = _target_row(c, b.level, mo, pid, tid)
    if b.amount_minor is None:
        if row:
            c.db.delete(row)
    elif row:
        row.amount_minor, row.updated_by = b.amount_minor, c.user.id
    else:
        c.db.add(m.RevenueTarget(tenant_id=c.tid, level=b.level, project_id=pid, tag_id=tid, month=mo, amount_minor=b.amount_minor, updated_by=c.user.id))
    audit(c.db, c.tid, c.user.id, "target.set", "target", f"{b.level}:{pid or tid or ''}", month=mo.isoformat()[:7], cleared=b.amount_minor is None)
    c.db.commit()
    return {"ok": True}


@router.get("/costing/profitability")
def profitability(month: str | None = None, basis: str = "standard", tags: str | None = None, c: Ctx = Depends(ctx)):
    c.require("costing.cost")
    if c.scope("costing.effort") != "all":
        raise err(403, "FORBIDDEN", "Profitability needs organization-wide effort access.")
    if basis not in ("standard", "target"):
        raise err(422, "VALIDATION", "Basis must be standard or target.")
    mo = _month(month)
    d = k.load(c, mo)
    r = k.compute(d)
    only = _filters(d, tags)
    trows = {t.project_id: t.amount_minor for t in c.db.execute(select(m.RevenueTarget).where(
        m.RevenueTarget.tenant_id == c.tid, m.RevenueTarget.month == mo, m.RevenueTarget.level == "project")).scalars()}
    rows = []
    for pid, p in sorted(d["projects"].items(), key=lambda kv: kv[1]["code"]):
        x = r["proj"][pid]
        if (only is not None and pid not in only) or (p["status"] not in OPEN_STATUSES and x["people"] == 0):
            continue
        rev = x["value"] if basis == "standard" else trows.get(pid)
        row = {"id": pid, "code": p["code"], "name": p["name"], "tags": p["tags"], "hours": round(x["hours"], 2), "revenue_minor": rev, "cost_minor": x["cost"],
               "target_minor": trows.get(pid), "value_minor": x["value"], "warnings": []}
        if x["people"] == 0:
            row["warnings"].append("No allocation")
        if x["missing_salary"]:
            row["warnings"].append("Salary missing")
        if rev is None:
            row["warnings"].append("Target not set")
            row.update(margin_minor=None, margin_pct=None)
        else:
            mg = rev - x["cost"]
            row.update(margin_minor=mg, margin_pct=round(mg * 100 / rev, 1) if rev else None)
        rows.append(row)
    ok = [x for x in rows if x["revenue_minor"] is not None]
    rev_t, cost_t = sum(x["revenue_minor"] for x in ok), sum(x["cost_minor"] for x in ok)
    t = k.org_totals(d, r)
    bench = t["bench_cost"] if only is None else None
    return {"month": mo.isoformat()[:7], "basis": basis, "rows": rows, "excluded_without_revenue": len(rows) - len(ok),
            "totals": {"revenue_minor": rev_t, "cost_minor": cost_t, "margin_minor": rev_t - cost_t, "margin_pct": round((rev_t - cost_t) * 100 / rev_t, 1) if rev_t else None,
                       "bench_cost_minor": bench, "result_after_bench_minor": None if bench is None else rev_t - cost_t - bench, "salary_pool_minor": t["salary_pool"]},
            "note": "Standard value is hours x rate, not invoiced revenue. Unallocated (bench) salary is shown separately and never charged to a project."}


def org_summary(c: Ctx) -> dict | None:
    """Compact month summary for the dashboard; only for holders of costing.cost and organization-wide effort access."""
    if not (c.can("costing.cost") and c.can("costing.effort") and c.scope("costing.effort") == "all"):
        return None
    d = k.load(c, k.month_start())
    r = k.compute(d)
    t = k.org_totals(d, r)
    return {"month": k.month_start().isoformat()[:7], "hours": round(t["hours"], 2), "value_minor": t["value"], "cost_minor": t["cost"],
            "bench_cost_minor": t["bench_cost"], "margin_minor": t["margin"], "salary_pool_minor": t["salary_pool"]}
