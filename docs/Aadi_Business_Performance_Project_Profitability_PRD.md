# Aadi Technology — Business Performance & Project Profitability Platform
## Product Requirements Document (PRD)

> **Revision 2 (November 2026):** salary-allocation costing, tags and project profitability were added. See **Part B** at the end of this document. Where Part B and Parts 1–22 differ, Part B governs the changed items; everything else stays in force. Sections 7 (MOD-007, MOD-008), 9 (BR-015), 13 and 19 carry short cross-references.

**Version:** 0.2 — Revision 2 (salary-allocation costing, tags, profitability) added as Part B; 0.1 content retained  
**Reference period:** November 2026  
**Status:** Proposed MVP baseline; customer validation required  
**Prepared for:** Aadi Technology / Customer review and Claude implementation planning

---

## 1. Executive Summary

The supplied workbook, `Aadi Technology Matrix.xlsx`, contains two operational views:

1. **Targets** — customer/business-wise revenue and cost categories, including infrastructure, third-party solutions, software, marketing, sales, consulting and salary. It also lists shared operating subscriptions/expenses such as OpenAI API, ChatGPT, Azure, Contabo, rent and Wi-Fi.
2. **November 2026** — project/scope-level work allocation with an owner, estimated hours, spend, daily planning cells for days 1–30, percentage complete, completed efforts and remaining hours.

The additional customer notes are:
- Matrix/Invoice — Employee Performance
- Sprint Planning — To team transition
- Target — Revenue
- Timesheet — To capture details

### Product interpretation

The customer appears to need a business operations and performance platform connecting financial outcomes with project delivery and employee effort. It should help management answer:

- What revenue is expected and realized by customer, project and period?
- What does it cost to deliver each project/customer?
- Which employees are assigned to the work and what are they expected to deliver?
- What work was actually completed and how much time was spent?
- Is the project/sprint on track?
- How are tasks and responsibilities transferred between team members?
- How do actual employee/project outcomes compare with agreed targets?
- What invoices should be raised, and what remains unpaid?

This interpretation is a recommendation derived from the workbook and notes. It is not a claim that the customer has approved every feature below.

## 2. Product Vision

Provide a configurable, multitenant SaaS platform for small and medium-sized service businesses to manage revenue targets, project delivery, employee effort, cost allocation, performance and invoicing in one connected system.

**Positioning:** Business Performance & Project Profitability Platform.

**Core value proposition:** Connect Revenue → Customers/Projects → Scope/Sprints → Employees → Timesheets → Costs → Invoices → Performance.

## 3. Source Inputs and Evidence Boundaries

### 3.1 Directly supplied workbook fields

**Targets sheet**
- Sr.No
- Business Name
- Revenue
- Infrastructure
- Third Party Solutions
- Software
- Marketing
- Sales
- Consulting
- Salary
- Total Amount
- Cursor Accounts list, including Open AI API, Open AI Chat GPT, Azure (uncertain entry), Contabo (uncertain entry), Rent and WiFi

The sheet has a displayed bottom total of ₹290,000 in the Total Amount column. Revenue and cost values are incomplete across rows; therefore, the amount must be treated as source-sheet data requiring validation, not as a confirmed financial result.

**November 2026 sheet**
- Sr.No.
- Project Name
- Available Scope
- Details
- Owner
- Estimated Hours
- Spend
- Daily columns 1–30
- Percent Complete
- Completed Efforts
- Remaining Hours

The supplied rows reference projects/businesses including RITe School, Marketing Product, Atlas, Internship, Smartkidz, Paneerwala, Nexa Tech and Space View Interiors. The Owner column contains employee names. Daily cells contain some S/H markers, but their meaning is not defined in the workbook. Do not infer what S and H mean; make the planning marker configurable or request customer confirmation.

### 3.2 Additional customer notes

Preserve the original wording:
- Matrix/Invoice - Employee Performance
- Sprint Planning - To team tranistion
- Target - Revenue
- Timesheet - To capture deatils

### 3.3 Classification

| Item | Classification | Interpretation |
|---|---|---|
| Customer-wise revenue/cost matrix | Supplied input | Financial tracking by business/customer |
| Employee owner and project scope | Supplied input | Work allocation |
| Estimated hours, spend, completion, effort remaining | Supplied input | Project effort/progress tracking |
| Matrix/Invoice – Employee Performance | Supplied note; ambiguous | Employee performance matrix and invoice-related workflow; confirm invoice scope |
| Sprint Planning – To team transition | Supplied note; ambiguous | Sprint/task planning and controlled handover |
| Revenue target | Supplied note | Target setting and actual-versus-target tracking |
| Timesheet | Supplied note | Actual work and time capture |
| Profitability, utilization, forecasting, approvals, notifications, AI insights | Recommendations | Useful derived capabilities; not explicitly confirmed |

## 4. Business Objectives and Success Measures

1. Give management a consolidated view of revenue, cost, project status and employee contribution.
2. Improve project planning and accountability through sprint/task ownership.
3. Capture actual effort consistently and compare it with estimates.
4. Calculate project/customer contribution and profitability using transparent cost allocation.
5. Monitor revenue targets and identify shortfalls early.
6. Reduce manual consolidation across spreadsheets.
7. Produce invoice-ready project and effort summaries, subject to customer confirmation of billing rules.

### Proposed measurable product KPIs (customer validation required)

- Percentage of active projects with an owner, scope and target.
- Percentage of employee work entries submitted and approved on time.
- Estimate-versus-actual effort variance.
- Employee utilization = approved productive hours / available working hours.
- Project gross contribution = recognized project revenue − directly attributable delivery cost.
- Revenue target achievement = actual revenue / revenue target.
- Invoice readiness and overdue receivables.
- Sprint commitment completion rate and carry-forward rate.

Do not equate utilization with employee quality. Performance must use role-appropriate, contextual measures and manager review.

## 5. Target Customers and Personas

Initial target segment is assumed to be service businesses, IT/software companies, consulting firms and agencies that manage multiple customers/projects and shared employees. This is a proposed market, not confirmed customer scope.

| Persona | Primary goals |
|---|---|
| Organization Owner / CEO | Revenue, margin, cost, targets, business performance |
| Finance Manager / Accountant | Revenue and expense entries, cost allocation, invoices, receivables |
| Operations / Delivery Manager | Project health, capacity, scope, sprint execution |
| Project Manager | Project plan, task assignment, estimates, progress, handover |
| Team Lead | Team workload, sprint commitments, review and approvals |
| Employee / Contributor | Assigned work, daily updates, timesheets, handover |
| Sales / Business Development | Customer pipeline, expected revenue, targets, won work |
| HR / People Manager (optional) | Employee capacity, leave/availability, performance review |
| SaaS Platform Administrator | Tenant setup, plans, entitlements and platform monitoring |

