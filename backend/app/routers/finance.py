"""Sprint 4: expenses and shared-cost allocation, invoices with approval and payments, planned vs actual from approved timesheets,
the project contribution view (value, salary, direct expenses, shared overhead, invoiced, collected) and the employee performance matrix.
Money exists in a response only for roles that hold the matching capability; everyone else never receives those numbers."""
from calendar import monthrange
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from .. import costing as k, models as m
from ..core import Ctx, audit, ctx, err
from .costing import MAX_MONEY, OPEN_STATUSES, _month, visible
from .work import assigned_project_ids

router = APIRouter(prefix="/api", tags=["finance"])

CATEGORIES = ["Infrastructure", "Third Party Solutions", "Software", "Marketing", "Sales", "Consulting", "Rent & Utilities", "Other"]
METHODS = {"equal": "Equal share between active projects", "hours": "In proportion to planned hours", "headcount": "In proportion to people allocated"}
DIMENSIONS = ["Delivery reliability", "Quality / acceptance", "Estimate accuracy", "Collaboration / handover", "Billable contribution", "Goal achievement", "General"]


def split(amount: int, weights: dict) -> dict:
    """Largest-remainder split of whole paise: the parts always add up to `amount` exactly."""
    total = sum(weights.values())
    if total <= 0 or amount == 0:
        return {}
    raw = {key: amount * w / total for key, w in weights.items()}
    out = {key: int(v) for key, v in raw.items()}
    left = amount - sum(out.values())
    for key in sorted(raw, key=lambda x: raw[x] - out[x], reverse=True)[:left]:
        out[key] += 1
    return out


def month_bounds(month: date):
    return month, k.month_end(month)


def shared_allocation(r: dict, expenses) -> tuple[dict, int]:
    """(project id -> allocated shared cost, unallocated paise) for the shared expenses given, using each expense's own method."""
    per = {pid: v for pid, v in r["proj"].items() if v["people"] > 0 and v["hours"] > 0}
    out, lost = {}, 0
    for e in expenses:
        w = {"equal": {pid: 1 for pid in per}, "hours": {pid: int(round(v["hours"] * 100)) for pid, v in per.items()},
             "headcount": {pid: v["people"] for pid, v in per.items()}}.get(e.alloc_method, {})
        parts = split(e.amount_minor, w)
        if not parts:
            lost += e.amount_minor
        for pid, v in parts.items():
            out[pid] = out.get(pid, 0) + v
    return out, lost


def _denied(c: Ctx, cap: str, action: str, entity_id):
    """Authorization failures on finance actions are audited, as the PRD requires, then re-raised."""
    try:
        return c.require(cap)
    except HTTPException:
        audit(c.db, c.tid, c.user.id, f"{action}.denied", "invoice", entity_id)
        c.db.commit()
        raise


# ---------------- expenses ----------------
class ExpenseIn(BaseModel):
    category: str
    vendor: str = ""
    description: str = ""
    amount_minor: int
    spent_on: date
    project_id: int | None = None
    alloc_method: str = "hours"
    status: str = "Planned"


def _exp_row(x: m.Expense, pnames: dict):
    return {"id": x.id, "category": x.category, "vendor": x.vendor, "description": x.description, "amount_minor": x.amount_minor,
            "spent_on": x.spent_on.isoformat(), "project_id": x.project_id, "project": pnames.get(x.project_id), "shared": x.project_id is None,
            "alloc_method": x.alloc_method if x.project_id is None else None, "status": x.status}


