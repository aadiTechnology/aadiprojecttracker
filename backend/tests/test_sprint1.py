from app import core, models as m, seed
from tests.conftest import login


def test_health_and_demo_accounts(client):
    assert client.get("/api/health").json()["status"] == "ok"
    d = client.get("/api/demo/accounts").json()
    roles = {a["role"] for a in d["accounts"]}
    assert len([a for a in d["accounts"] if a.get("org") != "matrix"]) == len(seed.USERS) + 1
    for r in ["Organization Owner / CEO", "Finance Manager", "Operations / Delivery Manager", "Project Manager", "Team Lead",
              "Employee / Contributor", "Sales / Business Development", "SaaS Platform Administrator"]:
        assert r in roles


def test_seed_covers_four_business_areas(client, H):
    cats = {p["category"] for p in client.get("/api/projects", headers=H("priya.rao")).json()}
    assert cats == {"Software Development", "Software Services", "Marketing", "Sales"}


def test_login_failures_and_lockout(client):
    key = "isha.kapoor"
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": f"{key}@{seed.DOMAIN}", "password": "wrong-pass"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": f"{key}@{seed.DOMAIN}", "password": seed.DEMO_PASSWORD}).status_code == 423
    with core.SessionLocal() as db:
        u = db.query(m.User).filter_by(email=f"{key}@{seed.DOMAIN}").one()
        u.locked_until = None
        db.commit()


def test_no_token_rejected(client):
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_owner_sees_everything_with_money(client, H):
    r = client.get("/api/projects", headers=H("priya.rao")).json()
    assert len(r) == len(seed.PROJECTS)
    assert all("budget_minor" in p and "contract_value_minor" in p for p in r)


def test_pm_sees_only_assigned(client, H):
    asha = client.get("/api/projects", headers=H("asha.kulkarni")).json()
    nisha = client.get("/api/projects", headers=H("nisha.verma")).json()
    assert asha and nisha and not ({p["id"] for p in asha} & {p["id"] for p in nisha})
    assert client.get(f"/api/projects/{nisha[0]['id']}", headers=H("asha.kulkarni")).status_code == 404


def test_team_lead_no_money(client, H):
    ps = client.get("/api/projects", headers=H("rohan.mehta")).json()
    assert ps and all("budget_minor" not in p and "contract_value_minor" not in p for p in ps)


def test_ops_budget_but_no_contract_value(client, H):
    ps = client.get("/api/projects", headers=H("vikram.shah")).json()
    assert all("budget_minor" in p and "contract_value_minor" not in p for p in ps)


def test_sales_contract_only(client, H):
    ps = client.get("/api/projects", headers=H("kabir.sethi")).json()
    assert ps
    for p in ps:
        assert "contract_value_minor" in p and "budget_minor" not in p and "est_hours" not in p


def test_employee_blocked_from_management_data(client, H):
    h = H("meera.nair")
    for path in ("/api/projects", "/api/customers", "/api/org/users", "/api/org/audit"):
        assert client.get(path, headers=h).status_code == 403, path


def test_platform_admin_has_no_tenant_content(client, H):
    h = H("platform.admin")
    assert client.get("/api/platform/tenants", headers=h).status_code == 200
    assert client.get("/api/projects", headers=h).status_code == 403
    assert client.get("/api/customers", headers=h).status_code == 403


def test_tenant_admin_cannot_use_platform_api(client, H):
    assert client.get("/api/platform/tenants", headers=H("priya.rao")).status_code == 403


def test_cross_tenant_isolation(client, H):
    r = client.post("/api/platform/tenants", headers=H("platform.admin"), json={"name": "Other Org", "owner_email": "owner@other.test", "owner_name": "Olive"})
    assert r.status_code == 200
    tok = r.json()["invite_link"].split("token=")[1]
    assert client.post("/api/auth/reset", json={"token": tok, "password": "Str0ngPassword1"}).status_code == 200
    r = client.post("/api/auth/login", json={"email": "owner@other.test", "password": "Str0ngPassword1"})
    h = {"Authorization": "Bearer " + r.json()["token"]}
    assert client.get("/api/projects", headers=h).json() == []
    assert client.get("/api/customers", headers=h).json() == []
    owner_proj = client.get("/api/projects", headers=H("priya.rao")).json()[0]["id"]
    assert client.get(f"/api/projects/{owner_proj}", headers=h).status_code == 404
    assert [u["email"] for u in client.get("/api/org/users", headers=h).json()] == ["owner@other.test"]


def test_entitlement_default_off_for_pillar_3(client, H):
    mods = {x["key"]: x["enabled"] for x in client.get("/api/org/modules", headers=H("priya.rao")).json()}
    assert mods["ai"] is False and mods["sales"] is False and mods["core"] is True


