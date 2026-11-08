"""Sign-in through Aadi Identity (OpenID Connect, authorization code with PKCE).

Additive and switched by AUTH_MODE: local (default, nothing changes) | both (pilot: Identity button plus the old form) |
platform (Identity only). Project Tracker keeps its own users, companies, roles and permissions: Identity only says who the
person is and which company they are signing in to. A person with no local membership is refused, never given a role.
"""
import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..core import SECRET, audit, err, get_db

router = APIRouter(prefix="/api/auth", tags=["sso"])

MODE = os.environ.get("AUTH_MODE", "local").lower()  # local | both | platform
ISSUER = os.environ.get("IDENTITY_ISSUER", "https://id.aadiprojecttracker.aaditechnology.com").rstrip("/")
CLIENT_ID = os.environ.get("IDENTITY_CLIENT_ID", "tracker-web")
CLIENT_SECRET = os.environ.get("IDENTITY_CLIENT_SECRET", "")  # empty = public client (PKCE only)
PRODUCT = os.environ.get("IDENTITY_PRODUCT", "tracker")
BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/")
AUTO_LINK_EMAIL = os.environ.get("IDENTITY_AUTO_LINK_EMAIL", "true").lower() == "true"
SSO_SESSION_MINUTES = int(os.environ.get("IDENTITY_SESSION_MINUTES", "60"))  # shorter than a local session so revocations bite sooner
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true" if BASE_URL.startswith("https") else "false").lower() == "true"
TX_COOKIE = "sso_tx"

_jwks = {"at": 0.0, "keys": []}
_used_codes: dict[str, float] = {}


def enabled() -> bool:
    return MODE in ("both", "platform")


def local_login_allowed() -> bool:
    return MODE != "platform"


def redirect_uri() -> str:
    return f"{BASE_URL}/api/auth/sso/callback"


def _get_json(url: str, data: dict | None = None, headers: dict | None = None) -> dict:
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def _signing_keys(force=False) -> list:
    if force or time.time() - _jwks["at"] > 300 or not _jwks["keys"]:
        _jwks["keys"] = _get_json(f"{ISSUER}/.well-known/jwks.json").get("keys", [])
        _jwks["at"] = time.time()
    return _jwks["keys"]


def verify_identity_token(token: str, audience: str, nonce: str | None = None) -> dict:
    kid = jwt.get_unverified_header(token).get("kid")
    for attempt in (0, 1):  # a rotated key shows up after one refresh
        key = next((k for k in _signing_keys(force=attempt == 1) if k.get("kid") == kid), None)
        if key:
            break
    else:
        raise JWTError("unknown signing key")
    claims = jwt.decode(token, key, algorithms=["RS256"], audience=audience, issuer=ISSUER)
    if nonce is not None and claims.get("nonce") != nonce:
        raise JWTError("nonce mismatch")
    return claims


def exchange_code(code: str, verifier: str) -> dict:
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri(), "code_verifier": verifier, "client_id": CLIENT_ID}
    if CLIENT_SECRET:
        data["client_secret"] = CLIENT_SECRET
    return _get_json(f"{ISSUER}/token", data)


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


@router.get("/config")
def config():
    """Tells the sign-in screen which options to show."""
    logout = f"{ISSUER}/logout?" + urllib.parse.urlencode({"client_id": CLIENT_ID, "post_logout_redirect_uri": BASE_URL + "/"})
    return {"mode": MODE, "sso": enabled(), "local": local_login_allowed(), "start_url": "/api/auth/sso/start",
            "logout_url": logout if enabled() else None, "hub_url": ISSUER + "/" if enabled() else None}


