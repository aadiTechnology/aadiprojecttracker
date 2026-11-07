"""Sprint 5: advisory assistant (permission-aware, rule-based, logged, limited), CSV exports, hardening."""
from app import seed_matrix as sm


def mx(client, key):
    r = client.post("/api/auth/login", json={"email": f"{key}@{sm.DOMAIN}", "password": sm.PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def ask(client, h, q):
    return client.post("/api/assistant", json={"question": q}, headers=h)


def test_assistant_is_advisory_and_discloses(client, H):
    r = ask(client, H("priya.rao"), "Give me a summary of this month")
    assert r.status_code == 200
    j = r.json()
    assert j["intent"] == "summary" and j["advisory"] and j["provider"] == "rules"
    assert j["evidence"] and "No language model" in j["disclosure"]
    assert any("Rs" in line for line in j["answer"])  # the CEO sees money


def test_assistant_masks_money_for_roles_without_cost(client):
    j = ask(client, mx(client, "anil.deshpande"), "Which projects have a thin margin?").json()
    assert j["intent"] == "margin" and "Rs " not in " ".join(j["answer"])
    s = ask(client, mx(client, "anil.deshpande"), "Give me a summary of this month").json()
    assert "Rs " not in " ".join(s["answer"]) and any("hidden" in x.lower() for x in s["caveats"])


def test_assistant_respects_scope_and_roles(client, H):
    # finance sees receivables; a project manager does not
    assert any("invoice" in x.lower() for x in ask(client, H("sameer.joshi"), "What invoices are overdue?").json()["answer"])
    pm = ask(client, mx(client, "anil.deshpande"), "What invoices are overdue?").json()
    assert "only to finance" in " ".join(pm["answer"]) and "INV-" not in " ".join(pm["answer"])
    # employees have no assistant at all
    assert ask(client, H("meera.nair"), "summary").status_code == 403
    assert client.get("/api/assistant/info", headers=H("meera.nair")).status_code == 403


def test_assistant_unknown_validation_and_logging(client, H):
    h = H("priya.rao")
    u = ask(client, h, "tell me a joke about unicorns").json()
    assert u["intent"] == "unknown" and u["follow_ups"]
    assert ask(client, h, "hi").status_code == 422
    assert ask(client, h, "x" * 301).status_code == 422
    before = client.get("/api/assistant/info", headers=h).json()["used_today"]
    ask(client, h, "who is free to take new work?")
    info = client.get("/api/assistant/info", headers=h).json()
    assert info["used_today"] == before + 1 and info["tenant_cost_minor"] == 0 and info["provider"] == "rules"


def test_assistant_daily_limit(client, H, monkeypatch):
    from app.routers import assistant
    monkeypatch.setattr(assistant, "DAILY_LIMIT", 1)
    h = H("rohan.mehta")
    r = ask(client, h, "what are my open tasks?")
    r2 = ask(client, h, "what are my open tasks?")
    assert r.status_code == 200 and r2.status_code == 429


def test_assistant_tenant_isolation(client, H):
    j = ask(client, mx(client, "rhea.kulkarni"), "Give me a summary of this month").json()
    assert "PRJ-" not in " ".join(j["answer"]) and "Retail Portal" not in str(j)


def test_exports_respect_permissions_and_are_audited(client, H):
    r = client.get("/api/export/invoices", headers=H("sameer.joshi"))
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
    assert r.text.splitlines()[0].lstrip("﻿").startswith("Number,Customer")
    assert client.get("/api/export/invoices", headers=H("meera.nair")).status_code == 403
    assert client.get("/api/export/contribution", headers=mx(client, "anil.deshpande")).status_code == 403
    assert client.get("/api/export/nothing", headers=H("priya.rao")).status_code == 404
    pm = client.get("/api/export/planned-actual", headers=mx(client, "anil.deshpande"))
    assert pm.status_code == 200 and "cost" not in pm.text.splitlines()[0].lower()
    from app import core, models as m
    with core.SessionLocal() as db:
        assert db.query(m.AuditEvent).filter(m.AuditEvent.action == "export.csv").count() >= 2


def test_export_blocks_formula_injection(client, H):
    f = H("sameer.joshi")
    from datetime import date
    client.post("/api/expenses", json={"category": "Other", "amount_minor": 100, "spent_on": date.today().isoformat(), "vendor": "=HYPERLINK(\"http://evil\")", "description": "+cmd"}, headers=f)
    t = client.get("/api/export/expenses", headers=f).text
    assert "\"'=HYPERLINK" in t or "'=HYPERLINK" in t
    assert ",=HYPERLINK" not in t and ",+cmd" not in t


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in r.headers["content-security-policy"] and "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["cache-control"] == "no-store"
    assert "strict-transport-security" in client.get("/api/health", headers={"x-forwarded-proto": "https"}).headers


def test_login_rate_limit(client, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "LOGIN_RATE", 3)
    main._hits.clear()
    codes = [client.post("/api/auth/login", json={"email": "nobody@x.test", "password": "x"}).status_code for _ in range(5)]
    main._hits.clear()
    assert codes[:3] == [401, 401, 401] and codes[3:] == [429, 429]


def test_no_cross_tenant_object_access(client, H):
    inv = client.get("/api/invoices", headers=H("sameer.joshi")).json()["rows"][0]["id"]
    rh = mx(client, "rhea.kulkarni")
    for method, path in (("get", f"/api/invoices/{inv}"), ("post", f"/api/invoices/{inv}/approve"), ("post", f"/api/invoices/{inv}/void"), ("delete", "/api/expenses/1")):
        assert getattr(client, method)(path, headers=rh).status_code in (403, 404)


def test_menu_flags_sprint_5(client, H):
    a = client.get("/api/me", headers=H("priya.rao")).json()["access"]
    assert a["assistant"]["built"] and a["assistant"]["level"]
    assert not client.get("/api/me", headers=H("meera.nair")).json()["access"]["assistant"]["level"]
