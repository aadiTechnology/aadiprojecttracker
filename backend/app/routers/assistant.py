"""Sprint 5: advisory management assistant and CSV exports.

The assistant answers management questions from the same screens' data, called as the signed-in user, so permissions, scope, tenant
isolation and money masking apply exactly as on the screens. It is RULE-BASED: it recognises the question, runs the permitted reports and
writes the answer from their numbers. No language model is called, nothing leaves the server, and cost is zero. Every answer lists its
evidence (which screen to open) and is advisory only: it never posts, approves, rates or sends anything (BR-014).
A pluggable provider slot exists (ASSISTANT_PROVIDER, default "rules") for a future model; it is deliberately not wired."""
import csv
import io
import re
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select

from .. import models as m
from ..core import Ctx, audit, ctx, err
from . import finance, insights as ins
from .work import assigned_project_ids

router = APIRouter(prefix="/api", tags=["assistant"])
DAILY_LIMIT = 100
INTENTS = [  # (intent, keywords)
    ("risk", ("risk", "blocked", "late", "delay", "worry", "attention", "act on", "what should")),
    ("margin", ("margin", "profit", "unprofitable", "loss", "thin", "losing money", "worst project", "best project")),
    ("bench", ("bench", "free", "capacity", "available", "idle", "who can", "spare")),
    ("receivables", ("overdue", "receivable", "outstanding", "unpaid", "invoice", "collect", "owe")),
    ("hours", ("over plan", "variance", "behind", "estimate", "actual", "timesheet", "planned", "approved hours")),
    ("expenses", ("expense", "spend", "spent", "shared cost", "overhead", "vendor", "subscription")),
    ("mywork", ("my task", "my work", "assigned to me", "my timesheet", "what do i")),
    ("summary", ("summary", "summarize", "overview", "how are we", "status", "how is", "snapshot")),
]
EXAMPLES = ["Give me a summary of this month", "Which projects have a thin margin?", "Who is free to take new work?", "What invoices are overdue?",
            "Which projects are over plan on hours?", "What did we spend this month?", "What should I act on?", "What are my open tasks?"]


def rs(minor) -> str:
    return f"Rs {round(minor / 100):,}"


def _try(c: Ctx, fn, *a):
    """Run a report as the caller. Returns None when the caller's role is not allowed, so the answer says so instead of leaking."""
    try:
        return fn(*a, c=c)
    except HTTPException as e:
        if e.status_code in (403, 404):
            return None
        raise


def classify(q: str) -> str:
    t = q.lower()
    best, score = "unknown", 0
    for name, words in INTENTS:
        s = sum(1 for w in words if w in t)
        if s > score:
            best, score = name, s
    return best


class Ask(BaseModel):
    question: str


def _ans(lines, evidence, follow=None, caveats=None):
    return {"answer": lines, "evidence": evidence, "follow_ups": follow or [], "caveats": caveats or []}


def a_summary(c: Ctx):
    j = _try(c, ins.insights, None)
    if j is None:
        return _ans(["Your role does not include the organization-wide effort view, so I cannot summarize the portfolio."], [], ["What are my open tasks?"])
    k = j["kpi"]
    lines = [f"{k['projects']} open projects use {k['hours']} of {k['capacity_h']} planned hours ({k['utilization_pct']}% utilization), with {k['people']} people in view."]
    if j["money"]:
        lines.append(f"Planned value is {rs(k['value_minor'])} against salary cost {rs(k['cost_minor'])}, a margin of {rs(k['margin_minor'])}. Bench salary is {rs(k['bench_cost_minor'])}.")
        if k.get("org_target_minor"):
            lines.append(f"The organization target is {rs(k['org_target_minor'])}; planned value is {'above' if k['value_minor'] >= k['org_target_minor'] else 'below'} it.")
    high = [s for s in j["signals"] if s["severity"] == "high"]
    lines.append(f"{len(high)} high-priority signal(s) need a decision." if high else "There are no high-priority signals.")
    return _ans(lines, [{"label": "Decision Insights", "path": "/insights"}], ["What should I act on?", "Which projects have a thin margin?"],
                [] if j["money"] else ["Money figures are hidden for your role."])


