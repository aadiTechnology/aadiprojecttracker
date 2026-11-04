# Claude Prompt — Generate Role-Based Application Proposal HTML
## Project: Aadi Technology Business Performance & Project Profitability Platform

You are acting as a Senior Product Designer, Business Analyst and Solution Architect.

### Context
Read the complete PRD file:
`Aadi_Business_Performance_Project_Profitability_PRD.md`

If the original workbook `Aadi Technology Matrix.xlsx` is available, inspect it as a source reference. The PRD distinguishes supplied customer inputs from inferred recommendations and open decisions. Preserve those distinctions.

### Objective
Create a polished, interactive, standalone HTML proposal that Aadi Technology can show to the customer to explain:
1. What application is being proposed.
2. Which user roles will use it.
3. What each role can see and do.
4. How the modules connect to the customer's stated expectations:
   - Matrix/Invoice – Employee Performance
   - Sprint Planning – To team transition
   - Target – Revenue
   - Timesheet – To capture details
5. How the proposed workflow connects Revenue → Customer/Project → Sprint/Tasks → Employee → Timesheet → Cost → Invoice → Performance.

This is a customer-facing product proposal/prototype, NOT a production application.

### Required output
Create:
`Aadi_Role_Based_Feature_Proposal.html`

The HTML must be self-contained:
- Inline CSS and JavaScript.
- No build step.
- No backend/API dependency.
- No external libraries or CDN dependencies.
- Works by opening the HTML file in a modern desktop browser.
- Responsive for desktop, tablet and mobile.
- Use realistic but clearly labelled illustrative sample data.
- Do not use real employee/customer financial data from the workbook in the demo unless explicitly marked as sample and approved. Prefer fictional names and values.

### Design direction
Create a professional modern SaaS admin experience:
- Light theme, clean neutral background, restrained accent colors.
- Strong information hierarchy, readable typography, consistent spacing.
- Sidebar navigation and top header.
- Attractive dashboard cards, tables, status chips, progress bars and charts drawn with CSS/SVG or native HTML.
- Avoid excessive gradients, oversized cards and decorative clutter.
- Make it look like a credible B2B SaaS product proposal.
- Add a clear label: “Interactive Product Proposal — Illustrative Data”.

### Main interaction: Role selector
At the top of the application provide a prominent role switcher. Changing the selected role must dynamically update:
- Dashboard summary cards.
- Sidebar navigation.
- Available modules.
- Feature descriptions.
- Table columns/data visibility.
- Actions and permissions.
- Example workflow relevant to that role.

Include these proposed roles:

1. **Organization Owner / CEO**
   - Overall revenue target vs actual
   - Customer/project profitability
   - Total costs and overhead
   - Active projects and delivery health
   - Employee utilization summary
   - Invoice outstanding
   - Business risk/variance alerts
   - Organization-level reports

2. **Finance Manager**
   - Revenue entries and target monitoring
   - Expense categories and cost allocation
   - Salary cost visibility (restricted)
   - Customer/project financial summaries
   - Invoice preparation, approval and payment status
   - Receivables and overdue invoices
   - Financial exports and reconciliation

3. **Operations / Delivery Manager**
   - Project portfolio and status
   - Project scope, capacity and planned effort
   - Sprint health and blocked work
   - Employee allocation and workload
   - Handover tracking
   - Estimate vs actual effort
   - Delivery reports

4. **Project Manager**
   - Assigned projects only
   - Scope, milestones and project budget visibility as permitted
   - Sprint planning and backlog
   - Task creation, assignment and reassignment
   - Handover initiation and acknowledgement status
   - Timesheet review for delegated team
   - Project progress and effort variance

5. **Team Lead**
   - Team sprint board
   - Team member assignments and capacity
   - Task progress and blockers
   - Handover review
   - Timesheet review if delegated
   - Team delivery indicators
   - No unrestricted organization financial or salary access

6. **Employee / Contributor**
   - My tasks and deadlines
   - My sprint commitments
   - Daily work log and timesheet
   - Submit timesheet and see approval status
   - Update task status and add work notes
   - Receive/acknowledge handover
   - Personal goals and own performance summary
   - No access to other employees' salary or confidential performance reviews

7. **Sales / Business Development**
   - Assigned customers and opportunities
   - Revenue target and achievement
   - Expected deal/project revenue
   - Follow-up reminders
   - Won opportunities converted to projects
   - Sales performance reports
   - No access to salary and restricted cost details

8. **SaaS Platform Administrator** (platform-level, separate from customer tenant)
   - Tenant/organization list and status
   - Subscription/entitlement overview
   - Platform health and usage summary
   - Support access only through controlled, audited process
   - No default access to tenant business content

Optional HR/People Manager role may be shown as “Optional / customer decision” with employee capacity, leave/availability and review administration. Do not imply it is confirmed MVP scope.

### Role-wise feature matrix
Create a dedicated “Role & Permission Matrix” view:
- Rows: modules/features.
- Columns: roles.
- Cell values: Full, Manage, View, Own, Delegated, No Access.
- Use a legend.
- Include a short explanation that final permissions are configurable and enforced by backend APIs.
- Make the matrix horizontally scrollable on smaller screens.

