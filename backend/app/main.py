import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import core
from .perms import MODULES
from .routers import auth, costing, delivery, demo, insights, org, platform, work

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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    r = await call_next(request)
    r.headers.setdefault("X-Content-Type-Options", "nosniff")
    r.headers.setdefault("Referrer-Policy", "same-origin")
    r.headers.setdefault("X-Frame-Options", "DENY")
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


for r in (auth.router, org.router, work.router, delivery.router, costing.router, insights.router, platform.router):
    app.include_router(r)
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
