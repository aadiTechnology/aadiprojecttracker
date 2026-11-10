"""Project Tracker on the shared organisation kit (aadi-org-kit).

The kit owns people, departments and roles for the People and roles screen. Tracker's own tables (memberships, roles, departments)
stay because costing, work and timesheets read them in about seventy places. The two are kept identical by two idempotent passes:

  pull(db, tenant)   Tracker's tables -> kit   (before any kit request, and after Tracker code changes people)
  push(db, tenant)   kit -> Tracker's tables   (after any change made through the kit)

Rows are matched by `kit_id`, never by name, so a rename is a rename. Fields only Tracker knows (team, hours_override, salary) are
never touched by either pass. Tracker's "org.admin" capability and the kit's org.users.manage / org.roles.manage / org.departments.manage
are translated both ways."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aadi_org.catalog import Capability, ProductCatalog, RoleDef
from aadi_org.caps import SCOPES
from aadi_org.router import OrgHooks, Principal
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import mail, models as m
from .core import Ctx, ctx, get_db, new_token
from .perms import AREA_MODULE, MODULES, ROLE_DEFAULTS

log = logging.getLogger("tracker.kit")
M = m.KIT

# ---- the catalog: Tracker's capabilities as the kit describes them ---------------------------------------------------
_scoped = {c.split(":")[0] for _, (_, perms) in ROLE_DEFAULTS.items() for c in perms if ":" in c}
_bases = sorted({c.split(":")[0] for _, (_, perms) in ROLE_DEFAULTS.items() for c in perms})
_TRACKERS_OWN = {"org.admin"}  # translated into the kit's organisation capabilities, see to_kit
KIT_ORG = ("org.users.view", "org.users.manage", "org.departments.manage", "org.roles.manage", "audit.view")
SALARY_CAPS = ("salary.view", "salary.manage", "costing.cost")


def to_kit(perms: list[str]) -> list[str]:
    """Tracker's role permissions as kit capabilities: org.admin becomes the kit's organisation capabilities."""
    out = [p for p in perms if p not in _TRACKERS_OWN]
    if "org.admin" in perms or "departments.manage" in perms:
        out.append("org.departments.manage")
    if "org.admin" in perms:
        out += ["org.users.view", "org.users.manage", "org.roles.manage"]
    return sorted(set(out))


def to_tracker(caps: list[str]) -> list[str]:
    """The kit's capabilities as Tracker role permissions: users.manage together with roles.manage means org.admin."""
    out = set(caps)
    if "org.users.manage" in out and "org.roles.manage" in out:
        out.add("org.admin")
    return sorted(out)


CATALOG = ProductCatalog(
    product="tracker",
    capabilities=[Capability(b, b.replace(".", ": ").replace("_", " "), SCOPES if b in _scoped else (), AREA_MODULE.get(b.split(".")[0], "core"))
                  for b in _bases if b not in _TRACKERS_OWN and b not in KIT_ORG],
    roles=[RoleDef(k, name, tuple(to_kit(perms))) for k, (name, perms) in ROLE_DEFAULTS.items() if k != "owner"]
    + [RoleDef("owner", ROLE_DEFAULTS["owner"][0], (), "", True)],
    admin_role="owner", default_role="employee", features={k: v[0] for k, v in MODULES.items()},
)


# ---- the two passes -----------------------------------------------------------------------------------------------------
def _status_to_kit(user: m.User, mem: m.Membership) -> str:
    if mem.status == "suspended" or user.status == "suspended":
        return "suspended"
    return "invited" if user.status == "invited" else "active"