Roles must be configurable and permissions must be enforced on the backend. Do not assume every user with a role can view every customer, project, employee or financial record.

## 6. Aadi Three-Pillar Product Strategy

### Pillar 1 — Software Product: Make the business operationally better

**Opportunity:** Core system for customer/project financials, delivery planning, employee allocation, sprint execution, timesheets, costs, invoices and reporting.

- Essential: customer/project register, scope, work allocation, timesheets, revenue/cost tracking, role-based access, dashboards and audit history.
- Recommended: approvals, handover workflow, resource capacity, project profitability and invoice preparation.
- Optional/future: advanced portfolio management, configurable workflows and integrations with accounting/payroll tools.

### Pillar 2 — Marketing & Sales: Bring more customers, convert and retain them

Do not build a full CRM by default. Assess the smallest useful commercial workflow.

- Recommended: customer directory, sales opportunity/value, expected close date, revenue forecast, follow-up reminders and won-project conversion.
- Optional: lead capture forms, campaign attribution, referral tracking and customer renewal/retention indicators.
- Not MVP unless customer confirms: full marketing automation, omnichannel campaign management and a standalone CRM.

### Pillar 3 — AI Solutions: Intelligent automation with measurable value

- Recommended: natural-language management summaries from authorized data; project risk/variance explanations; timesheet categorization suggestions; revenue shortfall signals.
- Optional/future: effort anomaly detection, delivery forecasting and AI-assisted sprint planning.
- AI must never approve timesheets, alter financial data, evaluate or penalize an employee, or send an external communication without authorized human approval.
- AI must obey tenant and user permissions, disclose uncertainty, log material actions and have usage-cost controls.

### Three-pillar assessment

| Pillar | MVP status | Reason |
|---|---|---|
| Pillar 1: Software Product | Essential | Directly addresses supplied matrix, planning and timesheet needs |
| Pillar 2: Marketing & Sales | Recommended / limited | Revenue targets need a source of expected revenue; lightweight opportunity tracking may help |
| Pillar 3: AI Solutions | Recommended / limited | Management summaries and anomaly explanations can add value after reliable data capture |

## 7. Product Scope and Modules

### MOD-001 — Organization, Tenant and User Administration
- Organization profile, timezone, currency and working-week configuration.
- Tenant-scoped users, invitations, activation/suspension.
- Configurable roles and permission assignment.
- Department/team and reporting-manager mapping where enabled.
- Tenant-level module entitlements.
- Audit log for access and configuration changes.

### MOD-002 — Customer and Business Register
- Create and maintain customer/business records.
- Customer status, contact details, billing details, account owner and notes.
- Associate projects, revenue targets, invoices and costs with a customer.
- Support internal business units such as Aadi Technology/Product where configured.
- Import/export with validation and duplicate detection.

### MOD-003 — Project and Scope Management
- Create projects linked to a customer/business unit.
- Project manager, team, start/end dates, status, billing model and currency.
- Capture available scope, details, milestones and deliverables.
- Allocate employees and define planned effort.
- Track project budget, expected revenue and delivery cost.
- Project status: Draft, Planned, Active, On Hold, Completed, Cancelled.
- Scope changes must be recorded with date, reason, requester and approver.

### MOD-004 — Sprint and Work Planning
- Create sprint/iteration with name, goal, start/end dates and status.
- Add tasks/work items linked to project and scope.
- Assign owner, priority, estimate, due date and acceptance criteria.
- Daily/weekly planning view; calendar-style view should support configurable markers.
- Sprint backlog, committed work, in-progress, blocked, review and done states.
- Carry forward unfinished work with reason.
- Reassign work and maintain ownership history.
- Sprint planning supports team transition/handover; it does not silently transfer accountability.
- Handover captures outgoing owner, incoming owner, work status, remaining effort, blockers, links/files, next action and acknowledgement.

### MOD-005 — Timesheet and Work Log
- Employees record date, project, task/sprint, work description, work type and duration.
- Support daily entry and weekly timesheet submission.
- Draft, Submitted, Approved, Rejected and Returned states.
- Manager review with comments and audit trail.
- Prevent or flag overlapping entries and invalid durations.
- Configure billable/non-billable classification.
- Compare actual effort against task/project estimates.
- Employees can correct returned entries; approved entries require controlled adjustment with audit history.
- Mobile-responsive time entry is recommended; native mobile app is not assumed for MVP.

### MOD-006 — Employee Performance Matrix
- Employee profile linked to team, manager, skills and role.
- Show assigned projects/tasks, planned effort, approved actual effort, completed work and handover history.
- Role-specific scorecard with transparent definitions.
- Suggested dimensions: delivery reliability, quality/acceptance, estimate accuracy, collaboration/handover, billable contribution and goal achievement.
- Managers add evidence-based review comments and conduct periodic reviews.
- Employee can view their own metrics and submit comments/acknowledgement.
- Do not use raw hours as the sole performance score.
- No opaque automated employee ranking or punitive AI scoring.

### MOD-007 — Revenue Targets and Forecasting
- *Revision 2: targets by project, tag and organization per month are detailed in Part B (FR-R2-F1).*
- Set targets by organization, period, customer, project and optionally sales owner.
- Target period: monthly initially; configurable quarterly/yearly later.
- Record target amount, currency, owner, baseline and approval.
- Track actual revenue, expected revenue and variance.
- Show achievement percentage, gap and trend.
- Revenue recognition basis must be configurable/confirmed (invoice date, payment date, milestone or accounting entry); do not assume.
- Prevent double-counting revenue across customer/project/organization rollups.
- Forecasting is based on explicit pipeline/probability rules if enabled.

### MOD-008 — Expense, Cost Allocation and Profitability
- Expense categories based on supplied matrix: Infrastructure, Third Party Solutions, Software, Marketing, Sales, Consulting, Salary and configurable additional categories.
- Record amount, date, vendor, customer/project allocation, category, payment status, supporting attachment and notes.
- Support direct project costs and shared overhead.
- Configurable allocation methods for shared expenses: equal share, percentage, headcount, usage, hours or manual allocation.
- Salary cost may be calculated from approved cost rates and allocated effort; salary rates must be restricted to authorized finance/management roles.
- Avoid double-counting direct costs and allocated overhead.
- Calculate revenue, direct cost, allocated overhead, gross contribution and contribution margin with clearly disclosed formulas.
- Show unallocated costs and incomplete financial data warnings.
- Do not treat the source workbook's displayed ₹290,000 as validated actual cost without reconciliation.
- *Revision 2:* salary cost by allocation, tags and project profitability are specified in Part B (B6, B7). The workbook's allocation model reports ₹3,07,500 cost, which is a formula error; the corrected figure is ₹2,00,000 (B3.2).

