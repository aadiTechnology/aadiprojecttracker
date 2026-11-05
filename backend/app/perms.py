"""Capability model. A capability is "<area>.<action>" optionally scoped ":all" | ":team" | ":assigned" | ":own".
Roles are data (stored per tenant) and seeded from these defaults; code never checks role names, only capabilities.
Final role names, delegation and scopes are PROPOSED defaults awaiting customer approval (PRD section 10)."""

# module key -> (label, pillar, mvp priority)  - tenant-level feature entitlements
MODULES = {
    "core": ("Organization, customers & projects", 1, "P0"),
    "sprint": ("Sprint, tasks & handover", 1, "P0"),
    "timesheet": ("Timesheets & approval", 1, "P0"),
    "revenue": ("Revenue targets", 1, "P0"),
    "expenses": ("Expenses & cost allocation", 1, "P0"),
    "performance": ("Employee performance", 1, "P1"),
    "invoices": ("Invoices & receivables", 1, "P1"),
    "sales": ("Opportunity tracking (lightweight)", 2, "P2"),
    "ai": ("AI management assistant (advisory)", 3, "P2"),
    "costing": ("Costing, allocation & profitability", 1, "P0"),
}

# capability area -> module whose entitlement must be on
AREA_MODULE = {"org": "core", "customers": "core", "projects": "core", "sprint": "sprint", "handover": "sprint",
               "timesheet": "timesheet", "revenue": "revenue", "expenses": "expenses", "salary": "costing", "employees": "core", "departments": "core", "tags": "core", "allocation": "costing", "costing": "costing", "targets": "costing",
               "perf": "performance", "invoices": "invoices", "opps": "sales", "ai": "ai", "reports": "core", "audit": "core"}

ALL = ["all"]


def _full():
    out = []
    for a in ["customers.view", "customers.manage", "projects.view", "projects.manage", "sprint.view", "sprint.manage",
              "sprint.update", "handover.view", "handover.manage", "timesheet.view", "timesheet.approve", "perf.view",
              "perf.manage", "revenue.view", "revenue.manage", "expenses.view", "expenses.manage", "invoices.view",
              "invoices.manage", "reports.view", "audit.view", "ai.use"]:
        out.append(a + ":all")
    out += ["employees.view:all", "allocation.view:all", "allocation.manage:all", "costing.effort:all", "targets.view:all", "projects.tag:all"]
    return out + ["org.admin", "projects.budget", "projects.finance", "salary.view", "timesheet.own", "invoices.approve", "opps.view",
                  "employees.manage", "salary.manage", "departments.manage", "tags.manage", "costing.settings", "costing.cost", "targets.manage"]


