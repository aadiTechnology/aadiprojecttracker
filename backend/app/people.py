"""People, roles and departments for Project Tracker, on the shared organisation kit.

The kit's tables (org_members, org_roles, org_departments) are the only place a person's role, title, department, manager and status live.
Tracker's own `memberships` table keeps just what the kit does not know about a person in a company: their team and their monthly-hours
override. Everything else in Tracker asks this module, so there is one answer to "who is in this company, and what may they do".

Statuses: a person is `active`, `invited` (their account has no password yet) or `suspended`. "Live" means active or invited: the
people a company has, who can be given work. Only `active` people can sign in (their account status says so as well)."""
from __future__ import annotations

from dataclasses import dataclass

from aadi_org.service import OrgError, OrgService
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m

K = m.KIT
LIVE = ("active", "invited")


def tkey(tenant_id: int) -> str:
    return str(tenant_id)


@dataclass
class Person:
    id: int                  # Tracker user id
    member_id: int           # the kit's id for this person
    name: str
    email: str
    title: str
    team: str
    hours_override: int | None
    department_id: int | None  # the kit's department id
    manager_user_id: int | None
    status: str              # active | invited | suspended
    role_id: int
    role_key: str
    role_name: str

    @property
    def live(self) -> bool:
        return self.status in LIVE


def _uid(member) -> int | None:
    return int(member.user_id) if member.user_id and str(member.user_id).isdigit() else None


def people(db: Session, tenant_id: int, live_only: bool = True) -> dict[int, Person]:
    """Everyone in a company, keyed by Tracker user id."""
    tk = tkey(tenant_id)
    members = db.scalars(select(K.Member).where(K.Member.tenant_id == tk)).all()
    roles = {r.id: r for r in db.scalars(select(K.Role).where(K.Role.tenant_id == tk))}
    profile = {p.user_id: p for p in db.scalars(select(m.Membership).where(m.Membership.tenant_id == tenant_id))}
    users = {u.id: u for u in db.scalars(select(m.User).where(m.User.id.in_([i for i in (_uid(x) for x in members) if i is not None] or [-1])))}
    by_member = {x.id: x for x in members}
    out: dict[int, Person] = {}
    for x in members:
        uid = _uid(x)
        if uid is None or uid not in users or (live_only and x.status not in LIVE):
            continue
        u, p, r = users[uid], profile.get(uid), roles.get(x.role_id)
        mgr = by_member.get(x.manager_id) if x.manager_id else None
        out[uid] = Person(id=uid, member_id=x.id, name=u.name, email=u.email, title=x.title or "", team=(p.team if p else "") or "", hours_override=p.hours_override if p else None,
                          department_id=x.department_id, manager_user_id=_uid(mgr) if mgr else None, status=x.status, role_id=x.role_id,
                          role_key=r.key if r else "", role_name=r.name if r else "")
    return out


def person(db: Session, tenant_id: int, user_id: int, live_only: bool = True) -> Person | None:
    return people(db, tenant_id, live_only).get(user_id)


def live_ids(db: Session, tenant_id: int) -> set[int]:
    return set(people(db, tenant_id))


def is_live(db: Session, tenant_id: int, user_id: int) -> bool:
    x = member(db, tenant_id, user_id)
    return x is not None and x.status in LIVE


def count_live(db: Session, tenant_id: int) -> int:
    return len(people(db, tenant_id))


def member(db: Session, tenant_id: int, user_id: int):
    """The kit's record for a person, or None."""
    return db.scalar(select(K.Member).where(K.Member.tenant_id == tkey(tenant_id), K.Member.user_id == str(user_id)))