### MOD-009 — Invoice Management
- Create draft invoice from customer/project, milestones or approved billable timesheets.
- Invoice number, issue date, due date, customer billing details, line items, tax configuration, currency, subtotal, tax and total.
- Status: Draft, Approved, Issued, Partially Paid, Paid, Overdue, Void.
- Record payments and outstanding balance.
- PDF export and email/share workflow are recommended.
- Tax/GST configuration and statutory invoice compliance require customer/accountant validation; do not hardcode tax assumptions.
- If invoice generation is not confirmed as part of the customer's intended meaning of “Matrix/Invoice”, treat full invoicing as a configurable MVP decision.

### MOD-010 — Dashboards and Reports
- Executive dashboard: revenue target vs actual, costs, contribution, receivables, active projects and risk alerts.
- Finance dashboard: category spend, customer/project cost, invoices and outstanding.
- Delivery dashboard: sprint progress, estimate vs actual, blocked work, overdue tasks.
- Employee dashboard: assigned work, timesheet status, workload and personal performance indicators.
- Project dashboard: scope, budget, effort, progress, team and profitability.
- Filters by period, customer, project, team and employee, subject to permissions.
- Export authorized reports to CSV/XLSX/PDF.

### MOD-011 — Notifications and Audit
- In-app notifications for assignment, due dates, handovers, timesheet submission/approval, sprint changes, target variance and invoice due dates.
- Email notifications configurable by tenant.
- Audit actor, timestamp, action, entity, before/after values where appropriate.
- Audit access restricted to authorized roles.

### MOD-012 — AI Management Assistant (Phase 2 / limited MVP pilot)
- Natural-language questions over permitted management data.
- Summarize project progress and revenue variance.
- Explain estimate-versus-actual differences using available evidence.
- Suggest follow-up actions for human review.
- Permission-aware retrieval and tenant isolation.
- No autonomous financial postings, invoice issuance, employee ratings or approvals.

## 8. Key Workflows

### WF-001 — Project setup and employee allocation
1. Authorized user creates customer and project.
2. Adds scope, milestones, budget and target revenue.
3. Adds sprint/work items and estimates.
4. Assigns employees and confirms availability.
5. Employees see only authorized assigned work.
6. Project manager reviews plan and activates project.

### WF-002 — Sprint planning and team transition
1. Project manager creates sprint and backlog.
2. Team lead reviews capacity and commits work.
3. Tasks are assigned with estimates and acceptance criteria.
4. If an owner changes, create a handover record.
5. Incoming owner acknowledges handover.
6. Sprint progress and carry-forward are reported with history.

### WF-003 — Timesheet submission and approval
1. Employee logs work against a project/task.
2. System validates date, duration and assignment.
3. Employee submits daily/weekly timesheet.
4. Manager reviews, approves, rejects or returns with comments.
5. Approved time updates project actual effort and eligible billable effort.
6. Corrections to approved entries use an auditable adjustment process.

### WF-004 — Revenue target monitoring
1. Management sets period/customer/project targets.
2. Actual revenue is recorded/imported using an approved revenue basis.
3. Dashboard compares actual and target.
4. Variance and shortfall are highlighted.
5. Authorized manager records corrective actions.

### WF-005 — Cost and profitability
1. Finance records direct and shared expenses.
2. Expenses are assigned to a customer/project or marked shared.
3. Shared costs are allocated using configured methods.
4. Salary cost allocation uses approved rates and approved effort.
5. Dashboard calculates contribution and flags missing data.
6. Finance reconciles results before external reporting.

### WF-006 — Invoice preparation
1. Finance selects customer/project and eligible billable milestones/time.
2. System creates draft invoice.
3. Authorized reviewer validates line items, tax and customer details.
4. Invoice is approved and issued by an authorized user.
5. Payments are recorded and outstanding balance updated.

## 9. Business Rules

- BR-001: Every project must belong to one tenant and be associated with a customer or internal business unit.
- BR-002: Every active task must have an accountable owner; multiple contributors may be recorded separately.
- BR-003: Reassignment must preserve previous ownership and handover history.
- BR-004: Timesheet duration must be positive and within tenant-configured limits.
- BR-005: Approved timesheets cannot be silently edited.
- BR-006: Only approved effort is used in official utilization and cost allocation calculations.
- BR-007: Employee utilization denominator must use configured working hours less approved leave/holidays where such data is available.
- BR-008: Employee performance must combine role-appropriate outcomes and manager evidence; hours alone are insufficient.
- BR-009: Revenue and cost rollups must not double count entries.
- BR-010: Every financial amount must carry a currency; currency conversion requires a recorded rate/date/source.
- BR-011: Shared cost allocation method and allocation period must be visible and auditable.
- BR-012: Invoice issuance requires appropriate finance permission and approval policy.
- BR-013: Tenant and resource authorization is enforced by backend APIs.
- BR-014: AI outputs are advisory and cannot perform high-impact actions without human authorization.
- BR-015: Source workbook daily markers S/H must remain undefined until the customer confirms their meaning. *(Revision 2: the workbook pattern suggests S = weekly off and H = holiday; still unconfirmed, see Part B D-R2-04. The meaning stays configurable and is not hard-coded.)*

## 10. Roles and Permission Model

| Capability | Owner/Admin | Finance | Operations | Project Manager | Team Lead | Employee | Sales |
|---|---:|---:|---:|---:|---:|---:|---:|
| Organization settings/users | Full | No | Limited | No | No | Own profile | No |
| View organization financials | Full | Full | Summary | Project scope only | No | No | Sales view |
| Manage expenses/costs | Full | Full | View | Project request | No | Submit if allowed | No |
| Revenue targets | Full | Manage | View | Project target view | No | Own goal if enabled | Manage assigned |
| Customer records | Full | Full | Full | Assigned | Assigned | Assigned only | Assigned |
| Projects/scope | Full | Finance view | Full | Assigned projects | Assigned projects | Assigned tasks | Won/assigned view |
| Sprint/task planning | Full | No | Full | Full on assigned | Team scope | Own assigned tasks | No |
| Assign/reassign work | Full | No | Full | Assigned projects | Team scope | No | No |
| Handover acknowledgement | View | No | Full | Full | Full | Own handovers | No |
| Submit timesheets | Own if needed | No | Own if needed | Own | Own | Own | Own if needed |
| Approve timesheets | Full | Finance validation only | Full | Assigned team if delegated | Team scope | No | No |
| Employee performance | Full | No | Full | Project evidence only | Team scope | Own only | No |
| Create/issue invoices | Full | Full | No | Draft request only | No | No | No |
| Reports | Full | Finance | Delivery | Assigned projects | Team | Own | Sales |
| Audit logs | Full | Financial scope | Operational scope | Assigned scope | Team scope | Own activity | Sales scope |

