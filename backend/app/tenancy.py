"""Tenant creation: roles, entitlements and the first owner (invited by email)."""
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import mail, models as m
from .core import ENV, err, new_token
from .perms import DEFAULT_MODULES, ROLE_DEFAULTS


def seed_roles_and_modules(db: Session, tenant: m.Tenant) -> dict:
    from . import org_kit
    roles = org_kit.seed_roles(db, tenant.id)  # the company's roles, in the shared organisation kit
    for mod, on in DEFAULT_MODULES.items():
        db.add(m.Entitlement(tenant_id=tenant.id, module=mod, enabled=on))
    db.flush()
    return roles


def create_tenant(db: Session, name: str, owner_email: str, owner_name: str, plan="growth", demo=False):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "org"
    if db.execute(select(m.Tenant).where(m.Tenant.slug == slug)).scalar_one_or_none():
        raise err(409, "DUPLICATE", "An organization with a similar name already exists.")
    t = m.Tenant(name=name, slug=slug, plan=plan, is_demo=demo)
    db.add(t)
    db.flush()
    roles = seed_roles_and_modules(db, t)
    u = db.execute(select(m.User).where(m.User.email == owner_email)).scalar_one_or_none()
    link, sent = None, False
    if not u:
        u = m.User(email=owner_email, name=owner_name, status="invited")
        db.add(u)
        db.flush()
        tok, h = new_token()
        db.add(m.AuthToken(user_id=u.id, purpose="invite", token_hash=h, expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
        subj, body = mail.invite_email(u.name, name, tok)
        sent = mail.send(u.email, subj, body)
        if ENV == "demo":  # demo only: the one-time link is shown on screen even when the email was sent, so walkthroughs can continue
            link = f"{mail.public_url()}/reset?token={tok}"
    from . import people
    db.flush()
    people.add_person(db, t.id, u, "owner", title="Owner", actor="system")
    return t, link, sent