def test_project_create_rules(client, H):
    h = H("priya.rao")
    cust = client.get("/api/customers", headers=h).json()[0]["id"]
    assert client.post("/api/projects", headers=h, json={"name": "X", "customer_id": 999999}).status_code == 422
    assert client.post("/api/projects", headers=h, json={"name": "X", "customer_id": cust, "start_date": "2026-12-01", "end_date": "2026-11-01"}).status_code == 422
    ok = client.post("/api/projects", headers=h, json={"name": "New Marketing Push", "category": "Marketing", "customer_id": cust})
    assert ok.status_code == 200
    pid = ok.json()["id"]
    assert client.post(f"/api/projects/{pid}/status", headers=h, json={"status": "Active"}).status_code == 409
    assert client.post(f"/api/projects/{pid}/status", headers=h, json={"status": "Completed"}).status_code == 409
    assert client.post("/api/projects", headers=H("asha.kulkarni"), json={"name": "Y", "customer_id": cust}).status_code == 403


def test_scope_change_needs_other_approver(client, H):
    h = H("asha.kulkarni")
    pid = client.get("/api/projects", headers=h).json()[0]["id"]
    sid = client.post(f"/api/projects/{pid}/scope-changes", headers=h, json={"description": "Add export", "reason": "customer ask"}).json()["id"]
    assert client.post(f"/api/projects/{pid}/scope-changes/{sid}/decision", headers=h, json={"approve": True}).status_code == 403
    assert client.post(f"/api/projects/{pid}/scope-changes/{sid}/decision", headers=H("priya.rao"), json={"approve": True}).status_code == 200


def test_last_owner_and_self_protection(client, H):
    h = H("priya.rao")
    me = next(u for u in client.get("/api/org/users", headers=h).json() if u["email"].startswith("priya"))
    assert client.patch(f"/api/org/users/{me['id']}", headers=h, json={"role_key": "pm"}).status_code == 409
    owner_role = next(r for r in client.get("/api/org/roles", headers=h).json()["roles"] if r["key"] == "owner")
    assert client.put(f"/api/org/roles/{owner_role['id']}", headers=h, json={"perms": []}).status_code == 409


def test_role_permission_change_is_audited_and_effective(client, H):
    h = H("priya.rao")
    tl = next(r for r in client.get("/api/org/roles", headers=h).json()["roles"] if r["key"] == "tl")
    new = [p for p in tl["perms"] if p != "projects.view:assigned"]
    assert client.put(f"/api/org/roles/{tl['id']}", headers=h, json={"perms": new}).status_code == 200
    assert client.get("/api/projects", headers=login(client, "rohan.mehta")).status_code == 403
    assert client.put(f"/api/org/roles/{tl['id']}", headers=h, json={"perms": tl["perms"]}).status_code == 200
    assert client.put(f"/api/org/roles/{tl['id']}", headers=h, json={"perms": ["nonsense.cap"]}).status_code == 422
    assert any(e["action"] == "role.permissions" for e in client.get("/api/org/audit?action=role.", headers=h).json())


def test_salary_permission_restricted(client, H):
    h = H("priya.rao")
    ops = next(r for r in client.get("/api/org/roles", headers=h).json()["roles"] if r["key"] == "ops")
    assert client.put(f"/api/org/roles/{ops['id']}", headers=h, json={"perms": ops["perms"] + ["salary.view"]}).status_code == 422


def test_me_access_map(client, H):
    emp = client.get("/api/me", headers=H("meera.nair")).json()
    assert emp["access"]["projects"]["level"] is None and emp["access"]["timesheets"]["level"] is not None
    assert client.get("/api/me", headers=H("priya.rao")).json()["access"]["projects"]["level"] == "all"


def test_suspension_revokes_session(client, H):
    h = H("priya.rao")
    u = next(u for u in client.get("/api/org/users", headers=h).json() if u["email"].startswith("arjun"))
    tok = login(client, "arjun.singh")
    assert client.get("/api/me", headers=tok).status_code == 200
    assert client.patch(f"/api/org/users/{u['id']}", headers=h, json={"status": "suspended"}).status_code == 200
    assert client.get("/api/me", headers=tok).status_code in (401, 403)
    client.patch(f"/api/org/users/{u['id']}", headers=h, json={"status": "active"})


def test_open_decisions_never_defaulted(client, H):
    h = H("priya.rao")
    assert client.get("/api/org/settings", headers=h).json()["revenue_basis"] is None
    assert client.patch("/api/org/settings", headers=h, json={"revenue_basis": "nonsense"}).status_code == 422
    assert client.patch("/api/org/settings", headers=H("vikram.shah"), json={"week_hours": 30}).status_code == 403