def a_margin(c: Ctx):
    j = _try(c, ins.insights, None)
    if j is None or not j["money"]:
        return _ans(["Margins need salary cost, which your role cannot see. I can show hours and staffing instead."], [], ["Who is free to take new work?"])
    rows = sorted([p for p in j["projects"] if p.get("margin_pct") is not None and p["people"]], key=lambda p: p["margin_pct"])
    if not rows:
        return _ans(["No project has both planned value and an allocation this month."], [{"label": "Decision Insights", "path": "/insights"}])
    thin = [p for p in rows if "Thin margin" in p["flags"] or p["margin_minor"] < 0]
    lines = [f"{len(thin)} of {len(rows)} projects are below the {ins.THIN_MARGIN_PCT}% margin line." if thin else f"No project is below the {ins.THIN_MARGIN_PCT}% margin line."]
    for p in rows[:4]:
        lines.append(f"{p['name']}: margin {p['margin_pct']}% ({rs(p['margin_minor'])} on value {rs(p['value_minor'])}).")
    lines.append(f"Strongest: {rows[-1]['name']} at {rows[-1]['margin_pct']}%.")
    return _ans(lines, [{"label": "Decision Insights, Projects by margin", "path": "/insights"}, {"label": "Project Profitability", "path": "/profitability"}],
                ["What should I act on?"], ["Margin is on standard value (hours x rate), not invoiced revenue."])


def a_bench(c: Ctx):
    j = _try(c, ins.insights, None)
    if j is None:
        return _ans(["Your role does not include capacity data."], [])
    free = sorted(j["bench"], key=lambda b: -b["free_pct"])
    free = [b for b in free if b["free_pct"] > 0]
    if not free:
        return _ans(["Everyone in your view is fully allocated this month."], [{"label": "Employee Allocation", "path": "/allocation"}])
    lines = [f"{len(free)} people have free capacity this month."]
    for b in free[:6]:
        lines.append(f"{b['name']} ({b['department']}): {b['free_pct']}% free, about {b['free_h']} hours.")
    return _ans(lines, [{"label": "Decision Insights, free capacity", "path": "/insights"}, {"label": "Employee Allocation", "path": "/allocation"}], ["Which projects have nobody allocated?"])


def a_receivables(c: Ctx):
    j = _try(c, finance.invoices)
    if j is None:
        return _ans(["Invoices are visible only to finance roles."], [])
    s = j["summary"]
    lines = [f"Invoiced {rs(s['invoiced_minor'])}, collected {rs(s['collected_minor'])}, outstanding {rs(s['outstanding_minor'])}."]
    od = [r for r in j["rows"] if r["status"] == "Overdue"]
    lines.append(f"{len(od)} invoice(s) are overdue, {rs(s['overdue_minor'])} in total." if od else "No invoice is overdue.")
    for r in od[:4]:
        lines.append(f"{r['number']} ({r['customer']}): {rs(r['outstanding_minor'])}, {r['days_overdue']} days late.")
    if s["drafts"] or s["awaiting_issue"]:
        lines.append(f"{s['drafts']} draft(s) wait for approval and {s['awaiting_issue']} approved invoice(s) wait to be issued.")
    return _ans(lines, [{"label": "Invoices", "path": "/invoices"}], ["What did we spend this month?"], ["Invoiced and collected are not recognized revenue."])


def a_hours(c: Ctx):
    j = _try(c, finance.planned_actual, None)
    if j is None:
        return _ans(["Your role does not include the planned-versus-actual view."], [])
    t = j["totals"]
    lines = [f"{t['approved_hours']} approved hours against {t['planned_to_date']} planned to date ({j['elapsed_pct']}% of the month); {t['pending_hours']} more hours wait for approval."]
    flagged = [p for p in j["projects"] if p["flag"]]
    for p in flagged[:5]:
        lines.append(f"{p['name']}: {p['flag'].lower()} ({p['approved_hours']} h approved, {p['planned_to_date']} h planned to date).")
    if not flagged:
        lines.append("No project is outside its planned range.")
    return _ans(lines, [{"label": "Planned vs Actual", "path": "/planned-actual"}], ["Which projects have a thin margin?"],
                ["Early in the month the comparison is small and noisy."] if j["elapsed_pct"] < 30 else [])


def a_expenses(c: Ctx):
    j = _try(c, finance.expenses, None)
    if j is None:
        return _ans(["Expenses are visible only to finance and operations roles."], [])
    t = j["totals"]
    lines = [f"{rs(t['all_minor'])} spent this month: {rs(t['direct_minor'])} direct to projects and {rs(t['shared_minor'])} shared. {rs(t['unpaid_minor'])} is not paid yet."]
    for cat in j["by_category"][:3]:
        lines.append(f"{cat['category']}: {rs(cat['amount_minor'])}.")
    return _ans(lines, [{"label": "Expenses & Cost", "path": "/expenses"}], ["What invoices are overdue?"])