This is a proposed starting matrix. Final role names and delegation rules require customer approval. Use permission capabilities rather than hardcoded role-name checks.

## 11. Screen Inventory

| Screen ID | Screen | Primary roles |
|---|---|---|
| UI-001 | Login / invitation / password reset | All |
| UI-002 | Role-aware home dashboard | All |
| UI-003 | Organization settings and users | Owner/Admin |
| UI-004 | Customer/business list and detail | Owner, Finance, Operations, PM, Sales |
| UI-005 | Project portfolio | Owner, Operations, PM |
| UI-006 | Project detail, scope and budget | Owner, Finance, Operations, PM |
| UI-007 | Sprint board and planning calendar | Operations, PM, Team Lead, Employee (limited) |
| UI-008 | Task detail and handover | PM, Team Lead, assigned Employee |
| UI-009 | My work and timesheet entry | Employee and all users for own work |
| UI-010 | Timesheet review and approval | Manager, Team Lead, delegated PM |
| UI-011 | Employee performance matrix | Owner, Operations, Team Lead; employee self-view |
| UI-012 | Revenue targets and variance | Owner, Finance, Sales, Operations (scoped) |
| UI-013 | Expense and cost allocation | Owner, Finance |
| UI-014 | Invoice list and detail | Owner, Finance |
| UI-015 | Executive/finance/delivery reports | Authorized roles |
| UI-016 | Notifications and audit | All (scoped); audit admins |

## 12. Data Entity Inventory

- Organization / Tenant
- User
- Role
- Permission
- UserRoleAssignment
- Department / Team
- Customer / BusinessUnit
- Project
- ProjectMember
- ProjectScope / Milestone
- Sprint
- Task / WorkItem
- TaskAssignmentHistory
- Handover
- Timesheet
- TimesheetEntry
- TimesheetApproval
- EmployeeProfile
- PerformanceGoal / PerformanceReview
- RevenueTarget
- RevenueEntry
- Opportunity (optional Pillar 2)
- Expense
- ExpenseCategory
- CostAllocation
- CostRate (restricted)
- Invoice
- InvoiceLine
- Payment
- Notification
- Attachment
- AuditEvent
- TenantFeatureEntitlement
- AIUsageLog (if AI enabled)

All tenant-owned records must include tenant scope and appropriate resource ownership. Avoid duplicate employee/customer master records.

## 13. Reporting and Calculation Definitions

All formulas below are proposed and must be validated with the customer/accountant.

- Revenue target achievement (%) = recognized actual revenue / target revenue × 100.
- Revenue variance = actual revenue − target revenue.
- Estimate variance (hours) = actual approved hours − estimated hours.
- Estimate variance (%) = (actual approved hours − estimated hours) / estimated hours × 100; handle zero estimate separately.
- Utilization (%) = approved productive hours / available working hours × 100.
- Direct project cost = directly attributable approved expenses + attributable employee labor cost.
- Allocated overhead = shared cost allocated using selected method.
- Project contribution = recognized project revenue − direct project cost − allocated overhead.
- Contribution margin (%) = project contribution / recognized project revenue × 100; handle zero revenue.
- Invoice outstanding = invoice total − recorded payments − credits/adjustments.

Clearly label estimated, accrued, invoiced, collected and recognized revenue separately. The application must not conflate these financial states.

## 14. Three-Pillar Module Mapping and Roadmap

| Module | Pillar | MVP recommendation |
|---|---|---|
| Customer/project/scope management | P1 | P0 |
| Sprint/task planning and handover | P1 | P0 |
| Timesheet and approval | P1 | P0 |
| Revenue target and actual tracking | P1 / P2 | P0 basic |
| Expense/cost allocation | P1 | P0 basic |
| Employee performance matrix | P1 | P1 |
| Invoice preparation and tracking | P1 | P1, subject to confirmation |
| Executive and role dashboards | P1 | P0 |
| Lightweight opportunity tracking | P2 | P2 |
| AI management summaries | P3 | P2 pilot after data quality |
| Predictive delivery/revenue forecasts | P3 | P3 |

### MVP release boundary

**P0**
- Tenant/user/role foundation
- Customer and project register
- Project scope and employee assignment
- Sprint/task planning with ownership history
- Basic handover
- Timesheet entry and approval
- Revenue targets and actual revenue entry
- Expense categories and basic direct/shared cost tracking
- Basic dashboards and exports
- Audit trail and tenant isolation

**P1**
- Employee performance matrix
- Invoice draft, approval and payment tracking
- Configurable shared-cost allocation
- More advanced reports and notifications

**P2/P3**
- Opportunity pipeline and sales follow-ups
- AI summaries and recommendations
- Predictive forecasts
- Accounting/payroll integrations
- Advanced resource capacity planning

## 15. Web and Mobile Scope

### Web
Primary application for management, finance, operations and project administration:
- Dashboards, master data, project and sprint planning
- Financial entry and cost allocation
- Timesheet review and approvals
- Performance matrix and reports
- Invoice preparation
- User, role and tenant configuration

### Mobile
MVP recommendation: responsive web experience first. A native mobile application is not confirmed by the source inputs. If introduced later, prioritize employee work view, quick timesheet entry, task updates, handover acknowledgement and notifications.

## 16. Non-Functional Requirements

| ID | Requirement | Proposed initial target / validation |
|---|---|---|
| NFR-001 | Tenant isolation | Automated cross-tenant negative tests for all tenant-owned APIs |
| NFR-002 | Authorization | Backend authorization on every protected API and resource |
| NFR-003 | Performance | Common dashboard/list requests target p95 under 2.5 seconds under agreed test load |
| NFR-004 | Auditability | Financial, approval, role and ownership changes recorded with actor/time |
| NFR-005 | Availability | Target to be agreed; propose 99.5% monthly for initial SaaS tier |
| NFR-006 | Backup/recovery | Automated backups; RPO/RTO to be agreed with customer |
| NFR-007 | Data export | Authorized CSV/XLSX export for core reports |
| NFR-008 | Security | Secure sessions, password policy, rate limiting, encryption in transit and protected secrets |
| NFR-009 | Accessibility | Keyboard-operable core workflows and accessible form labels |
| NFR-010 | Localization | Tenant-configurable timezone and currency; language support can be phased |
| NFR-011 | Observability | Structured application logs, error monitoring and health checks |
| NFR-012 | Data integrity | Transactional updates and validation for financial and approval workflows |

Targets are proposals, not customer-approved SLAs or compliance claims.

## 17. Security, Privacy and Governance

