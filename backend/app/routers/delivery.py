"""Sprint 2: sprints, tasks (assignment history), handover with acknowledgement, timesheets with approval, notifications.
Scoping is enforced here, never in the UI:
  all      every row of the organization
  assigned rows of projects the user is assigned to (member, project manager, or account owner)
  team     rows whose person is in the user's team or reports to the user
  own      rows that belong to the user"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select

from .. import models as m
from ..core import Ctx, audit, ctx, err
from .work import _names, assigned_project_ids

router = APIRouter(prefix="/api", tags=["delivery"])
TASK_STATUS = ["Todo", "In progress", "Blocked", "Done"]
PRIORITY = ["Low", "Medium", "High"]
MAX_DAY_HOURS = 24.0


def _notify(db, tid, uid, text, link=""):
    if uid:
        db.add(m.Notification(tenant_id=tid, user_id=uid, text=text[:300], link=link))


def _project(c: Ctx, pid: int) -> m.Project:
    p = c.db.get(m.Project, pid)
    if not p or p.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Project not found.")
    return p


# ---------------- scoping ----------------
def task_scope_clause(c: Ctx, cap: str):
    """SQL clause for the tasks a user may see/act on under capability `cap` (None if the capability is not held)."""
    s = c.require(cap)
    if s == "all":
        return m.Task.tenant_id == c.tid
    if s == "assigned":
        return and_(m.Task.tenant_id == c.tid, m.Task.project_id.in_(assigned_project_ids(c) or {-1}))
    if s == "team":
        return and_(m.Task.tenant_id == c.tid, m.Task.assignee_id.in_(c.team_user_ids()))
    return and_(m.Task.tenant_id == c.tid, m.Task.assignee_id == c.user.id)


def get_task(c: Ctx, tid: int, cap="sprint.view") -> m.Task:
    t = c.db.execute(select(m.Task).where(task_scope_clause(c, cap), m.Task.id == tid)).scalar_one_or_none()
    if not t:
        raise err(404, "NOT_FOUND", "Task not found.")
    return t


def _can_assign_to(c: Ctx, p: m.Project, uid: int):
    """The assignee must be an active member of the organization and on the project team."""
    from .. import people
    if not people.is_live(c.db, c.tid, uid):
        raise err(422, "VALIDATION", "That person is not an active member of this organization.")
    if not c.db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == p.id, m.ProjectMember.user_id == uid)).scalar_one_or_none():
        raise err(422, "NOT_ON_PROJECT", "Add the person to the project team before assigning work to them.")
    if c.scope("sprint.manage") == "team" and uid not in c.team_user_ids():
        raise err(403, "FORBIDDEN", "A team lead can assign work only within their own team.")


def _manageable_project(c: Ctx, pid: int) -> m.Project:
    s = c.require("sprint.manage")
    p = _project(c, pid)
    if s in ("assigned", "team") and p.id not in assigned_project_ids(c):
        raise err(404, "NOT_FOUND", "Project not found.")
    return p


def task_out(t: m.Task, names: dict, proj: dict, sprints: dict, c: Ctx) -> dict:
    manage = c.has("sprint.manage") and (c.scope("sprint.manage") == "all" or t.project_id in assigned_project_ids(c))
    return {"id": t.id, "project_id": t.project_id, "project": proj.get(t.project_id, ""), "sprint_id": t.sprint_id, "sprint": sprints.get(t.sprint_id),
            "title": t.title, "description": t.description, "status": t.status, "priority": t.priority, "est_hours": t.est_hours,
            "assignee_id": t.assignee_id, "assignee": names.get(t.assignee_id), "due_date": t.due_date, "can_manage": manage}


def _proj_names(c):
    return {p.id: f"{p.code} {p.name}" for p in c.db.execute(select(m.Project).where(m.Project.tenant_id == c.tid)).scalars()}


# ---------------- sprints ----------------
class SprintIn(BaseModel):
    project_id: int
    name: str
    goal: str = ""
    start_date: date | None = None
    end_date: date | None = None


@router.get("/sprints")
def sprints(project_id: int | None = None, c: Ctx = Depends(ctx)):
    s = c.require("sprint.view")
    q = select(m.Sprint).where(m.Sprint.tenant_id == c.tid)
    if project_id:
        q = q.where(m.Sprint.project_id == project_id)
    if s == "assigned":
        q = q.where(m.Sprint.project_id.in_(assigned_project_ids(c) or {-1}))
    elif s in ("team", "own"):  # sprints that contain work visible to this person
        ids = select(m.Task.sprint_id).where(task_scope_clause(c, "sprint.view"), m.Task.sprint_id.is_not(None))
        q = q.where(m.Sprint.id.in_(ids))
    rows = c.db.execute(q.order_by(m.Sprint.start_date.desc().nullslast(), m.Sprint.id.desc())).scalars().all()
    proj = _proj_names(c)
    counts = {}
    for sid, st, n, h in c.db.execute(select(m.Task.sprint_id, m.Task.status, func.count(), func.coalesce(func.sum(m.Task.est_hours), 0)).where(m.Task.tenant_id == c.tid, m.Task.sprint_id.is_not(None)).group_by(m.Task.sprint_id, m.Task.status)).all():
        d = counts.setdefault(sid, {"total": 0, "done": 0, "hours": 0.0})
        d["total"] += n
        d["hours"] += float(h)
        if st == "Done":
            d["done"] += n
    can = c.has("sprint.manage")
    return [{"id": x.id, "project_id": x.project_id, "project": proj.get(x.project_id, ""), "name": x.name, "goal": x.goal, "start_date": x.start_date,
             "end_date": x.end_date, "status": x.status, **counts.get(x.id, {"total": 0, "done": 0, "hours": 0.0}),
             "can_manage": can and (c.scope("sprint.manage") == "all" or x.project_id in assigned_project_ids(c))} for x in rows]


@router.post("/sprints")
def add_sprint(b: SprintIn, c: Ctx = Depends(ctx)):
    p = _manageable_project(c, b.project_id)
    if c.scope("sprint.manage") == "team":
        raise err(403, "FORBIDDEN", "Creating sprints needs project-level sprint management.")
    if not b.name.strip():
        raise err(422, "VALIDATION", "Enter a sprint name.")
    if b.start_date and b.end_date and b.end_date < b.start_date:
        raise err(422, "VALIDATION", "The end date cannot be before the start date.")
    if p.status in ("Completed", "Cancelled"):
        raise err(409, "PROJECT_CLOSED", "This project is closed; sprints cannot be added.")
    x = m.Sprint(tenant_id=c.tid, project_id=p.id, name=b.name.strip(), goal=b.goal.strip(), start_date=b.start_date, end_date=b.end_date)
    c.db.add(x)
    c.db.flush()
    audit(c.db, c.tid, c.user.id, "sprint.create", "sprint", x.id, project=p.code)
    c.db.commit()
    return {"id": x.id}


class SprintStatus(BaseModel):
    status: str


@router.post("/sprints/{sid}/status")
def sprint_status(sid: int, b: SprintStatus, c: Ctx = Depends(ctx)):
    x = c.db.get(m.Sprint, sid)
    if not x or x.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Sprint not found.")
    _manageable_project(c, x.project_id)
    allowed = {"Planned": {"Active"}, "Active": {"Closed"}, "Closed": set()}
    if b.status not in allowed[x.status]:
        raise err(409, "BAD_TRANSITION", f"A {x.status} sprint cannot move to {b.status}.")
    if b.status == "Active" and c.db.execute(select(m.Sprint).where(m.Sprint.project_id == x.project_id, m.Sprint.status == "Active")).first():
        raise err(409, "ONE_ACTIVE", "This project already has an active sprint. Close it first.")
    x.status = b.status
    audit(c.db, c.tid, c.user.id, "sprint.status", "sprint", x.id, status=b.status)
    c.db.commit()
    return {"status": x.status}


# ---------------- tasks ----------------
class TaskIn(BaseModel):
    project_id: int
    sprint_id: int | None = None
    title: str
    description: str = ""
    priority: str = "Medium"
    est_hours: float = 0
    assignee_id: int | None = None
    due_date: date | None = None


@router.get("/tasks")
def tasks(project_id: int | None = None, sprint_id: int | None = None, mine: bool = False, status: str = "", c: Ctx = Depends(ctx)):
    q = select(m.Task).where(task_scope_clause(c, "sprint.view"))
    if mine:
        q = q.where(m.Task.assignee_id == c.user.id)
    if project_id:
        q = q.where(m.Task.project_id == project_id)
    if sprint_id:
        q = q.where(m.Task.sprint_id == sprint_id)
    if status:
        q = q.where(m.Task.status == status)
    rows = c.db.execute(q.order_by(m.Task.status, m.Task.priority.desc(), m.Task.id)).scalars().all()
    n, proj = _names(c), _proj_names(c)
    sp = {s.id: s.name for s in c.db.execute(select(m.Sprint).where(m.Sprint.tenant_id == c.tid)).scalars()}
    return [task_out(t, n, proj, sp, c) for t in rows]


@router.post("/tasks")
def add_task(b: TaskIn, c: Ctx = Depends(ctx)):
    p = _manageable_project(c, b.project_id)
    if not b.title.strip():
        raise err(422, "VALIDATION", "Enter a task title.")
    if b.priority not in PRIORITY or b.est_hours < 0:
        raise err(422, "VALIDATION", "Choose a valid priority; hours cannot be negative.")
    if p.status in ("Completed", "Cancelled"):
        raise err(409, "PROJECT_CLOSED", "This project is closed; tasks cannot be added.")
    if b.sprint_id:
        sp = c.db.get(m.Sprint, b.sprint_id)
        if not sp or sp.tenant_id != c.tid or sp.project_id != p.id:
            raise err(422, "VALIDATION", "The sprint does not belong to this project.")
        if sp.status == "Closed":
            raise err(409, "SPRINT_CLOSED", "This sprint is closed.")
    if b.assignee_id:
        _can_assign_to(c, p, b.assignee_id)
    t = m.Task(tenant_id=c.tid, created_by=c.user.id, **{**b.model_dump(), "title": b.title.strip()})
    c.db.add(t)
    c.db.flush()
    if t.assignee_id:
        c.db.add(m.TaskAssignment(tenant_id=c.tid, task_id=t.id, to_user_id=t.assignee_id, by_user_id=c.user.id, reason="Initial assignment"))
        if t.assignee_id != c.user.id:
            _notify(c.db, c.tid, t.assignee_id, f"{c.user.name} assigned you: {t.title}", "/sprint")
    audit(c.db, c.tid, c.user.id, "task.create", "task", t.id, project=p.code)
    c.db.commit()
    return {"id": t.id}


@router.get("/tasks/{tid}")
def task_detail(tid: int, c: Ctx = Depends(ctx)):
    t = get_task(c, tid)
    n, proj = _names(c), _proj_names(c)
    d = task_out(t, n, proj, {s.id: s.name for s in c.db.execute(select(m.Sprint).where(m.Sprint.tenant_id == c.tid)).scalars()}, c)
    d["history"] = [{"from": n.get(a.from_user_id), "to": n.get(a.to_user_id), "by": n.get(a.by_user_id), "reason": a.reason, "at": a.at.isoformat(), "handover_id": a.handover_id}
                    for a in c.db.execute(select(m.TaskAssignment).where(m.TaskAssignment.task_id == t.id).order_by(m.TaskAssignment.id)).scalars()]
    d["logged_hours"] = float(c.db.execute(select(func.coalesce(func.sum(m.TimeEntry.hours), 0)).where(m.TimeEntry.task_id == t.id)).scalar()) if c.has("timesheet.view") else None
    return d


class TaskStatus(BaseModel):
    status: str


@router.post("/tasks/{tid}/status")
def task_status(tid: int, b: TaskStatus, c: Ctx = Depends(ctx)):
    t = get_task(c, tid, "sprint.update")
    if b.status not in TASK_STATUS:
        raise err(422, "VALIDATION", "Unknown status.")
    sp = c.db.get(m.Sprint, t.sprint_id) if t.sprint_id else None
    if sp and sp.status == "Closed":
        raise err(409, "SPRINT_CLOSED", "This sprint is closed; its tasks can no longer change.")
    if t.status != b.status:
        audit(c.db, c.tid, c.user.id, "task.status", "task", t.id, before=t.status, after=b.status)
        t.status = b.status
        if b.status == "Blocked":
            p = c.db.get(m.Project, t.project_id)
            _notify(c.db, c.tid, p.pm_user_id if p and p.pm_user_id != c.user.id else None, f"Blocked: {t.title} ({c.user.name})", "/sprint")
    c.db.commit()
    return {"status": t.status}


class TaskEdit(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    est_hours: float | None = None
    sprint_id: int | None = None
    due_date: date | None = None


@router.patch("/tasks/{tid}")
def edit_task(tid: int, b: TaskEdit, c: Ctx = Depends(ctx)):
    t = get_task(c, tid, "sprint.manage")
    p = _manageable_project(c, t.project_id)
    data = b.model_dump(exclude_unset=True)
    if "priority" in data and data["priority"] not in PRIORITY:
        raise err(422, "VALIDATION", "Choose a valid priority.")
    if data.get("est_hours") is not None and data["est_hours"] < 0:
        raise err(422, "VALIDATION", "Hours cannot be negative.")
    if data.get("sprint_id"):
        sp = c.db.get(m.Sprint, data["sprint_id"])
        if not sp or sp.tenant_id != c.tid or sp.project_id != p.id or sp.status == "Closed":
            raise err(422, "VALIDATION", "Choose an open sprint of this project.")
    for k, v in data.items():
        setattr(t, k, v.strip() if isinstance(v, str) and k == "title" else v)
    audit(c.db, c.tid, c.user.id, "task.update", "task", t.id, fields=sorted(data))
    c.db.commit()
    return {"ok": True}


class AssignIn(BaseModel):
    user_id: int
    reason: str = ""


@router.post("/tasks/{tid}/assign")
def assign_task(tid: int, b: AssignIn, c: Ctx = Depends(ctx)):
    t = get_task(c, tid, "sprint.manage")
    p = _manageable_project(c, t.project_id)
    _can_assign_to(c, p, b.user_id)
    if t.assignee_id == b.user_id:
        raise err(409, "NO_CHANGE", "The task is already assigned to this person.")
    c.db.add(m.TaskAssignment(tenant_id=c.tid, task_id=t.id, from_user_id=t.assignee_id, to_user_id=b.user_id, by_user_id=c.user.id, reason=b.reason.strip() or "Reassigned"))
    t.assignee_id = b.user_id
    _notify(c.db, c.tid, b.user_id, f"{c.user.name} assigned you: {t.title}", "/sprint")
    audit(c.db, c.tid, c.user.id, "task.assign", "task", t.id, to=b.user_id)
    c.db.commit()
    return {"ok": True}


@router.get("/projects/{pid}/assignable")
def assignable(pid: int, c: Ctx = Depends(ctx)):
    """People who may receive work on a project (its team). Only for roles that manage sprints; id and name only."""
    p = _manageable_project(c, pid)
    n = _names(c)
    ids = [r for r in c.db.execute(select(m.ProjectMember.user_id).where(m.ProjectMember.project_id == p.id)).scalars()]
    if c.scope("sprint.manage") == "team":
        ids = [i for i in ids if i in c.team_user_ids()]
    return [{"id": i, "name": n.get(i)} for i in ids]


# ---------------- handover ----------------
class HandoverIn(BaseModel):
    project_id: int
    from_user_id: int
    to_user_id: int
    task_ids: list[int] = []
    note: str


def handover_scope(c: Ctx, cap: str):
    s = c.require(cap)
    if s == "all":
        return m.Handover.tenant_id == c.tid
    if s == "assigned":
        return and_(m.Handover.tenant_id == c.tid, m.Handover.project_id.in_(assigned_project_ids(c) or {-1}))
    ids = c.team_user_ids() if s == "team" else {c.user.id}
    return and_(m.Handover.tenant_id == c.tid, or_(m.Handover.from_user_id.in_(ids), m.Handover.to_user_id.in_(ids)))


def handover_out(h: m.Handover, n: dict, proj: dict, c: Ctx, titles: dict) -> dict:
    return {"id": h.id, "project_id": h.project_id, "project": proj.get(h.project_id, ""), "from": n.get(h.from_user_id), "to": n.get(h.to_user_id),
            "to_user_id": h.to_user_id, "note": h.note, "status": h.status, "created_at": h.created_at.isoformat(), "ack_at": h.ack_at.isoformat() if h.ack_at else None,
            "ack_note": h.ack_note, "tasks": [{"id": i, "title": titles.get(i, f"Task {i}")} for i in h.task_ids],
            "can_ack": h.status == "Pending" and h.to_user_id == c.user.id and c.has("handover.ack")}


@router.get("/handovers")
def handovers(c: Ctx = Depends(ctx)):
    rows = c.db.execute(select(m.Handover).where(handover_scope(c, "handover.view")).order_by(m.Handover.id.desc())).scalars().all()
    n, proj = _names(c), _proj_names(c)
    titles = {t.id: t.title for t in c.db.execute(select(m.Task).where(m.Task.tenant_id == c.tid)).scalars()}
    return [handover_out(h, n, proj, c, titles) for h in rows]


@router.post("/handovers")
def add_handover(b: HandoverIn, c: Ctx = Depends(ctx)):
    p = _manageable_project(c, b.project_id)
    if not c.has("handover.manage"):
        raise err(403, "FORBIDDEN", "Your role does not allow this action.")
    if not b.note.strip():
        raise err(422, "VALIDATION", "A handover needs a note: context, status and what to do next.")
    if b.from_user_id == b.to_user_id:
        raise err(422, "VALIDATION", "Choose a different person to hand over to.")
    _can_assign_to(c, p, b.to_user_id)
    if c.scope("handover.manage") == "team" and b.from_user_id not in c.team_user_ids():
        raise err(403, "FORBIDDEN", "A team lead can hand over only work held by their own team.")
    if c.db.execute(select(m.Handover).where(m.Handover.project_id == p.id, m.Handover.from_user_id == b.from_user_id, m.Handover.to_user_id == b.to_user_id, m.Handover.status == "Pending")).first():
        raise err(409, "DUPLICATE", "A handover between these people is already waiting for acknowledgement.")
    tasks_ = c.db.execute(select(m.Task).where(m.Task.tenant_id == c.tid, m.Task.project_id == p.id, m.Task.id.in_(b.task_ids or [-1]), m.Task.assignee_id == b.from_user_id, m.Task.status != "Done")).scalars().all()
    if len(tasks_) != len(set(b.task_ids)):
        raise err(422, "VALIDATION", "Every task must belong to this project, be held by the person handing over, and not be done.")
    h = m.Handover(tenant_id=c.tid, project_id=p.id, from_user_id=b.from_user_id, to_user_id=b.to_user_id, created_by=c.user.id, note=b.note.strip(), task_ids=[t.id for t in tasks_])
    c.db.add(h)
    c.db.flush()
    for t in tasks_:  # ownership moves immediately; the receiver acknowledges it
        c.db.add(m.TaskAssignment(tenant_id=c.tid, task_id=t.id, from_user_id=t.assignee_id, to_user_id=b.to_user_id, by_user_id=c.user.id, reason="Handover", handover_id=h.id))
        t.assignee_id = b.to_user_id
    n = _names(c)
    _notify(c.db, c.tid, b.to_user_id, f"Handover from {n.get(b.from_user_id)} on {p.name}: {len(tasks_)} task(s). Please acknowledge.", "/handover")
    audit(c.db, c.tid, c.user.id, "handover.create", "handover", h.id, project=p.code, tasks=len(tasks_))
    c.db.commit()
    return {"id": h.id}


class AckIn(BaseModel):
    note: str = ""


@router.post("/handovers/{hid}/ack")
def ack_handover(hid: int, b: AckIn, c: Ctx = Depends(ctx)):
    c.require("handover.ack")
    h = c.db.get(m.Handover, hid)
    if not h or h.tenant_id != c.tid or h.to_user_id != c.user.id:  # only the receiver can acknowledge
        raise err(404, "NOT_FOUND", "Handover not found.")
    if h.status != "Pending":
        raise err(409, "DECIDED", "This handover was already acknowledged.")
    h.status, h.ack_at, h.ack_note = "Acknowledged", datetime.now(timezone.utc), b.note.strip()
    _notify(c.db, c.tid, h.created_by, f"{c.user.name} acknowledged the handover.", "/handover")
    if h.from_user_id != h.created_by:
        _notify(c.db, c.tid, h.from_user_id, f"{c.user.name} acknowledged your handover.", "/handover")
    audit(c.db, c.tid, c.user.id, "handover.ack", "handover", h.id)
    c.db.commit()
    return {"status": h.status}


# ---------------- timesheets ----------------
def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def entry_out(e: m.TimeEntry, proj: dict, n: dict, titles: dict) -> dict:
    return {"id": e.id, "user_id": e.user_id, "user": n.get(e.user_id), "project_id": e.project_id, "project": proj.get(e.project_id, ""), "task_id": e.task_id,
            "task": titles.get(e.task_id), "work_date": e.work_date, "hours": e.hours, "note": e.note, "status": e.status,
            "decided_by": n.get(e.decided_by), "reject_reason": e.reject_reason, "editable": e.status in ("Draft", "Rejected")}


@router.get("/timesheets/projects")
def timesheet_projects(c: Ctx = Depends(ctx)):
    """Projects the user may log time against: those where they are on the team. Id/code/name only."""
    c.require("timesheet.own")
    rows = c.db.execute(select(m.Project).join(m.ProjectMember, m.ProjectMember.project_id == m.Project.id)
                        .where(m.Project.tenant_id == c.tid, m.ProjectMember.user_id == c.user.id, m.Project.status.in_(["Planned", "Active", "On Hold"]))).scalars().all()
    tasks_ = c.db.execute(select(m.Task).where(m.Task.tenant_id == c.tid, m.Task.assignee_id == c.user.id, m.Task.status != "Done")).scalars().all()
    return [{"id": p.id, "label": f"{p.code} {p.name}", "tasks": [{"id": t.id, "title": t.title} for t in tasks_ if t.project_id == p.id]} for p in rows]


@router.get("/timesheets")
def my_timesheet(week: date | None = None, c: Ctx = Depends(ctx)):
    c.require("timesheet.own")
    start = monday(week or date.today())
    rows = c.db.execute(select(m.TimeEntry).where(m.TimeEntry.tenant_id == c.tid, m.TimeEntry.user_id == c.user.id, m.TimeEntry.work_date >= start,
                                                 m.TimeEntry.work_date < start + timedelta(days=7)).order_by(m.TimeEntry.work_date, m.TimeEntry.id)).scalars().all()
    titles = {t.id: t.title for t in c.db.execute(select(m.Task).where(m.Task.tenant_id == c.tid)).scalars()}
    out = [entry_out(e, _proj_names(c), {c.user.id: c.user.name}, titles) for e in rows]
    return {"week_start": start, "week_end": start + timedelta(days=6), "entries": out, "total": sum(e.hours for e in rows),
            "target": float(c.tenant.week_hours), "submittable": any(e.status in ("Draft", "Rejected") for e in rows)}


class EntryIn(BaseModel):
    project_id: int
    task_id: int | None = None
    work_date: date
    hours: float
    note: str = ""


def _check_entry(c: Ctx, b: EntryIn, exclude: int | None = None):
    if not 0 < b.hours <= MAX_DAY_HOURS:
        raise err(422, "VALIDATION", "Hours must be more than 0 and at most 24.")
    if b.work_date > date.today():
        raise err(422, "FUTURE_DATE", "You cannot log time for a future date.")
    if b.work_date < date.today() - timedelta(days=45):
        raise err(422, "TOO_OLD", "Time older than 45 days needs an administrator.")
    if not c.db.execute(select(m.ProjectMember).where(m.ProjectMember.project_id == b.project_id, m.ProjectMember.user_id == c.user.id, m.ProjectMember.tenant_id == c.tid)).scalar_one_or_none():
        raise err(403, "NOT_ON_PROJECT", "You can log time only on projects you are assigned to.")
    if b.task_id:
        t = c.db.get(m.Task, b.task_id)
        if not t or t.tenant_id != c.tid or t.project_id != b.project_id:
            raise err(422, "VALIDATION", "The task does not belong to that project.")
    q = select(func.coalesce(func.sum(m.TimeEntry.hours), 0)).where(m.TimeEntry.tenant_id == c.tid, m.TimeEntry.user_id == c.user.id, m.TimeEntry.work_date == b.work_date)
    if exclude:
        q = q.where(m.TimeEntry.id != exclude)
    if float(c.db.execute(q).scalar()) + b.hours > MAX_DAY_HOURS:
        raise err(422, "DAY_LIMIT", "That would exceed 24 hours for the day.")


@router.post("/timesheets")
def add_entry(b: EntryIn, c: Ctx = Depends(ctx)):
    c.require("timesheet.own")
    _check_entry(c, b)
    e = m.TimeEntry(tenant_id=c.tid, user_id=c.user.id, project_id=b.project_id, task_id=b.task_id, work_date=b.work_date, hours=b.hours, note=b.note.strip()[:300])
    c.db.add(e)
    c.db.commit()
    return {"id": e.id}


def _own_entry(c: Ctx, eid: int) -> m.TimeEntry:
    e = c.db.get(m.TimeEntry, eid)
    if not e or e.tenant_id != c.tid or e.user_id != c.user.id:
        raise err(404, "NOT_FOUND", "Entry not found.")
    if e.status not in ("Draft", "Rejected"):
        raise err(409, "LOCKED", "A submitted or approved entry cannot be changed.")
    return e


@router.patch("/timesheets/{eid}")
def edit_entry(eid: int, b: EntryIn, c: Ctx = Depends(ctx)):
    c.require("timesheet.own")
    e = _own_entry(c, eid)
    _check_entry(c, b, exclude=e.id)
    e.project_id, e.task_id, e.work_date, e.hours, e.note = b.project_id, b.task_id, b.work_date, b.hours, b.note.strip()[:300]
    e.status, e.reject_reason = "Draft", ""
    c.db.commit()
    return {"ok": True}


@router.delete("/timesheets/{eid}")
def delete_entry(eid: int, c: Ctx = Depends(ctx)):
    c.require("timesheet.own")
    c.db.delete(_own_entry(c, eid))
    c.db.commit()
    return {"ok": True}


class SubmitIn(BaseModel):
    week: date


@router.post("/timesheets/submit")
def submit_week(b: SubmitIn, c: Ctx = Depends(ctx)):
    c.require("timesheet.own")
    start = monday(b.week)
    rows = c.db.execute(select(m.TimeEntry).where(m.TimeEntry.tenant_id == c.tid, m.TimeEntry.user_id == c.user.id, m.TimeEntry.work_date >= start,
                                                 m.TimeEntry.work_date < start + timedelta(days=7), m.TimeEntry.status.in_(["Draft", "Rejected"]))).scalars().all()
    if not rows:
        raise err(409, "NOTHING", "There is nothing to submit for this week.")
    approvers = set()
    for e in rows:
        e.status, e.reject_reason = "Submitted", ""
        p = c.db.get(m.Project, e.project_id)
        if p and p.pm_user_id and p.pm_user_id != c.user.id:
            approvers.add(p.pm_user_id)
    tl = c.membership.manager_user_id  # the caller's reporting manager, from the shared kit
    if tl and tl != c.user.id:
        approvers.add(tl)
    for a in approvers:
        _notify(c.db, c.tid, a, f"{c.user.name} submitted a timesheet for week of {start.isoformat()}.", "/timesheets")
    audit(c.db, c.tid, c.user.id, "timesheet.submit", "timesheet", c.user.id, week=start.isoformat(), entries=len(rows))
    c.db.commit()
    return {"submitted": len(rows)}


def approval_scope(c: Ctx, cap: str):
    s = c.require(cap)
    base = [m.TimeEntry.tenant_id == c.tid, m.TimeEntry.user_id != c.user.id]  # nobody approves or views-as-approver their own time
    if s == "assigned":
        base.append(m.TimeEntry.project_id.in_(assigned_project_ids(c) or {-1}))
    elif s == "team":
        base.append(m.TimeEntry.user_id.in_(c.team_user_ids()))
    elif s == "own":
        base.append(m.TimeEntry.id == -1)
    return and_(*base)


@router.get("/timesheets/approvals")
def approvals(status: str = "Submitted", c: Ctx = Depends(ctx)):
    rows = c.db.execute(select(m.TimeEntry).where(approval_scope(c, "timesheet.view"), m.TimeEntry.status == status)
                        .order_by(m.TimeEntry.user_id, m.TimeEntry.work_date)).scalars().all()
    n, proj = _names(c), _proj_names(c)
    titles = {t.id: t.title for t in c.db.execute(select(m.Task).where(m.Task.tenant_id == c.tid)).scalars()}
    can = c.has("timesheet.approve")
    return {"can_approve": can, "entries": [entry_out(e, proj, n, titles) for e in rows]}


class DecideIn(BaseModel):
    ids: list[int]
    approve: bool
    reason: str = ""


@router.post("/timesheets/decide")
def decide(b: DecideIn, c: Ctx = Depends(ctx)):
    rows = c.db.execute(select(m.TimeEntry).where(approval_scope(c, "timesheet.approve"), m.TimeEntry.id.in_(b.ids or [-1]))).scalars().all()
    if len(rows) != len(set(b.ids)):
        raise err(403, "FORBIDDEN", "You cannot decide on some of these entries (your own time, or outside your scope).")
    if not b.approve and not b.reason.strip():
        raise err(422, "REASON_REQUIRED", "Give a reason when rejecting time.")
    if any(e.status != "Submitted" for e in rows):
        raise err(409, "DECIDED", "Only submitted entries can be decided.")
    now_ = datetime.now(timezone.utc)
    people = {}
    for e in rows:
        e.status, e.decided_by, e.decided_at, e.reject_reason = ("Approved" if b.approve else "Rejected"), c.user.id, now_, ("" if b.approve else b.reason.strip()[:300])
        people[e.user_id] = people.get(e.user_id, 0) + e.hours
    for uid, h in people.items():
        _notify(c.db, c.tid, uid, f"{c.user.name} {'approved' if b.approve else 'rejected'} {h:g} h of your time." + ("" if b.approve else f" Reason: {b.reason.strip()}"), "/timesheets")
    audit(c.db, c.tid, c.user.id, "timesheet.approve" if b.approve else "timesheet.reject", "timesheet", ",".join(map(str, b.ids))[:40], entries=len(rows))
    c.db.commit()
    return {"decided": len(rows)}


# ---------------- notifications and delivery summary ----------------
@router.get("/notifications")
def notifications(c: Ctx = Depends(ctx)):
    rows = c.db.execute(select(m.Notification).where(m.Notification.tenant_id == c.tid, m.Notification.user_id == c.user.id).order_by(m.Notification.id.desc()).limit(30)).scalars().all()
    return {"unread": sum(1 for r in rows if not r.read), "items": [{"id": r.id, "text": r.text, "link": r.link, "read": r.read, "at": r.at.isoformat()} for r in rows]}


@router.post("/notifications/read")
def read_notifications(c: Ctx = Depends(ctx)):
    for r in c.db.execute(select(m.Notification).where(m.Notification.tenant_id == c.tid, m.Notification.user_id == c.user.id, m.Notification.read.is_(False))).scalars():
        r.read = True
    c.db.commit()
    return {"ok": True}


def delivery_summary(c: Ctx) -> dict:
    """Role-aware delivery numbers for the dashboard: only blocks the role may see are present."""
    out = {}
    if c.can("sprint.view"):
        rows = c.db.execute(select(m.Task).where(task_scope_clause(c, "sprint.view"))).scalars().all()
        out["tasks"] = {"total": len(rows), **{s: sum(1 for t in rows if t.status == s) for s in TASK_STATUS},
                        "mine_open": sum(1 for t in rows if t.assignee_id == c.user.id and t.status != "Done"),
                        "overdue": sum(1 for t in rows if t.due_date and t.due_date < date.today() and t.status != "Done")}
    if c.can("timesheet.own"):
        start = monday(date.today())
        week = float(c.db.execute(select(func.coalesce(func.sum(m.TimeEntry.hours), 0)).where(m.TimeEntry.tenant_id == c.tid, m.TimeEntry.user_id == c.user.id, m.TimeEntry.work_date >= start)).scalar())
        out["my_week_hours"], out["week_target"] = week, float(c.tenant.week_hours)
    if c.can("timesheet.approve"):
        out["pending_approvals"] = c.db.execute(select(func.count()).select_from(m.TimeEntry).where(approval_scope(c, "timesheet.approve"), m.TimeEntry.status == "Submitted")).scalar()
    if c.can("handover.ack"):
        out["pending_handovers"] = c.db.execute(select(func.count()).select_from(m.Handover).where(m.Handover.tenant_id == c.tid, m.Handover.to_user_id == c.user.id, m.Handover.status == "Pending")).scalar()
    return out