@router.get("/expenses")
def expenses(month: str | None = None, c: Ctx = Depends(ctx)):
    c.require("expenses.view")
    mo = _month(month)
    lo, hi = month_bounds(mo)
    d = k.load(c, mo)
    r = k.compute(d)
    rows = c.db.execute(select(m.Expense).where(m.Expense.tenant_id == c.tid, m.Expense.spent_on >= lo, m.Expense.spent_on <= hi)
                        .order_by(m.Expense.spent_on.desc(), m.Expense.id.desc())).scalars().all()
    pnames = {pid: f"{p['code']} {p['name']}" for pid, p in d["projects"].items()}
    shared = [x for x in rows if x.project_id is None]
    alloc, lost = shared_allocation(r, shared)
    by_cat = {}
    for x in rows:
        by_cat[x.category] = by_cat.get(x.category, 0) + x.amount_minor
    direct = {}
    for x in rows:
        if x.project_id:
            direct[x.project_id] = direct.get(x.project_id, 0) + x.amount_minor
    return {"month": mo.strftime("%Y-%m"), "can_manage": c.can("expenses.manage"), "categories": CATEGORIES, "methods": METHODS,
            "projects": [{"id": pid, "name": pnames[pid]} for pid in d["projects"]],
            "rows": [_exp_row(x, pnames) for x in rows],
            "totals": {"all_minor": sum(x.amount_minor for x in rows), "direct_minor": sum(direct.values()), "shared_minor": sum(x.amount_minor for x in shared),
                       "unpaid_minor": sum(x.amount_minor for x in rows if x.status == "Planned")},
            "by_category": [{"category": cat, "amount_minor": v} for cat, v in sorted(by_cat.items(), key=lambda kv: -kv[1])],
            "allocation": [{"project_id": pid, "project": pnames[pid], "direct_minor": direct.get(pid, 0), "shared_minor": alloc.get(pid, 0),
                            "total_minor": direct.get(pid, 0) + alloc.get(pid, 0)} for pid in d["projects"] if direct.get(pid) or alloc.get(pid)],
            "unallocated_minor": lost,
            "note": "Direct costs belong to one project. Shared costs are split with the method chosen on each line, to whole paise, so the split always equals the source expense. Salary cost is not repeated here."}


@router.post("/expenses")
def add_expense(b: ExpenseIn, c: Ctx = Depends(ctx)):
    c.require("expenses.manage")
    if b.category not in CATEGORIES:
        raise err(422, "VALIDATION", "Choose one of the listed categories.")
    if not 0 < b.amount_minor <= MAX_MONEY:
        raise err(422, "VALIDATION", "Enter an amount above zero.")
    if b.alloc_method not in METHODS or b.status not in ("Planned", "Paid"):
        raise err(422, "VALIDATION", "Choose a valid allocation method and payment status.")
    if len(b.vendor) > 120 or len(b.description) > 300:
        raise err(422, "VALIDATION", "Vendor or description is too long.")
    if b.project_id is not None:
        p = c.db.get(m.Project, b.project_id)
        if not p or p.tenant_id != c.tid:
            raise err(422, "VALIDATION", "Choose an existing project, or leave it blank for a shared cost.")
    x = m.Expense(tenant_id=c.tid, category=b.category, vendor=b.vendor.strip(), description=b.description.strip(), amount_minor=b.amount_minor,
                  spent_on=b.spent_on, project_id=b.project_id, alloc_method=b.alloc_method, status=b.status, created_by=c.user.id)
    c.db.add(x)
    c.db.flush()
    audit(c.db, c.tid, c.user.id, "expense.create", "expense", x.id, category=b.category, amount_minor=b.amount_minor, shared=b.project_id is None)
    c.db.commit()
    return {"id": x.id}


class ExpensePatch(BaseModel):
    status: str


@router.patch("/expenses/{eid}")
def pay_expense(eid: int, b: ExpensePatch, c: Ctx = Depends(ctx)):
    c.require("expenses.manage")
    x = c.db.get(m.Expense, eid)
    if not x or x.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Expense not found.")
    if b.status not in ("Planned", "Paid"):
        raise err(422, "VALIDATION", "Status must be Planned or Paid.")
    x.status = b.status
    audit(c.db, c.tid, c.user.id, "expense.status", "expense", x.id, status=b.status)
    c.db.commit()
    return {"ok": True}


@router.delete("/expenses/{eid}")
def delete_expense(eid: int, c: Ctx = Depends(ctx)):
    c.require("expenses.manage")
    x = c.db.get(m.Expense, eid)
    if not x or x.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Expense not found.")
    audit(c.db, c.tid, c.user.id, "expense.delete", "expense", x.id, category=x.category, amount_minor=x.amount_minor)
    c.db.delete(x)
    c.db.commit()
    return {"ok": True}


# ---------------- invoices ----------------
class LineIn(BaseModel):
    description: str
    amount_minor: int


class InvoiceIn(BaseModel):
    project_id: int
    issue_date: date
    due_date: date
    lines: list[LineIn]
    tax_pct: float = 0
    note: str = ""


class PaymentIn(BaseModel):
    amount_minor: int
    paid_on: date
    reference: str = ""


def _paid(c: Ctx, ids):
    out = {}
    for p in c.db.execute(select(m.InvoicePayment).where(m.InvoicePayment.tenant_id == c.tid, m.InvoicePayment.invoice_id.in_(ids or {-1}))).scalars():
        out[p.invoice_id] = out.get(p.invoice_id, 0) + p.amount_minor
    return out


