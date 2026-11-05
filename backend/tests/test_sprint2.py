"""Sprint 2: sprints, tasks, handover with acknowledgement, timesheets with approval, scoping and notifications."""
from datetime import date, timedelta


def get(client, H, who, path):
    return client.get(path, headers=H(who))


def post(client, H, who, path, body=None):
    return client.post(path, headers=H(who), json=body or {})


def tasks_of(client, H, who):
    r = get(client, H, who, "/api/tasks")
    assert r.status_code == 200, r.text
    return r.json()


def pid(client, H, name):
    return next(p["id"] for p in get(client, H, "priya.rao", "/api/projects").json() if p["name"] == name)


# ---- scoping ----
def test_task_scope_by_role(client, H):
    owner = tasks_of(client, H, "priya.rao")
    assert len(owner) >= 25
    meera = tasks_of(client, H, "meera.nair")
    assert meera and all(t["assignee"] == "Meera Nair" for t in meera)  # employee: own work only
    rohan = tasks_of(client, H, "rohan.mehta")  # team lead: Team A people only
    assert {t["assignee"] for t in rohan} <= {"Meera Nair", "Dev Patel", "Isha Kapoor", "Rohan Mehta"}
    asha = {t["project"] for t in tasks_of(client, H, "asha.kulkarni")}
    assert asha and not any("Supply Tracker" in p for p in asha)  # PM: assigned projects only


def test_sales_and_finance_have_no_delivery_access(client, H):
    assert get(client, H, "kabir.sethi", "/api/tasks").status_code == 403
    assert get(client, H, "sameer.joshi", "/api/tasks").status_code == 403
    assert get(client, H, "sameer.joshi", "/api/handovers").status_code == 403


def test_employee_cannot_manage(client, H):
    p = pid(client, H, "Retail Portal Revamp")
    assert post(client, H, "meera.nair", "/api/tasks", {"project_id": p, "title": "x"}).status_code == 403
    assert post(client, H, "meera.nair", "/api/sprints", {"project_id": p, "name": "x"}).status_code == 403


def test_employee_updates_only_own_task_status(client, H):
    own = next(t for t in tasks_of(client, H, "dev.patel") if t["status"] == "In progress")
    assert post(client, H, "dev.patel", f"/api/tasks/{own['id']}/status", {"status": "In progress"}).status_code == 200
    other = next(t for t in tasks_of(client, H, "priya.rao") if t["assignee"] == "Nina Iyer")
    assert post(client, H, "dev.patel", f"/api/tasks/{other['id']}/status", {"status": "Done"}).status_code == 404  # not visible, so not found


# ---- sprints and tasks ----
def test_sprint_rules(client, H):
    p = pid(client, H, "Clinic Appointment Portal")
    r = post(client, H, "nisha.verma", "/api/sprints", {"project_id": p, "name": "Sprint A"})
    assert r.status_code == 200
    s2 = post(client, H, "nisha.verma", "/api/sprints", {"project_id": p, "name": "Sprint B"}).json()["id"]
    sid = r.json()["id"]
    assert post(client, H, "nisha.verma", f"/api/sprints/{sid}/status", {"status": "Active"}).status_code == 200
    assert post(client, H, "nisha.verma", f"/api/sprints/{s2}/status", {"status": "Active"}).status_code == 409  # one active sprint per project
    assert post(client, H, "nisha.verma", f"/api/sprints/{sid}/status", {"status": "Planned"}).status_code == 409
    bad = post(client, H, "nisha.verma", "/api/sprints", {"project_id": p, "name": "X", "start_date": "2026-12-10", "end_date": "2026-12-01"})
    assert bad.status_code == 422
    # a PM cannot touch a project she is not assigned to
    other = pid(client, H, "Retail Portal Revamp")
    assert post(client, H, "nisha.verma", "/api/sprints", {"project_id": other, "name": "Nope"}).status_code == 404


