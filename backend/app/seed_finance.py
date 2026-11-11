"""Sprint 4 demo data for any demo organization: expenses (direct and shared), invoices in every state with payments, approved timesheets
for planned-vs-actual, and a few review comments. ALL FICTIONAL. Idempotent: does nothing when the organization already has expenses."""
from datetime import date, datetime, timedelta, timezone
from math import ceil

from sqlalchemy import select

from . import costing, models as m, people

SHARED = [("Infrastructure", "Contabo", "Cloud servers for all products", 1800000, "hours", 3), ("Software", "OpenAI and ChatGPT", "AI subscriptions used by every team", 900000, "equal", 4),
          ("Rent & Utilities", "Landlord and ISP", "Office rent and Wi-Fi", 2400000, "headcount", 5), ("Marketing", "Search and social ads", "Brand campaign, shared across products", 600000, "hours", 6)]


def _weekdays(lo: date, hi: date):
    d, out = lo, []
    while d <= hi:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out or [hi]


def seed_finance(db, t) -> bool:
    if db.execute(select(m.Expense).where(m.Expense.tenant_id == t.id)).first():
        return False
    by_role = {}
    for person in people.people(db, t.id).values():
        by_role.setdefault(person.role_key, []).append(person.id)
    owner = by_role["owner"][0]
    fin = (by_role.get("finance") or [owner])[0]
    mgr = (by_role.get("pm") or by_role.get("ops") or [owner])[0]
    today = date.today()
    month = costing.month_start()
    projects = db.execute(select(m.Project, m.Customer).join(m.Customer, m.Customer.id == m.Project.customer_id).where(m.Project.tenant_id == t.id).order_by(m.Project.code)).all()
    client = [p for p, cu in projects if cu.kind == "customer" and p.status in ("Active", "Planned")]
    own = [p for p, cu in projects if cu.kind != "customer"]
    # ---- expenses
    for cat, vendor, desc, amt, method, day in SHARED:
        db.add(m.Expense(tenant_id=t.id, category=cat, vendor=vendor, description=desc, amount_minor=amt, spent_on=month.replace(day=min(day, 28)), project_id=None,
                         alloc_method=method, status="Paid" if day < 5 else "Planned", created_by=fin))
    direct = [("Software", "Design tools", "Licences for the project team", 600000, client[0] if client else None, 2), ("Consulting", "External security consultant", "Review of the delivery approach", 1200000, client[1] if len(client) > 1 else None, 4),
              ("Third Party Solutions", "SMS and email gateway", "Notifications for the product", 350000, own[0] if own else None, 3)]
    for cat, vendor, desc, amt, proj, day in direct:
        if proj:
            db.add(m.Expense(tenant_id=t.id, category=cat, vendor=vendor, description=desc, amount_minor=amt, spent_on=month.replace(day=day), project_id=proj.id,
                             alloc_method="hours", status="Paid", created_by=fin))
    # ---- invoices (every state)
    n = 0

    def invoice(proj, status, total_rupees, issued_days_ago, due_in, lines, paid_rupees=0, tax=18.0, approver=True):
        nonlocal n
        n += 1
        sub = total_rupees * 100
        tax_minor = costing.half_up(sub * int(tax * 100), 10000)
        issue = today - timedelta(days=issued_days_ago)
        inv = m.Invoice(tenant_id=t.id, number=f"INV-{issue.year}-{n:03d}", project_id=proj.id, customer_id=proj.customer_id, issue_date=issue, due_date=issue + timedelta(days=due_in),
                        lines=[{"description": d, "amount_minor": a * 100} for d, a in lines], subtotal_minor=sub, tax_pct=tax, tax_minor=tax_minor, total_minor=sub + tax_minor,
                        status=status, note="Illustrative invoice (demo data).", created_by=fin, approved_by=owner if approver and status != "Draft" else None)
        db.add(inv)
        db.flush()
        if paid_rupees:
            db.add(m.InvoicePayment(tenant_id=t.id, invoice_id=inv.id, amount_minor=paid_rupees * 100, paid_on=today - timedelta(days=max(0, issued_days_ago - 6)), reference="Bank transfer (demo)", recorded_by=fin))
        return inv

    specs = [("Issued", 60000, 28, 30, [("Milestone 1: design and set-up", 40000), ("Change request 1", 20000)], 70800),  # paid in full (incl. tax)
             ("Issued", 50000, 20, 30, [("Monthly delivery, first half", 50000)], 30000),  # partially paid
             ("Issued", 40000, 55, 30, [("Build and testing", 40000)], 0),  # overdue
             ("Issued", 24000, 3, 30, [("Consulting, first week", 24000)], 0),  # issued, not yet due
             ("Approved", 36000, 0, 15, [("Milestone 2: release", 36000)], 0),
             ("Draft", 18000, 0, 15, [("Support retainer", 18000)], 0)]
    for i, (status, total, ago, due, lines, paid) in enumerate(specs if client else []):
        invoice(client[i % len(client)], status, total, ago, due, lines, paid_rupees=paid)
    # ---- approved timesheets so planned vs actual has something to compare (skipped when the organization already logs time this month)
    already = db.execute(select(m.TimeEntry).where(m.TimeEntry.tenant_id == t.id, m.TimeEntry.work_date >= month, m.TimeEntry.status == "Approved")).first()
    if not already:
        elapsed = today.day / ((month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)).day
        days = _weekdays(month, today)
        allocs = db.execute(select(m.Allocation).where(m.Allocation.tenant_id == t.id, m.Allocation.month == month)).scalars().all()
        mem = {x.user_id: x for x in db.execute(select(m.Membership).where(m.Membership.tenant_id == t.id)).scalars()}  # the profile rows: team and hours
        per_user, k = {}, 0
        for a in sorted(allocs, key=lambda x: (x.user_id, x.project_id)):
            k += 1
            factor = 1.45 if k == 3 else (0.3 if k == 9 else 1.0)  # one project over plan and one behind, on purpose
            hours = mem[a.user_id].hours_override or t.monthly_hours
            per_user.setdefault(a.user_id, []).append((a.project_id, round(a.percent * hours / 100 * elapsed * factor * 2) / 2))
        for uid, items in per_user.items():
            queue = [[p, h] for p, h in items if h > 0]
            for di, day in enumerate(days):
                room = 8.0
                while room > 0 and queue:
                    p, h = queue[0]
                    take = min(room, h)
                    last = di == len(days) - 1
                    db.add(m.TimeEntry(tenant_id=t.id, user_id=uid, project_id=p, work_date=day, hours=take, note="Demo entry", status="Submitted" if last else "Approved",
                                       decided_by=None if last else mgr, decided_at=None if last else datetime.now(timezone.utc)))
                    room -= take
                    queue[0][1] -= take
                    if queue[0][1] <= 0:
                        queue.pop(0)
    # ---- review comments (one still waiting for the employee)
    staff = [u for u in (by_role.get("employee") or []) if u != owner][:2]
    texts = [("Delivery reliability", "Finished the sprint scope two days early and picked up a blocked item from a teammate. Handover note was complete."),
             ("Estimate accuracy", "Two estimates ran well over the plan this month. Let us split large tasks before committing, and review them together on Monday.")]
    for i, uid in enumerate(staff):
        db.add(m.PerfReview(tenant_id=t.id, user_id=uid, reviewer_id=owner, month=month, dimension=texts[i][0], comment=texts[i][1],
                            ack_at=datetime.now(timezone.utc) if i == 0 else None, ack_note="Thanks, noted." if i == 0 else ""))
    return True