def _state(i: m.Invoice, paid: int, today: date):
    """Draft, Approved and Void are stored. Paid, Partially Paid and Overdue are derived from payments and the due date."""
    out = i.total_minor - paid
    if i.status != "Issued":
        return i.status, out
    if paid >= i.total_minor:
        return "Paid", 0
    if i.due_date < today:
        return "Overdue", out
    return ("Partially Paid" if paid else "Issued"), out


def _inv_row(i: m.Invoice, paid: int, names: dict, today: date):
    status, out = _state(i, paid, today)
    return {"id": i.id, "number": i.number, "project_id": i.project_id, "project": names["p"].get(i.project_id), "customer": names["c"].get(i.customer_id),
            "issue_date": i.issue_date.isoformat(), "due_date": i.due_date.isoformat(), "status": status, "stored_status": i.status,
            "subtotal_minor": i.subtotal_minor, "tax_pct": i.tax_pct, "tax_minor": i.tax_minor, "total_minor": i.total_minor, "paid_minor": paid,
            "outstanding_minor": out if i.status != "Void" else 0, "days_overdue": (today - i.due_date).days if status == "Overdue" else 0, "note": i.note,
            "created_by": names["u"].get(i.created_by), "approved_by": names["u"].get(i.approved_by)}


def _inv_names(c: Ctx):
    return {"p": {p.id: f"{p.code} {p.name}" for p in c.db.execute(select(m.Project).where(m.Project.tenant_id == c.tid)).scalars()},
            "c": {x.id: x.name for x in c.db.execute(select(m.Customer).where(m.Customer.tenant_id == c.tid)).scalars()},
            "u": {u.id: u.name for u in c.db.execute(select(m.User)).scalars()}}


def _invoice(c: Ctx, iid: int) -> m.Invoice:
    i = c.db.get(m.Invoice, iid)
    if not i or i.tenant_id != c.tid:
        raise err(404, "NOT_FOUND", "Invoice not found.")
    return i


@router.get("/invoices")
def invoices(c: Ctx = Depends(ctx)):
    c.require("invoices.view")
    today = date.today()
    rows = c.db.execute(select(m.Invoice).where(m.Invoice.tenant_id == c.tid).order_by(m.Invoice.issue_date.desc(), m.Invoice.id.desc())).scalars().all()
    paid = _paid(c, {i.id for i in rows})
    names = _inv_names(c)
    out = [_inv_row(i, paid.get(i.id, 0), names, today) for i in rows]
    live = [x for x in out if x["status"] in ("Issued", "Partially Paid", "Paid", "Overdue")]
    return {"rows": out, "can_manage": c.can("invoices.manage"), "can_approve": c.can("invoices.approve"),
            "projects": [{"id": pid, "name": n} for pid, n in names["p"].items()],
            "summary": {"invoiced_minor": sum(x["total_minor"] for x in live), "collected_minor": sum(x["paid_minor"] for x in live),
                        "outstanding_minor": sum(x["outstanding_minor"] for x in live), "overdue_minor": sum(x["outstanding_minor"] for x in live if x["status"] == "Overdue"),
                        "overdue_count": sum(1 for x in live if x["status"] == "Overdue"), "drafts": sum(1 for x in out if x["status"] == "Draft"),
                        "awaiting_issue": sum(1 for x in out if x["status"] == "Approved")},
            "note": "Invoiced, collected and outstanding are shown separately and are never called revenue. Tax is whatever you enter per invoice: no statutory rate is assumed."}


@router.get("/invoices/{iid}")
def invoice_detail(iid: int, c: Ctx = Depends(ctx)):
    c.require("invoices.view")
    i = _invoice(c, iid)
    pays = c.db.execute(select(m.InvoicePayment).where(m.InvoicePayment.invoice_id == i.id).order_by(m.InvoicePayment.paid_on, m.InvoicePayment.id)).scalars().all()
    names = _inv_names(c)
    cust = c.db.get(m.Customer, i.customer_id)
    return {**_inv_row(i, sum(p.amount_minor for p in pays), names, date.today()), "lines": i.lines, "billing_details": cust.billing_details if cust else "",
            "payments": [{"id": p.id, "amount_minor": p.amount_minor, "paid_on": p.paid_on.isoformat(), "reference": p.reference, "by": names["u"].get(p.recorded_by)} for p in pays]}


