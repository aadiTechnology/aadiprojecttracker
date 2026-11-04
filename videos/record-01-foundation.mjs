/**
 * Sprint 1 demo video: sign-in with demo accounts, role-based dashboards, customers, projects across the four Aadi business
 * areas, organization admin, and what each role cannot see. Run against a freshly seeded RECORDING database.
 */
import { assertNoSecret, apiProbe, click, nav, origin, scroll, signInViaDemoList, signOut, typeSlow } from './common.mjs'
import { recordVideo } from './lib.mjs'

const NAME = '01-sprint-1-foundation-and-projects'
const scenes = [
  {
    chapter: 'Chapter 1 - Sign in', title: 'Demo accounts for every role',
    narration: 'Welcome to Sprint one of Aadi Project Tracker. The sign in page lists test users for every role, so a reviewer can try the product without asking for credentials. Each account sees different data. These accounts exist only in the demo environment, and all data is fictional.',
    actions: 'Open the sign-in page and scroll the demo accounts.', expected: 'Sign-in form with demo accounts listed below it.',
    run: async (page) => { await page.goto(origin + '/', { waitUntil: 'domcontentloaded' }); await page.getByRole('heading', { name: 'Demo accounts (test users for every role)' }).waitFor(); await scroll(page, 700, 7) },
  },
  {
    chapter: 'Chapter 2 - Owner', title: 'Owner dashboard',
    narration: 'We sign in as Priya Rao, the C E O. The dashboard shows projects across the whole organization, delivery health, total budget and contract value, plus open decisions the customer still has to make, such as the revenue basis.',
    actions: 'Use Priya Rao and sign in.', expected: 'Owner dashboard.',
    run: async (page) => { await signInViaDemoList(page, 'Priya Rao'); await page.getByRole('heading', { name: 'Overview Dashboard' }).waitFor(); await scroll(page, 500, 4) },
  },
  {
    chapter: 'Chapter 3 - Projects', title: 'Four business areas',
    narration: 'Projects are grouped into the four areas of Aadi Technology: software development of our own products, software services for customers, marketing, and sales. We filter to marketing, then to sales.',
    actions: 'Open Projects and filter by category.', expected: 'Filtered project lists.',
    run: async (page) => {
      await nav(page, 'Projects')
      await page.getByLabel('Category').selectOption('Marketing'); await page.waitForTimeout(1200)
      await page.getByLabel('Category').selectOption('Sales'); await page.waitForTimeout(1200)
      await page.getByLabel('Category').selectOption('')
    },
  },
  {
    chapter: 'Chapter 3 - Projects', title: 'Project detail',
    narration: 'Opening a project shows its status, health, customer, budget, scope, team with allocation, milestones and the scope change history. Every scope change records the requester and the approver.',
    actions: 'Open Supply Tracker and review tabs.', expected: 'Project detail modal.',
    run: async (page) => {
      await click(page.getByRole('button', { name: 'Supply Tracker' }))
      await page.getByRole('dialog').waitFor(); await page.waitForTimeout(1500)
      await click(page.getByRole('tab', { name: 'Team' })); await page.waitForTimeout(1500)
      await click(page.getByRole('tab', { name: 'Milestones' })); await page.waitForTimeout(1500)
      await click(page.getByRole('tab', { name: 'Scope changes' })); await page.waitForTimeout(2000)
    },
  },
  {
    chapter: 'Chapter 3 - Projects', title: 'Approve a scope change',
    narration: 'A scope change was requested by the project manager for geofence alerts. The owner approves it, and the approval is added to the scope and to the audit log. A requester cannot approve their own change.',
    actions: 'Approve the scope change.', expected: 'Status Approved.',
    run: async (page) => {
      await click(page.getByRole('button', { name: 'Approve', exact: true }))
      await page.getByText('Approved').first().waitFor(); await page.waitForTimeout(1200)
      await page.keyboard.press('Escape')
    },
  },
  {
    chapter: 'Chapter 4 - Create', title: 'Create a project with rules',
    narration: 'We create a new marketing project for the internal marketing unit. Every project needs a customer or internal business unit. The project starts as a draft, and the system refuses to activate it until a project manager and a scope exist.',
    actions: 'Create the project, then try to activate.', expected: 'Draft project; activation refused.',
    run: async (page) => {
      await click(page.getByRole('button', { name: '+ New project' }))
      const d = page.getByRole('dialog')
      await typeSlow(d.getByLabel('Project name'), 'Diwali Campaign 2026')
      await d.getByLabel('Category').selectOption('Marketing')
      await d.getByLabel('Customer / business unit').selectOption({ label: 'Aadi Marketing & Sales (internal)' })
      await d.getByLabel('Budget (₹)').fill('250000')
      await click(d.getByRole('button', { name: 'Create project' }))
      await page.getByText('Project created as Draft').waitFor()
      await click(page.getByRole('button', { name: 'Diwali Campaign 2026' }))
      await click(page.getByRole('button', { name: 'Active', exact: true }))
      await page.getByText('Before activating').waitFor(); await page.waitForTimeout(2200)
      await page.keyboard.press('Escape')
    },
  },
  {
    chapter: 'Chapter 5 - Customers and admin', title: 'Customers',
    narration: 'The customer register holds customers and internal business units, with the account owner. Billing details are visible only to roles that manage customers or invoices.',
    actions: 'Open Customers.', expected: 'Customer table.',
    run: async (page) => { await nav(page, 'Customers'); await page.waitForTimeout(2500) },
  },
  {
    chapter: 'Chapter 5 - Customers and admin', title: 'People, roles and audit',
    narration: 'Under organization admin the owner manages people and roles. Permissions are data, not code, and every change is audited. Here is the audit log, showing the scope approval and project creation we just did.',
    actions: 'Open Organization Admin, Roles & permissions, Audit log.', expected: 'Admin tabs.',
    run: async (page) => {
      await nav(page, 'Organization Admin'); await page.waitForTimeout(1800)
      await click(page.getByRole('tab', { name: 'Roles & permissions' })); await page.waitForTimeout(2000)
      await click(page.getByRole('tab', { name: 'Audit log' })); await page.waitForTimeout(2500)
    },
  },
  {
    chapter: 'Chapter 6 - Role views', title: 'Project manager sees only assigned work',
    narration: 'Now Asha Kulkarni, a project manager. Her project list contains only the projects she is assigned to, and menu items her role does not include are locked, with an explanation.',
    actions: 'Sign in as Asha Kulkarni.', expected: 'Assigned projects only.',
    run: async (page) => { await signOut(page); await signInViaDemoList(page, 'Asha Kulkarni'); await nav(page, 'Projects'); await page.waitForTimeout(2500); await page.getByRole('navigation').getByRole('link', { name: 'Expenses & Cost' }).click({ force: true }); await page.getByText('Access restricted').first().waitFor(); await page.waitForTimeout(2000) },
  },
  {
    chapter: 'Chapter 6 - Role views', title: 'Sales sees contract value only',
    narration: 'Kabir Sethi from sales sees only the customers he owns, and for those projects only the contract value. There is no budget, no internal cost and no effort estimate.',
    actions: 'Sign in as Kabir Sethi.', expected: 'Contract value column only.',
    run: async (page) => { await signOut(page); await signInViaDemoList(page, 'Kabir Sethi'); await nav(page, 'Projects'); await page.waitForTimeout(3000) },
  },
  {
    chapter: 'Chapter 6 - Role views', title: 'Employee blocked at the API',
    narration: 'An employee, Meera Nair, has no project list. This is enforced by the server, not just hidden in the menu. A direct call to the projects service is refused with a forbidden status.',
    actions: 'Sign in as Meera Nair and call the API directly.', expected: 'HTTP 403.',
    run: async (page) => {
      await signOut(page); await signInViaDemoList(page, 'Meera Nair')
      await page.getByRole('heading', { name: 'Overview Dashboard' }).waitFor(); await page.waitForTimeout(1500)
      await apiProbe(page, 'GET /api/projects as Employee', '/api/projects'); await page.waitForTimeout(3500)
    },
  },
  {
    chapter: 'Chapter 7 - Platform', title: 'Platform administrator',
    narration: 'The SaaS platform administrator manages organizations and module entitlements only. Direct calls for projects or customers are refused, so tenant business data is not exposed to the platform.',
    actions: 'Sign in as the platform admin and probe the API.', expected: 'Tenants table; HTTP 403.',
    run: async (page) => {
      await signOut(page); await click(page.getByRole('button', { name: 'Use Platform Admin' })); await click(page.getByRole('button', { name: 'Sign in', exact: true }))
      await page.getByRole('heading', { name: 'Tenants & entitlements' }).waitFor(); await page.waitForTimeout(2200)
      await apiProbe(page, 'GET /api/projects as Platform Admin', '/api/projects'); await page.waitForTimeout(3500)
    },
  },
  {
    chapter: 'Chapter 8 - Wrap up', title: 'What is next',
    narration: 'Sprint one delivers the foundation: sign in, roles and permissions, organizations and entitlements, customers, projects, scope changes and audit. Sprint two adds sprints, tasks, handover and timesheets, together with the first version of the mobile app. Revenue targets, expenses and invoices follow in sprint three.',
    actions: 'Closing summary.', expected: 'Sign-in page.',
    run: async (page) => { await page.evaluate(() => sessionStorage.clear()); await page.goto(origin + '/'); await page.waitForTimeout(2500) },
  },
]

await recordVideo({ name: NAME, scenes, check: assertNoSecret, password: undefined })
