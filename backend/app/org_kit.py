"""Project Tracker on the shared organisation kit (aadi-org-kit).

The kit's tables are the only copy of people, departments and roles. This module holds what makes the kit fit Tracker:
  * CATALOG: Tracker's capabilities and default roles, as the kit describes them;
  * to_kit / to_tracker: Tracker's "org.admin" and "audit.view:all" capabilities, translated to and from the kit's own;
  * seed_roles: the default roles of a new company;
  * principal / keep_in_step: how kit requests are signed in with Tracker's session, the salary rule, and giving a person added through the
    kit's screens a Tracker account (link_new_members) and an invitation (invite_new);
  * TrackerHooks: telling Aadi Identity about people added, suspended and reactivated.
Everything else in Tracker asks app/people.py. Tracker's `memberships` table keeps only team and monthly hours."""
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
    out = [("audit.view" if p.startswith("audit.view:") else p) for p in perms if p not in _TRACKERS_OWN]  # the kit's audit.view has no scope
    if "org.admin" in perms or "departments.manage" in perms:
        out.append("org.departments.manage")
    if "org.admin" in perms:
        out += ["org.users.view", "org.users.manage", "org.roles.manage"]
    return sorted(set(out))


def to_tracker(caps: list[str]) -> list[str]:
    """The kit's capabilities as Tracker role permissions: users.manage together with roles.manage means org.admin."""
    out = set(caps)
    if "audit.view" in out:
        out.discard("audit.view")
        out.add("audit.view:all")  # Tracker's own spelling
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


# ---- roles of a new company -----------------------------------------------------------------------------------------------------------
def seed_roles(db: Session, tenant_id: int) -> dict:
    """The default roles of a new company, created in the kit with exactly Tracker's default permissions (org.admin becomes the kit's organisation capabilities)."""
    tk = str(tenant_id)
    have = {r.key: r for r in db.scalars(select(M.Role).where(M.Role.tenant_id == tk))}
    for key, (name, perms) in ROLE_DEFAULTS.items():
        if key not in have:
            r = M.Role(tenant_id=tk, key=key, name=name, caps=to_kit(list(perms)), is_system=True)
            db.add(r)
            have[key] = r
    db.flush()
    return have


# ---- request plumbing ------------------------------------------------------------------------------------------------------------------
def principal(c: Ctx = Depends(ctx)) -> Principal:
    """Who is asking, for the kit."""
    return Principal(user_id=str(c.user.id), tenant_id=str(c.tid), email=c.user.email, name=c.user.name, identity_id=c.user.identity_id)


async def keep_in_step(request: Request, p: Principal = Depends(principal), db: Session = Depends(get_db)):
    """Before a role change, refuse what Tracker restricts; after any change made through the kit, give a person it just added a Tracker account."""
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
        new = link_new_members(db, int(p.tenant_id))
        db.commit()
        invite_new(db, int(p.tenant_id), new)


def link_new_members(db: Session, tenant_id: int) -> list[m.User]:
    """A person added through the kit's screens has no Tracker account yet: create it (invited), link it, and give them their profile row.
    Returns the people who were new, so they can be invited."""
    tk = str(tenant_id)
    new_users: list[m.User] = []
    for km in db.scalars(select(M.Member).where(M.Member.tenant_id == tk)).all():
        if km.user_id:
            u = db.get(m.User, int(km.user_id))
            if u is not None:
                if km.status == "active" and u.status == "suspended":
                    km.status = "suspended"
                continue
        u = db.scalar(select(m.User).where(m.User.email == km.email))
        if u is None:
            u = m.User(email=km.email, name=km.name or km.email.split("@")[0], status="invited")
            db.add(u)
            db.flush()
            new_users.append(u)
        km.user_id, km.identity_id = str(u.id), u.identity_id
        km.name = km.name or u.name
        if km.status != "suspended":
            km.status = "invited" if u.status == "invited" else "active"
        if db.scalar(select(m.Membership).where(m.Membership.tenant_id == tenant_id, m.Membership.user_id == u.id)) is None:
            db.add(m.Membership(tenant_id=tenant_id, user_id=u.id))
    db.flush()
    return new_users


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
