# Revision 2 — Business Assumptions and Decisions Requiring Approval

Source: `Aadi Technology Matrix.xlsx` (held by the business owner; not stored in the repository because it contains real salaries). Full detail: PRD Part B, section B12.

## Assumptions made (please confirm or correct)
| # | Assumption |
|---|---|
| A1 | Employee cost for a project = allocation % × monthly salary (the workbook's rule), not hourly salary × hours |
| A2 | Effort hours = allocation % × monthly hours (160) |
| A3 | "Revenue" in the workbook's allocation sheet = hours × ₹250, a **standard value of effort**, not actual revenue |
| A4 | The workbook's cost total (₹3,07,500) is a formula error; the correct total is ₹2,00,000 |
| A5 | Monthly working hours is an organization default with optional per-employee override; hourly rate is an organization default with optional per-project override |
| A6 | One department per employee; one Head of Department per department |
| A7 | Tags: many per project, managed list; tag totals overlap and are not additive |
| A8 | Month is the reporting period; allocation is set per month |
| A9 | Currency is INR |
| A10 | Names, salaries and project names in the prototype are fictional stand-ins with the workbook's numbers |

## Decisions needed
| ID | Decision | Recommended |
|---|---|---|
| D-R2-01 | Revenue basis for profitability | Standard value shown as planned value; targets separate; actual later |
| D-R2-02 | Accept corrected totals | Yes |
| D-R2-03 | Planned vs actual cost basis | Planned default; actual as comparison |
| D-R2-04 | Meaning of S / H markers | S = weekly off, H = holiday (observed pattern; unconfirmed) |
| D-R2-05 | Nature of ₹250 | Standard internal rate of effort |
| D-R2-06 | Non-salary costs in profitability | Optional layer, off by default |
| D-R2-07 | Shared cost allocation method | Defer |
| D-R2-08 | Tag governance | Managed list, many tags |
| D-R2-09 | HoD authority and salary visibility | View only; no salary |
| D-R2-10 | Multiple departments per person | No |
| D-R2-11 | Allocation above 100% | Block |
| D-R2-12 | Salary = gross or cost-to-company | Cost-to-company, effective-dated |
| D-R2-13 | Flat 160 h or working-day calendar (November implies ~168 h) | Flat 160 |
| D-R2-14 | Target levels and period | Project, tag, organization; monthly |
| D-R2-15 | Department-level profitability | Not in this revision |
