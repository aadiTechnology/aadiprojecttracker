import logging
import os
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from aadi_org.router import create_org_router
from fastapi import Depends

from . import core, identity_sync, org_kit
from .perms import MODULES
from .routers import assistant, auth, costing, delivery, demo, finance, insights, org, platform, sso, work

log = logging.getLogger("tracker")
ROOT = Path(__file__).resolve().parent.parent


def migrate():
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", core.DB_URL.replace("%", "%%"))
    command.upgrade(cfg, "head")


app = FastAPI(title="Aadi Project Tracker API", version="0.1.0", docs_url="/docs" if core.ENV == "demo" else None, redoc_url=None, openapi_url="/openapi.json" if core.ENV == "demo" else None)
app.add_middleware(CORSMiddleware, allow_origins=core.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"], allow_credentials=False)


@app.on_event("startup")
def _startup():
    migrate()
    # One-time maintenance, switched on by setting all three variables (then it runs once per id, however often the app restarts):
    #   APP_MAINTENANCE=reset-and-seed-aadi-test   APP_MAINTENANCE_ID=<any new text>   APP_MAINTENANCE_CONFIRM=ERASE-ALL-DATA
    if (os.environ.get("APP_MAINTENANCE") == "reset-and-seed-aadi-test" and os.environ.get("APP_MAINTENANCE_CONFIRM") == "ERASE-ALL-DATA"
            and os.environ.get("APP_MAINTENANCE_ID")):
        from . import seed_aadi_test

        with core.SessionLocal() as db:
            out = seed_aadi_test.maintenance_once(db, os.environ["APP_MAINTENANCE_ID"])
        print("Maintenance:", "already done for this id" if out is None else out, flush=True)
    hours = float(os.environ.get("IDENTITY_RECONCILE_HOURS") or 0)  # 0 = off; 24 = nightly, as an in-process safety net
    if hours > 0 and sso.enabled() and identity_sync.WEBHOOK_SECRET:
        identity_sync.start_reconcile_loop(sso.ISSUER, hours)


_hits: dict = {}
LOGIN_RATE = int(os.environ.get("LOGIN_RATE_PER_MIN", "60"))


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Per-address limit on sign-in and password-reset calls (on top of the per-account lockout), so one address cannot guess passwords across accounts."""
    if request.method == "POST" and request.url.path in ("/api/auth/login", "/api/auth/forgot", "/api/auth/reset"):
        ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?"))
        now = time.time()
        recent = [t for t in _hits.get(ip, []) if now - t < 60]
        if len(recent) >= LOGIN_RATE:
            return JSONResponse(status_code=429, content={"detail": {"code": "RATE_LIMITED", "message": "Too many attempts from this address. Wait a minute and try again."}})
        recent.append(now)
        _hits[ip] = recent
        if len(_hits) > 5000:
            for k_ in [k_ for k_, v in _hits.items() if not v or now - v[-1] > 60]:
                _hits.pop(k_, None)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    r = await call_next(request)
    r.headers.setdefault("X-Content-Type-Options", "nosniff")
    r.headers.setdefault("Referrer-Policy", "same-origin")
    r.headers.setdefault("X-Frame-Options", "DENY")
    r.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    r.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https: http://localhost:*; "
                         "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    if request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https":
        r.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/api"):
        r.headers.setdefault("Cache-Control", "no-store")
    return r


@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    d = exc.detail
    body = {"detail": d} if isinstance(d, dict) else {"detail": {"code": "ERROR", "message": str(d)}}
    return JSONResponse(body, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    return JSONResponse({"detail": {"code": "VALIDATION", "message": f"{loc}: {first.get('msg', 'invalid value')}".strip(": ")}}, status_code=422)


for r in (auth.router, org.router, work.router, delivery.router, costing.router, insights.router, finance.router, assistant.router, platform.router, sso.router):
    app.include_router(r)
app.include_router(create_org_router(get_db=core.get_db, principal=org_kit.principal, M=org_kit.M, catalog=org_kit.CATALOG, hooks=org_kit.TrackerHooks()),
                   prefix="/api/kit", dependencies=[Depends(org_kit.keep_in_step)])
if core.ENV == "demo":
    app.include_router(demo.router)


@app.get("/api/catalogue")
def catalogue():
    return [{"key": k, "label": v[0], "pillar": v[1], "priority": v[2]} for k, v in MODULES.items()]


DIST = ROOT.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": {"code": "NOT_FOUND", "message": "Not found."}}, status_code=404)
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
