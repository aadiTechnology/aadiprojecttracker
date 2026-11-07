import os
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import mail, models as m
from ..core import (ENV, LOCK_AFTER, LOCK_MINUTES, Ctx, audit, check_password_strength, ctx, err, get_db, hash_password,
                    hash_token, issue_jwt, load_ctx, new_token, verify_password)
from ..perms import MODULES

router = APIRouter(prefix="/api", tags=["auth"])
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# view -> (capability that grants it, sprint in which the screen is delivered)
VIEWS = {
    "dash": (None, 1), "customers": ("customers.view", 1), "projects": ("projects.view", 1), "sprint": ("sprint.view", 2),
    "handover": ("handover.view", 2), "timesheets": ("timesheet.own", 2), "perf": ("perf.view", 4),
    "insights": ("costing.effort", 3), "employees": ("employees.view", 3), "allocation": ("allocation.view", 3), "costing": ("costing.effort", 3), "profit": ("costing.cost", 3),
    "revenue": ("targets.view", 3), "costset": ("costing.settings", 3), "expenses": ("expenses.view", 4), "invoices": ("invoices.view", 4), "plannedactual": ("costing.effort", 4), "assistant": ("ai.use", 5),
    "admin": ("org.users.view", 1), "matrix": (None, 1), "workflow": (None, 1), "assumptions": (None, 1),
}
LIVE_SPRINT = int(os.environ.get("LIVE_SPRINT", "5"))  # raised as sprints ship; screens of later sprints are labelled honestly instead of faked


def tenant_list(db: Session, user: m.User):
    rows = db.execute(select(m.Membership, m.Tenant, m.Role).join(m.Tenant, m.Tenant.id == m.Membership.tenant_id)
                      .join(m.Role, m.Role.id == m.Membership.role_id).where(m.Membership.user_id == user.id, m.Membership.status == "active")).all()
    return [{"id": t.id, "name": t.name, "role": r.name, "demo": t.is_demo} for _, t, r in rows if t.status != "suspended"]


def me_payload(c: Ctx):
    access = {}
    for v, (cap, sprint) in VIEWS.items():
        if cap is None:
            level = "view"
        elif v == "admin":
            level = "full" if c.has("org.admin") else ("view" if c.can("org.users.view") else None)
        else:
            sc = c.scope(cap) if c.can(cap) else None
            level = sc
        access[v] = {"level": level, "sprint": sprint, "built": sprint <= LIVE_SPRINT}
    return {"user": {"id": c.user.id, "name": c.user.name, "email": c.user.email},
            "tenant": {"id": c.tenant.id, "name": c.tenant.name, "demo": c.tenant.is_demo, "currency": c.tenant.currency,
                       "revenue_basis": c.tenant.revenue_basis},
            "role": {"key": c.role.key, "name": c.role.name}, "team": c.membership.team, "perms": sorted(c.perms),
            "modules": c.modules, "access": access, "tenants": tenant_list(c.db, c.user)}


class Login(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(b: Login, db: Session = Depends(get_db)):
    u = db.execute(select(m.User).where(m.User.email == b.email.strip().lower())).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    bad = err(401, "BAD_CREDENTIALS", "Email or password is incorrect.")
    if not u:
        raise bad
    if u.locked_until and u.locked_until > now:
        raise err(423, "LOCKED", f"Too many failed attempts. Try again after {LOCK_MINUTES} minutes.")
    if u.status != "active" or not verify_password(b.password, u.password_hash):
        if u.status == "active":
            u.failed_logins += 1
            if u.failed_logins >= LOCK_AFTER:
                u.locked_until, u.failed_logins = now + timedelta(minutes=LOCK_MINUTES), 0
                audit(db, None, u.id, "auth.locked", "user", u.id)
            db.commit()
        raise bad
    u.failed_logins, u.locked_until = 0, None
    tenants = tenant_list(db, u)
    if not tenants and not u.is_platform_admin:
        raise err(403, "NO_TENANT", "Your account is not a member of any active organization.")
    tid = tenants[0]["id"] if tenants and not u.is_platform_admin else None
    audit(db, tid, u.id, "auth.login", "user", u.id)
    db.commit()
    return {"token": issue_jwt(u, tid), "platform_admin": u.is_platform_admin and tid is None}


class Switch(BaseModel):
    tenant_id: int


@router.post("/auth/switch")
def switch(b: Switch, c: Ctx = Depends(ctx)):
    if b.tenant_id not in [t["id"] for t in tenant_list(c.db, c.user)]:
        raise err(403, "NO_ACCESS", "You are not a member of that organization.")
    return {"token": issue_jwt(c.user, b.tenant_id)}


@router.get("/me")
def me(c: Ctx = Depends(ctx)):
    return me_payload(c)


@router.get("/me/platform")
def me_platform(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    c = load_ctx(db, authorization, need_tenant=False)
    return {"user": {"id": c.user.id, "name": c.user.name, "email": c.user.email}, "platform_admin": c.user.is_platform_admin}


@router.post("/auth/logout-all")
def logout_all(c: Ctx = Depends(ctx)):
    c.user.token_epoch += 1
    audit(c.db, c.tid, c.user.id, "auth.logout_all", "user", c.user.id)
    c.db.commit()
    return {"ok": True}


class Forgot(BaseModel):
    email: str


@router.post("/auth/forgot")
def forgot(b: Forgot, db: Session = Depends(get_db)):
    """Always answers the same, so the response never reveals whether an account exists."""
    u = db.execute(select(m.User).where(m.User.email == b.email.strip().lower())).scalar_one_or_none()
    if u and u.status in ("active", "invited"):
        t, h = new_token()
        db.add(m.AuthToken(user_id=u.id, purpose="reset", token_hash=h, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        db.commit()
        subj, body = mail.reset_email(u.name, t)
        mail.send(u.email, subj, body)
    return {"ok": True, "message": "If that email has an account, a reset link has been sent."}


class Reset(BaseModel):
    token: str
    password: str


@router.post("/auth/reset")
def reset(b: Reset, db: Session = Depends(get_db)):
    check_password_strength(b.password)
    t = db.execute(select(m.AuthToken).where(m.AuthToken.token_hash == hash_token(b.token))).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if not t or t.used_at or t.expires_at < now:
        raise err(400, "BAD_TOKEN", "This link is invalid or has expired. Ask for a new one.")
    u = db.get(m.User, t.user_id)
    u.password_hash, u.status, u.failed_logins, u.locked_until = hash_password(b.password), "active", 0, None
    u.token_epoch += 1
    t.used_at = now
    audit(db, None, u.id, "auth.password_set", "user", u.id, purpose=t.purpose)
    db.commit()
    return {"ok": True}


@router.get("/health")
def health():
    return {"status": "ok", "env": ENV}