@router.post("/invoices")
def add_invoice(b: InvoiceIn, c: Ctx = Depends(ctx)):
    c.require("invoices.manage")
    p = c.db.get(m.Project, b.project_id)
    if not p or p.tenant_id != c.tid:
        raise err(422, "VALIDATION", "Choose an existing project.")
    if not 1 <= len(b.lines) <= 20 or any(not x.description.strip() or not 0 < x.amount_minor <= MAX_MONEY for x in b.lines):
        raise err(422, "VALIDATION", "Add 1 to 20 lines, each with a description and an amount above zero.")
    if not 0 <= b.tax_pct <= 100:
        raise err(422, "VALIDATION", "Tax must be between 0 and 100 percent.")
    if b.due_date < b.issue_date:
        raise err(422, "VALIDATION", "The due date cannot be before the issue date.")
    sub = sum(x.amount_minor for x in b.lines)
    tax = k.half_up(sub * int(round(b.tax_pct * 100)), 10000)
    n = c.db.query(m.Invoice).filter(m.Invoice.tenant_id == c.tid).count() + 1
    number = f"INV-{b.issue_date.year}-{n:03d}"
    while c.db.execute(select(m.Invoice).where(m.Invoice.tenant_id == c.tid, m.Invoice.number == number)).first():
        n += 1
        number = f"INV-{b.issue_date.year}-{n:03d}"
    i = m.Invoice(tenant_id=c.tid, number=number, project_id=p.id, customer_id=p.customer_id, issue_date=b.issue_date, due_date=b.due_date,
                  lines=[{"description": x.description.strip()[:200], "amount_minor": x.amount_minor} for x in b.lines], subtotal_minor=sub,
                  tax_pct=b.tax_pct, tax_minor=tax, total_minor=sub + tax, status="Draft", note=b.note.strip()[:300], created_by=c.user.id)
    c.db.add(i)
    c.db.flush()
    audit(c.db, c.tid, c.user.id, "invoice.draft", "invoice", i.id, number=number, total_minor=i.total_minor)
    c.db.commit()
    return {"id": i.id, "number": number}


@router.post("/invoices/{iid}/approve")
def approve_invoice(iid: int, c: Ctx = Depends(ctx)):
    _denied(c, "invoices.approve", "invoice.approve", iid)
    i = _invoice(c, iid)
    if i.status != "Draft":
        raise err(409, "BAD_STATE", "Only a draft can be approved.")
    i.status, i.approved_by = "Approved", c.user.id
    audit(c.db, c.tid, c.user.id, "invoice.approve", "invoice", i.id, number=i.number)
    if i.created_by != c.user.id:
        c.db.add(m.Notification(tenant_id=c.tid, user_id=i.created_by, text=f"Invoice {i.number} was approved and is ready to issue.", link="/invoices"))
    c.db.commit()
    return {"ok": True}


@router.post("/invoices/{iid}/issue")
def issue_invoice(iid: int, c: Ctx = Depends(ctx)):
    _denied(c, "invoices.manage", "invoice.issue", iid)
    i = _invoice(c, iid)
    if i.status != "Approved":
        raise err(409, "BAD_STATE", "An invoice must be approved before it is issued.")
    i.status = "Issued"
    audit(c.db, c.tid, c.user.id, "invoice.issue", "invoice", i.id, number=i.number, total_minor=i.total_minor)
    c.db.commit()
    return {"ok": True}


@router.post("/invoices/{iid}/payments")
def pay_invoice(iid: int, b: PaymentIn, c: Ctx = Depends(ctx)):
    c.require("invoices.manage")
    i = _invoice(c, iid)
    if i.status != "Issued":
        raise err(409, "BAD_STATE", "Payments can be recorded only on an issued invoice.")
    out = i.total_minor - _paid(c, {i.id}).get(i.id, 0)
    if not 0 < b.amount_minor <= out:
        raise err(422, "VALIDATION", "The payment must be above zero and not more than the outstanding balance.")
    c.db.add(m.InvoicePayment(tenant_id=c.tid, invoice_id=i.id, amount_minor=b.amount_minor, paid_on=b.paid_on, reference=b.reference.strip()[:80], recorded_by=c.user.id))
    audit(c.db, c.tid, c.user.id, "invoice.payment", "invoice", i.id, number=i.number, amount_minor=b.amount_minor)
    c.db.commit()
    return {"ok": True}


