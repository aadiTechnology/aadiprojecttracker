"""Sprint 3 (Revision 2): salary-allocation costing, tags, departments, allocation rule, masking, targets and profitability."""
from app import costing as k, seed_costing as sc
from app.costing import half_up


def get(client, H, who, path):
    return client.get(path, headers=H(who))


def put(client, H, who, path, body):
    return client.put(path, headers=H(who), json=body)


def post(client, H, who, path, body=None):
    return client.post(path, headers=H(who), json=body or {})


def uid(client, H, name):
    return next(e["id"] for e in get(client, H, "priya.rao", "/api/employees").json() if e["name"] == name)


def pid(client, H, code):
    return next(p["id"] for p in get(client, H, "priya.rao", "/api/projects").json() if p["code"] == code)


# ---------------- the arithmetic (pure) ----------------
def test_worked_example_from_the_workbook():
    """25%, 50%, 75%, 100% of employees earning 30,000 / 20,000 / 20,000 / 20,000 -> 400 h, Rs 1,00,000 value, Rs 52,500 cost."""
    sal = {1: 3000000, 2: 2000000, 3: 2000000, 4: 2000000}
    d = {"emps": {i: {"id": i, "name": f"E{i}", "hours": 160, "salary": s, "dept_id": None} for i, s in sal.items()},
         "projects": {1: {"id": 1, "code": "P", "name": "P", "rate": 25000, "tags": []}}, "alloc": {(1, 1): 25, (2, 1): 50, (3, 1): 75, (4, 1): 100}}
    r = k.compute(d)
    p = r["proj"][1]
    assert p["hours"] == 400 and p["value"] == 100000 * 100 and p["cost"] == 52500 * 100
    # each person's cost uses that person's own salary (the workbook error used one salary for everybody)
    assert [r["cells"][(i, 1)]["cost"] for i in (1, 2, 3, 4)] == [750000, 1000000, 1500000, 2000000]


def test_bench_is_the_remainder_so_totals_reconcile():
    d = {"emps": {1: {"id": 1, "name": "A", "hours": 160, "salary": 3333333, "dept_id": None}, 2: {"id": 2, "name": "B", "hours": 160, "salary": 1000000, "dept_id": None}},
         "projects": {1: {"id": 1, "code": "P", "name": "P", "rate": 25000, "tags": []}}, "alloc": {(1, 1): 33}}
    r = k.compute(d)
    t = k.org_totals(d, r)
    assert t["salary_pool"] == t["cost"] + t["bench_cost"] and t["reconciles"]
    assert r["emp"][2]["pct"] == 0 and r["emp"][2]["bench_cost"] == 1000000  # nobody allocated: whole salary is bench


def test_half_up():
    assert half_up(5, 2) == 3 and half_up(4, 2) == 2 and half_up(1, 3) == 0


