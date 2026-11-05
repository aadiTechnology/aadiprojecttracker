"""Sprint 2 demo data for Aadi Technology: sprints, tasks, handovers, timesheets, notifications. ALL FICTIONAL.
Dates are relative to today so the demo always looks current. Idempotent: does nothing if the organization already has sprints."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from . import models as m

# project -> (sprint names: closed, active, planned), tasks: title, assignee, status, priority, hours, sprint index
DELIVERY = {
    "Aadi Project Tracker Product": (["Sprint 1 - Foundation", "Sprint 2 - Delivery workflows", "Sprint 3 - Finance modules"], [
        ("Role and permission model", "meera.nair", "Done", "High", 16, 0), ("Customer and project screens", "dev.patel", "Done", "Medium", 20, 0),
        ("Sprint and task board", "meera.nair", "In progress", "High", 18, 1), ("Handover with acknowledgement", "dev.patel", "In progress", "High", 14, 1),
        ("Timesheet entry and approval", "isha.kapoor", "In progress", "High", 20, 1), ("Mobile app: my tasks", "isha.kapoor", "Todo", "Medium", 16, 1),
        ("Revenue target screens", "dev.patel", "Todo", "Medium", 12, 2), ("Invoice register", "meera.nair", "Todo", "Low", 12, 2)]),
    "Aadi SpendOS Expense Platform": (["Hardening 1", "Hardening 2", "Release prep"], [
        ("Load test the receipt upload", "isha.kapoor", "Done", "Medium", 8, 0), ("Fix report export timeout", "dev.patel", "In progress", "High", 10, 1),
        ("Accessibility review", "isha.kapoor", "Blocked", "Medium", 6, 1)]),
    "Retail Portal Revamp": (["Design and discovery", "Checkout beta", "UAT"], [
        ("Catalogue filters", "meera.nair", "Done", "Medium", 18, 0), ("Checkout payment step", "dev.patel", "In progress", "High", 24, 1),
        ("Order confirmation emails", "meera.nair", "In progress", "Medium", 10, 1), ("Admin console reports", "isha.kapoor", "Todo", "Low", 16, 1),
        ("UAT test plan", "isha.kapoor", "Todo", "Medium", 8, 2)]),
    "Learning App Pilot": (["Prototype", "Pilot release", "Feedback round"], [
        ("Quiz engine scoring", "meera.nair", "Done", "High", 14, 0), ("Teacher dashboard", "isha.kapoor", "In progress", "High", 18, 1),
        ("Progress report PDF", "meera.nair", "Todo", "Medium", 10, 1)]),
    "Supply Tracker": (["Architecture", "Telemetry v1", "Driver app beta"], [
        ("Ingestion pipeline", "nina.iyer", "Done", "High", 24, 0), ("Live map view", "arjun.singh", "In progress", "High", 20, 1),
        ("Driver app login", "nina.iyer", "Blocked", "High", 10, 1), ("Geofence alerts (pending scope approval)", "nina.iyer", "Todo", "Medium", 12, 2)]),
    "Aadi Brand and Website Relaunch": (["Messaging", "Site build", "Launch"], [
        ("Homepage copy and layout", "arjun.singh", "Done", "High", 12, 0), ("Product pages", "arjun.singh", "In progress", "High", 20, 1),
        ("Case study: Northwind Retail", "nina.iyer", "Todo", "Medium", 8, 1)]),
    "Harbor Foods Social Campaign": (["Planning", "Festival launch", "Wrap-up"], [
        ("Content calendar", "arjun.singh", "Done", "Medium", 8, 0), ("Festival creative set", "arjun.singh", "In progress", "High", 14, 1)]),
    "Enterprise Pipeline Build-out": (["Research", "Proposal kit", "Outreach"], [
        ("Target account list (50 accounts)", "nina.iyer", "Done", "Medium", 10, 0), ("Proposal template", "nina.iyer", "In progress", "High", 10, 1)]),
}
# who logs time on which (project, task, hours per day) and who approves them
TIME_PLAN = {
    "meera.nair": [("Aadi Project Tracker Product", "Sprint and task board", 5.0), ("Learning App Pilot", "Progress report PDF", 3.0)],
    "dev.patel": [("Retail Portal Revamp", "Checkout payment step", 8.0), ("Aadi Project Tracker Product", "Handover with acknowledgement", 4.0)],
    "isha.kapoor": [("Aadi Project Tracker Product", "Timesheet entry and approval", 8.0), ("Learning App Pilot", "Teacher dashboard", 4.0)],
    "nina.iyer": [("Supply Tracker", "Driver app login", 4.0), ("Aadi Brand and Website Relaunch", "Case study: Northwind Retail", 4.0)],
    "arjun.singh": [("Supply Tracker", "Live map view", 4.0), ("Aadi Brand and Website Relaunch", "Product pages", 4.0)],
}
APPROVER = {"meera.nair": "rohan.mehta", "dev.patel": "rohan.mehta", "isha.kapoor": "rohan.mehta", "nina.iyer": "nisha.verma", "arjun.singh": "nisha.verma"}
THIS_WEEK = {"meera.nair": "Draft", "dev.patel": "Submitted", "isha.kapoor": "Rejected", "nina.iyer": "Submitted", "arjun.singh": "Draft"}


def seed_delivery(db, t) -> bool:
    if db.execute(select(m.Sprint).where(m.Sprint.tenant_id == t.id)).first():
        return False
    uid = {u.email.split("@")[0]: u.id for u in db.execute(select(m.User)).scalars()}
    key = {v: k for k, v in uid.items()}
    proj = {p.name: p for p in db.execute(select(m.Project).where(m.Project.tenant_id == t.id)).scalars()}
    today = date.today()
    m0 = today - timedelta(days=today.weekday())
    spans = [(m0 - timedelta(days=14), m0 - timedelta(days=1), "Closed"), (m0, m0 + timedelta(days=13), "Active"), (m0 + timedelta(days=14), m0 + timedelta(days=27), "Planned")]
    tasks = {}
    for pname, (names, items) in DELIVERY.items():
        p = proj[pname]
        sp = []
        for nm, (a, b, st) in zip(names, spans):
            s = m.Sprint(tenant_id=t.id, project_id=p.id, name=nm, goal=f"{nm}: {p.name}", start_date=a, end_date=b, status=st)
            db.add(s)
            sp.append(s)
        db.flush()
        for title, who, status, prio, hrs, idx in items:
            tk = m.Task(tenant_id=t.id, project_id=p.id, sprint_id=sp[idx].id, title=title, status=status, priority=prio, est_hours=hrs, assignee_id=uid[who],
                        created_by=p.pm_user_id, due_date=spans[idx][1])
            db.add(tk)
            db.flush()
            db.add(m.TaskAssignment(tenant_id=t.id, task_id=tk.id, to_user_id=uid[who], by_user_id=p.pm_user_id, reason="Initial assignment"))
            tasks[(pname, title)] = tk

    def handover(pname, titles, frm, to, by, note, ack):
        h = m.Handover(tenant_id=t.id, project_id=proj[pname].id, from_user_id=uid[frm], to_user_id=uid[to], created_by=uid[by], note=note,
                       task_ids=[tasks[(pname, x)].id for x in titles], status="Acknowledged" if ack else "Pending",
                       ack_at=datetime.now(timezone.utc) - timedelta(days=1) if ack else None, ack_note="Understood, picking this up." if ack else "")
        db.add(h)
        db.flush()
        for x in titles:
            tk = tasks[(pname, x)]
            db.add(m.TaskAssignment(tenant_id=t.id, task_id=tk.id, from_user_id=uid[frm], to_user_id=uid[to], by_user_id=uid[by], reason="Handover", handover_id=h.id))
            tk.assignee_id = uid[to]

    handover("Retail Portal Revamp", ["Order confirmation emails"], "meera.nair", "dev.patel", "asha.kulkarni",
             "Email templates are in the shared repo. Provider credentials are in the vault. Remaining: order-cancelled template and retry on bounce.", True)
    handover("Learning App Pilot", ["Progress report PDF"], "meera.nair", "isha.kapoor", "asha.kulkarni",
             "Meera moves to the Tracker mobile app. The PDF layout is agreed with Lumen Academy; the data query is already written. Next: pagination and the school logo.", False)

    def days(start, count):
        return [d for d in (start + timedelta(days=i) for i in range(count)) if d.weekday() < 5]

    for who, lines in TIME_PLAN.items():
        for week_start, count, state in ((m0 - timedelta(days=7), 5, "Approved"), (m0, today.weekday() + 1, THIS_WEEK[who])):
            for i, d in enumerate(days(week_start, count)):
                pname, title, hrs = lines[i % 2]
                e = m.TimeEntry(tenant_id=t.id, user_id=uid[who], project_id=proj[pname].id, task_id=tasks[(pname, title)].id, work_date=d, hours=hrs, note=title, status=state)
                if state in ("Approved", "Rejected"):
                    e.decided_by, e.decided_at = uid[APPROVER[who]], datetime.now(timezone.utc) - timedelta(days=1)
                if state == "Rejected":
                    e.reject_reason = "Please split the hours between the two projects as discussed."
                db.add(e)
    for who, text, link in (("dev.patel", "Handover from Meera Nair on Retail Portal Revamp was acknowledged.", "/handover"),
                            ("isha.kapoor", "Handover from Meera Nair on Learning App Pilot: 1 task(s). Please acknowledge.", "/handover"),
                            ("isha.kapoor", "Rohan Mehta rejected your time. Reason: Please split the hours between the two projects as discussed.", "/timesheets"),
                            ("rohan.mehta", "Dev Patel submitted a timesheet for week of " + m0.isoformat() + ".", "/timesheets"),
                            ("nisha.verma", "Nina Iyer submitted a timesheet for week of " + m0.isoformat() + ".", "/timesheets"),
                            ("nisha.verma", "Blocked: Driver app login (Nina Iyer)", "/sprint")):
        db.add(m.Notification(tenant_id=t.id, user_id=uid[who], text=text, link=link))
    return True