@router.post("/invoices/{iid}/void")
def void_invoice(iid: int, c: Ctx = Depends(ctx)):
    c.require("invoices.manage")
    i = _invoice(c, iid)
    if i.status == "Void" or _paid(c, {i.id}).get(i.id, 0) > 0:
        raise err(409, "BAD_STATE", "An invoice that is void or has payments cannot be voided.")
    i.status = "Void"
    audit(c.db, c.tid, c.user.id, "invoice.void", "invoice", i.id, number=i.number)
    c.db.commit()
    return {"ok": True}


# ---------------- contribution (value, salary, direct expenses, shared overhead, invoiced, collected) ----------------
@router.get("/finance/contribution")
def contribution(month: str | None = None, c: Ctx = Depends(ctx)):
    c.require("costing.cost")
    c.require("expenses.view")
    if c.scope("costing.effort") != "all":
        raise err(403, "FORBIDDEN", "Contribution needs organization-wide access.")
    mo = _month(month)
    lo, hi = month_bounds(mo)
    d = k.load(c, mo)
    r = k.compute(d)
    exp = c.db.execute(select(m.Expense).where(m.Expense.tenant_id == c.tid, m.Expense.spent_on >= lo, m.Expense.spent_on <= hi)).scalars().all()
    direct = {}
    for x in exp:
        if x.project_id:
            direct[x.project_id] = direct.get(x.project_id, 0) + x.amount_minor
    shared_total = sum(x.amount_minor for x in exp if x.project_id is None)
    alloc, lost = shared_allocation(r, [x for x in exp if x.project_id is None])
    today = date.today()
    inv = c.db.execute(select(m.Invoice).where(m.Invoice.tenant_id == c.tid, m.Invoice.status == "Issued")).scalars().all()
    paid = _paid(c, {i.id for i in inv})
    invoiced, collected, owed = {}, {}, {}
    for i in inv:
        if lo <= i.issue_date <= hi:
            invoiced[i.project_id] = invoiced.get(i.project_id, 0) + i.total_minor
        owed[i.project_id] = owed.get(i.project_id, 0) + (i.total_minor - paid.get(i.id, 0))
    for p in c.db.execute(select(m.InvoicePayment).where(m.InvoicePayment.tenant_id == c.tid, m.InvoicePayment.paid_on >= lo, m.InvoicePayment.paid_on <= hi)).scalars():
        pid = c.db.get(m.Invoice, p.invoice_id).project_id
        collected[pid] = collected.get(pid, 0) + p.amount_minor
    rows = []
    for pid, p in d["projects"].items():
        v = r["proj"][pid]
        if not (v["people"] or direct.get(pid) or alloc.get(pid) or invoiced.get(pid) or collected.get(pid) or owed.get(pid)):
            continue
        contrib = v["value"] - v["cost"] - direct.get(pid, 0) - alloc.get(pid, 0)
        rows.append({"project_id": pid, "code": p["code"], "name": p["name"], "tags": [t["name"] for t in p["tags"]], "hours": v["hours"],
                     "value_minor": v["value"], "salary_cost_minor": v["cost"], "direct_minor": direct.get(pid, 0), "shared_minor": alloc.get(pid, 0),
                     "contribution_minor": contrib, "margin_pct": None if v["value"] == 0 else round(contrib * 100 / v["value"], 1),
                     "invoiced_minor": invoiced.get(pid, 0), "collected_minor": collected.get(pid, 0), "outstanding_minor": owed.get(pid, 0)})
    rows.sort(key=lambda x: x["contribution_minor"])
    t = k.org_totals(d, r)
    sums = {key: sum(x[key] for x in rows) for key in ("value_minor", "salary_cost_minor", "direct_minor", "shared_minor", "contribution_minor", "invoiced_minor", "collected_minor", "outstanding_minor")}
    return {"month": mo.strftime("%Y-%m"), "rows": rows, "totals": {**sums, "bench_minor": t["bench_cost"], "shared_unallocated_minor": lost,
            "after_bench_minor": sums["contribution_minor"] - t["bench_cost"] - lost},
            "reconciles": sums["shared_minor"] + lost == shared_total,
            "note": "Standard value is planned effort at the hourly rate, not revenue. Invoiced and collected come from invoices and payments in the month and are shown beside it, never mixed with it. Contribution = standard value − salary cost − direct expenses − shared overhead."}


# ---------------- planned vs actual ----------------
def elapsed_fraction(mo: date) -> float:
    today = date.today()
    if today < mo:
        return 0.0
    if today > k.month_end(mo):
        return 1.0
    return today.day / monthrange(mo.year, mo.month)[1]


