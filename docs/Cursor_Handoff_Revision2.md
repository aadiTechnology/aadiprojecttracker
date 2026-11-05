# Cursor Handoff Notes — PRD Revision 2

**Read first:** `docs/Aadi_Business_Performance_Project_Profitability_PRD.md`, **Part B**. Prototype for behaviour: `docs/Aadi_Role_Based_Feature_Proposal.html` (section "Costing & Profitability · Revision 2"). Explanation video: `videos/03-revision-2-prd-and-prototype.mp4`.

You (Cursor) are the implementation decision-maker. This note does not prescribe a design; it states what to verify and what must not break.

## 1. Before changing anything
1. Analyze Part B against the **actual code**: `backend/app/models.py`, `perms.py`, `routers/`, `seed*.py`, `alembic/versions/` (0001, 0002), `frontend/src`, `mobile/`. PRD section B2 lists what was found; re-verify, do not trust it blindly.
2. List the **minimum** changes needed. Reuse existing tenancy (`Ctx`, `tenant_id` filters), capability checks, entitlement modules (`expenses`, `revenue`, `performance`), audit helper, money-in-paise convention, the web shell and the role-masking pattern used for `budget_minor` and `contract_value_minor`.
3. Do not refactor unrelated code. Preserve working Sprint 1 and Sprint 2 behaviour (41 backend tests, `videos/check-screens.mjs` for 14 personas) unless Part B requires a change.

## 2. Likely touch points (confirm in code)
| Need | Existing thing to look at |
|---|---|
| Salary, department, HoD | `Membership` (has `team` text, `manager_user_id`; no salary). Capability `salary.view` exists but nothing stores salary |
| Tags | `Project` has `category` only |
| Allocation per month, ≤100% rule | `ProjectMember.allocation_pct` has no period and no cross-project check |
| Hours 160 and rate ₹250 | `Tenant.week_hours` (40) exists; add costing settings (org default; rate override per project; hours override per employee, see D-R2-05, FR-R2-D3/D4) |
| Revenue targets, profitability | Not built; `VIEWS` in `routers/auth.py` marks revenue/expenses "Sprint 3" and `AREA_MODULE` already maps `salary`, `expenses`, `revenue` |
| Masking | `work.project_out`, `Ctx.has/scope/require` |

## 3. Migration and backward compatibility
- New Alembic revision after `0002`; additive only; defaults keep existing demo and live data working.
- Existing `allocation_pct` values must be migrated into the new monthly allocation (or kept in parallel) without losing the team display on the project screen.
- Existing roles are stored per tenant: new capabilities must be **added to existing tenants' system roles** by the migration (see how `0002` added `handover.ack:own`), without touching edited roles' other permissions.
- Demo seed must load the fictional baseline in `docs/Aadi_Role_Based_Feature_Proposal.html` (14 employees, 11 projects) so totals can be checked: **1,760 h, ₹4,40,000 value, ₹2,00,000 cost, ₹60,000 unallocated, ₹2,40,000 margin**.
- Keep `LIVE_SPRINT` honest: new screens are labelled until built.

## 4. Non-negotiables
- Salary, cost and profit values must be **masked by the API** for roles without `salary.view` / `cost.view`; platform admin sees none.
- Every query filtered by `tenant_id`. Money in integer paise.
- Calculations exactly as Part B7; **do not copy the workbook's formula error** (B3.2).
- Open decisions (B12) are **not** defaulted silently: store as configuration or leave null, as done for `revenue_basis` and `planning_markers`.
- Real employee data must never be committed to the repository (the repo is public). Use fictional seed data.

## 5. Suggested verification
- Unit tests reproducing B3.1 totals and the worked example in B7 (400 h, ₹1,00,000, ₹52,500, ₹47,500).
- API tests: over-allocation rejected; salary hidden for Operations/PM/Team Lead; tag totals non-additive note; tenant isolation.
- Extend `videos/check-screens.mjs` personas for any new menu items.

## 6. Out of scope for this handoff
Invoices, performance matrix, Backblaze attachments, AI assistant, hardening: on hold and to be re-planned (PRD B14).