Include at least these modules:
- Organization & User Administration
- Customer / Business Register
- Project & Scope Management
- Sprint & Task Planning
- Team Transition / Handover
- Timesheet Entry
- Timesheet Approval
- Employee Performance
- Revenue Targets
- Expense & Cost Allocation
- Invoice Management
- Executive / Financial / Delivery Reports
- AI Management Assistant

### Required screens / navigation
Build working navigation (client-side tab switching) for:
1. Overview Dashboard
2. Projects
3. Sprint Planning
4. Team Handover
5. Timesheets
6. Employee Performance
7. Revenue Targets
8. Expenses & Cost
9. Invoices
10. Role & Permission Matrix
11. Product Workflow
12. Assumptions & Decisions

The content of each view must change appropriately for the selected role. Hide unauthorized navigation items or show them disabled with a clear “Access restricted” explanation; do not show confidential data to unauthorized roles.

### Dashboard requirements
Create different illustrative dashboards per role:
- CEO: revenue target/actual, total expenses, contribution, active projects, invoice outstanding, delivery alerts.
- Finance: revenue, expenses by category, project cost, invoice status and receivables.
- Operations: active projects, sprint completion, overdue tasks, workload and effort variance.
- Project Manager: project budget/effort, sprint progress, tasks by status, team assignments and handovers.
- Team Lead: team workload, sprint board, blocked tasks and pending timesheets.
- Employee: assigned tasks, due today, hours logged this week, timesheet approval status and personal goals.
- Sales: target vs achieved, opportunities, forecast and follow-ups.
- Platform Admin: active tenants, plan distribution, usage and platform alerts only.

Use sample data clearly marked “Illustrative”. Do not present sample financial values as customer actuals.

### Key workflow visualization
Create a visually clear workflow/timeline:
1. Revenue target is defined.
2. Customer/project is created.
3. Scope and deliverables are defined.
4. Sprint and tasks are planned.
5. Employees are assigned.
6. Work is recorded in timesheets.
7. Manager approves timesheets.
8. Actual effort and cost are calculated.
9. Invoice is prepared/issued by Finance.
10. Management reviews revenue, cost, margin and employee/project performance.

Show which roles participate at each step.

### Customer-input mapping
Include a section mapping the customer's original four notes to proposed capabilities:
- Matrix/Invoice – Employee Performance → employee contribution matrix, project/customer cost matrix, invoice preparation/tracking (mark exact invoice scope as requiring confirmation).
- Sprint Planning – To team transition → sprint planning, task assignment, reassignment and auditable handover.
- Target – Revenue → target setup and actual-vs-target dashboard.
- Timesheet – To capture details → work logs, time entry, approval and estimate-vs-actual.

### Assumptions & decisions view
Clearly list unresolved questions:
- Meaning of daily S/H markers in November planning sheet.
- Meaning of “Matrix/Invoice”.
- Whether invoice PDF/GST/tax workflows are required.
- Revenue basis: invoiced, collected, recognized or milestone-based.
- How salary and shared overhead are allocated.
- Whether revenue targets apply at organization, customer, project, employee or sales-owner level.
- Whether native mobile app is required.
- Final role hierarchy and approval delegation.

Provide recommended defaults as proposals only; do not silently mark them approved.

### Interaction and quality requirements
- Role selector works.
- Sidebar navigation works.
- Role/permission matrix can be viewed and filtered by module or role.
- Search/filter controls should work where shown.
- Tabs, dropdowns and buttons must have meaningful demo behavior.
- Provide tooltips or short descriptions for less obvious financial metrics.
- Include empty states where appropriate.
- Ensure accessible labels, keyboard focus states and semantic HTML.
- No dead buttons. If an action is illustrative only, show a toast/modal explaining that this is a proposal prototype and no data is saved.
- Do not create login credentials or pretend authentication is real.
- Do not invent customer approvals, legal compliance claims or confirmed requirements.

### Important product governance
Follow the Aadi Three-Pillar strategy from the PRD:
- Pillar 1: Software Product — operational management and profitability.
- Pillar 2: Marketing & Sales — lightweight opportunity and revenue conversion visibility; do not build a full CRM without approval.
- Pillar 3: AI Solutions — advisory insights only, permission-aware and human-reviewed.
Show each feature's pillar where useful.

### Final validation before delivery
1. Confirm all eight roles are represented.
2. Confirm role switching changes dashboard, navigation and access.
3. Confirm the role matrix includes all listed modules and roles.
4. Confirm all four customer notes are mapped.
5. Confirm assumptions are visible.
6. Confirm sample data is labelled illustrative.
7. Confirm no unauthorized role can see restricted financial/salary content in the prototype.
8. Confirm the HTML opens locally without external dependencies.
9. Return the exact output path and a short summary of what was created.
10. Do not start backend or production implementation; this deliverable is for customer discussion and scope validation.
