"""Decision views for the CEO, Product Owner and Project Manager, built from department, industry tag and project category.
One endpoint. Scope and masking follow the costing rules: money (value, salary cost, margin) is returned only to holders of
`costing.cost` with organization-wide effort access; everyone else gets hours, people and staffing signals only."""
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select

from .. import costing as k, models as m
from ..core import Ctx, ctx
from .costing import OPEN_STATUSES, _month, visible

router = APIRouter(prefix="/api", tags=["insights"])
DEFAULT_LENS = {"owner": "ceo", "finance": "ceo", "ops": "ceo", "po": "po", "pm": "pm", "tl": "pm"}
THIN_MARGIN_PCT = 30
KEY_PERSON_SHARE = 0.7


def _mix(d: dict) -> dict:
    return {a: round(b, 2) for a, b in sorted(d.items(), key=lambda kv: -kv[1])}


@router.get("/insights")
def insights(month: str | None = None, c: Ctx = Depends(ctx)):
    c.require("costing.effort")
    mo = _month(month)
    d = k.load(c, mo)
    emp_ids, proj_ids, partial = visible(c, "costing.effort", d)
    r = k.compute(d, emp_ids, proj_ids)
    money = c.can("costing.cost") and not partial
    dname_by_id = {x.id: x for x in c.db.execute(select(m.Department).where(m.Department.tenant_id == c.tid)).scalars()}

    def dept_of(uid):
        x = dname_by_id.get(d["emps"][uid]["dept_id"])
        return x.name if x else "No department"

    trows = {t.project_id: t.amount_minor for t in c.db.execute(select(m.RevenueTarget).where(
        m.RevenueTarget.tenant_id == c.tid, m.RevenueTarget.month == mo, m.RevenueTarget.level == "project")).scalars()}
    cat_by_pid = {p.id: p.category for p in c.db.execute(select(m.Project).where(m.Project.tenant_id == c.tid)).scalars()}

    # ---- departments
    depts = {}
    for uid in emp_ids:
        e, x = d["emps"][uid], r["emp"][uid]
        row = depts.setdefault(dept_of(uid), {"department": dept_of(uid), "people": 0, "capacity_h": 0, "hours": 0.0, "bench_people": 0,
                                              "cost": 0, "bench_cost": 0, "value": 0})
        row["people"] += 1
        row["capacity_h"] += e["hours"]
        row["hours"] += x["hours"]
        row["bench_people"] += 1 if x["pct"] == 0 else 0
        if money:
            row["cost"] += x["cost"] or 0
            row["bench_cost"] += x["bench_cost"] or 0
    heads = {x.name: d["emps"][x.head_user_id]["name"] for x in dname_by_id.values() if x.head_user_id in d["emps"]}

    # ---- per project, department mix and tag / category rollups
    mix_h, mix_cost, mix_val = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    top = defaultdict(lambda: ("", 0.0))
    for (uid, pid), cell in r["cells"].items():
        dn = dept_of(uid)
        mix_h[pid][dn] += cell["hours"]
        val = k.half_up(cell["pct"] * d["emps"][uid]["hours"] * d["projects"][pid]["rate"], 100)
        mix_val[pid][dn] += val
        mix_cost[pid][dn] += cell["cost"] or 0
        depts[dn]["value"] += val if dn in depts else 0
        if cell["hours"] > top[pid][1]:
            top[pid] = (d["emps"][uid]["name"], cell["hours"])
    projects, signals = [], []
    for pid in sorted(proj_ids, key=lambda i: d["projects"][i]["code"]):
        p, x = d["projects"][pid], r["proj"][pid]
        if p["status"] not in OPEN_STATUSES and x["people"] == 0:
            continue
        row = {"id": pid, "code": p["code"], "name": p["name"], "category": cat_by_pid.get(pid, ""), "tags": p["tags"], "status": p["status"],
               "people": x["people"], "hours": round(x["hours"], 2), "mix": _mix(mix_h[pid]), "flags": []}
        share = top[pid][1] / x["hours"] if x["hours"] else 0
        if x["people"] == 0:
            row["flags"].append("No one allocated")
        elif x["people"] == 1 or share >= KEY_PERSON_SHARE:
            row["flags"].append("Depends on one person")
            row["key_person"] = top[pid][0]
        if money:
            mg = x["value"] - x["cost"]
            row.update(value_minor=x["value"], cost_minor=x["cost"], margin_minor=mg, margin_pct=round(mg * 100 / x["value"], 1) if x["value"] else None,
                       target_minor=trows.get(pid), mix_cost={a: b for a, b in mix_cost[pid].items()})
            if x["people"] and x["value"] and mg * 100 / x["value"] < THIN_MARGIN_PCT:
                row["flags"].append("Thin margin")
            if trows.get(pid) and x["value"] < trows[pid]:
                row["flags"].append("Below target")
        projects.append(row)

    def rollup(key_of):
        out = {}
        for row in projects:
            for key in key_of(row):
                g = out.setdefault(key, {"name": key, "projects": 0, "hours": 0.0, "value": 0, "cost": 0, "mix": defaultdict(float), "mix_cost": defaultdict(int)})
                g["projects"] += 1
                g["hours"] += row["hours"]
                for a, b in row["mix"].items():
                    g["mix"][a] += b
                if money:
                    g["value"] += row["value_minor"]
                    g["cost"] += row["cost_minor"]
                    for a, b in row["mix_cost"].items():
                        g["mix_cost"][a] += b
        res = []
        for g in out.values():
            item = {"name": g["name"], "projects": g["projects"], "hours": round(g["hours"], 2), "mix": _mix(g["mix"])}
            if money:
                item.update(value_minor=g["value"], cost_minor=g["cost"], margin_minor=g["value"] - g["cost"],
                            margin_pct=round((g["value"] - g["cost"]) * 100 / g["value"], 1) if g["value"] else None, mix_cost=dict(g["mix_cost"]))
            res.append(item)
        return sorted(res, key=lambda i: -i["hours"])

    by_tag = rollup(lambda row: [t["name"] for t in row["tags"][:1]] or ["Untagged"])  # primary tag: additive, sums to the total
    by_cat = rollup(lambda row: [row["category"] or "Uncategorised"])
    tag_targets = {}
    if money:
        for t in c.db.execute(select(m.RevenueTarget, m.Tag).join(m.Tag, m.Tag.id == m.RevenueTarget.tag_id).where(
                m.RevenueTarget.tenant_id == c.tid, m.RevenueTarget.month == mo, m.RevenueTarget.level == "tag")).all():
            tag_targets[t[1].name] = t[0].amount_minor
        for g in by_tag:
            g["target_minor"] = tag_targets.get(g["name"])
    dept_list = []
    for row in sorted(depts.values(), key=lambda i: -i["capacity_h"]):
        item = {"department": row["department"], "head": heads.get(row["department"]), "people": row["people"], "capacity_h": row["capacity_h"], "hours": round(row["hours"], 2),
                "utilization_pct": round(row["hours"] * 100 / row["capacity_h"], 1) if row["capacity_h"] else 0, "bench_people": row["bench_people"]}
        if money:
            item.update(cost_minor=row["cost"], bench_cost_minor=row["bench_cost"], value_minor=row["value"], margin_minor=row["value"] - row["cost"])
        dept_list.append(item)

    # ---- department x industry (primary tag) heat map
    heat = {}
    for row in projects:
        tg = row["tags"][0]["name"] if row["tags"] else "Untagged"
        for a, b in row["mix"].items():
            cell = heat.setdefault((a, tg), {"department": a, "tag": tg, "hours": 0.0, **({"cost_minor": 0} if money else {})})
            cell["hours"] += b
            if money:
                cell["cost_minor"] += row["mix_cost"].get(a, 0)
    heat_list = [{**v, "hours": round(v["hours"], 2)} for v in heat.values() if v["hours"] > 0]

    # ---- people on the bench and headline numbers
    bench = [{"id": u, "name": d["emps"][u]["name"], "department": dept_of(u), "free_pct": 100 - r["emp"][u]["pct"], "free_h": round(r["emp"][u]["bench_hours"], 2),
              **({"bench_cost_minor": r["emp"][u]["bench_cost"]} if money else {})}
             for u in emp_ids if r["emp"][u]["pct"] < 100 and not partial]
    bench.sort(key=lambda x: -x["free_pct"])
    capacity = sum(d["emps"][u]["hours"] for u in emp_ids)
    hours = sum(p["hours"] for p in r["proj"].values())
    kpi = {"people": len(emp_ids), "projects": len(projects), "hours": round(hours, 2), "capacity_h": capacity,
           "utilization_pct": round(hours * 100 / capacity, 1) if capacity else 0, "bench_people": sum(1 for b in bench if b["free_pct"] == 100)}
    org_target = None
    if money:
        t = k.org_totals(d, r)
        org_target = c.db.execute(select(m.RevenueTarget.amount_minor).where(m.RevenueTarget.tenant_id == c.tid, m.RevenueTarget.month == mo, m.RevenueTarget.level == "org")).scalar()
        kpi.update(value_minor=t["value"], cost_minor=t["cost"], bench_cost_minor=t["bench_cost"], margin_minor=t["margin"], salary_pool_minor=t["salary_pool"],
                   reconciles=t["reconciles"], org_target_minor=org_target)

    # ---- decision signals: what to look at, for whom
    def sig(lens, sev, title, detail):
        signals.append({"lens": lens, "severity": sev, "title": title, "detail": detail})

    for row in projects:
        if "No one allocated" in row["flags"] and row["status"] in OPEN_STATUSES:
            sig("pm", "high", f"{row['name']} has nobody allocated", "Open project with no allocation this month. Staff it from the bench list or confirm it is paused.")
            sig("po", "high", f"{row['name']} has nobody allocated", "Open project with no allocation this month.")
        if "Depends on one person" in row["flags"]:
            sig("pm", "med", f"{row['name']} depends on {row.get('key_person')}", "Most of the hours sit with one person. Add a second contributor or plan a handover.")
    free = [b for b in bench if b["free_pct"] == 100]
    if free and not partial:
        names = ", ".join(b["name"] for b in free[:4])
        sig("pm", "med", f"{len(free)} people are completely free", f"{names}: candidates for staffing gaps.")
        sig("ceo", "med", f"{len(free)} people have no allocation", f"{names}." + (f" Their salary this month is carried as bench cost." if money else ""))
    for dep in dept_list:
        if dep["utilization_pct"] >= 100 and dep["people"] > 1 and not partial:
            sig("ceo", "med", f"{dep['department']} is fully booked", "No spare capacity: new work needs hiring, re-planning or a lower-priority project to pause.")
        if dep["people"] > 1 and dep["utilization_pct"] < 60 and not partial:
            sig("ceo", "med", f"{dep['department']} is under-used ({dep['utilization_pct']}%)", "Spare capacity could take more projects or be lent to another department.")
    if money:
        for row in projects:
            if row["margin_pct"] is not None and row["people"]:
                if row["margin_minor"] < 0:
                    sig("ceo", "high", f"{row['name']} costs more than its value", f"Margin {row['margin_pct']}% on standard value.")
                elif row["margin_pct"] < THIN_MARGIN_PCT:
                    sig("ceo", "med", f"{row['name']} has a thin margin ({row['margin_pct']}%)", "Review who is allocated: senior salary on low-value work drives this.")
            if row.get("target_minor") and row["value_minor"] < row["target_minor"]:
                gap = row["target_minor"] - row["value_minor"]
                sig("ceo", "med" if row["value_minor"] else "high", f"{row['name']} is below its target", f"Planned value is short by Rs {gap // 100:,}.")
                sig("po", "med", f"{row['name']} is below its target", f"Planned value is short by Rs {gap // 100:,}. Add effort or revisit the target.")
        if org_target and kpi["value_minor"] < org_target:
            sig("ceo", "high", "Organization target is not covered", f"Planned value is short of the target by Rs {(org_target - kpi['value_minor']) // 100:,}.")
        ranked = [g for g in by_tag if g["margin_pct"] is not None]
        if len(ranked) > 1:
            lo, hi = min(ranked, key=lambda g: g["margin_pct"]), max(ranked, key=lambda g: g["margin_pct"])
            sig("ceo", "info", f"Best industry: {hi['name']} ({hi['margin_pct']}%), weakest: {lo['name']} ({lo['margin_pct']}%)", "Margin on standard value, each project counted once under its first tag.")
    for g in by_tag:
        gap = [x for x in projects if x["tags"] and x["tags"][0]["name"] == g["name"] and "No one allocated" in x["flags"]]
        if gap:
            sig("po", "med", f"{g['name']}: {len(gap)} project(s) without a team", ", ".join(x["name"] for x in gap))
    core_depts = [n for n in ("Software Development", "Marketing", "Sales") if any(x.name == n for x in dname_by_id.values())]
    for row in projects:
        if row["category"] == "Own Product" and row["people"]:
            gaps = [n for n in core_depts if n not in row["mix"]]
            if gaps:
                sig("po", "med", f"{row['name']} has no {' or '.join(gaps)} effort", "An own product needs build, marketing and sales effort to reach customers. Check the mix before the next planning.")
    order = {"high": 0, "med": 1, "info": 2}
    signals.sort(key=lambda s: order[s["severity"]])
    return {"month": mo.isoformat()[:7], "partial": partial, "money": money, "default_lens": DEFAULT_LENS.get(c.role.key, "pm"), "kpi": kpi,
            "departments": dept_list, "tags": by_tag, "categories": by_cat, "projects": projects, "heat": heat_list, "bench": bench, "signals": signals,
            "note": "Value is hours x standard rate, not invoiced revenue. Industries count each project once under its first tag, so they add up to the total."}