def a_risk(c: Ctx):
    lines, ev = [], []
    j = _try(c, ins.insights, None)
    if j:
        top = [s for s in j["signals"] if s["severity"] in ("high", "med")][:5]
        lines += [f"{s['title']}. {s['detail']}" for s in top]
        ev.append({"label": "Decision Insights", "path": "/insights"})
    inv = _try(c, finance.invoices)
    if inv and inv["summary"]["overdue_count"]:
        lines.append(f"{inv['summary']['overdue_count']} invoice(s) are overdue ({rs(inv['summary']['overdue_minor'])}).")
        ev.append({"label": "Invoices", "path": "/invoices"})
    if c.can("sprint.view"):
        pids = None if c.scope("sprint.view") == "all" else assigned_project_ids(c)
        q = select(func.count()).select_from(m.Task).where(m.Task.tenant_id == c.tid, m.Task.status == "Blocked")
        if pids is not None:
            q = q.where(m.Task.project_id.in_(pids or {-1}))
        blocked = c.db.execute(q).scalar()
        if blocked:
            lines.append(f"{blocked} task(s) are blocked.")
            ev.append({"label": "Sprint Planning", "path": "/sprint"})
    if not lines:
        lines = ["Nothing needs attention in the areas your role can see."]
    return _ans(lines, ev, ["Give me a summary of this month"], ["Signals are rule-based thresholds, not predictions."])


def a_mywork(c: Ctx):
    rows = c.db.execute(select(m.Task).where(m.Task.tenant_id == c.tid, m.Task.assignee_id == c.user.id, m.Task.status != "Done").order_by(m.Task.due_date)).scalars().all()
    if not rows:
        return _ans(["You have no open tasks."], [{"label": "Sprint Planning", "path": "/sprint"}])
    today = date.today()
    late = [t for t in rows if t.due_date and t.due_date < today]
    lines = [f"You have {len(rows)} open task(s), {len(late)} overdue."]
    for t in rows[:5]:
        lines.append(f"{t.title} ({t.status}{', due ' + t.due_date.isoformat() if t.due_date else ''}).")
    return _ans(lines, [{"label": "Sprint Planning", "path": "/sprint"}, {"label": "Timesheets", "path": "/timesheets"}])


HANDLERS = {"summary": a_summary, "margin": a_margin, "bench": a_bench, "receivables": a_receivables, "hours": a_hours, "expenses": a_expenses, "risk": a_risk, "mywork": a_mywork}


@router.post("/assistant")
def ask(b: Ask, c: Ctx = Depends(ctx)):
    c.require("ai.use")
    q = re.sub(r"\s+", " ", b.question).strip()
    if not 3 <= len(q) <= 300:
        raise err(422, "VALIDATION", "Ask a question of 3 to 300 characters.")
    since = datetime.now(timezone.utc) - timedelta(days=1)
    used = c.db.execute(select(func.count()).select_from(m.AIUsageLog).where(m.AIUsageLog.tenant_id == c.tid, m.AIUsageLog.user_id == c.user.id, m.AIUsageLog.at >= since)).scalar()
    if used >= DAILY_LIMIT:
        raise err(429, "LIMIT", f"Daily assistant limit of {DAILY_LIMIT} questions reached.")
    intent = classify(q)
    out = HANDLERS[intent](c) if intent in HANDLERS else _ans(["I can answer questions about the areas below. I cannot guess beyond the data your role can see."], [], EXAMPLES[:5])
    c.db.add(m.AIUsageLog(tenant_id=c.tid, user_id=c.user.id, question=q[:300], intent=intent))
    audit(c.db, c.tid, c.user.id, "assistant.ask", "assistant", intent)
    c.db.commit()
    return {"intent": intent, "question": q, **out, "advisory": True, "provider": "rules",
            "disclosure": "Rule-based answer from your permitted screens. No language model is used and no data leaves the server. Advisory only: it never changes data, approves, rates people or sends anything."}


@router.get("/assistant/info")
def info(c: Ctx = Depends(ctx)):
    c.require("ai.use")
    since = datetime.now(timezone.utc) - timedelta(days=1)
    used = c.db.execute(select(func.count()).select_from(m.AIUsageLog).where(m.AIUsageLog.tenant_id == c.tid, m.AIUsageLog.user_id == c.user.id, m.AIUsageLog.at >= since)).scalar()
    tenant = c.db.execute(select(func.count(), func.coalesce(func.sum(m.AIUsageLog.cost_minor), 0)).where(m.AIUsageLog.tenant_id == c.tid)).one()
    return {"examples": EXAMPLES, "limit": DAILY_LIMIT, "used_today": used, "provider": "rules", "tenant_questions": tenant[0] if c.has("audit.view") else None,
            "tenant_cost_minor": int(tenant[1]) if c.has("audit.view") else None}


