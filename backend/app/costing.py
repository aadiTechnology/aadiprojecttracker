"""Costing engine (Revision 2). Pure calculation plus loaders. No HTTP, no permission checks: callers apply scope and masking.

Rules (PRD section 13), per month:
  effort hours (e, p)  = allocation% x monthly hours of e
  salary cost (e, p)   = allocation% x e's own monthly salary           (never one salary for everybody)
  project value        = project hours x hourly rate of the project     (standard value of effort, NOT invoiced revenue)
  bench (e)            = salary(e) - allocated cost(e)                   (so salary pool = allocated cost + bench, exactly)
Money is integer paise; cell cost is rounded half up, bench is the remainder, so totals always reconcile.
"""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select

from . import models as m


def month_start(d: date | None = None) -> date:
    return (d or date.today()).replace(day=1)


def parse_month(s: str | None) -> date:
    if not s:
        return month_start()
    try:
        y, mo = s[:7].split("-")
        return date(int(y), int(mo), 1)
    except (ValueError, TypeError):
        raise ValueError("Month must look like 2026-11")


def month_end(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def half_up(num: int, den: int) -> int:
    return (num * 2 + den) // (den * 2)


def load(c, month: date) -> dict:
    """Everything the engine needs for one tenant and month."""
    t = c.tenant
    users = c.db.execute(select(m.User, m.Membership).join(m.Membership, m.Membership.user_id == m.User.id)
                         .where(m.Membership.tenant_id == c.tid, m.Membership.status == "active")).all()
    sal = defaultdict(list)
    for r in c.db.execute(select(m.EmployeeSalary).where(m.EmployeeSalary.tenant_id == c.tid).order_by(m.EmployeeSalary.effective_from, m.EmployeeSalary.id)).scalars():
        sal[r.user_id].append((r.effective_from, r.amount_minor))
    end = month_end(month)
    emps = {}
    for u, mem in users:
        valid = [a for d, a in sal.get(u.id, []) if d <= end]
        emps[u.id] = {"id": u.id, "name": u.name, "email": u.email, "title": mem.title, "team": mem.team, "dept_id": mem.department_id,
                      "hours": mem.hours_override or t.monthly_hours, "hours_override": mem.hours_override, "salary": valid[-1] if valid else None}
    projects = {p.id: {"id": p.id, "code": p.code, "name": p.name, "status": p.status, "category": p.category,
                       "rate": p.rate_override_minor or t.hourly_rate_minor, "rate_override": p.rate_override_minor, "tags": []}
                for p in c.db.execute(select(m.Project).where(m.Project.tenant_id == c.tid).order_by(m.Project.code)).scalars()}
    for pt, tg in c.db.execute(select(m.ProjectTag, m.Tag).join(m.Tag, m.Tag.id == m.ProjectTag.tag_id).where(m.ProjectTag.tenant_id == c.tid).order_by(m.ProjectTag.position)).all():
        if pt.project_id in projects:
            projects[pt.project_id]["tags"].append({"id": tg.id, "name": tg.name})
    alloc = {(a.user_id, a.project_id): a.percent for a in c.db.execute(
        select(m.Allocation).where(m.Allocation.tenant_id == c.tid, m.Allocation.month == month)).scalars()}
    return {"emps": emps, "projects": projects, "alloc": alloc, "month": month, "default_hours": t.monthly_hours, "default_rate": t.hourly_rate_minor}


def compute(d: dict, emp_ids=None, proj_ids=None) -> dict:
    """Aggregate by employee, project and cell. emp_ids / proj_ids restrict the cells counted (used for scoped roles)."""
    emps, projects = d["emps"], d["projects"]
    cells = {}
    for (uid, pid), pct in d["alloc"].items():
        if uid not in emps or pid not in projects or pct <= 0:
            continue
        if (emp_ids is not None and uid not in emp_ids) or (proj_ids is not None and pid not in proj_ids):
            continue
        e = emps[uid]
        cells[(uid, pid)] = {"pct": pct, "ph": pct * e["hours"], "hours": pct * e["hours"] / 100,
                             "cost": None if e["salary"] is None else half_up(e["salary"] * pct, 100)}
    per_emp = {}
    for uid, e in emps.items():
        mine = [v for (u, _), v in cells.items() if u == uid]
        pct = sum(v["pct"] for v in mine)
        costs = [v["cost"] for v in mine]
        allocated = None if (e["salary"] is None and mine) else sum(x or 0 for x in costs)
        bench_pct = max(0, 100 - pct)
        per_emp[uid] = {"pct": pct, "hours": sum(v["hours"] for v in mine), "cost": allocated,
                        "bench_pct": bench_pct, "bench_hours": bench_pct * e["hours"] / 100,
                        "bench_cost": None if e["salary"] is None else max(0, e["salary"] - (allocated or 0)), "salary": e["salary"]}
    per_proj = {}
    for pid, p in projects.items():
        mine = [(u, v) for (u, q), v in cells.items() if q == pid]
        ph = sum(v["ph"] for _, v in mine)
        missing = any(v["cost"] is None for _, v in mine)
        per_proj[pid] = {"people": len(mine), "hours": ph / 100, "cost": sum(v["cost"] or 0 for _, v in mine),
                         "value": half_up(ph * p["rate"], 100), "missing_salary": missing}
    return {"cells": cells, "emp": per_emp, "proj": per_proj}


def org_totals(d: dict, r: dict) -> dict:
    pool = sum(e["salary"] or 0 for e in d["emps"].values())
    allocated = sum(p["cost"] for p in r["proj"].values())
    bench = sum(x["bench_cost"] or 0 for x in r["emp"].values())
    value = sum(p["value"] for p in r["proj"].values())
    return {"hours": sum(p["hours"] for p in r["proj"].values()), "value": value, "cost": allocated, "bench_cost": bench, "salary_pool": pool,
            "margin": value - allocated, "reconciles": pool == allocated + bench,
            "missing_salary": [e["name"] for e in d["emps"].values() if e["salary"] is None]}


def tag_groups(d: dict, primary: bool = False, tag_filter=None) -> dict:
    """tag id -> {name, project ids}. With primary=True each project counts once under its first tag (additive view)."""
    out = {}
    for pid, p in d["projects"].items():
        tags = p["tags"][:1] if primary else p["tags"]
        for tg in tags:
            if tag_filter and tg["id"] not in tag_filter:
                continue
            out.setdefault(tg["id"], {"name": tg["name"], "projects": []})["projects"].append(pid)
    return out
