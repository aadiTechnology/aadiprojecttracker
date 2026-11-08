"""Keeps Project Tracker in step with Aadi Identity.

Two inputs, one set of rules:
  * events pushed by Identity (signed, near real time), and
  * a periodic reconcile from Identity's snapshot (repairs anything an event missed).

Rules: Project Tracker never creates people or roles from Identity. It only *restricts* (suspend a membership, a person or a company)
when Identity says so, and it only *restores* what an explicit reactivation event says. A reconcile never reactivates anything,
so a suspension an administrator made inside Project Tracker is never undone by a nightly job.
"""
import hashlib
import hmac
import json
import logging
import os
import threading
import time
import urllib.parse
import urllib.request

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .core import audit

log = logging.getLogger("tracker.identity")
PRODUCT = os.environ.get("IDENTITY_PRODUCT") or "tracker"
WEBHOOK_SECRET = os.environ.get("IDENTITY_WEBHOOK_SECRET", "")
TOLERANCE_SECONDS = 300
LIVE_SUBSCRIPTION = ("active", "trial")


def sign(secret: str, timestamp: int, body: str) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()


def signature_ok(header: str | None, body: str, secret: str, now: float | None = None) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in (header or "").split(","))
        ts, sig = int(parts["t"]), parts["v1"]
    except (ValueError, KeyError):
        return False
    if abs((now or time.time()) - ts) > TOLERANCE_SECONDS:
        return False
    return hmac.compare_digest(sig, sign(secret, ts, body))


# ---- finding the local records ----
def find_tenant(db: Session, t: dict) -> m.Tenant | None:
    x = db.execute(select(m.Tenant).where(m.Tenant.identity_tenant_id == t["id"])).scalar_one_or_none()
    return x or db.execute(select(m.Tenant).where(m.Tenant.slug == t.get("slug", ""))).scalar_one_or_none()


def find_user(db: Session, u: dict) -> m.User | None:
    x = db.execute(select(m.User).where(m.User.identity_id == u["id"])).scalar_one_or_none()
    # an unlinked person is matched by e-mail only so that a restriction still lands; they are never linked here
    return x or db.execute(select(m.User).where(m.User.email == (u.get("email") or "").strip().lower(), m.User.identity_id.is_(None))).scalar_one_or_none()


def membership(db: Session, user: m.User, tenant: m.Tenant) -> m.Membership | None:
    return db.execute(select(m.Membership).where(m.Membership.user_id == user.id, m.Membership.tenant_id == tenant.id)).scalar_one_or_none()


# ---- the small actions (each returns True when something changed) ----
def suspend_membership(db: Session, tenant: m.Tenant, user: m.User, why: str) -> bool:
    mem = membership(db, user, tenant)
    if not mem or mem.status == "suspended":
        return False
    mem.status = "suspended"  # the next request from this person is refused: Project Tracker checks the membership every time
    audit(db, tenant.id, None, "identity.membership_suspended", "user", user.id, why=why)
    return True


def restore_membership(db: Session, tenant: m.Tenant, user: m.User) -> bool:
    mem = membership(db, user, tenant)
    if not mem or mem.status != "suspended":
        return False
    mem.status = "active"
    audit(db, tenant.id, None, "identity.membership_restored", "user", user.id)
    return True


def suspend_user(db: Session, user: m.User, why: str) -> bool:
    if user.status == "suspended":
        return False
    user.status = "suspended"
    user.token_epoch += 1  # signs the person out of every company at once
    audit(db, None, None, "identity.user_suspended", "user", user.id, why=why)
    return True


def restore_user(db: Session, user: m.User) -> bool:
    if user.status != "suspended":
        return False
    user.status = "active"
    audit(db, None, None, "identity.user_restored", "user", user.id)
    return True