# ---------------- CSV exports ----------------
def _safe(v):
    """Spreadsheet formula injection guard: text that starts with = + - @ is stored as text."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def _r(minor):
    return None if minor is None else round(minor / 100, 2)


def _rows(name: str, month, c: Ctx):
    if name == "invoices":
        j = finance.invoices(c=c)
        return ["Number", "Customer", "Project", "Issued", "Due", "Status", "Total", "Paid", "Outstanding"], [
            [r["number"], r["customer"], r["project"], r["issue_date"], r["due_date"], r["status"], _r(r["total_minor"]), _r(r["paid_minor"]), _r(r["outstanding_minor"])] for r in j["rows"]]
    if name == "expenses":
        j = finance.expenses(month=month, c=c)
        return ["Date", "Category", "Vendor", "Note", "Charged to", "Split", "Amount", "Status"], [
            [r["spent_on"], r["category"], r["vendor"], r["description"], r["project"] or "Shared", r["alloc_method"] or "", _r(r["amount_minor"]), r["status"]] for r in j["rows"]]
    if name == "planned-actual":
        j = finance.planned_actual(month=month, c=c)
        head = ["Code", "Project", "Planned h", "Planned to date h", "Approved h", "Waiting h", "Difference h", "Signal"] + (["Planned cost", "Actual cost"] if j["money"] else [])
        return head, [[p["code"], p["name"], p["planned_hours"], p["planned_to_date"], p["approved_hours"], p["pending_hours"], p["variance_hours"], p["flag"] or ""]
                      + ([_r(p["planned_cost_minor"]), _r(p["actual_cost_minor"])] if j["money"] else []) for p in j["projects"]]
    if name == "contribution":
        j = finance.contribution(month=month, c=c)
        return ["Code", "Project", "Planned value", "Salary cost", "Direct", "Shared", "Contribution", "Invoiced", "Collected", "Outstanding"], [
            [p["code"], p["name"], _r(p["value_minor"]), _r(p["salary_cost_minor"]), _r(p["direct_minor"]), _r(p["shared_minor"]), _r(p["contribution_minor"]),
             _r(p["invoiced_minor"]), _r(p["collected_minor"]), _r(p["outstanding_minor"])] for p in j["rows"]]
    if name == "performance":
        j = finance.performance(month=month, c=c)
        return ["Person", "Title", "Tasks assigned", "Tasks done", "Overdue", "Estimate accuracy %", "Approved h", "Planned h", "Handovers received", "Acknowledged", "Rejected entries"], [
            [r["name"], r["title"], r["tasks"]["assigned"], r["tasks"]["done"], r["tasks"]["overdue"], r["estimates"]["accuracy_pct"], r["hours"]["approved"], r["hours"]["planned"],
             r["handover"]["received"], r["handover"]["acknowledged"], r["timesheets"]["rejected"]] for r in j["rows"]]
    if name == "projects":
        j = ins.insights(month=month, c=c)
        head = ["Code", "Project", "Type", "Status", "People", "Hours", "Flags"] + (["Value", "Salary cost", "Margin", "Margin %"] if j["money"] else [])
        return head, [[p["code"], p["name"], p["category"], p["status"], p["people"], p["hours"], "; ".join(p["flags"])]
                      + ([_r(p["value_minor"]), _r(p["cost_minor"]), _r(p["margin_minor"]), p["margin_pct"]] if j["money"] else []) for p in j["projects"]]
    raise err(404, "NOT_FOUND", "Unknown report.")


EXPORTS = ("invoices", "expenses", "planned-actual", "contribution", "performance", "projects")


@router.get("/export/{name}")
def export(name: str, month: str | None = None, c: Ctx = Depends(ctx)):
    if name not in EXPORTS:
        raise err(404, "NOT_FOUND", "Unknown report.")
    head, rows = _rows(name, month, c)  # runs the same permission checks as the screen, so an export never exceeds what the user can see
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(head)
    for r in rows:
        w.writerow([_safe(v) for v in r])
    audit(c.db, c.tid, c.user.id, "export.csv", "report", name, rows=len(rows), month=month)
    c.db.commit()
    stamp = date.today().isoformat()
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}-{stamp}.csv"'})