- Enforce tenant isolation at API and data-access layers.
- Use least-privilege role and resource permissions.
- Restrict salary rates, employee cost and financial reports to authorized roles.
- Maintain audit trails for financial records, approvals, role changes and task handovers.
- Secure file attachments and invoice documents.
- Define retention, deletion, export and backup policies with the customer.
- Avoid collecting sensitive employee data not required for the stated workflows.
- Provide transparent metric definitions and employee access to their own performance data.
- AI must use authorized data only and must not become an unreviewed decision-maker.

## 18. API Capability Inventory (logical)

- Organization and user administration
- Role and permission management
- Customer/business CRUD
- Project/scope/member CRUD
- Sprint/task planning and assignment
- Handover creation/acknowledgement
- Timesheet create/submit/review/approve/adjust
- Employee performance goals and reviews
- Revenue targets and revenue entries
- Expense and cost allocation
- Invoice and payment management
- Dashboard/report aggregation
- Notification and audit retrieval
- Tenant feature entitlements

API request/response schemas, pagination, idempotency and versioning are to be finalized during technical design. Every endpoint must enforce tenant and resource authorization.

## 19. Risks, Dependencies and Open Decisions

### High-priority decisions
1. What does “Matrix/Invoice” mean exactly: employee performance matrix, customer invoice matrix, invoice generation, or all three?
2. Does the customer want actual invoice creation/PDF/GST handling, or only invoice tracking?
3. What do daily calendar markers `S` and `H` mean in the November sheet? *(Rev 2: likely weekly off / holiday, see D-R2-04.)*
4. What is the revenue definition: invoiced, collected, recognized, milestone-based or manually reported?
5. Are targets set at organization, customer, project, employee, sales owner or all levels?
6. How should salary be allocated: actual salary/working hours, standard hourly cost rate, percentage allocation or manual? *(Rev 2: the workbook uses percentage allocation × monthly salary; see B7 and D-R2-03.)*
7. How should shared costs (rent, Wi-Fi, hosting, AI subscriptions) be allocated?
8. What is the intended sprint cadence and what does “team transition” require: task reassignment, project handover, sprint carry-forward or all?
9. Are the listed business names customers, internal products, departments or a mixture?
10. Which currencies, tax rules and invoice formats are required?
11. Which approval hierarchy applies to timesheets, expenses and invoices?
12. Is mobile/native app required for MVP?

### Key risks
- Incomplete financial values may produce misleading profitability reports.
- Inconsistent timesheet capture will undermine employee cost and utilization metrics.
- Ambiguous revenue recognition can create incorrect target achievement.
- Poorly defined role permissions can expose salary and customer financial data.
- Uncontrolled handovers can lose accountability and project context.
- Performance scoring based only on hours can reward the wrong behavior.

## 20. Acceptance Criteria — MVP Examples

- Given a tenant user, when they access a project outside their authorized scope, then the API denies access.
- Given an active project, when a manager assigns a task, then the task has an accountable owner and estimate.
- Given a task reassignment, when handover is initiated, then old ownership and handover details remain auditable.
- Given an employee work entry, when it is submitted, then it enters the approval workflow and cannot be treated as approved effort until approved.
- Given approved timesheet entries, when project actual effort is calculated, then only eligible approved entries are included.
- Given a revenue target and actual revenue entries, when the dashboard is opened, then target, actual, variance and achievement are displayed with the configured revenue basis.
- Given shared expenses, when a cost allocation run is performed, then the selected method and allocation period are visible and totals reconcile to the source expense.
- Given an invoice draft, when an unauthorized user attempts to issue it, then the operation is denied and audited.
- Given a user from another tenant, when they query any tenant-owned resource, then no data is disclosed.
- Given an employee, when they open their performance view, then they can see their own permitted metrics but not other employees' restricted salary or review data.

## 21. Product Owner Review and Readiness

| Area | Initial status |
|---|---|
| Source feature inventory | Complete |
| Product interpretation | Proposed; customer validation required |
| Three-pillar assessment | Initial assessment complete |
| MVP module boundaries | Proposed |
| Detailed revenue recognition rules | Requires decision |
| Salary/cost allocation rules | Requires decision |
| Invoice/GST requirements | Requires decision |
| Daily S/H marker meanings | Requires decision |
| Final role hierarchy | Requires decision |
| Final NFR/SLA targets | Requires decision |
| Technical architecture and API contracts | To be designed |
| Strategy approval | Not yet approved |
| Implementation readiness | Not yet approved pending critical decisions |

## 22. Instructions for Claude

Use this PRD as the source of truth for product discovery and implementation planning. Do not silently convert proposed recommendations into confirmed customer requirements.

Before coding:
1. Read this entire PRD and the original `Aadi Technology Matrix.xlsx` if available in the project workspace.
2. Produce a requirements traceability matrix mapping source input → module/requirement → screen/API → acceptance test.
3. Produce a concise list of critical ambiguities and recommended defaults. Do not block all progress on non-critical decisions.
4. Identify contradictions, missing details and implementation dependencies.
5. Propose an MVP architecture and phased sprint plan.
6. Separate confirmed scope, recommended scope, assumptions and open decisions.
7. Do not implement unapproved tax/GST, revenue recognition or salary allocation assumptions.
8. Enforce tenant isolation and backend authorization from the beginning.
9. Do not use hours alone as an employee performance score.
10. Obtain product-owner approval of the baseline and sprint plan before implementation.

The PRD is a product definition draft, not authorization for production deployment.


---

# PART B — REVISION 2: Salary-Allocation Costing, Tags and Project Profitability

> **Status:** Proposed for business review. Nothing in Part B is approved scope until the business owner confirms the items in section B12.
> **Sprint hold:** Former Sprint 3 and 4 content is paused and will be re-planned in iterations after this revision is reviewed (see B14).
> **Data handling:** The business owner's Excel workbook (`Aadi Technology Matrix.xlsx`) contains real employee names and salaries. It is **not** stored in this repository. All names, salaries and project names in the prototype and in this document are **fictional stand-ins** that reproduce the workbook's structure, allocation percentages and arithmetic, so that totals can be reconciled.

## B1. Business Objective and Expected Outcomes

Aadi Technology wants one place to answer: *what does each project cost us in people, what is that effort worth, and are we making or losing money — by employee, by project and by project tag?*

| # | Objective (preserved from the business input) | Expected outcome |
|---|---|---|
| A | Employee master: employee list, department, Head of Department, salary | One governed list; salary visible only to authorised roles |
| B | Project master: project list, tags, filtering and financial reporting by tag | Any report can be sliced by tag (e.g. Marketing, Education, Internal) |
| C | Employee allocation: % of an employee's month per project, across several projects | Planned effort and cost per employee-project pair |
| D | Configuration: monthly working hours (160) and standard hourly rate (₹250) | Values set once at organization level, overridable where it makes sense |
| E | Effort and cost by employee, project and tag | Calculations match the Excel model (after correcting its formula errors, B3) |
| F | Revenue target definition and project-wise profitability from salary and allocation cost | Target vs value vs cost vs profit for every project and tag |