@router.get("/planned-actual")
def planned_actual(month: str | None = None, c: Ctx = Depends(ctx)):
    mo = _month(month)
    d = k.load(c, mo)
    emp_ids, proj_ids, partial = visible(c, "costing.effort", d)
    money = c.can("costing.cost") and not partial
    lo, hi = month_bounds(mo)
    r = k.compute(d, emp_ids, proj_ids)
    frac = elapsed_fraction(mo)
    te = c.db.execute(select(m.TimeEntry).where(m.TimeEntry.tenant_id == c.tid, m.TimeEntry.work_date >= lo, m.TimeEntry.work_date <= hi,
                                                m.TimeEntry.status.in_(("Approved", "Submitted")))).scalars().all()
    appr, pend, appr_cost = {}, {}, {}
    ep_a = {}
    for t in te:
        if t.user_id not in emp_ids or t.project_id not in proj_ids:
            continue
        key = appr if t.status == "Approved" else pend
        key[t.project_id] = key.get(t.project_id, 0) + t.hours
        ep_a.setdefault(t.user_id, [0, 0])[0 if t.status == "Approved" else 1] += t.hours
        if t.status == "Approved":
            e = d["emps"].get(t.user_id)
            if e and e["salary"] is not None:
                appr_cost[t.project_id] = appr_cost.get(t.project_id, 0) + e["salary"] * t.hours / e["hours"]

    def flag(planned, actual):
        to_date = planned * frac
        if planned == 0 and actual > 0:
            return "Hours without allocation"
        if planned and actual > to_date * 1.1 and actual > 0:
            return "Over plan"
        if planned and frac >= 0.5 and actual < to_date * 0.5:
            return "Behind on approved hours"
        return None

    projects = []
    for pid in d["projects"]:
        if pid not in proj_ids:
            continue
        v = r["proj"][pid]
        a, pe = appr.get(pid, 0), pend.get(pid, 0)
        if not (v["hours"] or a or pe):
            continue
        row = {"project_id": pid, "code": d["projects"][pid]["code"], "name": d["projects"][pid]["name"], "planned_hours": round(v["hours"], 1),
               "planned_to_date": round(v["hours"] * frac, 1), "approved_hours": round(a, 1), "pending_hours": round(pe, 1),
               "variance_hours": round(a - v["hours"] * frac, 1), "variance_pct": None if v["hours"] * frac == 0 else round((a - v["hours"] * frac) * 100 / (v["hours"] * frac), 1),
               "flag": flag(v["hours"], a)}
        if money:
            ac = int(round(appr_cost.get(pid, 0)))
            row.update(planned_cost_minor=v["cost"], actual_cost_minor=ac, cost_variance_minor=ac - int(round(v["cost"] * frac)))
        projects.append(row)
    people = []
    for uid in sorted(emp_ids, key=lambda i: d["emps"][i]["name"]):
        pl = r["emp"][uid]["hours"]
        a, pe = ep_a.get(uid, [0, 0])
        if pl or a or pe:
            people.append({"user_id": uid, "name": d["emps"][uid]["name"], "planned_hours": round(pl, 1), "planned_to_date": round(pl * frac, 1),
                           "approved_hours": round(a, 1), "pending_hours": round(pe, 1), "flag": flag(pl, a)})
    tot = lambda key: round(sum(x[key] for x in projects), 1)
    out = {"month": mo.strftime("%Y-%m"), "elapsed_pct": round(frac * 100), "money": money, "partial": partial, "projects": projects, "people": people,
           "totals": {"planned_hours": tot("planned_hours"), "planned_to_date": tot("planned_to_date"), "approved_hours": tot("approved_hours"), "pending_hours": tot("pending_hours")},
           "note": "Planned is the monthly allocation. Actual counts only approved timesheet hours; submitted hours still waiting for approval are shown apart. Planned to date prorates the month so far."}
    if money:
        out["totals"].update(planned_cost_minor=sum(x["planned_cost_minor"] for x in projects), actual_cost_minor=sum(x["actual_cost_minor"] for x in projects))
    return out


# ---------------- employee performance matrix ----------------
def _perf_users(c: Ctx, d: dict) -> set:
    s = c.require("perf.view")
    everyone = set(d["emps"])
    if s == "all":
        return everyone
    if s == "team":
        return c.team_user_ids() & everyone
    if s == "own":
        return {c.user.id}
    pids = assigned_project_ids(c)
    mates = set(c.db.execute(select(m.ProjectMember.user_id).where(m.ProjectMember.project_id.in_(pids or {-1}))).scalars())
    return (mates | {c.user.id}) & everyone