@router.get("/sso/start")
def start(tenant: str = ""):
    if not enabled():
        raise err(404, "NOT_FOUND", "Not found.")
    verifier, state, nonce = secrets.token_urlsafe(48), secrets.token_urlsafe(16), secrets.token_urlsafe(10)
    q = {"response_type": "code", "client_id": CLIENT_ID, "redirect_uri": redirect_uri(), "scope": "openid profile email", "state": state,
         "nonce": nonce, "code_challenge": _b64u(hashlib.sha256(verifier.encode()).digest()), "code_challenge_method": "S256"}
    if tenant:
        q["tenant"] = tenant
    tx = jwt.encode({"v": verifier, "s": state, "n": nonce, "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, SECRET, algorithm="HS256")
    resp = RedirectResponse(f"{ISSUER}/authorize?{urllib.parse.urlencode(q)}", 303)
    resp.set_cookie(TX_COOKIE, tx, max_age=600, httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/api/auth/sso")
    return resp


def _fail(reason: str):
    resp = RedirectResponse(f"{BASE_URL}/?sso_error={reason}", 303)
    resp.delete_cookie(TX_COOKIE, path="/api/auth/sso")
    return resp


@router.get("/sso/callback")
def callback(request: Request, code: str = "", state: str = "", error: str = "", db: Session = Depends(get_db)):
    if not enabled():
        raise err(404, "NOT_FOUND", "Not found.")
    if error:
        return _fail("denied")
    try:
        tx = jwt.decode(request.cookies.get(TX_COOKIE, ""), SECRET, algorithms=["HS256"])
    except JWTError:
        return _fail("expired")
    if not code or not secrets.compare_digest(tx["s"], state):
        return _fail("state")
    try:
        tok = exchange_code(code, tx["v"])
        claims = verify_identity_token(tok["id_token"], CLIENT_ID, tx["n"])
        verify_identity_token(tok["access_token"], PRODUCT)
    except (urllib.error.URLError, JWTError, KeyError, ValueError):
        return _fail("exchange")
    user = _local_user(db, claims)
    tenant = _local_tenant(db, claims)
    if not user or not tenant:
        return _fail("no_account" if not user else "no_company")
    mem = db.execute(select(m.Membership).where(m.Membership.user_id == user.id, m.Membership.tenant_id == tenant.id)).scalar_one_or_none()
    if user.status != "active" or not mem or mem.status != "active" or tenant.status == "suspended":
        audit(db, tenant.id, user.id, "auth.sso_denied", "user", user.id)
        db.commit()
        return _fail("no_access")
    audit(db, tenant.id, user.id, "auth.sso_login", "user", user.id)
    db.commit()
    one_time = jwt.encode({"purpose": "sso", "sub": str(user.id), "tid": tenant.id, "ep": user.token_epoch, "jti": secrets.token_urlsafe(12),
                           "exp": datetime.now(timezone.utc) + timedelta(seconds=60)}, SECRET, algorithm="HS256")
    resp = RedirectResponse(f"{BASE_URL}/?sso={one_time}", 303)
    resp.delete_cookie(TX_COOKIE, path="/api/auth/sso")
    return resp


def _local_user(db: Session, claims: dict) -> m.User | None:
    u = db.execute(select(m.User).where(m.User.identity_id == claims["sub"])).scalar_one_or_none()
    if u:
        return u
    email = (claims.get("email") or "").strip().lower()
    u = db.execute(select(m.User).where(m.User.email == email)).scalar_one_or_none() if AUTO_LINK_EMAIL and email else None
    if u and not u.identity_id:
        u.identity_id = claims["sub"]  # first sign-in links the two accounts
        db.flush()
        return u
    return None


def _local_tenant(db: Session, claims: dict) -> m.Tenant | None:
    t = db.execute(select(m.Tenant).where(m.Tenant.identity_tenant_id == claims["tid"])).scalar_one_or_none()
    if t:
        return t
    t = db.execute(select(m.Tenant).where(m.Tenant.slug == claims.get("tenant_slug", ""))).scalar_one_or_none()
    if t and not t.identity_tenant_id:
        t.identity_tenant_id = claims["tid"]
        db.flush()
        return t
    return None


class Exchange(BaseModel):
    code: str


@router.post("/sso/exchange")
def exchange(b: Exchange, db: Session = Depends(get_db)):
    """The browser trades the one-time code from the callback for a normal Project Tracker session token."""
    from ..core import issue_jwt

    try:
        p = jwt.decode(b.code, SECRET, algorithms=["HS256"])
    except JWTError:
        raise err(401, "SSO_EXPIRED", "The sign-in link expired. Sign in again.")
    now = time.time()
    for k in [k for k, t in _used_codes.items() if t < now]:
        del _used_codes[k]
    if p.get("purpose") != "sso" or p["jti"] in _used_codes:
        raise err(401, "SSO_EXPIRED", "The sign-in link was already used. Sign in again.")
    _used_codes[p["jti"]] = now + 120
    user = db.get(m.User, int(p["sub"]))
    if not user or user.status != "active" or user.token_epoch != p.get("ep"):
        raise err(401, "SSO_EXPIRED", "The sign-in link expired. Sign in again.")
    return {"token": issue_jwt(user, p["tid"], minutes=SSO_SESSION_MINUTES), "platform_admin": False}