def set_tenant_state(db: Session, tenant: m.Tenant, allowed: bool, why: str, restore: bool = True) -> bool:
    if not allowed and tenant.status != "suspended":
        tenant.status = "suspended"
        audit(db, tenant.id, None, "identity.tenant_suspended", "tenant", tenant.id, why=why)
        return True
    if allowed and restore and tenant.status == "suspended":
        tenant.status = "active"
        audit(db, tenant.id, None, "identity.tenant_restored", "tenant", tenant.id, why=why)
        return True
    return False


# ---- events ----
def apply_event(db: Session, ev: dict) -> str:
    """Applies one event. Returns what happened (for the response and the logs)."""
    kind = ev.get("type", "")
    tenant = find_tenant(db, ev["tenant"]) if ev.get("tenant") else None
    user = find_user(db, ev["user"]) if ev.get("user") else None
    changed = False
    if kind in ("membership.suspended", "membership.removed") and tenant and user:
        changed = suspend_membership(db, tenant, user, kind)
    elif kind == "membership.reactivated" and tenant and user and user.identity_id:
        changed = restore_membership(db, tenant, user)
    elif kind == "user.suspended" and user:
        changed = suspend_user(db, user, kind)
    elif kind == "user.reactivated" and user and user.identity_id:
        changed = restore_user(db, user)
    elif kind == "user.revoked" and user:
        user.token_epoch += 1
        changed = True
    elif kind == "subscription.changed" and tenant and (ev.get("subscription") or {}).get("product") == PRODUCT:
        changed = set_tenant_state(db, tenant, ev["subscription"]["status"] in LIVE_SUBSCRIPTION, kind)
    elif kind == "tenant.status_changed" and tenant:
        changed = set_tenant_state(db, tenant, ev["tenant"]["status"] in ("active", "trial"), kind)
    elif kind == "membership.added":
        return "noted"  # a person is never given a role automatically; an administrator adds them in Project Tracker
    return "applied" if changed else "no change"


# ---- reconcile ----
def fetch_snapshot(issuer: str) -> dict:
    req = urllib.request.Request(f"{issuer}/api/sync/snapshot?{urllib.parse.urlencode({'product': PRODUCT})}",
                                 headers={"Authorization": f"Bearer {WEBHOOK_SECRET}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def reconcile(db: Session, snapshot: dict) -> dict:
    """Restrictions only. Returns counts so the run can be reported."""
    counts = {"tenants": 0, "memberships": 0, "users": 0}
    for t in snapshot.get("tenants", []):
        tenant = find_tenant(db, t)
        if not tenant:
            continue
        allowed = t["status"] in ("active", "trial") and t["subscription_status"] in LIVE_SUBSCRIPTION
        if set_tenant_state(db, tenant, allowed, "reconcile", restore=False):
            counts["tenants"] += 1
        for mem in t.get("members", []):
            user = find_user(db, {"id": mem["user_id"], "email": mem["email"]})
            if not user:
                continue
            if mem["user_status"] == "suspended" and suspend_user(db, user, "reconcile"):
                counts["users"] += 1
            if mem["membership_status"] != "active" and suspend_membership(db, tenant, user, "reconcile"):
                counts["memberships"] += 1
    audit(db, None, None, "identity.reconcile", "system", "", **counts)
    db.commit()
    return counts


def run_reconcile(issuer: str) -> dict:
    from .core import SessionLocal

    snap = fetch_snapshot(issuer)
    with SessionLocal() as db:
        return reconcile(db, snap)


def start_reconcile_loop(issuer: str, hours: float) -> threading.Thread:
    def loop():
        while True:
            time.sleep(hours * 3600)
            try:
                log.info("identity reconcile: %s", run_reconcile(issuer))
            except Exception as e:  # never stop the loop
                log.warning("identity reconcile failed: %s", e)
    t = threading.Thread(target=loop, name="identity-reconcile", daemon=True)
    t.start()
    return t


if __name__ == "__main__":  # python -m app.identity_sync   (run from cron if the in-process loop is not wanted)
    from .routers.sso import ISSUER

    print(run_reconcile(ISSUER))