def _perf_metrics(c: Ctx, d: dict, r: dict, mo: date, uids: set) -> list:
    lo, hi = month_bounds(mo)
    today = date.today()
    tasks = c.db.execute(select(m.Task).where(m.Task.tenant_id == c.tid, m.Task.assignee_id.in_(uids or {-1}))).scalars().all()
    appr_by_task = {}
    te_all = c.db.execute(select(m.TimeEntry).where(m.TimeEntry.tenant_id == c.tid, m.TimeEntry.user_id.in_(uids or {-1}))).scalars().all()
    appr_m, rej_m, all_m = {}, {}, {}
    for t in te_all:
        if t.status == "Approved" and t.task_id:
            appr_by_task[t.task_id] = appr_by_task.get(t.task_id, 0) + t.hours
        if lo <= t.work_date <= hi:
            if t.status == "Approved":
                appr_m[t.user_id] = appr_m.get(t.user_id, 0) + t.hours
            if t.status == "Rejected":
                rej_m[t.user_id] = rej_m.get(t.user_id, 0) + 1
            if t.status in ("Approved", "Rejected"):
                all_m[t.user_id] = all_m.get(t.user_id, 0) + 1
    hand = c.db.execute(select(m.Handover).where(m.Handover.tenant_id == c.tid)).scalars().all()
    revs = c.db.execute(select(m.PerfReview).where(m.PerfReview.tenant_id == c.tid, m.PerfReview.user_id.in_(uids or {-1}))).scalars().all()
    out = []
    for uid in sorted(uids, key=lambda i: d["emps"][i]["name"]):
        mine = [t for t in tasks if t.assignee_id == uid]
        done = [t for t in mine if t.status == "Done"]
        est = [t for t in done if t.est_hours > 0 and t.id in appr_by_task]
        est_h, act_h = sum(t.est_hours for t in est), sum(appr_by_task[t.id] for t in est)
        got = [h for h in hand if h.to_user_id == uid]
        gave = [h for h in hand if h.from_user_id == uid]
        my_revs = [x for x in revs if x.user_id == uid]
        planned = r["emp"][uid]["hours"] if uid in r["emp"] else 0
        e = d["emps"][uid]
        out.append({"user_id": uid, "name": e["name"], "title": e["title"], "team": e["team"],
                    "tasks": {"assigned": len(mine), "done": len(done), "open": len([t for t in mine if t.status != "Done"]),
                              "blocked": len([t for t in mine if t.status == "Blocked"]),
                              "overdue": len([t for t in mine if t.status != "Done" and t.due_date and t.due_date < today]),
                              "completion_pct": None if not mine else round(len(done) * 100 / len(mine))},
                    "estimates": {"tasks_compared": len(est), "estimated_hours": round(est_h, 1), "approved_hours": round(act_h, 1),
                                  "accuracy_pct": None if est_h == 0 else round(act_h * 100 / est_h)},
                    "hours": {"planned": round(planned, 1), "approved": round(appr_m.get(uid, 0), 1),
                              "utilization_pct": None if planned == 0 else round(appr_m.get(uid, 0) * 100 / planned)},
                    "handover": {"received": len(got), "acknowledged": len([h for h in got if h.status == "Acknowledged"]), "given": len(gave)},
                    "timesheets": {"decided": all_m.get(uid, 0), "rejected": rej_m.get(uid, 0)},
                    "reviews": {"count": len(my_revs), "unacknowledged": len([x for x in my_revs if not x.ack_at])}})
    return out


PERF_DEFINITIONS = [
    "Completion = done tasks ÷ tasks assigned to the person. Overdue = open tasks past their due date.",
    "Estimate accuracy = approved hours ÷ estimated hours on done tasks that have both (100% means the estimate was right; it is not a grade).",
    "Utilization = approved timesheet hours this month ÷ planned hours from allocation.",
    "Handover = handovers received and acknowledged, and handovers given.",
    "Timesheet rejections = approved or rejected entries this month, and how many were sent back.",
    "No single score or ranking is calculated. Hours alone are never used as a performance measure; managers add evidence-based comments.",
]


