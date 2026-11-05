/**
 * Revision 2 explanation video: records the ACTUAL interactive HTML prototype (docs/Aadi_Role_Based_Feature_Proposal.html),
 * no production application involved. All names and amounts in it are fictional stand-ins for the business owner's workbook.
 */
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import { click, here, recordVideo } from './lib.mjs'
import { scroll } from './common.mjs'

const NAME = '03-revision-2-prd-and-prototype'
const URL_ = pathToFileURL(path.resolve(here, '../docs/Aadi_Role_Based_Feature_Proposal.html')).href
const go = async (page, v) => { await click(page.locator(`#nav [data-view="${v}"]`)); await page.waitForTimeout(500) }
const close = async (page) => { await click(page.locator('#dx')); await page.waitForTimeout(400) }

const scenes = [
  {
    title: 'The revised business objective',
    narration: 'This video explains the revised proposal for Aadi Project Tracker. The business now wants to answer one question: what does each project cost us in people, what is that effort worth, and are we making money, by employee, by project and by project tag. The screens you see are the interactive prototype, built from your Excel workbook. All names and salaries in it are fictional stand ins, with the same percentages and arithmetic as the workbook.',
    run: async (page) => { await page.goto(URL_); await page.waitForTimeout(2500); await scroll(page, 700, 6) },
  },
  {
    title: 'Employees, departments and salary',
    narration: 'First, the employee master. Each employee has one department, a title and a monthly salary. Every department has a Head of Department, which can be changed here and is audited. Salary is a restricted field. Only the owner and finance see it, and the server hides it from everyone else. The list also shows who is fully allocated and who is on the bench.',
    run: async (page) => {
      await go(page, 'emp2'); await page.waitForTimeout(2500)
      await page.locator('select[data-r2hod="1"]').selectOption('Hemant Patil'); await page.waitForTimeout(2200)
      await scroll(page, 600, 5)
    },
  },
  {
    title: 'Employee validation',
    narration: 'Adding an employee is validated. A name and a salary above zero are required, and a department must be chosen. Nothing is saved in this prototype.',
    run: async (page) => {
      await page.evaluate(() => window.scrollTo(0, 0))
      await click(page.getByRole('button', { name: '+ Add employee' })); await page.waitForTimeout(1500)
      await click(page.locator('#dok')); await page.waitForTimeout(2500); await close(page)
    },
  },
  {
    title: 'Projects and tags',
    narration: 'Next, the project master with tags. Tags are a managed list, and a project can carry several. Here we filter by Marketing, then also by Customer. The numbers above the table follow the filter, so any financial view can be sliced by tag. We can also add a new tag, and tag names must be unique.',
    run: async (page) => {
      await go(page, 'pm2'); await page.waitForTimeout(2000)
      await click(page.locator('[data-r2="tagf:Marketing"]')); await page.waitForTimeout(2200)
      await click(page.locator('[data-r2="tagf:Customer"]')); await page.waitForTimeout(2800)
      await click(page.locator('[data-r2="tagclear"]')); await page.waitForTimeout(800)
      await page.locator('#r2_newtag').fill('Pilot'); await click(page.getByRole('button', { name: 'Add tag' })); await page.waitForTimeout(2200)
    },
  },
  {
    title: 'Allocation across projects',
    narration: 'Now allocation. Each cell is the percentage of an employee\'s month spent on a project, and one person can work on many projects. The total per person can never exceed one hundred percent. If we try to give Esha fifty percent on the first project, when she is already at one hundred, the entry is rejected with a clear message. Giving Ananya, who is on the bench, fifty percent on the third project works, and her free capacity drops to fifty percent.',
    run: async (page) => {
      await go(page, 'al2'); await page.waitForTimeout(2500)
      await page.locator('#r2a_0_4').fill('50'); await page.waitForTimeout(3500)
      await page.locator('#r2a_2_0').fill('50'); await page.waitForTimeout(3200)
      await scroll(page, 500, 4)
    },
  },
  {
    title: 'Restore the baseline',
    narration: 'Reset brings back the baseline from the workbook: fourteen employees, eleven projects, and three people on the bench.',
    run: async (page) => { await page.evaluate(() => window.scrollTo(0, 0)); await click(page.getByRole('button', { name: 'Reset to workbook baseline' })); await page.waitForTimeout(2500) },
  },
  {
    title: 'Organization and project settings',
    narration: 'Settings hold the two numbers from your guidelines: one hundred sixty working hours a month and an hourly rate of two hundred fifty rupees. They are organization defaults. We propose that the rate can be overridden for a project and the hours for a part time employee. Watch the totals on the right when the rate changes to three hundred, and when one project gets its own rate of four hundred.',
    run: async (page) => {
      await go(page, 'set2'); await page.waitForTimeout(2500)
      await page.locator('#r2_rate').fill('300'); await page.waitForTimeout(3000)
      await page.locator('#r2_pr_5').fill('400'); await page.waitForTimeout(3000)
      await page.locator('#r2_pr_5').fill(''); await page.locator('#r2_rate').fill('250'); await page.waitForTimeout(2200)
    },
  },
  {
    title: 'Effort and cost by employee',
    narration: 'Effort and cost. Effort is allocation times monthly hours. Cost is allocation times the employee\'s own monthly salary. Opening Chitra Pillai shows the steps: fifty percent on two projects, eighty hours each, and ten thousand rupees each. Bench hours and bench cost show capacity that is paid for but not allocated.',
    run: async (page) => {
      await go(page, 'cost2'); await page.waitForTimeout(2500)
      await click(page.locator('[data-r2="emp:2"]')); await page.waitForTimeout(4500); await close(page)
    },
  },
  {
    title: 'Effort and cost by project',
    narration: 'By project, the first project is the worked example. Four people give four hundred hours, worth one lakh rupees at the standard rate. The salary cost is fifty two thousand five hundred rupees, so the margin is forty seven thousand five hundred.',
    run: async (page) => {
      await click(page.getByRole('tab', { name: 'By project' })); await page.waitForTimeout(1800)
      await click(page.locator('[data-r2="prj:0"]')); await page.waitForTimeout(5500); await close(page)
    },
  },
  {
    title: 'Effort and cost by tag',
    narration: 'And by tag. A project with two tags appears under both, so tag rows overlap and are not meant to be added together. The tag analysis screen offers an additive view as well.',
    run: async (page) => { await click(page.getByRole('tab', { name: 'By tag' })); await page.waitForTimeout(4000) },
  },
  {
    title: 'Revenue targets',
    narration: 'Revenue targets are set per project and per month. In your workbook only three projects have a target. The others show a warning, not a misleading zero. We set a target of ninety thousand rupees on the Aadi Product Suite and immediately see how planned value compares with the target and with cost.',
    run: async (page) => {
      await go(page, 'rev2'); await page.waitForTimeout(2500)
      await page.locator('#r2_t_1').fill('90000'); await page.waitForTimeout(3500)
      await scroll(page, 400, 4)
    },
  },
  {
    title: 'Project profitability',
    narration: 'Project profitability. Margin is the revenue basis minus salary cost. With the standard value basis, the organization earns two lakh forty thousand rupees on allocated work, a margin of fifty four point five percent. The unallocated salary of sixty thousand rupees is shown on its own line, so the bench is never hidden. Switching to the target basis only includes projects that have a target.',
    run: async (page) => {
      await go(page, 'prof2'); await page.waitForTimeout(2500); await scroll(page, 700, 5); await page.waitForTimeout(1500)
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.locator('#r2_basis').selectOption({ index: 1 }); await page.waitForTimeout(3500)
      await page.locator('#r2_basis').selectOption({ index: 0 }); await page.waitForTimeout(1200)
    },
  },
  {
    title: 'Non salary costs',
    narration: 'The categories from your targets sheet, such as infrastructure, third party, marketing and sales, can be added as an optional layer. It is off by default, because whether they belong in profitability is a decision for you.',
    run: async (page) => { await page.locator('#r2_other').check(); await page.waitForTimeout(4000); await page.locator('#r2_other').uncheck(); await page.waitForTimeout(800) },
  },
  {
    title: 'Tag wise financial analysis',
    narration: 'Tag wise analysis shows hours, value, cost and margin per tag, with a drill down to the projects. Opening the Marketing tag lists its projects. With primary tag only, every project is counted once, and the rows add up to the organization total.',
    run: async (page) => {
      await go(page, 'tag2'); await page.waitForTimeout(2500)
      await click(page.locator('[data-r2="tagdrill:Marketing"]')); await page.waitForTimeout(3800); await close(page)
      await page.locator('#r2_primary').check(); await page.waitForTimeout(3500)
    },
  },
  {
    title: 'Excel check',
    narration: 'This screen compares your workbook with the corrected calculation. Hours and value agree. The cost does not. On projects two to eleven the workbook multiplies every allocation by one fixed salary cell of thirty thousand rupees, instead of each person\'s own salary. It reports three lakh seven thousand five hundred rupees. The correct cost is two lakh rupees. We need you to confirm this correction.',
    run: async (page) => { await go(page, 'chk2'); await page.waitForTimeout(2500); await scroll(page, 700, 6) },
  },
  {
    title: 'Who sees what',
    narration: 'Roles matter. Switching to Operations, the effort screen still works in hours, but salary, cost and value are restricted. A project manager sees only assigned projects, and no salary data. The platform administrator sees none of it. These limits are enforced by the server in the real product.',
    run: async (page) => {
      await click(page.locator('#roles [data-role="ops"]')); await go(page, 'cost2'); await page.waitForTimeout(3500)
      await click(page.locator('#roles [data-role="pm"]')); await go(page, 'al2'); await page.waitForTimeout(3500)
      await click(page.locator('#roles [data-role="ceo"]')); await page.waitForTimeout(800)
    },
  },
  {
    title: 'Decisions needed',
    narration: 'To finish, the proposal lists the decisions we need from you. The main ones are what counts as revenue, whether the corrected cost is right, whether cost is planned or from actual timesheets, what the S and H markers mean, whether non salary costs are included, and how tags and heads of department should work. Each has a recommended answer. The product requirements document, the handoff notes for Cursor, and this prototype are ready for your review. No production code has been changed.',
    run: async (page) => { await go(page, 'assump'); await page.waitForTimeout(2500); await scroll(page, 1400, 8) },
  },
]
for (const sc of scenes) { sc.chapter ??= 'Revision 2'; sc.actions ??= sc.title; sc.expected ??= sc.title }
await recordVideo({ name: NAME, scenes, check: undefined, password: undefined })
