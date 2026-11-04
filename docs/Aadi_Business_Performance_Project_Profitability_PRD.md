# Aadi Technology — Business Performance & Project Profitability Platform
## Product Requirements Document (PRD)
**Version:** 0.1 — Initial customer-input-based draft  
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
- BR-015: Source workbook daily markers S/H must remain undefined until the customer confirms their meaning.

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
3. What do daily calendar markers `S` and `H` mean in the November sheet?
4. What is the revenue definition: invoiced, collected, recognized, milestone-based or manually reported?
5. Are targets set at organization, customer, project, employee, sales owner or all levels?
6. How should salary be allocated: actual salary/working hours, standard hourly cost rate, percentage allocation or manual?
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
