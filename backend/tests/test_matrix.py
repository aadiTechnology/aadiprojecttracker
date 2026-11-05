"""Matrix demo organization (workbook-shaped): departments, industry tags, decision views for CEO, Product Owner and Project Manager."""
from app import seed_matrix as sm

from conftest import login


def hdr(client, key):
    r = client.post("/api/auth/login", json={"email": f"{key}@{sm.DOMAIN}", "password": sm.PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_structure_matches_workbook(client):
    h = hdr(client, "rhea.kulkarni")
    deps = {d["name"]: d for d in client.get("/api/departments", headers=h).json()}
    assert set(deps) == {"Management", "Software Development", "Marketing", "Sales"}
    tags = {t["name"] for t in client.get("/api/tags", headers=h).json()}
    assert {"Education", "Security", "Interior Design", "E-commerce"} <= tags
    assert not tags & {"Marketing", "Sales", "Software Services"}  # functions are departments, not tags
    assert len(client.get("/api/employees", headers=h).json()) == 15


def test_ceo_reconciles_and_sees_money(client):
    j = client.get("/api/insights", headers=hdr(client, "rhea.kulkarni")).json()
    assert j["money"] and j["kpi"]["reconciles"]
    assert j["kpi"]["salary_pool_minor"] == 27000000
    assert j["kpi"]["cost_minor"] + j["kpi"]["bench_cost_minor"] == j["kpi"]["salary_pool_minor"]
    assert sum(t["hours"] for t in j["tags"]) == j["kpi"]["hours"]  # primary-tag view is additive
    assert sum(x["hours"] for x in j["departments"]) == j["kpi"]["hours"]
    assert j["kpi"]["bench_people"] == 3 or j["kpi"]["bench_people"] == 2
    assert any(s["lens"] == "ceo" for s in j["signals"])
    assert j["default_lens"] == "ceo"


def test_pm_and_po_get_hours_never_money(client):
    for key, lens in (("anil.deshpande", "pm"), ("tanvi.joshi", "po")):
        r = client.get("/api/insights", headers=hdr(client, key))
        assert r.status_code == 200
        j = r.json()
        assert j["money"] is False and j["default_lens"] == lens
        blob = r.text
        for banned in ("cost_minor", "value_minor", "margin_minor", "salary", "bench_cost"):
            assert banned not in blob, banned
    po = client.get("/api/insights", headers=hdr(client, "tanvi.joshi")).json()
    assert {p["category"] for p in po["projects"]} <= {"Own Product", "Client Service", "Internal Growth"}
    assert po["kpi"]["projects"] < 12  # scoped to her projects


def test_unallocated_project_is_flagged_and_employee_blocked(client):
    j = client.get("/api/insights", headers=hdr(client, "rhea.kulkarni")).json()
    p = next(x for x in j["projects"] if x["code"] == "MTX-111")
    assert "No one allocated" in p["flags"]
    assert client.get("/api/insights", headers=hdr(client, "kunal.rane")).status_code == 403
    assert client.get("/api/costing/summary", headers=hdr(client, "kunal.rane")).status_code == 403


def test_tenants_are_isolated(client):
    h = hdr(client, "rhea.kulkarni")
    codes = {p["code"] for p in client.get("/api/projects", headers=h).json()}
    assert all(c.startswith("MTX-") for c in codes)
    first = {p["code"] for p in client.get("/api/projects", headers=login(client, "priya.rao")).json()}
    assert not first & codes
