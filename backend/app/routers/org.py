import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from .. import mail, models as m
from ..core import ENV, Ctx, audit, ctx, err, hash_password, new_token, check_password_strength
from ..perms import CAPABILITY_CATALOG, MODULES

router = APIRouter(prefix="/api/org", tags=["organization"])
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REVENUE_BASES = {"invoiced", "collected", "recognized", "milestone"}


def _user_row(c: Ctx, mem, u, role):
    return {"id": u.id, "name": u.name, "email": u.email, "status": u.status if mem.status == "active" else mem.status,
            "role_key": role.key, "role": role.name, "title": mem.title, "team": mem.team, "manager_user_id": mem.manager_user_id}


def _need_users(c: Ctx):
    if not (c.has("org.admin") or c.has("org.users.view")):
        raise err(403, "FORBIDDEN", "Your role does not allow this action.")


@router.get("/users")
def users(c: Ctx = Depends(ctx)):
    _need_users(c)
    rows = c.db.execute(select(m.Membership, m.User, m.Role).join(m.User, m.User.id == m.Membership.user_id)
                        .join(m.Role, m.Role.id == m.Membership.role_id).where(m.Membership.tenant_id == c.tid).order_by(m.User.name)).all()
    return [_user_row(c, mem, u, r) for mem, u, r in rows]


class Invite(BaseModel):
    email: str
    name: str
    role_key: str
    title: str = ""
    team: str = ""
    manager_user_id: int | None = None