@router.get("/performance")
def performance(month: str | None = None, c: Ctx = Depends(ctx)):
    mo = _month(month)
    d = k.load(c, mo)
    uids = _perf_users(c, d)
    r = k.compute(d)
    return {"month": mo.strftime("%Y-%m"), "scope": c.scope("perf.view"), "can_review": c.can("perf.manage"), "me": c.user.id, "dimensions": DIMENSIONS,
            "definitions": PERF_DEFINITIONS, "rows": _perf_metrics(c, d, r, mo, uids)}


@router.get("/performance/{uid}")
def performance_detail(uid: int, month: str | None = None, c: Ctx = Depends(ctx)):
    mo = _month(month)
    d = k.load(c, mo)
    uids = _perf_users(c, d)
    if uid not in uids:
        raise err(404, "NOT_FOUND", "Employee not found.")
    r = k.compute(d)
    row = _perf_metrics(c, d, r, mo, {uid})[0]
    names = {u.id: u.name for u in c.db.execute(select(m.User)).scalars()}
    revs = c.db.execute(select(m.PerfReview).where(m.PerfReview.tenant_id == c.tid, m.PerfReview.user_id == uid).order_by(m.PerfReview.created_at.desc())).scalars().all()
    lo, hi = month_bounds(mo)
    ap = {}
    for t in c.db.execute(select(m.TimeEntry).where(m.TimeEntry.tenant_id == c.tid, m.TimeEntry.user_id == uid, m.TimeEntry.status == "Approved",
                                                    m.TimeEntry.work_date >= lo, m.TimeEntry.work_date <= hi)).scalars():
        ap[t.project_id] = ap.get(t.project_id, 0) + t.hours
    projs = []
    for pid in set(ap) | {p for (u, p) in r["cells"] if u == uid}:
        cell = r["cells"].get((uid, pid))
        projs.append({"project": f"{d['projects'][pid]['code']} {d['projects'][pid]['name']}", "planned_hours": round(cell["hours"], 1) if cell else 0, "approved_hours": round(ap.get(pid, 0), 1)})
    return {**row, "projects": sorted(projs, key=lambda x: x["project"]), "can_review": c.can("perf.manage") and uid != c.user.id,
            "reviews": [{"id": x.id, "month": x.month.strftime("%Y-%m"), "dimension": x.dimension, "comment": x.comment, "by": names.get(x.reviewer_id),
                         "at": x.created_at.date().isoformat(), "acknowledged": bool(x.ack_at), "ack_note": x.ack_note, "mine": x.user_id == c.user.id} for x in revs]}


class ReviewIn(BaseModel):
    user_id: int
    month: str | None = None
    dimension: str = "General"
    comment: str


@router.post("/performance/reviews")
def add_review(b: ReviewIn, c: Ctx = Depends(ctx)):
    c.require("perf.manage")
    mo = _month(b.month)
    d = k.load(c, mo)
    if b.user_id == c.user.id:
        raise err(422, "VALIDATION", "You cannot review yourself.")
    if b.user_id not in _perf_users(c, d):
        raise err(404, "NOT_FOUND", "Employee not found.")
    text = b.comment.strip()
    if b.dimension not in DIMENSIONS or not 10 <= len(text) <= 1000:
        raise err(422, "VALIDATION", "Choose a dimension and write 10 to 1000 characters of evidence-based comment.")
    x = m.PerfReview(tenant_id=c.tid, user_id=b.user_id, reviewer_id=c.user.id, month=mo, dimension=b.dimension, comment=text)
    c.db.add(x)
    c.db.flush()
    c.db.add(m.Notification(tenant_id=c.tid, user_id=b.user_id, text=f"{c.user.name} added a review comment ({b.dimension}). Please read and acknowledge it.", link="/performance"))
    audit(c.db, c.tid, c.user.id, "perf.review", "user", b.user_id, dimension=b.dimension)
    c.db.commit()
    return {"id": x.id}


class AckIn(BaseModel):
    note: str = ""


@router.post("/performance/reviews/{rid}/ack")
def ack_review(rid: int, b: AckIn, c: Ctx = Depends(ctx)):
    c.require("perf.view")
    x = c.db.get(m.PerfReview, rid)
    if not x or x.tenant_id != c.tid or x.user_id != c.user.id:
        raise err(404, "NOT_FOUND", "Review not found.")
    if x.ack_at:
        raise err(409, "BAD_STATE", "Already acknowledged.")
    x.ack_at, x.ack_note = datetime.now(timezone.utc), b.note.strip()[:300]
    audit(c.db, c.tid, c.user.id, "perf.ack", "review", x.id)
    c.db.commit()
    return {"ok": True}