## B2. Existing System Analysis (what the code actually has)

Verified against the repository (`backend/app/models.py`, `perms.py`, `routers/*.py`, `frontend/src`, `mobile/`), not assumed.

| Area | What exists today | Relevance to Revision 2 |
|---|---|---|
| Multi-tenancy | Every row has `tenant_id`; roles stored per tenant; module entitlements (`revenue`, `expenses`, `performance` already defined, screens marked "Sprint 3") | Reuse unchanged. New features sit behind existing `expenses`/`revenue` entitlements |
| Employee | `User` + `Membership` (title, `team` free text, `manager_user_id`, status). **No salary, no department entity, no Head of Department** | Gap: add department master, HoD, salary |
| Salary permission | Capability `salary.view` exists for Owner and Finance; area `salary` maps to the `expenses` module; **no salary data is stored** | Reuse the capability; add storage and masking |
| Project | `Project`: code, name, customer, PM, `category` (Software Development / Services / Marketing / Sales), status, health, dates, scope, `budget_minor`, `contract_value_minor`, `est_hours`. **No tags** | Gap: tags. `category` stays and is complementary |
| Allocation | `ProjectMember.allocation_pct` (1–100) per project, no period, **no check that an employee's total across projects is ≤ 100%**, used for team display only | Modify: add period (month) and cross-project validation; feed calculations |
| Actual effort | `TimeEntry` with approval workflow (Sprint 2), hours per project/task/day | Reuse later for planned-vs-actual comparison |
| Org settings | `Tenant.week_hours` (40), `currency`, `timezone`, `revenue_basis` (null = undecided), `planning_markers` (undecided) | Modify: add monthly hours (160) and standard hourly rate (₹250); resolves part of two open decisions |
| Money | Integer paise everywhere; INR default | Reuse; hourly rate and salary stored as paise |
| Revenue, cost, profitability | Not built (planned Sprint 3). Dashboard shows only sums of budget and contract value | New |
| Reports | None beyond dashboard | New |
| Web screens | Customers, Projects, Sprint Planning, Handover, Timesheets, Organization Admin, matrix/workflow/assumptions | Reuse shell, tables, modals, role masking pattern |
| Mobile | Tasks, timesheet, handover, alerts | No change required; Revision 2 is management-facing (web) |
| Role permissions | Roles as data, scopes all/team/assigned/own, server-side field masking (budget, contract value) | Reuse the masking pattern for salary and cost |

## B3. What the Excel workbook contains (analysis)

| Sheet | Content | How Revision 2 uses it |
|---|---|---|
| **Targets** | 11 businesses/projects; columns: Revenue (only 3 filled), Infrastructure, Third-party, Software, Marketing, Sales, Consulting, Salary, Total; shared-cost list ("Cursor Accounts": AI API, ChatGPT, Azure, Contabo, rent, Wi-Fi) | Revenue targets (F) and optional non-salary cost layer (decision D-R2-06, D-R2-07) |
| **Novemeber** (main model) | 14 employees with monthly salary; per project an *Allocation* row (% per employee), an *Efforts* row (= allocation × 160) and a *Budget* row (= allocation × salary). Column C = cost (sum of Budget row); column D = "Revenue" = total effort hours × ₹250 | Source of calculation expectations (C, D, E) |
| **Sheet1** | Earlier version of the same allocation model with per-project hours/cost blocks | Confirms the model; contains the same anchoring error |
| **November 2026** | Monthly plan: project × scope item × owner, estimated hours, spend, day columns 1–30 with `S`/`H` markers, % complete, remaining hours | Resolves part of the S/H question (D-R2-04); scope-item planning stays in Sprint Planning |

### B3.1 Expected totals when the model is computed correctly

Employee cost = allocation % × monthly salary. Effort hours = allocation % × 160. Standard value = hours × ₹250.

| Measure | Value |
|---|---|
| Employees / projects | 14 / 11 |
| Total salary pool (all 14 employees) | ₹2,60,000 |
| Allocated effort | 1,760 hours |
| Standard value of effort (hours × ₹250) | ₹4,40,000 |
| Allocated salary cost | ₹2,00,000 |
| Unallocated salary (3 employees on bench) | ₹60,000 |
| Margin on allocated work (value − cost) | ₹2,40,000 (54.5%) |

### B3.2 Defects found in the workbook (must not be copied into the product)

1. **Cost formula anchored to one salary cell.** On projects 2–11 the cost row multiplies *every* employee's allocation by a single fixed salary cell (`$F$4`, ₹30,000) instead of each employee's own salary; project 1 is correct. Result: the sheet reports total cost **₹3,07,500**; the correct figure is **₹2,00,000** (overstated by ₹1,07,500). Sheet1 has the same pattern (`$C$3`).
2. **Fragile ranges.** Several cost totals sum `E:P` and omit the last two employee columns; they happen to be zero today.
3. **Revenue column is derived, not actual.** "Revenue" = hours × ₹250 is a *standard value of effort*, not invoiced or collected revenue. Real revenue targets exist for only 3 of 11 projects.
4. **Unallocated capacity** is not reported (3 employees are at 0%).
5. **Targets sheet** total (₹2,90,000) mixes budgeted categories and has one row without a total; treat as planning data.

The prototype's "Excel Check" screen shows this reconciliation side by side. **Business confirmation of the corrected totals is required (D-R2-02).**

## B4. Scope Classification

| Class | Item |
|---|---|
| **Retain** | Multi-tenant platform, authentication, roles/permissions engine, module entitlements, audit log, customers, projects, sprints/tasks, handover, timesheets and approval, notifications, mobile app, demo and deployment setup |
| **Modify** | `Membership` (add department link, salary); `Project` (add tags, optional hourly-rate override); `ProjectMember.allocation_pct` (add month, enforce ≤100% per employee per month); organization settings (add monthly hours, standard hourly rate); dashboards (add cost and profit widgets for authorised roles); role matrix (new capabilities); former Sprint 3 revenue/expense scope (re-planned around this revision) |
| **New** | Department master and Head of Department; employee salary (effective-dated, restricted); tag master and project tagging; monthly allocation matrix with bench view; effort/cost engine; revenue target by project/tag/organization; project profitability; tag-wise financial analysis; export |
| **Needs confirmation** | Items D-R2-01 to D-R2-15 (B12). Notably: revenue basis, planned vs actual cost basis, S/H meaning, non-salary and shared costs, tag governance, HoD authority |

## B5. Roles and Permissions (proposed)

Capabilities follow the existing pattern `<area>.<action>[:scope]`. **Code must check capabilities, never role names.**