@router.post("/users")
def invite(b: Invite, c: Ctx = Depends(ctx)):
    c.require("org.admin")
    email = b.email.strip().lower()
    if not EMAIL.match(email) or not b.name.strip():
        raise err(422, "VALIDATION", "Enter a name and a valid email address.")
    role = c.db.execute(select(m.Role).where(m.Role.tenant_id == c.tid, m.Role.key == b.role_key)).scalar_one_or_none()
    if not role:
        raise err(422, "VALIDATION", "Unknown role.")
    u = c.db.execute(select(m.User).where(m.User.email == email)).scalar_one_or_none()
    if u and c.db.execute(select(m.Membership).where(m.Membership.user_id == u.id, m.Membership.tenant_id == c.tid)).scalar_one_or_none():
        raise err(409, "DUPLICATE", "That person is already a member of this organization.")
    if u and u.is_platform_admin:
        raise err(422, "VALIDATION", "That address belongs to a platform account.")
    if b.manager_user_id and not c.db.execute(select(m.Membership).where(m.Membership.user_id == b.manager_user_id, m.Membership.tenant_id == c.tid)).scalar_one_or_none():
        raise err(422, "VALIDATION", "The reporting manager is not in this organization.")
    if not u:
        u = m.User(email=email, name=b.name.strip(), status="invited")
        c.db.add(u)
        c.db.flush()
    mem = m.Membership(tenant_id=c.tid, user_id=u.id, role_id=role.id, title=b.title, team=b.team, manager_user_id=b.manager_user_id)
    c.db.add(mem)
    link = None
    sent = False
    if u.status == "invited":
        t, h = new_token()
        c.db.add(m.AuthToken(user_id=u.id, purpose="invite", token_hash=h, expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
        subj, body = mail.invite_email(u.name, c.tenant.name, t)
        sent = mail.send(u.email, subj, body)
        if not sent and ENV == "demo":
            link = f"{mail.public_url()}/reset?token={t}"  # demo only: lets the reviewer continue when SMTP is not configured
    audit(c.db, c.tid, c.user.id, "user.invite", "user", u.id, role=role.key, email_sent=sent)
    c.db.commit()
    return {"user": _user_row(c, mem, u, role), "email_sent": sent, "invite_link": link}


class UserPatch(BaseModel):
    role_key: str | None = None
    title: str | None = None
    team: str | None = None
    manager_user_id: int | None = None
    status: str | None = None  # active | suspended


@router.patch("/users/{uid}")
def patch_user(uid: int, b: UserPatch, c: Ctx = Depends(ctx)):
    c.require("org.admin")
    mem = c.db.execute(select(m.Membership).where(m.Membership.user_id == uid, m.Membership.tenant_id == c.tid)).scalar_one_or_none()
    if not mem:
        raise err(404, "NOT_FOUND", "User not found.")
    old_role = c.db.get(m.Role, mem.role_id)
    before = {"role": old_role.key, "team": mem.team, "status": mem.status}
    owners = c.db.execute(select(func.count()).select_from(m.Membership).join(m.Role, m.Role.id == m.Membership.role_id)
                          .where(m.Membership.tenant_id == c.tid, m.Role.key == "owner", m.Membership.status == "active")).scalar()
    losing_owner = old_role.key == "owner" and ((b.role_key and b.role_key != "owner") or b.status == "suspended")
    if losing_owner and owners <= 1:
        raise err(409, "LAST_OWNER", "The organization must keep at least one active owner.")
    if uid == c.user.id and (b.role_key or b.status == "suspended"):
        raise err(409, "SELF_CHANGE", "You cannot change your own role or suspend yourself.")
    if b.role_key:
        r = c.db.execute(select(m.Role).where(m.Role.tenant_id == c.tid, m.Role.key == b.role_key)).scalar_one_or_none()
        if not r:
            raise err(422, "VALIDATION", "Unknown role.")
        mem.role_id = r.id
    if b.title is not None:
        mem.title = b.title
    if b.team is not None:
        mem.team = b.team
    if b.manager_user_id is not None:
        mem.manager_user_id = b.manager_user_id or None
    if b.status in ("active", "suspended"):
        mem.status = b.status
        if b.status == "suspended":
            c.db.get(m.User, uid).token_epoch += 1  # revoke live sessions immediately
    audit(c.db, c.tid, c.user.id, "user.update", "user", uid, before=before, after=b.model_dump(exclude_none=True))
    c.db.commit()
    return {"ok": True}


@router.get("/roles")
def roles(c: Ctx = Depends(ctx)):
    _need_users(c)
    counts = dict(c.db.execute(select(m.Membership.role_id, func.count()).where(m.Membership.tenant_id == c.tid).group_by(m.Membership.role_id)).all())
    rs = c.db.execute(select(m.Role).where(m.Role.tenant_id == c.tid).order_by(m.Role.id)).scalars().all()
    return {"roles": [{"id": r.id, "key": r.key, "name": r.name, "perms": r.perms, "members": counts.get(r.id, 0)} for r in rs],
            "catalog": CAPABILITY_CATALOG, "note": "Permissions are configurable by the Organization Owner and enforced by the API on every request."}


class RolePerms(BaseModel):
    perms: list[str]


@router.put("/roles/{rid}")
def set_role(rid: int, b: RolePerms, c: Ctx = Depends(ctx)):
    c.require("org.admin")
    r = c.db.get(m.Role, rid)
    if not r or r.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Role not found.")
    if r.key == "owner":
        raise err(409, "PROTECTED", "The Owner role keeps all permissions so the organization can never be locked out.")
    for p in b.perms:
        base = p.split(":")[0]
        if base not in CAPABILITY_CATALOG or (":" in p and p.split(":")[1] not in ("all", "team", "assigned", "own")):
            raise err(422, "VALIDATION", f"Unknown capability: {p}")
    if any(x in b.perms for x in ("salary.view", "salary.manage", "costing.cost")) and r.key not in ("finance",):
        raise err(422, "RESTRICTED", "Salary and cost visibility is restricted to the Finance role and the Owner in this release.")
    before = list(r.perms)
    r.perms = sorted(set(b.perms))
    audit(c.db, c.tid, c.user.id, "role.permissions", "role", r.id, before=before, after=r.perms)
    c.db.commit()
    return {"ok": True}


@router.get("/modules")
def modules(c: Ctx = Depends(ctx)):
    return [{"key": k, "label": v[0], "pillar": v[1], "priority": v[2], "enabled": bool(c.modules.get(k))} for k, v in MODULES.items()]


@router.get("/settings")
def settings(c: Ctx = Depends(ctx)):
    t = c.tenant
    return {"name": t.name, "currency": t.currency, "timezone": t.timezone, "week_hours": t.week_hours,
            "revenue_basis": t.revenue_basis, "planning_markers": t.planning_markers,
            "open_decisions": ["revenue_basis" if not t.revenue_basis else None, "planning_markers" if not t.planning_markers else None]}


class SettingsPatch(BaseModel):
    name: str | None = None
    timezone: str | None = None
    week_hours: int | None = None
    revenue_basis: str | None = None
    planning_markers: dict | None = None


@router.patch("/settings")
def patch_settings(b: SettingsPatch, c: Ctx = Depends(ctx)):
    c.require("org.admin")
    t = c.tenant
    if b.week_hours is not None and not 1 <= b.week_hours <= 80:
        raise err(422, "VALIDATION", "Working week must be between 1 and 80 hours.")
    if b.revenue_basis is not None and b.revenue_basis not in REVENUE_BASES:
        raise err(422, "VALIDATION", "Revenue basis must be one of: " + ", ".join(sorted(REVENUE_BASES)))
    for k, v in b.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    audit(c.db, c.tid, c.user.id, "settings.update", "tenant", c.tid, changes=b.model_dump(exclude_none=True))
    c.db.commit()
    return {"ok": True}


@router.get("/audit")
def audit_log(limit: int = 50, offset: int = 0, action: str = "", c: Ctx = Depends(ctx)):
    c.require("audit.view")
    q = select(m.AuditEvent, m.User.name).outerjoin(m.User, m.User.id == m.AuditEvent.actor_id).where(m.AuditEvent.tenant_id == c.tid)
    if action:
        q = q.where(m.AuditEvent.action.like(action + "%"))
    rows = c.db.execute(q.order_by(m.AuditEvent.id.desc()).limit(min(limit, 200)).offset(offset)).all()
    return [{"id": a.id, "at": a.at.isoformat(), "actor": n or "system", "action": a.action, "entity": a.entity, "entity_id": a.entity_id, "detail": a.detail} for a, n in rows]


MATRIX_ROWS = [("Organization & user administration", "org.admin"), ("Customer / business register", "customers.view"), ("Project & scope management", "projects.view"),
               ("Sprint & task planning", "sprint.view"), ("Team transition / handover", "handover.view"), ("Timesheet entry", "timesheet.own"),
               ("Timesheet approval", "timesheet.approve"), ("Employee performance", "perf.view"), ("Revenue targets", "revenue.view"),
               ("Expense & cost allocation", "expenses.view"), ("Salary / cost rates (restricted)", "salary.view"), ("Invoice management", "invoices.view"),
               ("Reports", "reports.view"), ("Audit log", "audit.view"), ("AI management assistant", "ai.use"),
               ("Employees & departments", "employees.view"), ("Salary management (restricted)", "salary.manage"), ("Project tags", "projects.tag"),
               ("Employee allocation", "allocation.view"), ("Costing settings", "costing.settings"), ("Effort (hours)", "costing.effort"),
               ("Cost, value & profit (restricted)", "costing.cost"), ("Revenue targets (planning)", "targets.view")]


@router.get("/matrix")
def matrix(c: Ctx = Depends(ctx)):
    """Live role x module matrix computed from this organization's role permissions (so edits are reflected)."""
    roles = c.db.execute(select(m.Role).where(m.Role.tenant_id == c.tid).order_by(m.Role.id)).scalars().all()

    def cell(perms, cap):
        for s in ("all", "team", "assigned", "own"):
            if f"{cap}:{s}" in perms:
                return {"all": "All", "team": "Team", "assigned": "Assigned", "own": "Own"}[s]
        return "Yes" if cap in perms else "No"
    return {"roles": [{"key": r.key, "name": r.name} for r in roles], "current": c.role.key,
            "rows": [{"module": n, "cap": cap, "cells": {r.key: cell(set(r.perms), cap) for r in roles}} for n, cap in MATRIX_ROWS]}