def pull(db: Session, tenant_id: int) -> None:
    """Tracker's tables -> kit. Creates what the kit lacks, updates what matches by kit_id. Never deletes."""
    tid = str(tenant_id)
    for r in db.scalars(select(m.Role).where(m.Role.tenant_id == tenant_id)).all():
        kr = db.get(M.Role, r.kit_id) if r.kit_id else None
        if kr is None:  # a role the kit already created from its own defaults is adopted, not duplicated
            kr = db.scalar(select(M.Role).where(M.Role.tenant_id == tid, M.Role.key == r.key))
        if kr is None:
            kr = M.Role(tenant_id=tid, key=r.key, name=r.name, caps=[], is_system=r.is_system)
            db.add(kr)
        want = to_kit(list(r.perms or []))
        if kr.key != r.key or kr.name != r.name or list(kr.caps or []) != want or kr.is_system != r.is_system:
            kr.key, kr.name, kr.caps, kr.is_system = r.key, r.name, want, r.is_system
        db.flush()
        r.kit_id = kr.id
    for d in db.scalars(select(m.Department).where(m.Department.tenant_id == tenant_id)).all():
        kd = db.get(M.Department, d.kit_id) if d.kit_id else db.scalar(select(M.Department).where(M.Department.tenant_id == tid, M.Department.name == d.name))
        if kd is None:
            kd = M.Department(tenant_id=tid, name=d.name)
            db.add(kd)
        kd.name = d.name
        db.flush()
        d.kit_id = kd.id
    rows = db.execute(select(m.Membership, m.User).join(m.User, m.User.id == m.Membership.user_id).where(m.Membership.tenant_id == tenant_id)).all()
    by_user: dict[int, object] = {}
    for mem, u in rows:  # first pass: the people themselves
        km = db.get(M.Member, mem.kit_id) if mem.kit_id else db.scalar(select(M.Member).where(M.Member.tenant_id == tid, M.Member.email == u.email.lower()))
        role = db.get(m.Role, mem.role_id)
        dept = db.get(m.Department, mem.department_id) if mem.department_id else None
        if km is None:
            km = M.Member(tenant_id=tid, email=u.email.lower(), role_id=role.kit_id)
            db.add(km)
        km.user_id, km.identity_id, km.email, km.name = str(u.id), u.identity_id, u.email.lower(), u.name
        km.title, km.role_id, km.department_id, km.status = mem.title, role.kit_id, (dept.kit_id if dept else None), _status_to_kit(u, mem)
        db.flush()
        mem.kit_id = km.id
        by_user[u.id] = km
    for mem, u in rows:  # second pass: reporting lines, once everyone has a kit id
        by_user[u.id].manager_id = by_user[mem.manager_user_id].id if mem.manager_user_id in by_user else None
    for d in db.scalars(select(m.Department).where(m.Department.tenant_id == tenant_id)):
        db.get(M.Department, d.kit_id).head_member_id = by_user[d.head_user_id].id if d.head_user_id in by_user else None
    db.flush()


def push(db: Session, tenant_id: int) -> list[m.User]:
    """Kit -> Tracker's tables. Returns the people who were new to Tracker (so they can be invited)."""
    tid = str(tenant_id)
    new_users: list[m.User] = []
    kit_roles = db.scalars(select(M.Role).where(M.Role.tenant_id == tid)).all()
    for kr in kit_roles:
        r = db.scalar(select(m.Role).where(m.Role.tenant_id == tenant_id, m.Role.kit_id == kr.id))
        if r is None:
            r = db.scalar(select(m.Role).where(m.Role.tenant_id == tenant_id, m.Role.key == kr.key)) or m.Role(tenant_id=tenant_id, key=kr.key, name=kr.name)
            db.add(r)
        r.kit_id, r.key, r.name, r.is_system = kr.id, kr.key, kr.name, kr.is_system
        r.perms = to_tracker(list(kr.caps or []))
    alive = {kr.id for kr in kit_roles}
    for r in db.scalars(select(m.Role).where(m.Role.tenant_id == tenant_id, m.Role.kit_id.is_not(None))).all():
        if r.kit_id not in alive:
            db.delete(r)
    db.flush()
    kit_depts = db.scalars(select(M.Department).where(M.Department.tenant_id == tid)).all()
    for kd in kit_depts:
        d = db.scalar(select(m.Department).where(m.Department.tenant_id == tenant_id, m.Department.kit_id == kd.id))
        if d is None:
            d = db.scalar(select(m.Department).where(m.Department.tenant_id == tenant_id, m.Department.name == kd.name)) or m.Department(tenant_id=tenant_id, name=kd.name)
            db.add(d)
        d.kit_id, d.name = kd.id, kd.name
    alive_d = {kd.id for kd in kit_depts}
    db.flush()
    for d in db.scalars(select(m.Department).where(m.Department.tenant_id == tenant_id, m.Department.kit_id.is_not(None))).all():
        if d.kit_id not in alive_d:
            for mem in db.scalars(select(m.Membership).where(m.Membership.department_id == d.id)):
                mem.department_id = None
            db.flush()
            db.delete(d)
    db.flush()
    role_of = {r.kit_id: r for r in db.scalars(select(m.Role).where(m.Role.tenant_id == tenant_id))}
    dept_of = {d.kit_id: d for d in db.scalars(select(m.Department).where(m.Department.tenant_id == tenant_id))}
    kit_members = db.scalars(select(M.Member).where(M.Member.tenant_id == tid)).all()
    user_of: dict[int, m.User] = {}
    mem_of: dict[int, m.Membership] = {}
    for km in kit_members:
        u = db.get(m.User, int(km.user_id)) if km.user_id else None
        if u is None:
            u = db.scalar(select(m.User).where(m.User.email == km.email))
        if u is None:
            u = m.User(email=km.email, name=km.name or km.email.split("@")[0], status="invited")
            db.add(u)
            db.flush()
            new_users.append(u)
        km.user_id = str(u.id)
        if not km.name:
            km.name = u.name
        mem = db.scalar(select(m.Membership).where(m.Membership.tenant_id == tenant_id, m.Membership.kit_id == km.id)) or \
            db.scalar(select(m.Membership).where(m.Membership.tenant_id == tenant_id, m.Membership.user_id == u.id))
        if mem is None:
            mem = m.Membership(tenant_id=tenant_id, user_id=u.id, role_id=role_of[km.role_id].id)
            db.add(mem)
        mem.kit_id, mem.role_id, mem.title = km.id, role_of[km.role_id].id, km.title
        mem.department_id = dept_of[km.department_id].id if km.department_id in dept_of else None
        if km.status == "suspended" and mem.status != "suspended":
            u.token_epoch += 1  # a suspended person's live sessions end at once
        mem.status = "suspended" if km.status == "suspended" else "active"
        user_of[km.id], mem_of[km.id] = u, mem
    db.flush()
    for km in kit_members:
        mem_of[km.id].manager_user_id = user_of[km.manager_id].id if km.manager_id in user_of else None
    for kd in kit_depts:
        dept_of[kd.id].head_user_id = user_of[kd.head_member_id].id if kd.head_member_id in user_of else None
    db.flush()
    return new_users


