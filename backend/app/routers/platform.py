"""SaaS Platform Administrator: tenant lifecycle and entitlements ONLY. No endpoint here returns tenant business content
(projects, customers, financials, employees). Support access to a tenant is a separate controlled, audited process (not built)."""
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from .. import models as m
from ..core import Ctx, audit, err, hash_password, platform_ctx
from ..perms import DEFAULT_MODULES, MODULES
from ..tenancy import create_tenant

router = APIRouter(prefix="/api/platform", tags=["platform"])


@router.get("/tenants")
def tenants(c: Ctx = Depends(platform_ctx)):
    users: dict[int, int] = {}
    for x in c.db.scalars(select(m.KIT.Member)):
        if str(x.tenant_id).isdigit():
            users[int(x.tenant_id)] = users.get(int(x.tenant_id), 0) + 1
    ents = {}
    for e in c.db.execute(select(m.Entitlement)).scalars():
        ents.setdefault(e.tenant_id, {})[e.module] = e.enabled
    return [{"id": t.id, "name": t.name, "slug": t.slug, "status": t.status, "plan": t.plan, "users": users.get(t.id, 0),
             "demo": t.is_demo, "modules": ents.get(t.id, {}), "created_at": t.created_at.isoformat()}
            for t in c.db.execute(select(m.Tenant).order_by(m.Tenant.id)).scalars()]


class TenantIn(BaseModel):
    name: str
    owner_email: str
    owner_name: str
    plan: str = "growth"


@router.post("/tenants")
def new_tenant(b: TenantIn, c: Ctx = Depends(platform_ctx)):
    if not b.name.strip() or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", b.owner_email):
        raise err(422, "VALIDATION", "Enter an organization name and a valid owner email.")
    t, link, sent = create_tenant(c.db, b.name.strip(), b.owner_email.strip().lower(), b.owner_name.strip() or "Owner", b.plan)
    audit(c.db, t.id, c.user.id, "tenant.create", "tenant", t.id, email_sent=sent)
    c.db.commit()
    return {"id": t.id, "invite_link": link, "email_sent": sent}


class StatusIn(BaseModel):
    status: str


@router.post("/tenants/{tid}/status")
def tenant_status(tid: int, b: StatusIn, c: Ctx = Depends(platform_ctx)):
    t = c.db.get(m.Tenant, tid)
    if not t or b.status not in ("active", "suspended", "trial"):
        raise err(422, "VALIDATION", "Unknown tenant or status.")
    t.status = b.status
    audit(c.db, tid, c.user.id, "tenant.status", "tenant", tid, status=b.status)
    c.db.commit()
    return {"ok": True}


class ModuleIn(BaseModel):
    enabled: bool


@router.put("/tenants/{tid}/modules/{module}")
def tenant_module(tid: int, module: str, b: ModuleIn, c: Ctx = Depends(platform_ctx)):
    if module not in MODULES or module == "core":
        raise err(422, "VALIDATION", "Unknown or non-optional module.")
    e = c.db.execute(select(m.Entitlement).where(m.Entitlement.tenant_id == tid, m.Entitlement.module == module)).scalar_one_or_none()
    if e:
        e.enabled = b.enabled
    else:
        c.db.add(m.Entitlement(tenant_id=tid, module=module, enabled=b.enabled))
    audit(c.db, tid, c.user.id, "entitlement.set", "tenant", tid, module=module, enabled=b.enabled)
    c.db.commit()
    return {"ok": True}
