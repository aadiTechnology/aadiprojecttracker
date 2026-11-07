"""Sprint 4: expenses and shared-cost split, invoice approval and payments, planned vs actual, contribution, performance matrix."""
from datetime import date, timedelta

from app import seed_matrix as sm
from app.routers.finance import split

from conftest import login


def mx(client, key):
    r = client.post("/api/auth/login", json={"email": f"{key}@{sm.DOMAIN}", "password": sm.PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_split_always_reconciles():
    for amount in (1, 7, 100, 1800000, 999999):
        for w in ({"a": 1, "b": 1, "c": 1}, {"a": 3, "b": 5}, {"a": 40, "b": 0, "c": 7}):
            assert sum(split(amount, w).values()) == amount
    assert split(100, {}) == {}


def test_expenses_split_and_reconcile(client, H):
    j = client.get("/api/expenses", headers=H("sameer.joshi")).json()
    assert j["can_manage"] and j["totals"]["shared_minor"] > 0
    assert sum(a["shared_minor"] for a in j["allocation"]) + j["unallocated_minor"] == j["totals"]["shared_minor"]
    assert j["totals"]["all_minor"] == j["totals"]["direct_minor"] + j["totals"]["shared_minor"]
    c = client.get("/api/finance/contribution", headers=H("sameer.joshi")).json()
    assert c["reconciles"]
    assert c["totals"]["shared_minor"] == j["totals"]["shared_minor"] - j["unallocated_minor"]


def test_expense_validation_and_roles(client, H):
    f = H("sameer.joshi")
    body = {"category": "Software", "amount_minor": 50000, "spent_on": date.today().isoformat(), "vendor": "Test vendor"}
    assert client.post("/api/expenses", json={**body, "category": "Nonsense"}, headers=f).status_code == 422
    assert client.post("/api/expenses", json={**body, "amount_minor": 0}, headers=f).status_code == 422
    assert client.post("/api/expenses", json={**body, "project_id": 999999}, headers=f).status_code == 422
    r = client.post("/api/expenses", json=body, headers=f)
    assert r.status_code == 200
    eid = r.json()["id"]
    assert client.patch(f"/api/expenses/{eid}", json={"status": "Paid"}, headers=f).status_code == 200
    # a project manager cannot manage or even view expenses; an employee neither
    assert client.post("/api/expenses", json=body, headers=H("vikram.shah")).status_code == 403
    assert client.get("/api/expenses", headers=H("rohan.mehta")).status_code == 403
    # operations may view but not change
    ops = client.get("/api/expenses", headers=H("vikram.shah"))
    assert ops.status_code == 403 or ops.json()["can_manage"] is False
    assert client.delete(f"/api/expenses/{eid}", headers=f).status_code == 200


def test_invoice_lifecycle_and_segregation(client, H):
    fin, ceo = H("sameer.joshi"), H("priya.rao")
    projects = client.get("/api/invoices", headers=fin).json()["projects"]
    pid = projects[0]["id"]
    today = date.today()
    body = {"project_id": pid, "issue_date": today.isoformat(), "due_date": (today + timedelta(days=15)).isoformat(), "tax_pct": 18,
            "lines": [{"description": "Build", "amount_minor": 1000000}, {"description": "Support", "amount_minor": 500000}]}
    bad = client.post("/api/invoices", json={**body, "lines": []}, headers=fin)
    assert bad.status_code == 422
    assert client.post("/api/invoices", json={**body, "due_date": (today - timedelta(days=2)).isoformat()}, headers=fin).status_code == 422
    assert client.post("/api/invoices", json={**body, "tax_pct": 120}, headers=fin).status_code == 422
    r = client.post("/api/invoices", json=body, headers=fin)
    assert r.status_code == 200, r.text
    iid = r.json()["id"]
    d = client.get(f"/api/invoices/{iid}", headers=fin).json()
    assert d["status"] == "Draft" and d["subtotal_minor"] == 1500000 and d["tax_minor"] == 270000 and d["total_minor"] == 1770000
    # finance cannot approve its own draft (no invoices.approve); the attempt is audited. Issue before approval is a conflict.
    assert client.post(f"/api/invoices/{iid}/approve", headers=fin).status_code == 403
    assert client.post(f"/api/invoices/{iid}/issue", headers=fin).status_code == 409
    assert client.post(f"/api/invoices/{iid}/payments", json={"amount_minor": 100, "paid_on": today.isoformat()}, headers=fin).status_code == 409
    # a project manager is denied issuing
    assert client.post(f"/api/invoices/{iid}/issue", headers=H("vikram.shah")).status_code == 403
    from app import core, models as m
    with core.SessionLocal() as db:
        acts = {x.action for x in db.query(m.AuditEvent).filter(m.AuditEvent.entity == "invoice").all()}
    assert {"invoice.approve.denied", "invoice.issue.denied"} <= acts
    assert client.post(f"/api/invoices/{iid}/approve", headers=ceo).status_code == 200
    assert client.post(f"/api/invoices/{iid}/approve", headers=ceo).status_code == 409
    assert client.post(f"/api/invoices/{iid}/issue", headers=fin).status_code == 200
    over = client.post(f"/api/invoices/{iid}/payments", json={"amount_minor": 1770001, "paid_on": today.isoformat()}, headers=fin)
    assert over.status_code == 422
    assert client.post(f"/api/invoices/{iid}/payments", json={"amount_minor": 770000, "paid_on": today.isoformat(), "reference": "UTR1"}, headers=fin).status_code == 200
    d = client.get(f"/api/invoices/{iid}", headers=fin).json()
    assert d["status"] == "Partially Paid" and d["outstanding_minor"] == 1000000
    assert client.post(f"/api/invoices/{iid}/void", headers=fin).status_code == 409  # has payments
    assert client.post(f"/api/invoices/{iid}/payments", json={"amount_minor": 1000000, "paid_on": today.isoformat()}, headers=fin).status_code == 200
    assert client.get(f"/api/invoices/{iid}", headers=fin).json()["status"] == "Paid"


def test_overdue_and_summary(client, H):
    j = client.get("/api/invoices", headers=H("sameer.joshi")).json()
    states = {r["status"] for r in j["rows"]}
    assert {"Draft", "Overdue"} <= states
    s = j["summary"]
    live = [r for r in j["rows"] if r["status"] in ("Issued", "Partially Paid", "Paid", "Overdue")]
    assert s["invoiced_minor"] == sum(r["total_minor"] for r in live)
    assert s["invoiced_minor"] - s["collected_minor"] == s["outstanding_minor"]
    assert all(r["days_overdue"] > 0 for r in j["rows"] if r["status"] == "Overdue")
    # voiding an unpaid invoice is final
    drafts = [r for r in j["rows"] if r["status"] == "Draft"]
    assert client.post(f"/api/invoices/{drafts[0]['id']}/void", headers=H("sameer.joshi")).status_code == 200
    assert client.post(f"/api/invoices/{drafts[0]['id']}/void", headers=H("sameer.joshi")).status_code == 409


def test_invoices_tenant_isolation_and_roles(client, H):
    inv = client.get("/api/invoices", headers=H("sameer.joshi")).json()["rows"][0]["id"]
    assert client.get(f"/api/invoices/{inv}", headers=mx(client, "rhea.kulkarni")).status_code == 404
    assert client.get("/api/invoices", headers=H("rohan.mehta")).status_code == 403
    assert client.get("/api/invoices", headers=H("vikram.shah")).status_code == 403


def test_planned_vs_actual(client, H):
    j = client.get("/api/planned-actual", headers=mx(client, "rhea.kulkarni")).json()
    assert j["money"] and j["projects"] and j["totals"]["approved_hours"] > 0
    assert round(sum(p["planned_hours"] for p in j["projects"]), 1) == j["totals"]["planned_hours"]
    flags = {p["flag"] for p in j["projects"]}
    assert flags & {"Over plan", "Behind on approved hours"} or j["elapsed_pct"] < 50
    assert j["totals"]["actual_cost_minor"] >= 0
    # a project manager gets hours but never money
    pm = client.get("/api/planned-actual", headers=mx(client, "anil.deshpande"))
    assert pm.status_code == 200 and pm.json()["money"] is False
    assert "cost_minor" not in pm.text
    # an employee has no access
    assert client.get("/api/planned-actual", headers=mx(client, "omkar.pawar")).status_code == 403


def test_contribution_masking(client, H):
    assert client.get("/api/finance/contribution", headers=mx(client, "rhea.kulkarni")).status_code == 200
    assert client.get("/api/finance/contribution", headers=mx(client, "anil.deshpande")).status_code == 403
    assert client.get("/api/finance/contribution", headers=H("vikram.shah")).status_code == 403
    c = client.get("/api/finance/contribution", headers=mx(client, "rhea.kulkarni")).json()
    t = c["totals"]
    assert t["contribution_minor"] == t["value_minor"] - t["salary_cost_minor"] - t["direct_minor"] - t["shared_minor"]


def test_performance_scopes_and_definitions(client, H):
    ceo = client.get("/api/performance", headers=mx(client, "rhea.kulkarni")).json()
    assert len(ceo["rows"]) == 15 and ceo["definitions"] and ceo["can_review"]
    me = client.get("/api/performance", headers=mx(client, "omkar.pawar")).json()
    assert [r["name"] for r in me["rows"]] == ["Omkar Pawar"] and not me["can_review"]
    tl = client.get("/api/performance", headers=mx(client, "gauri.patil")).json()
    assert {r["name"] for r in tl["rows"]} <= {"Gauri Patil", "Meghna Shah", "Jayant Rao"}
    assert client.get("/api/performance", headers=H("meera.nair")).status_code == 200


def test_review_comment_and_acknowledge(client, H):
    boss = mx(client, "rhea.kulkarni")
    uid = next(r["user_id"] for r in client.get("/api/performance", headers=boss).json()["rows"] if r["name"] == "Kunal Rane")
    me = next(r["user_id"] for r in client.get("/api/performance", headers=boss).json()["rows"] if r["name"] == "Rhea Kulkarni")
    assert client.post("/api/performance/reviews", json={"user_id": me, "comment": "reviewing myself is blocked"}, headers=boss).status_code == 422
    assert client.post("/api/performance/reviews", json={"user_id": uid, "comment": "short"}, headers=boss).status_code == 422
    assert client.post("/api/performance/reviews", json={"user_id": uid, "dimension": "Nope", "comment": "long enough comment text"}, headers=boss).status_code == 422
    r = client.post("/api/performance/reviews", json={"user_id": uid, "dimension": "Delivery reliability", "comment": "Delivered the release on the planned date with no defects."}, headers=boss)
    assert r.status_code == 200
    kunal = mx(client, "kunal.rane")
    assert client.post("/api/performance/reviews", json={"user_id": uid, "comment": "an employee cannot write reviews"}, headers=kunal).status_code == 403
    mine = client.get(f"/api/performance/{uid}", headers=kunal).json()
    rid = next(x["id"] for x in mine["reviews"] if not x["acknowledged"])
    assert client.post(f"/api/performance/reviews/{rid}/ack", json={"note": "Thanks"}, headers=boss).status_code == 404  # only the subject acknowledges
    assert client.post(f"/api/performance/reviews/{rid}/ack", json={"note": "Thanks"}, headers=kunal).status_code == 200
    assert client.post(f"/api/performance/reviews/{rid}/ack", json={}, headers=kunal).status_code == 409
    # another employee cannot open this profile
    assert client.get(f"/api/performance/{uid}", headers=mx(client, "neha.gokhale")).status_code == 404


def test_menu_flags_sprint_4(client, H):
    a = client.get("/api/me", headers=H("sameer.joshi")).json()["access"]
    assert a["expenses"]["built"] and a["invoices"]["built"] and a["perf"]["built"] and a["plannedactual"]["built"]
    e = client.get("/api/me", headers=mx(client, "omkar.pawar")).json()["access"]
    assert e["perf"]["level"] == "own" and not e["invoices"]["level"] and not e["expenses"]["level"]