def test_task_create_assign_history_and_notification(client, H):
    p = pid(client, H, "Retail Portal Revamp")
    sprint = next(s for s in get(client, H, "asha.kulkarni", f"/api/sprints?project_id={p}").json() if s["status"] == "Active")
    r = post(client, H, "asha.kulkarni", "/api/tasks", {"project_id": p, "sprint_id": sprint["id"], "title": "Wishlist page", "assignee_id": None, "est_hours": 6})
    assert r.status_code == 200
    tid = r.json()["id"]
    people = {x["name"]: x["id"] for x in get(client, H, "asha.kulkarni", f"/api/projects/{p}/assignable").json()}
    assert "Dev Patel" in people and "Nina Iyer" not in people
    assert post(client, H, "asha.kulkarni", f"/api/tasks/{tid}/assign", {"user_id": people["Dev Patel"], "reason": "Has capacity"}).status_code == 200
    assert post(client, H, "asha.kulkarni", f"/api/tasks/{tid}/assign", {"user_id": people["Dev Patel"]}).status_code == 409  # no change
    assert post(client, H, "asha.kulkarni", f"/api/tasks/{tid}/assign", {"user_id": people["Isha Kapoor"], "reason": "Rebalance"}).status_code == 200
    hist = get(client, H, "asha.kulkarni", f"/api/tasks/{tid}").json()["history"]
    assert [h["to"] for h in hist] == ["Dev Patel", "Isha Kapoor"] and hist[1]["from"] == "Dev Patel"
    nina = next(u for u in get(client, H, "priya.rao", "/api/people").json() if u["name"] == "Nina Iyer")
    assert post(client, H, "asha.kulkarni", f"/api/tasks/{tid}/assign", {"user_id": nina["id"]}).status_code == 422  # not on the project team
    notes = get(client, H, "dev.patel", "/api/notifications").json()
    assert any("Wishlist page" in n["text"] for n in notes["items"])


def test_closed_sprint_locks_tasks(client, H):
    p = pid(client, H, "Aadi Project Tracker Product")
    closed = next(s for s in get(client, H, "asha.kulkarni", f"/api/sprints?project_id={p}").json() if s["status"] == "Closed")
    t = next(t for t in get(client, H, "asha.kulkarni", f"/api/tasks?sprint_id={closed['id']}").json())
    assert post(client, H, "asha.kulkarni", f"/api/tasks/{t['id']}/status", {"status": "Todo"}).status_code == 409


def test_team_lead_assigns_only_within_team(client, H):
    p = pid(client, H, "Supply Tracker")
    # Rohan is not on Supply Tracker, so he cannot manage its work at all
    assert post(client, H, "rohan.mehta", "/api/tasks", {"project_id": p, "title": "x"}).status_code == 404


# ---- handover ----
def test_handover_flow_and_ack_rules(client, H):
    p = pid(client, H, "Aadi SpendOS Expense Platform")
    people = {x["name"]: x["id"] for x in get(client, H, "asha.kulkarni", f"/api/projects/{p}/assignable").json()}
    t = next(t for t in tasks_of(client, H, "asha.kulkarni") if t["project"].endswith("SpendOS Expense Platform") and t["assignee"] == "Dev Patel" and t["status"] != "Done")
    body = {"project_id": p, "from_user_id": people["Dev Patel"], "to_user_id": people["Isha Kapoor"], "task_ids": [t["id"]], "note": "Export fix is half done; see branch notes."}
    assert post(client, H, "asha.kulkarni", "/api/handovers", {**body, "note": " "}).status_code == 422  # a note is mandatory
    r = post(client, H, "asha.kulkarni", "/api/handovers", body)
    assert r.status_code == 200
    hid = r.json()["id"]
    assert post(client, H, "asha.kulkarni", "/api/handovers", body).status_code == 409  # duplicate pending
    moved = get(client, H, "asha.kulkarni", f"/api/tasks/{t['id']}").json()
    assert moved["assignee"] == "Isha Kapoor" and moved["history"][-1]["reason"] == "Handover"
    assert post(client, H, "dev.patel", f"/api/handovers/{hid}/ack").status_code == 404  # only the receiver can acknowledge
    assert post(client, H, "asha.kulkarni", f"/api/handovers/{hid}/ack").status_code == 404
    assert post(client, H, "isha.kapoor", f"/api/handovers/{hid}/ack", {"note": "Got it"}).json()["status"] == "Acknowledged"
    assert post(client, H, "isha.kapoor", f"/api/handovers/{hid}/ack").status_code == 409
    assert any("acknowledged" in n["text"] for n in get(client, H, "asha.kulkarni", "/api/notifications").json()["items"])