ROLE_DEFAULTS = {
    "owner": ("Organization Owner / CEO", _full()),
    "finance": ("Finance Manager", [
        "customers.view:all", "customers.manage:all", "projects.view:all", "projects.budget", "projects.finance",
        "timesheet.own", "timesheet.finance", "revenue.view:all", "revenue.manage:all", "expenses.view:all",
        "expenses.manage:all", "salary.view", "invoices.view:all", "invoices.manage:all", "reports.view:all", "ai.use:own",
        "employees.view:all", "salary.manage", "tags.manage", "projects.tag:all", "allocation.view:all", "costing.settings", "costing.effort:all",
        "costing.cost", "targets.manage", "targets.view:all"]),
    "ops": ("Operations / Delivery Manager", [
        "org.users.view", "customers.view:all", "customers.manage:all", "projects.view:all", "projects.manage:all",
        "projects.budget", "sprint.view:all", "sprint.manage:all", "sprint.update:all", "handover.view:all",
        "handover.manage:all", "timesheet.own", "timesheet.view:all", "timesheet.approve:all", "perf.view:all",
        "perf.manage:all", "revenue.view:all", "expenses.view:all", "reports.view:all", "ai.use:own",
        "employees.view:all", "departments.manage", "tags.manage", "projects.tag:all", "allocation.view:all", "allocation.manage:all",
        "costing.effort:all", "targets.view:all"]),
    "pm": ("Project Manager", [
        "customers.view:assigned", "projects.view:assigned", "projects.manage:assigned", "projects.budget",
        "sprint.view:assigned", "sprint.manage:assigned", "sprint.update:assigned", "handover.view:assigned",
        "handover.manage:assigned", "handover.ack:own", "timesheet.own", "timesheet.view:assigned", "timesheet.approve:assigned",
        "perf.view:assigned", "revenue.view:assigned", "expenses.request", "invoices.request", "reports.view:assigned",
        "ai.use:own", "employees.view:assigned", "projects.tag:assigned", "allocation.view:assigned", "allocation.manage:assigned",
        "costing.effort:assigned", "targets.view:assigned"]),
    "po": ("Product Owner", [
        "customers.view:assigned", "projects.view:assigned", "projects.manage:assigned", "projects.budget",
        "sprint.view:assigned", "sprint.manage:assigned", "sprint.update:assigned", "handover.view:assigned",
        "handover.manage:assigned", "handover.ack:own", "timesheet.own", "timesheet.view:assigned", "reports.view:assigned",
        "ai.use:own", "employees.view:assigned", "projects.tag:assigned", "allocation.view:assigned",
        "costing.effort:assigned", "targets.view:assigned"]),
    "tl": ("Team Lead", [
        "customers.view:assigned", "projects.view:assigned", "sprint.view:team", "sprint.manage:team",
        "sprint.update:team", "handover.view:team", "handover.manage:team", "handover.ack:own", "timesheet.own", "timesheet.view:team",
        "timesheet.approve:team", "perf.view:team", "reports.view:team", "ai.use:own",
        "employees.view:team", "allocation.view:team", "costing.effort:team"]),
    "employee": ("Employee / Contributor", [
        "sprint.view:own", "sprint.update:own", "handover.view:own", "handover.ack:own", "timesheet.own",
        "perf.view:own", "reports.view:own"]),
    "sales": ("Sales / Business Development", [
        "customers.view:assigned", "projects.view:assigned", "projects.contract", "revenue.view:assigned",
        "opps.view", "opps.manage", "timesheet.own", "reports.view:assigned"]),
}

# default modules for a new tenant (Pillar 2 and 3 are off by default: explicit tenant opt-in)
DEFAULT_MODULES = {k: k in ("core", "sprint", "timesheet", "revenue", "expenses", "performance", "invoices", "costing") for k in MODULES}
SCOPE_ORDER = ["all", "team", "assigned", "own"]

CAPABILITY_CATALOG = sorted({c.split(":")[0] for _, (_, perms) in ROLE_DEFAULTS.items() for c in perms})


# Capabilities introduced in Sprint 3 (Revision 2), per default role. Used by the migration to extend existing tenants'
# system roles without touching anything else an administrator edited.
SPRINT3_ADDED = {
    "owner": ["employees.view:all", "allocation.view:all", "allocation.manage:all", "costing.effort:all", "targets.view:all", "projects.tag:all",
              "employees.manage", "salary.manage", "departments.manage", "tags.manage", "costing.settings", "costing.cost", "targets.manage"],
    "finance": ["employees.view:all", "salary.manage", "tags.manage", "projects.tag:all", "allocation.view:all", "costing.settings",
                "costing.effort:all", "costing.cost", "targets.manage", "targets.view:all"],
    "ops": ["employees.view:all", "departments.manage", "tags.manage", "projects.tag:all", "allocation.view:all", "allocation.manage:all",
            "costing.effort:all", "targets.view:all"],
    "pm": ["employees.view:assigned", "projects.tag:assigned", "allocation.view:assigned", "allocation.manage:assigned",
           "costing.effort:assigned", "targets.view:assigned"],
    "tl": ["employees.view:team", "allocation.view:team", "costing.effort:team"],
}
