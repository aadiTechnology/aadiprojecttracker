/** Sprint 4 user manual video: expenses and shared costs, invoices (draft, approve, issue, collect), planned vs actual, contribution and the performance matrix.
 * Needs a freshly seeded database (demo data now includes Sprint 4 records). Roles: Finance Manager, CEO, an employee. */
import { apiProbe, assertNoSecret, click, nav, origin, scroll, signInViaDemoList, signOut, typeSlow } from './common.mjs'
import { recordVideo } from './lib.mjs'

const NAME = '06-sprint-4-finance-and-performance-user-manual'
const as = async (page, name) => { await signInViaDemoList(page, name); await page.getByRole('heading', { name: 'Overview Dashboard' }).waitFor(); await page.waitForTimeout(1200) }
const tab = async (page, name) => { await click(page.getByRole('tab', { name, exact: true })); await page.waitForTimeout(2600) }
const btn = async (page, name, wait = 2200) => { await click(page.getByRole('button', { name })); await page.waitForTimeout(wait) }

const scenes = [
  { chapter: 'Chapter 1 - Where things are', title: 'The finance and performance menu',
    narration: 'This is the user manual for Sprint four of Aadi Project Tracker. It covers expenses and shared costs, invoices and receivables, planned against actual hours, project contribution, and the employee performance matrix. We sign in as Sameer Joshi, the Finance Manager. Under Finance and Performance, the menu now lists Planned versus Actual, Expenses, Invoices and Employee Performance. Each person sees only the items their role allows.',
    actions: 'Sign in as Sameer Joshi.', expected: 'Menu with Finance & Performance group.',
    run: async (page) => { await page.goto(origin + '/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(1500); await as(page, 'Sameer Joshi'); await page.waitForTimeout(3000); await scroll(page, 300, 2).catch(() => {}); await page.waitForTimeout(3500) } },
  { chapter: 'Chapter 2 - Expenses', title: 'Expenses and where the money goes',
    narration: 'Open Expenses and Cost. Pick a month at the top. The cards show the total, what is charged directly to one project, shared overhead, and what is not paid yet. The bars show spend by category, such as infrastructure, software, consulting and rent. Salary cost is not repeated here, because it already comes from allocation.',
    actions: 'Open Expenses & Cost.', expected: 'KPIs and category bars.',
    run: async (page) => { await nav(page, 'Expenses & Cost'); await page.waitForTimeout(6500) } },
  { chapter: 'Chapter 2 - Expenses', title: 'Shared costs are split and reconciled',
    narration: 'Some costs belong to everyone, such as servers, AI subscriptions and rent. Each shared expense carries its own split method: equal share, in proportion to planned hours, or in proportion to people. The table on the right shows the cost charged to each project, direct plus its share. The split is in whole paise, so the total charged always equals the source expense.',
    actions: 'Scroll to the project allocation table.', expected: 'Cost charged to each project.',
    run: async (page) => { await scroll(page, 280, 3); await page.waitForTimeout(6500); await scroll(page, 500, 3); await page.waitForTimeout(4500) } },
  { chapter: 'Chapter 2 - Expenses', title: 'Add an expense',
    narration: 'To add an expense choose Add expense. We record a shared cloud backup subscription. Choose the category, amount, vendor and date. Leave Charged to as shared by all projects and split it by planned hours. Save, and the cards and the project table update straight away.',
    actions: 'Add a shared expense.', expected: 'New row and updated totals.',
    run: async (page) => {
      await scroll(page, -2000, 2); await page.waitForTimeout(800)
      await btn(page, '+ Add expense', 1200)
      await page.getByLabel('Category').selectOption('Software'); await page.waitForTimeout(500)
      await typeSlow(page.getByLabel('Amount (₹)'), '7500'); await typeSlow(page.getByLabel('Vendor'), 'Cloud backup service'); await typeSlow(page.getByLabel('Note'), 'Nightly backups for all products')
      await page.waitForTimeout(2500)
      await btn(page, 'Save expense', 4500)
    } },
  { chapter: 'Chapter 3 - Invoices', title: 'Invoice list and receivables',
    narration: 'Open Invoices. The cards show invoiced, collected, outstanding and overdue, and they are never called revenue. The tabs filter by status: draft, approved, issued, partially paid, paid and overdue. Overdue invoices show how many days they are late.',
    actions: 'Open Invoices, filter Overdue.', expected: 'Invoice list.',
    run: async (page) => { await nav(page, 'Invoices'); await page.waitForTimeout(5500); await tab(page, 'Overdue'); await page.waitForTimeout(3000); await tab(page, 'All') } },
  { chapter: 'Chapter 3 - Invoices', title: 'Open an invoice',
    narration: 'Open shows the customer, billing details, every line, tax, total, who drafted and who approved it, and each payment with its reference. Tax is whatever you enter on the invoice. The product does not assume a statutory rate.',
    actions: 'Open the first paid or part paid invoice.', expected: 'Invoice detail.',
    run: async (page) => { await page.getByRole('button', { name: 'Open' }).first().click(); await page.waitForTimeout(7500); await page.keyboard.press('Escape'); await page.waitForTimeout(1200) } },
  { chapter: 'Chapter 3 - Invoices', title: 'Draft a new invoice',
    narration: 'To bill a customer, choose New invoice. Pick the project, the dates, and add lines. The subtotal, tax and total update as you type. Saving creates a draft. A draft cannot be issued yet: it must be approved by someone with approval rights.',
    actions: 'Create a draft invoice.', expected: 'Draft in the list.',
    run: async (page) => {
      await btn(page, '+ New invoice', 1200)
      const sel = page.getByLabel('Project'); const opt = await sel.locator('option').nth(3).getAttribute('value'); await sel.selectOption(opt); await page.waitForTimeout(600)
      await typeSlow(page.getByLabel('Description').first(), 'Sprint demo and release support'); await typeSlow(page.getByLabel('Amount (₹)').first(), '25000')
      await page.waitForTimeout(3500)
      await btn(page, 'Save draft', 4500)
      await tab(page, 'Draft')
    } },
  { chapter: 'Chapter 3 - Invoices', title: 'Approval by the CEO',
    narration: 'Finance prepares, the CEO approves. We sign in as Priya Rao and open Invoices on the Draft tab. Approve moves the draft to approved, and the person who drafted it is notified. If Sameer tried to approve his own draft, the server would refuse and record the attempt in the audit trail.',
    actions: 'Sign in as Priya Rao, approve the draft.', expected: 'Status Approved.',
    run: async (page) => { await signOut(page); await as(page, 'Priya Rao'); await nav(page, 'Invoices'); await page.waitForTimeout(2500); await tab(page, 'Draft'); await page.getByRole('button', { name: 'Approve' }).first().click(); await page.waitForTimeout(4500); await tab(page, 'Approved') } },
  { chapter: 'Chapter 3 - Invoices', title: 'Issue and record a payment',
    narration: 'Back as Sameer. An approved invoice can now be issued. Once issued, open it and record a payment with its reference. A part payment makes the invoice partially paid and leaves the balance outstanding. A payment can never exceed the balance.',
    actions: 'Sign in as Sameer, issue and part-pay.', expected: 'Partially paid.',
    run: async (page) => {
      await signOut(page); await as(page, 'Sameer Joshi'); await nav(page, 'Invoices'); await page.waitForTimeout(2200); await tab(page, 'Approved')
      await page.getByRole('button', { name: 'Issue' }).first().click(); await page.waitForTimeout(3500); await tab(page, 'Issued')
      await page.getByRole('button', { name: 'Open' }).first().click(); await page.waitForTimeout(2500)
      await typeSlow(page.getByLabel('Payment amount (₹)'), '10000'); await typeSlow(page.getByLabel('Reference'), 'Bank transfer demo')
      await page.waitForTimeout(1800); await btn(page, 'Record payment', 5000)
      await page.keyboard.press('Escape'); await page.waitForTimeout(800)
    } },
  { chapter: 'Chapter 4 - Planned vs actual', title: 'Planned against approved hours',
    narration: 'Planned versus Actual compares the monthly allocation with approved timesheet hours. Planned to date prorates the month so far. Hours still waiting for approval are shown apart and are never counted as actual. Projects get a signal: over plan, behind on approved hours, or hours without any allocation.',
    actions: 'Open Planned vs Actual.', expected: 'Projects and people tables.',
    run: async (page) => { await nav(page, 'Planned vs Actual'); await page.waitForTimeout(6000); await scroll(page, 450, 3); await page.waitForTimeout(5500) } },
  { chapter: 'Chapter 4 - Planned vs actual', title: 'Project contribution',
    narration: 'Finance and the CEO also get the Project contribution tab. For each project it shows planned value, salary cost, direct expenses and shared overhead, and the contribution that is left. Invoiced, collected and outstanding sit beside it, deliberately not mixed in. The note confirms that shared costs reconcile.',
    actions: 'Open the Project contribution tab.', expected: 'Contribution table.',
    run: async (page) => { await scroll(page, -2000, 2); await tab(page, 'Project contribution'); await page.waitForTimeout(4500); await scroll(page, 400, 3); await page.waitForTimeout(4500) } },
  { chapter: 'Chapter 5 - Performance', title: 'The performance matrix',
    narration: 'Employee Performance shows transparent delivery measures per person: tasks done and overdue, estimate accuracy, approved against planned hours, handovers acknowledged, and timesheet rejections. There is no score and no ranking. The definitions are listed on the page, and hours alone are never treated as performance.',
    actions: 'Sign in as Priya Rao, open Employee Performance.', expected: 'Matrix with definitions.',
    run: async (page) => { await signOut(page); await as(page, 'Priya Rao'); await nav(page, 'Employee Performance'); await page.waitForTimeout(6500); await scroll(page, 600, 4); await page.waitForTimeout(4500) } },
  { chapter: 'Chapter 5 - Performance', title: 'Add an evidence-based comment',
    narration: 'Managers add review comments with evidence. Open a person, pick a dimension such as delivery reliability, and write what happened and what you expect next. The employee is notified and must acknowledge it. You cannot review yourself.',
    actions: 'Open Meera Nair, add a comment.', expected: 'Comment listed as waiting.',
    run: async (page) => {
      await scroll(page, -2000, 2); await page.waitForTimeout(600)
      await page.locator('tr', { hasText: 'Meera Nair' }).getByRole('button', { name: 'Open' }).click(); await page.waitForTimeout(3500)
      await page.getByLabel('Dimension').selectOption('Collaboration / handover'); await page.waitForTimeout(500)
      await typeSlow(page.getByLabel('Evidence-based comment'), 'Handed over the payment module with a complete note and stayed available for questions for a week.')
      await page.waitForTimeout(1500); await btn(page, 'Add comment', 5000)
    } },
  { chapter: 'Chapter 5 - Performance', title: 'The employee view',
    narration: 'Meera signs in. She sees only herself, never her colleagues, and no money. The new comment is waiting, and she acknowledges it with one click. The manager then sees it as acknowledged.',
    actions: 'Sign in as Meera Nair, acknowledge.', expected: 'Acknowledged.',
    run: async (page) => {
      await signOut(page); await as(page, 'Meera Nair'); await nav(page, 'Employee Performance'); await page.waitForTimeout(5000)
      await page.getByRole('button', { name: 'Open' }).first().click(); await page.waitForTimeout(3500)
      await page.getByRole('button', { name: 'Acknowledge' }).first().click(); await page.waitForTimeout(5000)
    } },
  { chapter: 'Chapter 6 - Limits and next', title: 'What employees cannot see',
    narration: 'Employees have no menu items for invoices, expenses or contribution, and the server refuses direct calls with a forbidden error.',
    actions: 'Probe /api/invoices and /api/expenses as an employee.', expected: 'HTTP 403.',
    run: async (page) => { await page.keyboard.press('Escape'); await apiProbe(page, 'GET /api/invoices as Employee', '/api/invoices'); await apiProbe(page, 'GET /api/expenses as Employee', '/api/expenses'); await page.waitForTimeout(4500) } },
  { chapter: 'Chapter 6 - Limits and next', title: 'What is next',
    narration: 'Sprint four delivered expenses and shared costs, invoices with approval and payments, planned against actual, project contribution, and the performance matrix. File attachments to object storage wait for the storage keys. Sprint five brings the advisory AI assistant, exports and advanced reports, accessibility, security and load testing, and the production cut-over.',
    actions: 'Closing summary.', expected: 'Sign-in page.',
    run: async (page) => { await page.evaluate(() => sessionStorage.clear()); await page.goto(origin + '/'); await page.waitForTimeout(2500) } },
]

await recordVideo({ name: NAME, scenes, check: assertNoSecret, password: undefined })