def test_handover_rejects_foreign_or_done_tasks(client, H):
    p = pid(client, H, "Retail Portal Revamp")
    people = {x["name"]: x["id"] for x in get(client, H, "asha.kulkarni", f"/api/projects/{p}/assignable").json()}
    done = next(t for t in tasks_of(client, H, "asha.kulkarni") if t["status"] == "Done" and t["project"].endswith("Retail Portal Revamp"))
    r = post(client, H, "asha.kulkarni", "/api/handovers", {"project_id": p, "from_user_id": people["Meera Nair"], "to_user_id": people["Dev Patel"], "task_ids": [done["id"]], "note": "n"})
    assert r.status_code == 422


def test_employee_sees_only_own_handovers(client, H):
    rows = get(client, H, "dev.patel", "/api/handovers").json()
    assert rows and all("Dev Patel" in (h["from"], h["to"]) for h in rows)


# ---- timesheets ----
def last_weekday():
    d = date.today()
    while d.weekday() > 4:
        d -= timedelta(days=1)
    return d


def test_timesheet_validation(client, H):
    pr = get(client, H, "nina.iyer", "/api/timesheets/projects").json()
    sup = next(p for p in pr if "Supply Tracker" in p["label"])
    d = last_weekday().isoformat()
    base = {"project_id": sup["id"], "work_date": d, "hours": 1}
    assert post(client, H, "nina.iyer", "/api/timesheets", {**base, "hours": 0}).status_code == 422
    assert post(client, H, "nina.iyer", "/api/timesheets", {**base, "hours": 25}).status_code == 422
    assert post(client, H, "nina.iyer", "/api/timesheets", {**base, "work_date": (date.today() + timedelta(days=2)).isoformat()}).json()["detail"]["code"] == "FUTURE_DATE"
    other = pid(client, H, "Retail Portal Revamp")  # Nina is not on this project
    assert post(client, H, "nina.iyer", "/api/timesheets", {**base, "project_id": other}).status_code == 403
    assert post(client, H, "nina.iyer", "/api/timesheets", {**base, "hours": 23}).json()["detail"]["code"] == "DAY_LIMIT"