# ---------------- seeded baseline ----------------
def expected_totals():
    sal = {key: v[1] * 100 for key, v in sc.PEOPLE.items()}
    cost = sum(sal[u] * pct // 100 for u, rows in sc.ALLOC.items() for pct in rows.values())
    hours = sum(160 * pct / 100 for rows in sc.ALLOC.values() for pct in rows.values())
    return sum(sal.values()), cost, hours


def test_org_summary_matches_independent_calculation(client, H):
    pool, cost, hours = expected_totals()
    s = get(client, H, "priya.rao", "/api/costing/summary").json()
    assert s["salary_pool_minor"] == pool and s["cost_minor"] == cost and s["hours"] == hours
    assert s["value_minor"] == int(hours * 25000) and s["reconciles"] is True
    assert s["salary_pool_minor"] == s["cost_minor"] + s["bench_cost_minor"]


def test_finance_sees_the_same_numbers_as_owner(client, H):
    a, b = get(client, H, "priya.rao", "/api/costing/summary").json(), get(client, H, "sameer.joshi", "/api/costing/summary").json()
    assert a["cost_minor"] == b["cost_minor"] and a["value_minor"] == b["value_minor"]


def test_matrix_mirrors_workbook_structure(client, H):
    mx = get(client, H, "priya.rao", "/api/costing/matrix").json()
    assert mx["reconciliation"]["check"].startswith("OK")
    proj = next(p for p in mx["projects"] if p["code"] == "PRJ-103")
    assert sum(proj["effort"].values()) == proj["hours"] == 240  # asha 25, meera 25, dev 50, isha 25, vikram 25 of 160 h = 40+40+80+40+40
    assert sum(proj["cost"].values()) == proj["cost_minor"]
    assert all(e["status"] in ("Full", "Part", "Bench") for e in mx["employees"])


def test_each_projects_cost_sums_employee_cells(client, H):
    rows = get(client, H, "priya.rao", "/api/costing/projects").json()["rows"]
    emps = get(client, H, "priya.rao", "/api/costing/employees").json()["rows"]
    assert sum(r["cost_minor"] for r in rows) == sum(e["cost_minor"] for e in emps)


# ---------------- masking and scope ----------------
def test_salary_and_cost_never_reach_unauthorised_roles(client, H):
    for who in ("vikram.shah", "asha.kulkarni", "rohan.mehta"):
        txt = (get(client, H, who, "/api/costing/projects").text + get(client, H, who, "/api/costing/employees").text + get(client, H, who, "/api/costing/matrix").text
               + get(client, H, who, "/api/employees").text + get(client, H, who, "/api/costing/summary").text)
        for forbidden in ("salary_minor", "cost_minor", "value_minor", "margin_minor", "cost_per_hour", "bench_cost"):
            assert forbidden not in txt, (who, forbidden)
    assert get(client, H, "vikram.shah", "/api/costing/profitability").status_code == 403
    assert get(client, H, "vikram.shah", "/api/costing/settings").json().get("hourly_rate_minor") is None


def test_employees_and_sales_have_no_costing_access(client, H):
    for who in ("meera.nair", "kabir.sethi"):
        for path in ("/api/costing/summary", "/api/employees", "/api/allocations", "/api/targets", "/api/costing/matrix"):
            assert get(client, H, who, path).status_code == 403, (who, path)


def test_pm_sees_only_assigned_projects_and_partial_totals(client, H):
    r = get(client, H, "asha.kulkarni", "/api/costing/projects").json()
    assert r["partial"] and {x["code"] for x in r["rows"]} == {"PRJ-101", "PRJ-102", "PRJ-103", "PRJ-104"}
    emps = get(client, H, "asha.kulkarni", "/api/costing/employees").json()["rows"]
    assert all("allocated_pct" not in e for e in emps)  # a PM must not see another project's load of a shared employee


def test_team_lead_sees_only_team(client, H):
    emps = get(client, H, "rohan.mehta", "/api/employees").json()
    assert emps and {e["team"] for e in emps} == {"Team A"}


def test_only_finance_may_hold_salary_capabilities(client, H):
    roles = get(client, H, "priya.rao", "/api/org/roles").json()
    ops = next(r for r in roles["roles"] if r["key"] == "ops") if isinstance(roles, dict) else next(r for r in roles if r["key"] == "ops")
    r = put(client, H, "priya.rao", f"/api/org/roles/{ops['id']}", {"perms": ops["perms"] + ["costing.cost"]})
    assert r.status_code == 422


# ---------------- allocation rule ----------------
def test_allocation_above_100_is_rejected(client, H):
    dev, p = uid(client, H, "Dev Patel"), pid(client, H, "PRJ-101")  # Dev is already at 100%
    r = put(client, H, "priya.rao", "/api/allocations", {"user_id": dev, "project_id": p, "percent": 25})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "OVER_ALLOCATED" and "125%" in r.json()["detail"]["message"]
    assert put(client, H, "priya.rao", "/api/allocations", {"user_id": dev, "project_id": p, "percent": 101}).status_code == 422


def test_allocation_change_and_reconciliation(client, H):
    nov = get(client, H, "priya.rao", "/api/allocations").json()
    sameer, p = uid(client, H, "Sameer Joshi"), pid(client, H, "PRJ-107")
    assert put(client, H, "priya.rao", "/api/allocations", {"user_id": sameer, "project_id": p, "percent": 40}).status_code == 200
    s = get(client, H, "priya.rao", "/api/costing/summary").json()
    assert s["salary_pool_minor"] == s["cost_minor"] + s["bench_cost_minor"]
    emps = {e["name"]: e for e in get(client, H, "priya.rao", "/api/costing/employees").json()["rows"]}
    assert emps["Sameer Joshi"]["allocated_pct"] == 40 and emps["Sameer Joshi"]["cost_minor"] == 2000000 * 40 // 100
    assert put(client, H, "priya.rao", "/api/allocations", {"user_id": sameer, "project_id": p, "percent": 0}).status_code == 200  # restores the baseline
    key = lambda x: (x["user_id"], x["project_id"])
    assert sorted(nov["cells"], key=key) == sorted(get(client, H, "priya.rao", "/api/allocations").json()["cells"], key=key)


def test_allocation_adds_the_person_to_the_project_team(client, H):
    sameer, p = uid(client, H, "Sameer Joshi"), pid(client, H, "PRJ-106")
    put(client, H, "priya.rao", "/api/allocations", {"user_id": sameer, "project_id": p, "percent": 10})
    team = get(client, H, "priya.rao", f"/api/projects/{p}").json()["members"]
    assert "Sameer Joshi" in {x["name"] for x in team}
    put(client, H, "priya.rao", "/api/allocations", {"user_id": sameer, "project_id": p, "percent": 0})


def test_pm_can_allocate_only_on_assigned_projects(client, H):
    isha = uid(client, H, "Isha Kapoor")
    other = pid(client, H, "PRJ-105")  # Supply Tracker belongs to the other PM
    assert put(client, H, "asha.kulkarni", "/api/allocations", {"user_id": isha, "project_id": other, "percent": 0}).status_code == 404
    mine = pid(client, H, "PRJ-101")
    assert put(client, H, "asha.kulkarni", "/api/allocations", {"user_id": isha, "project_id": mine, "percent": 0}).status_code == 200


def test_team_lead_cannot_change_allocation(client, H):
    assert put(client, H, "rohan.mehta", "/api/allocations", {"user_id": uid(client, H, "Dev Patel"), "project_id": pid(client, H, "PRJ-102"), "percent": 50}).status_code == 403


def test_copy_allocations_to_next_month(client, H):
    r = post(client, H, "priya.rao", "/api/allocations/copy", {"from_month": "2027-02", "to_month": "2027-03"})
    assert r.status_code == 200 and r.json()["added"] == 0  # nothing to copy from an empty month
    nowm = get(client, H, "priya.rao", "/api/allocations").json()["month"]
    r = post(client, H, "priya.rao", "/api/allocations/copy", {"from_month": nowm, "to_month": "2027-04"})
    assert r.json()["added"] == sum(len(rows) for rows in sc.ALLOC.values())
    assert post(client, H, "priya.rao", "/api/allocations/copy", {"from_month": nowm, "to_month": "2027-04"}).json()["added"] == 0  # idempotent


# ---------------- salary is effective-dated ----------------
def test_salary_change_does_not_rewrite_earlier_months(client, H):
    dev = uid(client, H, "Dev Patel")
    nowm = get(client, H, "priya.rao", "/api/allocations").json()["month"]
    post(client, H, "priya.rao", "/api/allocations/copy", {"from_month": nowm, "to_month": "2027-04"})  # idempotent
    base = {e["name"]: e for e in get(client, H, "priya.rao", "/api/costing/employees?month=2027-04").json()["rows"]}["Dev Patel"]["cost_minor"]
    assert put(client, H, "sameer.joshi", f"/api/employees/{dev}/salary", {"amount_minor": 4000000, "effective_from": "2027-04-01"}).status_code == 200
    later = {e["name"]: e for e in get(client, H, "priya.rao", "/api/costing/employees?month=2027-04").json()["rows"]}["Dev Patel"]["cost_minor"]
    earlier = {e["name"]: e for e in get(client, H, "priya.rao", "/api/costing/employees").json()["rows"]}["Dev Patel"]["cost_minor"]
    assert later == 4000000 and base == 2000000 and earlier == 2000000
    hist = get(client, H, "sameer.joshi", f"/api/employees/{dev}/salary").json()
    assert [h["amount_minor"] for h in hist] == [4000000, 2000000]
    assert put(client, H, "sameer.joshi", f"/api/employees/{dev}/salary", {"amount_minor": 0, "effective_from": "2027-04-01"}).status_code == 422
    assert put(client, H, "vikram.shah", f"/api/employees/{dev}/salary", {"amount_minor": 100, "effective_from": "2027-04-01"}).status_code == 403
    assert "4000000" not in str(get(client, H, "priya.rao", "/api/org/audit").json())  # amounts are never written to the audit log


# ---------------- departments ----------------
def test_head_of_department_rules(client, H):
    deps = {d["name"]: d for d in get(client, H, "priya.rao", "/api/departments").json()}
    sales = deps["Sales"]
    tara = uid(client, H, "Tara Menon")
    r = client.patch(f"/api/departments/{deps['Engineering']['id']}", headers=H("priya.rao"), json={"name": "Engineering", "head_user_id": tara})
    assert r.status_code == 422  # Tara is not in Engineering
    r = client.patch(f"/api/departments/{sales['id']}", headers=H("priya.rao"), json={"name": "Sales", "head_user_id": tara})
    assert r.status_code == 200
    kabir = uid(client, H, "Kabir Sethi")
    assert client.patch(f"/api/employees/{tara}", headers=H("priya.rao"), json={"department_id": deps["Finance"]["id"]}).status_code == 409  # she now heads Sales
    client.patch(f"/api/departments/{sales['id']}", headers=H("priya.rao"), json={"name": "Sales", "head_user_id": kabir})
    assert post(client, H, "priya.rao", "/api/departments", {"name": "sales"}).status_code == 409  # case-insensitive duplicate
    assert post(client, H, "vikram.shah", "/api/departments", {"name": "Support"}).status_code == 200  # operations manages departments
    assert post(client, H, "sameer.joshi", "/api/departments", {"name": "Other"}).status_code == 403


# ---------------- tags ----------------
def test_tags_are_unique_and_filter_projects(client, H):
    assert post(client, H, "vikram.shah", "/api/tags", {"name": "software"}).status_code == 409
    new = post(client, H, "vikram.shah", "/api/tags", {"name": "Pilot"})
    assert new.status_code == 200 and post(client, H, "vikram.shah", "/api/tags", {"name": " "}).status_code == 422
    tags = {t["name"]: t["id"] for t in get(client, H, "priya.rao", "/api/tags").json()}
    both = get(client, H, "priya.rao", f"/api/projects?tags={tags['Marketing']},{tags['Customer']}").json()
    assert {p["code"] for p in both} == {"PRJ-108"} and [t["name"] for t in both[0]["tags"]] == ["Marketing", "Customer"]
    only_internal = get(client, H, "priya.rao", f"/api/projects?tags={tags['Internal']}").json()
    assert len(only_internal) == 6


def test_pm_tags_assigned_projects_only(client, H):
    tags = {t["name"]: t["id"] for t in get(client, H, "priya.rao", "/api/tags").json()}
    mine, other = pid(client, H, "PRJ-101"), pid(client, H, "PRJ-105")
    assert put(client, H, "asha.kulkarni", f"/api/projects/{mine}/tags", {"tag_ids": [tags["Software"], tags["Internal"]]}).status_code == 200
    assert put(client, H, "asha.kulkarni", f"/api/projects/{other}/tags", {"tag_ids": [tags["Software"]]}).status_code == 404
    assert put(client, H, "asha.kulkarni", f"/api/projects/{mine}/tags", {"tag_ids": [99999]}).status_code == 422
    assert post(client, H, "asha.kulkarni", "/api/tags", {"name": "Nope"}).status_code == 403


def test_tag_totals_overlap_but_primary_view_adds_up(client, H):
    allp = get(client, H, "priya.rao", "/api/costing/summary").json()
    overlap = get(client, H, "priya.rao", "/api/costing/tags").json()
    prim = get(client, H, "priya.rao", "/api/costing/tags?primary=true").json()
    assert sum(r["cost_minor"] for r in overlap["rows"]) > allp["cost_minor"]   # projects counted under several tags
    assert sum(r["cost_minor"] for r in prim["rows"]) == allp["cost_minor"]     # each project once
    assert prim["additive"] and not overlap["additive"]
    internal = next(r for r in overlap["rows"] if r["tag"] == "Internal")
    assert internal["margin_minor"] == internal["value_minor"] - internal["cost_minor"]


# ---------------- settings ----------------
def test_costing_settings_change_the_numbers_and_are_validated(client, H):
    before = get(client, H, "priya.rao", "/api/costing/summary").json()
    assert client.patch("/api/costing/settings", headers=H("sameer.joshi"), json={"monthly_hours": 0, "hourly_rate_minor": 25000}).status_code == 422
    assert client.patch("/api/costing/settings", headers=H("sameer.joshi"), json={"monthly_hours": 160, "hourly_rate_minor": 0}).status_code == 422
    assert client.patch("/api/costing/settings", headers=H("vikram.shah"), json={"monthly_hours": 160, "hourly_rate_minor": 30000}).status_code == 403
    assert client.patch("/api/costing/settings", headers=H("sameer.joshi"), json={"monthly_hours": 160, "hourly_rate_minor": 30000}).status_code == 200
    after = get(client, H, "priya.rao", "/api/costing/summary").json()
    assert after["value_minor"] == int(before["value_minor"] * 30000 / 25000) and after["cost_minor"] == before["cost_minor"]  # rate moves value, never cost
    client.patch("/api/costing/settings", headers=H("sameer.joshi"), json={"monthly_hours": 160, "hourly_rate_minor": 25000})


def test_project_rate_and_employee_hours_overrides(client, H):
    p = pid(client, H, "PRJ-103")
    base = next(r for r in get(client, H, "priya.rao", "/api/costing/projects").json()["rows"] if r["code"] == "PRJ-103")
    assert put(client, H, "sameer.joshi", f"/api/costing/project-rate/{p}", {"rate_minor": 40000}).status_code == 200
    now = next(r for r in get(client, H, "priya.rao", "/api/costing/projects").json()["rows"] if r["code"] == "PRJ-103")
    assert now["rate_overridden"] and now["value_minor"] == base["value_minor"] * 40000 // 25000 and now["cost_minor"] == base["cost_minor"]
    put(client, H, "sameer.joshi", f"/api/costing/project-rate/{p}", {"rate_minor": None})
    dev = uid(client, H, "Dev Patel")
    assert put(client, H, "sameer.joshi", f"/api/costing/employee-hours/{dev}", {"hours": 80}).status_code == 200
    emp = {e["name"]: e for e in get(client, H, "priya.rao", "/api/costing/employees").json()["rows"]}["Dev Patel"]
    assert emp["hours"] == 100 * 80 / 100 and emp["cost_minor"] == 2000000  # hours halve, cost is allocation x salary and does not
    put(client, H, "sameer.joshi", f"/api/costing/employee-hours/{dev}", {"hours": None})
    assert put(client, H, "sameer.joshi", f"/api/costing/employee-hours/{dev}", {"hours": 400}).status_code == 422


# ---------------- targets and profitability ----------------
def test_targets_and_profitability(client, H):
    p = pid(client, H, "PRJ-102")
    assert put(client, H, "sameer.joshi", "/api/targets", {"level": "project", "project_id": p, "amount_minor": -1}).status_code == 422
    assert put(client, H, "vikram.shah", "/api/targets", {"level": "project", "project_id": p, "amount_minor": 100}).status_code == 403
    assert put(client, H, "sameer.joshi", "/api/targets", {"level": "project", "project_id": p, "amount_minor": 9000000}).status_code == 200
    pr = get(client, H, "priya.rao", "/api/costing/profitability?basis=target").json()
    row = next(r for r in pr["rows"] if r["id"] == p)
    assert row["margin_minor"] == 9000000 - row["cost_minor"] and "Target not set" not in row["warnings"]
    unset = [r for r in pr["rows"] if r["target_minor"] is None]
    assert unset and all("Target not set" in r["warnings"] and r["margin_minor"] is None for r in unset)
    assert pr["excluded_without_revenue"] == len(unset)
    std = get(client, H, "priya.rao", "/api/costing/profitability").json()
    t = std["totals"]
    assert t["margin_minor"] == t["revenue_minor"] - t["cost_minor"] and t["result_after_bench_minor"] == t["margin_minor"] - t["bench_cost_minor"]
    assert t["salary_pool_minor"] == t["cost_minor"] + t["bench_cost_minor"]
    put(client, H, "sameer.joshi", "/api/targets", {"level": "project", "project_id": p, "amount_minor": None})
    assert next(r for r in get(client, H, "priya.rao", "/api/targets").json()["projects"] if r["project_id"] == p)["target_minor"] is None


def test_pm_sees_only_assigned_targets(client, H):
    r = get(client, H, "asha.kulkarni", "/api/targets").json()
    assert {x["code"] for x in r["projects"]} <= {"PRJ-101", "PRJ-102", "PRJ-103", "PRJ-104"} and "org_target_minor" not in r
    assert all("cost_minor" not in x for x in r["projects"]) and r["can_manage"] is False


def test_profitability_requires_cost_capability(client, H):
    for who in ("vikram.shah", "asha.kulkarni", "rohan.mehta", "meera.nair", "kabir.sethi"):
        assert get(client, H, who, "/api/costing/profitability").status_code == 403


def test_dashboard_costing_block_is_masked(client, H):
    assert get(client, H, "priya.rao", "/api/dashboard").json()["costing"]["cost_minor"] > 0
    assert get(client, H, "vikram.shah", "/api/dashboard").json()["costing"] is None


def test_screens_for_sprint3_are_live_and_gated(client, H):
    a = get(client, H, "sameer.joshi", "/api/me").json()["access"]
    assert a["profit"]["level"] and a["costing"]["built"] and a["revenue"]["built"] and a["invoices"]["built"]
    b = get(client, H, "vikram.shah", "/api/me").json()["access"]
    assert b["profit"]["level"] is None and b["allocation"]["level"] == "all"
    c = get(client, H, "meera.nair", "/api/me").json()["access"]
    assert c["employees"]["level"] is None and c["costing"]["level"] is None


def test_tenant_isolation_for_costing(client, H):
    for path in ("/api/employees", "/api/costing/summary", "/api/allocations", "/api/tags"):
        assert get(client, H, "platform.admin", path).status_code == 403