| Capability (new) | Owner | Finance | Operations | Project Manager | Team Lead | HoD (scope of role) | Employee / Sales |
|---|---|---|---|---|---|---|---|
| `employees.view` (name, department, title) | all | all | all | assigned | team | team/department | — |
| `employees.manage` (create/edit, department, HoD) | all | — | — | — | — | — | — |
| `salary.view` (existing) / `salary.manage` | view+manage | view+manage | — | — | — | not by default | — |
| `departments.manage` | all | — | all | — | — | — | — |
| `tags.manage` | all | all | all | — | — | — | — |
| `projects.tag` (assign tags) | all | all | all | assigned | — | — | — |
| `allocation.view` | all | all | all | assigned | team | department | own (read) |
| `allocation.manage` | all | — | all | assigned | — | — | — |
| `settings.costing` (hours, hourly rate) | all | all | view | — | — | — | — |
| `cost.view` (₹ cost, profit) | all | all | — | — | — | — | — |
| `effort.view` (hours only, no ₹) | all | all | all | assigned | team | department | own |
| `revenue.target.manage` | all | all | — | — | — | — | — |
| `revenue.target.view` | all | all | view | assigned | — | — | — |
| `reports.profitability` | all | all | — | — | — | — | — |

Rules: users without `salary.view` or `cost.view` never receive salary, cost or profit values from the API (server-side masking, not just hidden columns). The platform administrator has no access to any of this data.

## B6. Functional Requirements and Acceptance Criteria

### A. Employee and department management
| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-R2-A1 | Maintain employees (name, email, title, department, status, monthly salary) | Authorised user can create/edit; salary field absent in API responses for others |
| FR-R2-A2 | Maintain departments with one Head of Department | HoD must be an active employee; changing HoD is audited |
| FR-R2-A3 | Each employee belongs to exactly one department | Saving without a department is refused |
| FR-R2-A4 | Salary changes are effective-dated and audited | Changing salary never alters previously closed months |
| FR-R2-A5 | Employee list shows total allocation % and bench status | Allocation 0% → "Bench"; 100% → "Fully allocated"; >100% impossible |

### B. Project and tag management
| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-R2-B1 | Maintain tag master (name, optional type) | Duplicate names refused (case-insensitive) |
| FR-R2-B2 | Assign one or more tags to a project | Tags editable by `projects.tag`; change audited |
| FR-R2-B3 | Filter projects and every financial report by one or more tags | Filter result totals equal the sum of the listed projects |
| FR-R2-B4 | Tag totals are *not additive* when projects carry several tags | Report shows a note; optional "primary tag" gives an additive roll-up |
| FR-R2-B5 | Existing project `category` remains | Category and tags can be combined in filters |

### C. Employee–project allocation
| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-R2-C1 | Allocate % of an employee's month to each project; an employee may be on many projects | Matrix of employees × projects per month |
| FR-R2-C2 | An employee's total in a month must not exceed 100% | Entry over 100% is rejected with a clear message |
| FR-R2-C3 | Under-allocation is reported as bench capacity (hours and salary) | Bench report lists employee, free %, free hours, unabsorbed salary |
| FR-R2-C4 | Allocation is per month and can be copied forward | New month starts from previous month on request |
| FR-R2-C5 | Allocation to a project requires the employee to be an active member of the project team | Adding allocation adds the person to the team |

### D. Organization and project configuration
| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-R2-D1 | Organization default **monthly working hours** = 160 | Editable by `settings.costing`; change audited; affects open months only |
| FR-R2-D2 | Organization default **standard hourly rate** = ₹250 | Stored in paise; currency shown |
| FR-R2-D3 | **Hourly rate** may be overridden per project (recommended interpretation) | Override shown with an indicator; blank = inherit |
| FR-R2-D4 | **Monthly hours** may be overridden per employee (part-time) (recommended interpretation) | Override shown; effort uses the override |
| FR-R2-D5 | Settings are versioned by month | Past months are not recalculated silently |

### E. Effort and cost calculation — see B7. Acceptance criteria use the corrected baseline (B3.1):
- With the baseline allocations, total effort is **1,760 h**, standard value **₹4,40,000**, allocated salary cost **₹2,00,000**, unallocated **₹60,000**.
- Changing one allocation updates employee, project and tag views consistently.
- Calculations are available **by employee, by project and by tag**.

### F. Revenue and profitability
| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-R2-F1 | Define revenue target per project, per tag and for the organization, per month | Target optional per project; organization total = sum of project targets unless an organization target is set separately |
| FR-R2-F2 | Show target vs standard value vs cost vs profit per project | Matches B7 formulas |
| FR-R2-F3 | Project profitability = revenue basis − salary cost (− optional other direct costs) | Revenue basis selectable (D-R2-01); shown on every report |
| FR-R2-F4 | Tag-wise analysis with drill-down to projects | Drill-down rows sum to the tag total |
| FR-R2-F5 | Unallocated salary cost shown separately and never hidden | Appears as its own line on the organization view |
| FR-R2-F6 | Missing data warnings (no target, no allocation, no salary) | Warning chip instead of a misleading zero |
| FR-R2-F7 | Export to CSV/Excel with formulas disclosed | Export respects the caller's masking |

## B7. Calculation Rules and Formulas (proposed; validate with the accountant)

Definitions per month *m*. `a(e,p)` = allocation fraction of employee *e* on project *p*. `H(e)` = monthly hours of *e* (org default 160 unless overridden). `S(e)` = monthly salary. `R(p)` = hourly rate (org default ₹250 unless overridden for *p*).

| Measure | Formula |
|---|---|
| Effort hours (e, p) | `a(e,p) × H(e)` |
| Salary cost (e, p) | `a(e,p) × S(e)` |
| Project effort / cost | sum over employees |
| Standard value of effort (p) | `Σ_e effort(e,p) × R(p)` |
| Project margin (p) | `revenue basis(p) − salary cost(p) − other direct cost(p)` (other direct cost optional) |
| Margin % | `margin ÷ revenue basis` (blank when revenue basis is 0) |
| Employee allocated % | `Σ_p a(e,p)` (must be ≤ 100%) |
| Bench (e) | `(1 − Σ_p a(e,p))`; bench hours = `bench × H(e)`; bench cost = `bench × S(e)` |
| Cost per hour (e) | `S(e) ÷ H(e)` (informational) |
| Tag totals (t) | sum over projects carrying tag *t* (overlap allowed; non-additive) |
| Organization totals | sums over projects **plus** a separate "unallocated salary" line |
| Target achievement | `standard value ÷ revenue target` (planned view); later `actual revenue ÷ target` |