def profile(db: Session, tenant_id: int, user_id: int, create: bool = False) -> m.Membership | None:
    row = db.scalar(select(m.Membership).where(m.Membership.tenant_id == tenant_id, m.Membership.user_id == user_id))
    if row is None and create:
        row = m.Membership(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.flush()
    return row


def tenant_ids_of(db: Session, user_id: int) -> list[int]:
    """Companies a person belongs to (live), in the order of their membership."""
    rows = db.scalars(select(K.Member).where(K.Member.user_id == str(user_id), K.Member.status.in_(LIVE)).order_by(K.Member.id)).all()
    return [int(r.tenant_id) for r in rows if str(r.tenant_id).isdigit()]


def memberships_of(db: Session, user_id: int) -> list[tuple[int, str, str]]:
    """(tenant id, role key, role name) for each company a person is live in."""
    out = []
    for x in db.scalars(select(K.Member).where(K.Member.user_id == str(user_id), K.Member.status == "active").order_by(K.Member.id)):
        r = db.get(K.Role, x.role_id)
        if str(x.tenant_id).isdigit():
            out.append((int(x.tenant_id), r.key if r else "", r.name if r else ""))
    return out


# ---- departments ----------------------------------------------------------------------------------------------------------------
def departments(db: Session, tenant_id: int) -> list:
    return list(db.scalars(select(K.Department).where(K.Department.tenant_id == tkey(tenant_id)).order_by(K.Department.name)))


def department(db: Session, tenant_id: int, department_id: int | None):
    if department_id is None:
        return None
    d = db.get(K.Department, department_id)
    return d if d is not None and d.tenant_id == tkey(tenant_id) else None


def department_names(db: Session, tenant_id: int) -> dict[int, str]:
    return {d.id: d.name for d in departments(db, tenant_id)}


def head_user_id(db: Session, dept) -> int | None:
    """The Tracker user id of a department's head, or None."""
    if dept is None or dept.head_member_id is None:
        return None
    x = db.get(K.Member, dept.head_member_id)
    return _uid(x) if x is not None else None


def department_heads(db: Session, tenant_id: int) -> dict[int, int | None]:
    members = {x.id: _uid(x) for x in db.scalars(select(K.Member).where(K.Member.tenant_id == tkey(tenant_id)))}
    return {d.id: members.get(d.head_member_id) if d.head_member_id else None for d in departments(db, tenant_id)}


# ---- roles ----------------------------------------------------------------------------------------------------------------------
def roles(db: Session, tenant_id: int) -> list:
    return list(db.scalars(select(K.Role).where(K.Role.tenant_id == tkey(tenant_id)).order_by(K.Role.id)))


def role(db: Session, tenant_id: int, role_id: int):
    r = db.get(K.Role, role_id)
    return r if r is not None and r.tenant_id == tkey(tenant_id) else None


def role_by_key(db: Session, tenant_id: int, key: str):
    return db.scalar(select(K.Role).where(K.Role.tenant_id == tkey(tenant_id), K.Role.key == key))


def role_counts(db: Session, tenant_id: int) -> dict[int, int]:
    counts: dict[int, int] = {}
    for x in db.scalars(select(K.Member).where(K.Member.tenant_id == tkey(tenant_id))):
        counts[x.role_id] = counts.get(x.role_id, 0) + 1
    return counts


def active_owner_count(db: Session, tenant_id: int, owner_key: str = "owner") -> int:
    r = role_by_key(db, tenant_id, owner_key)
    if r is None:
        return 0
    return sum(1 for x in db.scalars(select(K.Member).where(K.Member.tenant_id == tkey(tenant_id), K.Member.role_id == r.id, K.Member.status == "active")))


# ---- changing people -------------------------------------------------------------------------------------------------------------
def service(db: Session) -> OrgService:
    from .org_kit import CATALOG
    return OrgService(db, K, CATALOG)


def add_person(db: Session, tenant_id: int, user: m.User, role_key: str, title: str = "", team: str = "", manager_user_id: int | None = None,
               department_id: int | None = None, actor: str = "") -> Person:
    """Make a Tracker user a member of a company with a role. The kit keeps the record; the profile row keeps team and hours."""
    r = role_by_key(db, tenant_id, role_key)
    if r is None:
        raise OrgError(422, "UNKNOWN_ROLE", "Unknown role.")
    mgr = member(db, tenant_id, manager_user_id) if manager_user_id else None
    out = service(db).create_member(tkey(tenant_id), actor or "", user.email, user.name, r.id, title, department_id, mgr.id if mgr else None)
    x = db.get(K.Member, out["id"])
    x.user_id, x.identity_id, x.name = str(user.id), user.identity_id, user.name
    x.status = "invited" if user.status == "invited" else ("suspended" if user.status == "suspended" else "active")
    p = profile(db, tenant_id, user.id, create=True)
    p.team = team
    db.flush()
    return people(db, tenant_id, live_only=False)[user.id]


def set_status(db: Session, tenant_id: int, user_id: int, status: str) -> bool:
    """active or suspended. Returns True when something changed. Never reactivates a person whose account has no password (they stay invited)."""
    x = member(db, tenant_id, user_id)
    if x is None:
        return False
    u = db.get(m.User, user_id)
    if status == "suspended":
        new = "suspended"
    else:
        new = "invited" if u is not None and u.status == "invited" else "active"
    if x.status == new:
        return False
    x.status = new
    db.flush()
    return True


def mark_active(db: Session, user: m.User) -> None:
    """A person who was invited has now set their password: everywhere they were `invited` they are now `active`."""
    for x in db.scalars(select(K.Member).where(K.Member.user_id == str(user.id), K.Member.status == "invited")):
        x.status = "active"
    db.flush()


def set_team(db: Session, tenant_id: int, user_id: int, team: str) -> None:
    profile(db, tenant_id, user_id, create=True).team = team


def set_hours(db: Session, tenant_id: int, user_id: int, hours: int | None) -> None:
    profile(db, tenant_id, user_id, create=True).hours_override = hours


def set_department(db: Session, tenant_id: int, user_id: int, department_id: int | None) -> None:
    x = member(db, tenant_id, user_id)
    x.department_id = department_id
    db.flush()


def set_title(db: Session, tenant_id: int, user_id: int, title: str) -> None:
    member(db, tenant_id, user_id).title = title


def set_manager(db: Session, tenant_id: int, user_id: int, manager_user_id: int | None) -> None:
    mgr = member(db, tenant_id, manager_user_id) if manager_user_id else None
    member(db, tenant_id, user_id).manager_id = mgr.id if mgr else None


def set_role(db: Session, tenant_id: int, user_id: int, role_id: int) -> None:
    member(db, tenant_id, user_id).role_id = role_id
    db.flush()


def create_department(db: Session, tenant_id: int, name: str):
    d = K.Department(tenant_id=tkey(tenant_id), name=name)
    db.add(d)
    db.flush()
    return d


def set_head(db: Session, dept, head_user_id_: int | None) -> None:
    x = member(db, int(dept.tenant_id), head_user_id_) if head_user_id_ else None
    dept.head_member_id = x.id if x else None
