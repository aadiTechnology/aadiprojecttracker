/** Sprint 3 demo video: costing and profitability (PRD Revision 2). Run against a freshly seeded recording database. */
import { apiProbe, assertNoSecret, click, nav, origin, scroll, signInViaDemoList, signOut } from './common.mjs'
import { recordVideo } from './lib.mjs'

const NAME = '04-sprint-3-costing-and-profitability'
const as = async (page, name) => { await signInViaDemoList(page, name); await page.getByRole('heading', { name: 'Overview Dashboard' }).waitFor(); await page.waitForTimeout(1200) }
const tab = async (page, name) => { await click(page.getByRole('tab', { name })); await page.waitForTimeout(2800) }

const scenes = [
  { chapter: 'Chapter 1 - Setup', title: 'Employees and departments',
    narration: 'Welcome to Sprint three of Aadi Project Tracker: costing and profitability, built from the Aadi Technology matrix workbook. We sign in as Priya Rao, the CEO. Employees and Departments holds the employee master. Each employee belongs to one department, and each department has one head of department. Salary is shown only to roles that hold salary access.',
    actions: 'Sign in as Priya Rao, open Employees.', expected: 'Employee list with departments and salary.',
    run: async (page) => { await page.goto(origin + '/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(1500); await as(page, 'Priya Rao'); await page.waitForTimeout(2500); await nav(page, 'Employees & Departments'); await page.waitForTimeout(4000) } },
  { chapter: 'Chapter 1 - Setup', title: 'Costing settings',
    narration: 'Costing Settings holds the two organization defaults. A month has one hundred and sixty working hours, and the standard hourly rate is two hundred and fifty rupees. Part time employees can have their own monthly hours, and any project can have its own rate. This rate values the effort. It is not an invoice rate.',
    actions: 'Open Costing Settings.', expected: 'Defaults and overrides.',
    run: async (page) => { await nav(page, 'Costing Settings'); await page.waitForTimeout(5000); await scroll(page, 300, 3) } },
  { chapter: 'Chapter 2 - Allocation', title: 'Monthly allocation',
    narration: 'Allocation is the heart of the workbook. Each cell is the percentage of an employee month spent on a project. Totals per employee appear on the right, and anything under one hundred percent is bench capacity.',
    actions: 'Open Employee Allocation.', expected: 'Allocation grid.',
    run: async (page) => { await nav(page, 'Employee Allocation'); await page.waitForTimeout(5500) } },
  { chapter: 'Chapter 2 - Allocation', title: 'The one hundred percent limit',
    narration: 'The server enforces the rule that nobody can be above one hundred percent in a month. We try to give an already busy employee a full one hundred percent on another project, and the change is rejected with the reason.',
    actions: 'Enter 100 in an empty cell of a busy employee.', expected: 'Rejected toast.',
    run: async (page) => {
      const found = await page.evaluate(() => {
        for (const tr of document.querySelectorAll('table.alloc tbody tr')) {
          const ins = [...tr.querySelectorAll('input')]
          const full = ins.filter((i) => i.value !== '')
          const empty = ins.find((i) => i.value === '')
          if (full.length && empty) { empty.setAttribute('data-pick', '1'); return true }
        }
        return false
      })
      if (!found) throw new Error('No allocation row with a free cell')
      const input = page.locator('[data-pick="1"]')
      await input.scrollIntoViewIfNeeded(); await input.click(); await input.pressSequentially('100', { delay: 80 }); await page.keyboard.press('Enter')
      await page.waitForTimeout(4500)
    } },
  { chapter: 'Chapter 3 - Effort and cost', title: 'By employee',
    narration: 'Effort and Cost turns allocation into numbers. By employee, the hours are allocation times monthly hours, and the salary cost is allocation times that employee own salary. Unallocated salary is shown as bench cost.',
    actions: 'Open Effort & Cost.', expected: 'By employee table.',
    run: async (page) => { await nav(page, 'Effort & Cost'); await page.waitForTimeout(5500) } },
  { chapter: 'Chapter 3 - Effort and cost', title: 'By project and tag',
    narration: 'By project shows hours, standard value and salary cost for each project. Projects can carry tags, and we can filter by one or more of them. By tag adds up all projects under a tag. A project can have several tags, so tag totals can overlap, and one switch counts each project once under its primary tag.',
    actions: 'Open By project, filter by tag, then By tag.', expected: 'Project and tag views.',
    run: async (page) => {
      await tab(page, 'By project')
      await click(page.getByRole('group', { name: 'Filter by tag' }).getByRole('button').first()); await page.waitForTimeout(3000)
      await tab(page, 'By tag')
    } },
  { chapter: 'Chapter 3 - Effort and cost', title: 'Workbook matrix and reconciliation',
    narration: 'The workbook matrix mirrors the Excel layout, with employees across the top and projects down the side. The problem in the original sheet was that every cost cell used one fixed salary, so project cost did not match the salary total. Here each cell uses its own employee salary, and a reconciliation proves that allocated cost plus bench cost equals the salary pool exactly.',
    actions: 'Open Workbook matrix.', expected: 'Matrix with reconciliation.',
    run: async (page) => { await tab(page, 'Workbook matrix'); await scroll(page, 600, 4); await page.waitForTimeout(4500) } },
  { chapter: 'Chapter 4 - Profitability', title: 'Project profitability',
    narration: 'Project Profitability shows revenue basis minus salary cost for each project. Unallocated salary is shown on its own line below, so the result after bench is honest. You can switch the revenue basis between standard value and revenue targets.',
    actions: 'Open Project Profitability.', expected: 'Profit table with bench line.',
    run: async (page) => { await nav(page, 'Project Profitability'); await page.waitForTimeout(4500); await scroll(page, 600, 4); await page.waitForTimeout(3000) } },
  { chapter: 'Chapter 4 - Profitability', title: 'Tag-wise analysis',
    narration: 'The tag-wise tab compares groups of projects, for example by service line, and lets us open the projects behind any tag.',
    actions: 'Open Tag-wise analysis.', expected: 'Tag table.',
    run: async (page) => { await page.evaluate(() => window.scrollTo(0, 0)); await tab(page, 'Tag-wise analysis') } },
  { chapter: 'Chapter 4 - Profitability', title: 'Revenue targets',
    narration: 'Revenue Targets lets finance and leadership set a monthly target per project, per tag and for the whole organization, and compares each with planned value and cost. Projects without a target say Not set instead of showing zero.',
    actions: 'Open Revenue Targets.', expected: 'Targets table.',
    run: async (page) => { await nav(page, 'Revenue Targets'); await page.waitForTimeout(5500) } },
  { chapter: 'Chapter 5 - Role limits', title: 'Project manager sees hours only',
    narration: 'Money is protected on the server. Asha Kulkarni is a project manager. She can plan allocation and see effort for her own projects, but no salary, cost or profit figures reach her screen.',
    actions: 'Sign in as Asha Kulkarni.', expected: 'Hours without money.',
    run: async (page) => { await signOut(page); await as(page, 'Asha Kulkarni'); await nav(page, 'Effort & Cost'); await page.waitForTimeout(5000) } },
  { chapter: 'Chapter 5 - Role limits', title: 'Employee is blocked',
    narration: 'An employee has no access to costing at all. The menu entry is locked, and a direct call to the costing service is refused by the server.',
    actions: 'Sign in as Meera Nair and probe the API.', expected: 'HTTP 403.',
    run: async (page) => { await signOut(page); await as(page, 'Meera Nair'); await apiProbe(page, 'GET /api/costing/summary as Employee', '/api/costing/summary'); await page.waitForTimeout(4500) } },
  { chapter: 'Chapter 6 - Wrap up', title: 'What is next',
    narration: 'Sprint three delivers the employee and department master, allocation, effort and cost, tag analysis, profitability and revenue targets. Sprint four adds the performance matrix, expenses, shared costs, invoices and planned versus actual from timesheets.',
    actions: 'Closing summary.', expected: 'Sign-in page.',
    run: async (page) => { await page.evaluate(() => sessionStorage.clear()); await page.goto(origin + '/'); await page.waitForTimeout(2500) } },
]

await recordVideo({ name: NAME, scenes, check: assertNoSecret, password: undefined })