**Worked example (fictional "Lumen Academy Platform", reproduces workbook project 1):** allocations 25%, 50%, 75% and 100% of four employees earning ₹30,000, ₹20,000, ₹20,000 and ₹20,000. Effort = 40 + 80 + 120 + 160 = **400 h**. Value = 400 × ₹250 = **₹1,00,000**. Cost = 7,500 + 10,000 + 15,000 + 20,000 = **₹52,500**. Margin = **₹47,500 (47.5%)**.

## B8. Data Requirements (logical; Cursor decides the physical design from the code)

| Entity | Key fields | Reuse / change |
|---|---|---|
| Department | id, tenant, name, head_employee, status | New |
| Employee (extends Membership) | department, monthly_salary_minor (restricted), salary_effective_from, hours_override | Extend existing `Membership`; salary history table recommended |
| Tag, ProjectTag | tag id, name, type; project–tag link | New |
| Project | + rate_override_minor (nullable) | Extend existing `Project` |
| Allocation | tenant, employee, project, month, percent | Extend/replace use of `ProjectMember.allocation_pct` (add month) |
| Costing settings | tenant, month, monthly_hours, hourly_rate_minor | Extend tenant settings; versioned by month |
| RevenueTarget | tenant, level (organization/project/tag), reference, month, amount_minor, owner | New (planned in the earlier roadmap) |
| Other cost (optional layer) | tenant, project, category, month, amount_minor | Decision D-R2-06; categories per the Targets sheet |

All money in integer minor units (paise); every amount carries a currency.

## B9. Validation Rules

- Allocation per cell 0–100 (steps of 1); employee total per month ≤ 100%.
- Salary > 0 and ≤ configured ceiling; hours 1–300 per month; hourly rate > 0.
- Department and Head of Department must be active; HoD must belong to that department.
- Tag name 1–40 characters, unique per tenant (case-insensitive); a tag in use cannot be deleted, only archived.
- Revenue target ≥ 0; one target per level, reference and month.
- Closed months are read-only except through an audited reopen.
- Calculations never divide by zero: show "—" and a data-quality note.

## B10. Dashboards and Reports

| Report | Audience | Content |
|---|---|---|
| Organization costing summary | Owner, Finance | Hours, standard value, allocated cost, bench cost, margin, % |
| Employee effort and cost | Owner, Finance (₹); Ops/PM/TL (hours only) | Allocation %, hours, cost, cost per hour, bench |
| Project profitability | Owner, Finance | Target, value, cost, margin, warnings |
| Tag-wise financial analysis | Owner, Finance | Projects, hours, cost, value, margin per tag; drill-down |
| Bench / capacity | Owner, Finance, Operations | Free % and hours per employee |
| Excel reconciliation (one-time) | Owner, Finance | Workbook vs system totals |

## B11. Dependencies and Assumptions

- Revision 2 relies on the existing multi-tenant, role and entitlement engine (no change).
- Sprint 2 timesheets provide *actual* hours; the planned cost model does not depend on them.
- Assumed single currency (INR) and a monthly period.
- Employee names, salaries, department membership and project tags in the prototype are illustrative; the business owner supplies real data at implementation.
- No payroll integration, tax or statutory cost (PF, bonus) is included unless confirmed (D-R2-12).

## B12. Open Business Decisions (recommended interpretation shown; approval needed)

| ID | Question | Recommended interpretation |
|---|---|---|
| D-R2-01 | What is "revenue" for profitability: standard value (hours × rate), revenue target, or actual invoiced/collected? (links to earlier decision 4) | Show **standard value** as "Planned value" and **targets** separately; add actual revenue when invoicing is built |
| D-R2-02 | Confirm the corrected workbook totals (cost ₹2,00,000, not ₹3,07,500) | Accept the corrected formula (B3.2) |
| D-R2-03 | Cost basis: planned (allocation × salary, as in Excel) or actual (approved hours × hourly cost) | Planned by default; actual shown as comparison once timesheets exist |
| D-R2-04 | Meaning of `S` and `H` day markers (earlier decision 3). Observed: `S` falls on every Sunday of November 2026; `H` on four other days | Treat as `S` = weekly off, `H` = holiday, **pending confirmation**; configurable |
| D-R2-05 | Is ₹250 a customer billing rate, an internal charge-out rate or a cost rate? | Label as "Standard hourly rate (internal value of effort)" |
| D-R2-06 | Are non-salary cost categories (infrastructure, third-party, software, marketing, sales, consulting) part of profitability? | Optional layer, off by default |
| D-R2-07 | Allocation method for shared costs (rent, Wi-Fi, AI tools, hosting) | Defer; proposed equal share or by effort hours |
| D-R2-08 | Tag governance: free text or managed list; one or many tags per project | Managed list; many tags; non-additive totals plus optional primary tag |
| D-R2-09 | Authority of Head of Department: view only, or approve allocations/timesheets? Can HoD see salaries? | View only; no salary unless granted |
| D-R2-10 | Can an employee belong to more than one department? | No |
| D-R2-11 | Over-allocation above 100%: block or allow with approval? | Block |
| D-R2-12 | Salary meaning: gross monthly salary or cost-to-company (incl. benefits)? | Monthly cost-to-company, effective-dated |
| D-R2-13 | Is 160 hours flat for every month or derived from working days (the workbook's November calendar implies 21 working days ≈ 168 h)? | Flat 160 default; calendar option later |
| D-R2-14 | Revenue targets: which levels and period? | Project, tag and organization; monthly |
| D-R2-15 | Should department-level profitability be reported (department vs project cost)? | Not in this revision; can be added |

## B13. Handoff to Cursor

See `docs/Cursor_Handoff_Revision2.md`. Cursor must analyze this PRD against the actual codebase, make technical decisions from the code, reuse existing architecture, identify migration and backward-compatibility needs, avoid unnecessary refactoring and preserve working functionality unless this PRD requires a change.

## B14. Impact on the Iteration Plan (indicative; confirm after review)

Earlier Sprint 3 (money) and Sprint 4 (hardening) are **on hold**. Proposed re-plan, each iteration shipping web screens, API, tests and a demo video:

| Iteration | Scope | Depends on |
|---|---|---|
| R2-I1 Masters | Departments and HoD, employee salary (restricted), tags, costing settings | Approval of D-R2-09/10/12 |
| R2-I2 Allocation and cost | Monthly allocation matrix, over-allocation rule, bench, effort/cost by employee, project and tag | R2-I1; D-R2-03/05/13 |
| R2-I3 Targets and profitability | Revenue targets, project profitability, tag analysis, exports, workbook reconciliation | R2-I2; D-R2-01/02/14 |
| Later (re-planned) | Non-salary and shared costs, actual-vs-planned using timesheets, invoices, performance matrix, Backblaze attachments, AI assistant, hardening | Decisions D-R2-06/07 and business priorities |
