"""Create or update the Aadi Project Tracker resource in Coolify through its API, then deploy it. Idempotent.
Reads ../.env.coolify (git-ignored; values are never printed). Usage:  python deploy/coolify_deploy.py [--no-deploy]
Environment pushed to Coolify = the variables of .env.coolify (Coolify/CRM_* bookkeeping keys excluded) + the overrides below."""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env.coolify"
env = {}
for line in ENV_FILE.read_text(encoding="utf8").splitlines():
    line = line.rstrip("\r")
    if line.strip() and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

BASE = env["COOLIFY_URL"].rstrip("/") + "/api/v1"
NAME = "aadi-project-tracker"
REPO, BRANCH, COMPOSE = "aadiTechnology/aadiprojecttracker", "main", "/docker-compose.coolify.yml"
UI = env.get("CRM_UI_URL", "https://aadiprojecttracker.aaditechnology.com").rstrip("/")
API = env.get("CRM_API_URL", "https://aadiprojecttrackerapi.aaditechnology.com").rstrip("/")


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + env["COOLIFY_API_TOKEN"], "Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t[:1] in "{[" else t)
    except urllib.error.HTTPError as e:
        t = e.read().decode()
        try:
            return e.code, json.loads(t)
        except ValueError:
            return e.code, t[:400]


def runtime_env() -> dict:
    skip = {"COOLIFY_URL", "COOLIFY_API_TOKEN", "CRM_UI_URL", "CRM_API_URL", "COOKIE_SECURE", "COOKIE_SAMESITE", "NGINX_MAX_BODY", "WEB_CONCURRENCY"}
    out = {k: v for k, v in env.items() if k not in skip and v != ""}
    # Backblaze: accept the DMS-prefixed names used in the shared env file
    for src, dst in (("DMS_B2_KEY_ID", "B2_KEY_ID"), ("DMS_B2_APP_KEY", "B2_APP_KEY"), ("DMS_B2_BUCKET_NAME", "B2_BUCKET_NAME"), ("DMS_B2_ENDPOINT", "B2_ENDPOINT")):
        if env.get(src):
            out[dst] = env[src]
        out.pop(src, None)
    sender = env.get("SMTP_FROM", "")
    m = re.search(r"<([^>]+)>", sender)
    out["SMTP_FROM"] = f"Aadi Project Tracker <{m.group(1) if m else sender}>" if sender else ""
    out.update({"APP_ENV": "demo", "APP_SEED_DEMO": "true", "APP_BASE_URL": UI, "CORS_ORIGINS": UI, "VITE_API_URL": API})
    return {k: v for k, v in out.items() if v != ""}


def main(deploy=True):
    st, servers = call("GET", "/servers")
    server = servers[0]["uuid"]
    st, projects = call("GET", "/projects")
    project = projects[0]["uuid"]
    st, apps = call("GET", "/applications")
    existing = next((a for a in apps if a.get("name", "").startswith(NAME)), None)
    domains = [{"name": "app", "domain": f"{UI},{API}"}]
    if existing:
        uuid = existing["uuid"]
        print("Updating existing resource", NAME)
        st, r = call("PATCH", f"/applications/{uuid}", {"docker_compose_domains": domains, "git_branch": BRANCH, "docker_compose_location": COMPOSE})
        print("  update:", st)
    else:
        st, ghs = call("GET", "/github-apps")
        gh = next(g["uuid"] for g in ghs if g["name"] != "Public GitHub")
        st, r = call("POST", "/applications/private-github-app", {
            "project_uuid": project, "server_uuid": server, "environment_name": "production", "github_app_uuid": gh,
            "git_repository": REPO, "git_branch": BRANCH, "build_pack": "dockercompose", "ports_exposes": "8000", "base_directory": "/",
            "docker_compose_location": COMPOSE, "name": NAME, "docker_compose_domains": domains, "instant_deploy": False})
        print("  create:", st, "" if st < 300 else r)
        if st >= 300:
            raise SystemExit(1)
        uuid = r["uuid"]
    values = runtime_env()
    data = [{"key": k, "value": v, "is_preview": False, "is_buildtime": k == "VITE_API_URL", "is_runtime": True} for k, v in values.items()]
    st, r = call("PATCH", f"/applications/{uuid}/envs/bulk", {"data": data})
    print("  environment variables set:", st, sorted(values))
    print("  resource uuid:", uuid)
    if not deploy:
        return
    st, r = call("POST", f"/deploy?uuid={uuid}&force=true")
    print("  deploy requested:", st, r if st >= 300 else "")
    dep = (r.get("deployments") or [{}])[0].get("deployment_uuid") if isinstance(r, dict) else None
    for _ in range(60):
        time.sleep(10)
        st, d = call("GET", f"/deployments/{dep}") if dep else (0, {})
        status = d.get("status") if isinstance(d, dict) else None
        print("  status:", status, flush=True)
        if status in ("finished", "failed", "cancelled", "error"):
            break
    st, a = call("GET", f"/applications/{uuid}")
    print("  application status:", a.get("status") if isinstance(a, dict) else a)


if __name__ == "__main__":
    main(deploy="--no-deploy" not in sys.argv)