def seed_task_hours(db, t) -> bool:
    """Approved hours (last month) on finished tasks, so estimate accuracy has data. Own guard, so existing demo databases receive it too."""
    if db.execute(select(m.TimeEntry).where(m.TimeEntry.tenant_id == t.id, m.TimeEntry.note == "Demo estimate sample")).first():
        return False
    month = costing.month_start()
    when = (month - timedelta(days=1)).replace(day=15)
    boss = next((p for p in people.people(db, t.id).values() if p.role_key == "owner"), None)
    done = db.execute(select(m.Task).where(m.Task.tenant_id == t.id, m.Task.status == "Done", m.Task.est_hours > 0, m.Task.assignee_id.is_not(None)).order_by(m.Task.id)).scalars().all()
    for i, task in enumerate(done):
        db.add(m.TimeEntry(tenant_id=t.id, user_id=task.assignee_id, project_id=task.project_id, task_id=task.id, work_date=when, hours=round(task.est_hours * (0.8, 1.0, 1.3, 1.1)[i % 4] * 2) / 2 or 0.5,
                           note="Demo estimate sample", status="Approved", decided_by=boss.id if boss else None, decided_at=datetime.now(timezone.utc)))
    return bool(done)


def enable_assistant(db, t) -> bool:
    """Demo organizations get the advisory assistant switched on; real organizations opt in per tenant (module entitlement, off by default)."""
    e = db.execute(select(m.Entitlement).where(m.Entitlement.tenant_id == t.id, m.Entitlement.module == "ai")).scalar_one_or_none()
    if e is None:
        db.add(m.Entitlement(tenant_id=t.id, module="ai", enabled=True))
        return True
    if not e.enabled:
        e.enabled = True
        return True
    return False
