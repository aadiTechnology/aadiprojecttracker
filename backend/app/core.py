"""Configuration, database, security, request context, permission and entitlement enforcement (backend-enforced)."""
import hashlib
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from . import models as m
from .perms import AREA_MODULE, SCOPE_ORDER

ROOT = Path(__file__).resolve().parent.parent
ENV = os.environ.get("APP_ENV", "production")  # demo | production (demo may load sample data; production never does)
if ENV == "production":
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL must be set in production")
    if len(os.environ.get("JWT_SECRET", "")) < 32:
        raise RuntimeError("JWT_SECRET must be a random value of at least 32 characters in production")
DB_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://tracker:tracker_dev@localhost:15434/tracker_demo")
SECRET = os.environ.get("JWT_SECRET", "demo-only-secret-change-me-in-any-real-environment")
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
SESSION_HOURS = 8
LOCK_AFTER, LOCK_MINUTES = 5, 15

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def err(status: int, code: str, message: str):
    return HTTPException(status, {"code": code, "message": message})


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt(rounds=10)).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bool(h) and bcrypt.checkpw(p.encode()[:72], h.encode())
    except ValueError:
        return False


def check_password_strength(p: str):
    if len(p) < 10 or p.lower() == p or not any(c.isdigit() for c in p):
        raise err(422, "WEAK_PASSWORD", "Use at least 10 characters with upper and lower case letters and a number.")


def new_token() -> tuple[str, str]:
    t = secrets.token_urlsafe(32)
    return t, hashlib.sha256(t.encode()).hexdigest()


def hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def issue_jwt(user: m.User, tenant_id: int | None, minutes: int | None = None) -> str:
    exp = datetime.now(timezone.utc) + (timedelta(minutes=minutes) if minutes else timedelta(hours=SESSION_HOURS))
    return jwt.encode({"sub": str(user.id), "tid": tenant_id, "ep": user.token_epoch, "exp": exp}, SECRET, algorithm="HS256")


def audit(db: Session, tenant_id, actor_id, action, entity="", entity_id="", **detail):
    db.add(m.AuditEvent(tenant_id=tenant_id, actor_id=actor_id, action=action, entity=entity, entity_id=str(entity_id), detail=detail))


@dataclass
class Ctx:
    db: Session
    user: m.User
    tenant: m.Tenant | None
    membership: m.Membership | None
    role: m.Role | None
    perms: set = field(default_factory=set)
    modules: dict = field(default_factory=dict)

    @property
    def tid(self) -> int:
        return self.tenant.id

    def scope(self, cap: str) -> str | None:
        """Widest scope held for a capability: all > team > assigned > own. Unscoped capabilities return 'all'."""
        for s in SCOPE_ORDER:
            if f"{cap}:{s}" in self.perms:
                return s
        return "all" if cap in self.perms else None

    def has(self, cap: str) -> bool:
        return self.scope(cap) is not None

    def entitled(self, module: str) -> bool:
        return bool(self.modules.get(module))

    def can(self, cap: str) -> bool:
        return self.has(cap) and self.entitled(AREA_MODULE.get(cap.split(".")[0], "core"))

    def require(self, cap: str) -> str:
        area = cap.split(".")[0]
        mod = AREA_MODULE.get(area, "core")
        if not self.entitled(mod):
            raise err(403, "ENTITLEMENT_DENIED", f"The '{mod}' module is not enabled for this organization.")
        s = self.scope(cap)
        if s is None:
            raise err(403, "FORBIDDEN", "Your role does not allow this action.")
        return s

    def team_user_ids(self) -> set:
        """Users in the same team, plus direct reports (team scope)."""
        ids = {self.user.id}
        rows = self.db.execute(select(m.Membership).where(m.Membership.tenant_id == self.tid)).scalars().all()
        mine = self.membership.team if self.membership else ""
        for r in rows:
            if (mine and r.team == mine) or r.manager_user_id == self.user.id:
                ids.add(r.user_id)
        return ids


def _decode(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise err(401, "UNAUTHENTICATED", "Sign in to continue.")
    try:
        return jwt.decode(authorization.split(" ", 1)[1], SECRET, algorithms=["HS256"])
    except JWTError:
        raise err(401, "SESSION_EXPIRED", "Your session has expired. Sign in again.")


def load_ctx(db: Session, authorization: str | None, need_tenant=True) -> Ctx:
    p = _decode(authorization)
    user = db.get(m.User, int(p["sub"]))
    if not user or user.status != "active" or user.token_epoch != p.get("ep"):
        raise err(401, "SESSION_EXPIRED", "Your session has expired. Sign in again.")
    tid = p.get("tid")
    if not tid:
        if need_tenant:
            raise err(403, "NO_TENANT", "No organization is selected.")
        return Ctx(db, user, None, None, None)
    mem = db.execute(select(m.Membership).where(m.Membership.user_id == user.id, m.Membership.tenant_id == tid)).scalar_one_or_none()
    tenant = db.get(m.Tenant, tid)
    if not mem or mem.status != "active" or not tenant or tenant.status == "suspended":
        raise err(403, "NO_ACCESS", "You no longer have access to this organization.")
    role = db.get(m.Role, mem.role_id)
    ents = {e.module: e.enabled for e in db.execute(select(m.Entitlement).where(m.Entitlement.tenant_id == tid)).scalars()}
    return Ctx(db, user, tenant, mem, role, set(role.perms), ents)


def ctx(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> Ctx:
    return load_ctx(db, authorization)


def platform_ctx(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> Ctx:
    c = load_ctx(db, authorization, need_tenant=False)
    if not c.user.is_platform_admin:
        raise err(403, "FORBIDDEN", "Platform administrators only.")
    return c