def test_timesheet_submit_approve_reject(client, H):
    pr = get(client, H, "arjun.singh", "/api/timesheets/projects").json()
    proj = next(p for p in pr if "Brand and Website" in p["label"])
    old = (date.today() - timedelta(days=30))
    while old.weekday() > 4:
        old -= timedelta(days=1)
    ids = [post(client, H, "arjun.singh", "/api/timesheets", {"project_id": proj["id"], "work_date": old.isoformat(), "hours": 2, "note": "t"}).json()["id"] for _ in range(2)]
    assert post(client, H, "arjun.singh", "/api/timesheets/submit", {"week": old.isoformat()}).json()["submitted"] == 2
    assert post(client, H, "arjun.singh", f"/api/timesheets/{ids[0]}", {}).status_code == 405
    edit = client.patch(f"/api/timesheets/{ids[0]}", headers=H("arjun.singh"), json={"project_id": proj["id"], "work_date": old.isoformat(), "hours": 3})
    assert edit.status_code == 409  # submitted entries are locked
    # an employee cannot approve, and nobody approves their own time
    assert post(client, H, "arjun.singh", "/api/timesheets/decide", {"ids": ids, "approve": True}).status_code == 403
    assert post(client, H, "rohan.mehta", "/api/timesheets/decide", {"ids": ids, "approve": True}).status_code == 403  # Arjun is not in Rohan's team
    assert post(client, H, "nisha.verma", "/api/timesheets/decide", {"ids": [ids[0]], "approve": False}).json()["detail"]["code"] == "REASON_REQUIRED"
    assert post(client, H, "nisha.verma", "/api/timesheets/decide", {"ids": [ids[0]], "approve": False, "reason": "Wrong project"}).json()["decided"] == 1
    assert post(client, H, "nisha.verma", "/api/timesheets/decide", {"ids": [ids[1]], "approve": True}).json()["decided"] == 1
    assert post(client, H, "nisha.verma", "/api/timesheets/decide", {"ids": [ids[1]], "approve": True}).status_code == 409
    wk = get(client, H, "arjun.singh", f"/api/timesheets?week={old.isoformat()}").json()
    st = {e["id"]: e for e in wk["entries"]}
    assert st[ids[0]]["status"] == "Rejected" and st[ids[0]]["reject_reason"] == "Wrong project" and st[ids[1]]["status"] == "Approved"
    # a rejected entry can be corrected and resubmitted
    assert client.patch(f"/api/timesheets/{ids[0]}", headers=H("arjun.singh"), json={"project_id": proj["id"], "work_date": old.isoformat(), "hours": 2}).status_code == 200
    assert any("rejected" in n["text"] for n in get(client, H, "arjun.singh", "/api/notifications").json()["items"])


def test_manager_cannot_approve_own_time(client, H):
    pr = get(client, H, "rohan.mehta", "/api/timesheets/projects").json()
    proj = pr[0]
    e = post(client, H, "rohan.mehta", "/api/timesheets", {"project_id": proj["id"], "work_date": last_weekday().isoformat(), "hours": 1}).json()["id"]
    post(client, H, "rohan.mehta", "/api/timesheets/submit", {"week": last_weekday().isoformat()})
    assert post(client, H, "rohan.mehta", "/api/timesheets/decide", {"ids": [e], "approve": True}).status_code == 403
    assert post(client, H, "priya.rao", "/api/timesheets/decide", {"ids": [e], "approve": True}).status_code == 200  # someone else may


def test_approvals_scope(client, H):
    team = get(client, H, "rohan.mehta", "/api/timesheets/approvals?status=Approved").json()["entries"]
    assert team and {x["user"] for x in team} <= {"Meera Nair", "Dev Patel", "Isha Kapoor"}
    assert get(client, H, "meera.nair", "/api/timesheets/approvals").status_code == 403
    assert get(client, H, "kabir.sethi", "/api/timesheets/approvals").status_code == 403


def test_dashboard_delivery_blocks(client, H):
    emp = get(client, H, "meera.nair", "/api/dashboard").json()["delivery"]
    assert "tasks" in emp and "pending_approvals" not in emp and "my_week_hours" in emp
    tl = get(client, H, "rohan.mehta", "/api/dashboard").json()["delivery"]
    assert "pending_approvals" in tl
    sales = get(client, H, "kabir.sethi", "/api/dashboard").json()["delivery"]
    assert "tasks" not in sales and "pending_approvals" not in sales


def test_me_marks_sprint2_screens_live(client, H):
    a = get(client, H, "meera.nair", "/api/me").json()["access"]
    assert a["sprint"]["built"] and a["timesheets"]["built"] and a["handover"]["level"] == "own"
    assert not a["revenue"]["built"]


def test_notifications_mark_read(client, H):
    assert get(client, H, "isha.kapoor", "/api/notifications").json()["unread"] > 0
    post(client, H, "isha.kapoor", "/api/notifications/read")
    assert get(client, H, "isha.kapoor", "/api/notifications").json()["unread"] == 0


def test_tenant_isolation_of_delivery_data(client, H):
    # another organization's user (platform admin has no tenant) cannot reach any delivery route
    r = client.get("/api/tasks", headers=H("platform.admin"))
    assert r.status_code == 403