def sync_all(db: Session) -> int:
    """Start-up helper: bring every company's kit tables up to date with Tracker's."""
    n = 0
    for t in db.scalars(select(m.Tenant)).all():
        pull(db, t.id)
        n += 1
    db.commit()
    return n


# ---- request plumbing ------------------------------------------------------------------------------------------------------
def principal(c: Ctx = Depends(ctx)) -> Principal:
    """Who is asking, for the kit. The kit's tables are brought up to date with Tracker's before every request."""
    pull(c.db, c.tid)
    c.db.commit()
    return Principal(user_id=str(c.user.id), tenant_id=str(c.tid), email=c.user.email, name=c.user.name, identity_id=c.user.identity_id)


async def keep_in_step(request: Request, p: Principal = Depends(principal), db: Session = Depends(get_db)):
    """Before a role change, refuse what Tracker restricts; after any change made through the kit, copy it to Tracker's tables."""
    write = request.method in ("POST", "PUT", "PATCH", "DELETE")
    if request.method in ("POST", "PUT") and "/roles" in request.url.path:
        try:
            body = await request.json()
        except ValueError:
            body = {}
        wants_salary = any(str(c).split(":")[0] in SALARY_CAPS for c in (body.get("caps") or []))
        if wants_salary:
            last = request.url.path.rstrip("/").rsplit("/", 1)[-1]
            role = db.get(M.Role, int(last)) if last.isdigit() else None
            key = role.key if role else body.get("key", "")
            if key != "finance":
                raise HTTPException(422, "Salary and cost visibility is restricted to the Finance role and the Owner in this release.")
    yield
    if write:
        new = push(db, int(p.tenant_id))
        db.commit()
        invite_new(db, int(p.tenant_id), new)


def invite_new(db: Session, tenant_id: int, users: list[m.User]) -> None:
    """A new person gets Tracker's own invitation unless Aadi Identity is enrolling them (Identity sends its own)."""
    from .identity_client import CLIENT
    t = db.get(m.Tenant, tenant_id)
    if not users or (CLIENT.enabled and t and t.identity_tenant_id):
        return
    for u in users:
        tok, h = new_token()
        db.add(m.AuthToken(user_id=u.id, purpose="invite", token_hash=h, expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
        subj, body = mail.invite_email(u.name, t.name, tok)
        try:
            mail.send(u.email, subj, body)
        except Exception:  # noqa: BLE001 - a mail problem never undoes the person being added
            log.exception("invitation email failed")
    db.commit()


class TrackerHooks(OrgHooks):
    """Tell Aadi Identity about people added, suspended and reactivated through the kit."""

    @staticmethod
    def _identity_tenant(principal: Principal) -> str | None:
        from .core import SessionLocal
        with SessionLocal() as db:
            t = db.get(m.Tenant, int(principal.tenant_id))
            return t.identity_tenant_id if t else None

    def member_created(self, member: dict, principal: Principal):
        from .identity_client import CLIENT
        tid = self._identity_tenant(principal) if CLIENT.enabled else None
        return CLIENT.enrol(tid, member["email"], member.get("name") or "", principal.email) if tid else None

    def member_status_changed(self, member: dict, principal: Principal):
        from .identity_client import CLIENT
        tid = self._identity_tenant(principal) if CLIENT.enabled else None
        if not tid:
            return None
        if member["status"] == "suspended":
            out = CLIENT.remove(tid, member["email"], principal.email)
            return None if (not out["ok"] and "not registered" in out["message"]) else out
        return CLIENT.enrol(tid, member["email"], member.get("name") or "", principal.email)
