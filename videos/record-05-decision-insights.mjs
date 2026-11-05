/** Demo video: matrix demo organization and Decision Insights for CEO, Product Owner and Project Manager. Needs a freshly seeded database. */
import { apiProbe, assertNoSecret, click, nav, origin, scroll, signInViaDemoList, signOut } from './common.mjs'
import { recordVideo } from './lib.mjs'

const NAME = '05-decision-insights-matrix-organization'
const as = async (page, name) => { await signInViaDemoList(page, name); await page.getByRole('heading', { name: 'Overview Dashboard' }).waitFor(); await page.waitForTimeout(1200) }
const lens = async (page, name) => { await click(page.getByRole('tab', { name: new RegExp('^' + name) })); await page.waitForTimeout(1500) }

const scenes = [
  { chapter: 'Chapter 1 - The organization', title: 'CEO portfolio view',
    narration: 'This video shows a second demo organization built from the structure of the Aadi Technology matrix workbook. All people and clients are fictional. Departments are functions: management, software development, marketing and sales. Tags are industries, such as education, security and e-commerce. We sign in as Rhea Kulkarni, the CEO, and open Decision Insights. The headline numbers are planned value, salary cost on projects, margin and bench salary.',
    actions: 'Sign in as Rhea Kulkarni, open Decision Insights.', expected: 'CEO lens with KPIs.',
    run: async (page) => { await page.goto(origin + '/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(1500); await as(page, 'Rhea Kulkarni'); await nav(page, 'Decision Insights'); await page.waitForTimeout(5000) } },
  { chapter: 'Chapter 1 - The organization', title: 'Departments and industries',
    narration: 'The departments table shows how busy each function is, who heads it, and what its salary and bench cost. Next to it, each industry shows planned value against salary cost, its margin, and its target where one is set. Every project counts once, under its first tag, so industries add up to the total.',
    actions: 'Scroll over departments and industries.', expected: 'Two tables.',
    run: async (page) => { await scroll(page, 250, 3); await page.waitForTimeout(6000) } },
  { chapter: 'Chapter 1 - The organization', title: 'Department by industry heat map',
    narration: 'The heat map crosses departments with industries. Darker cells mean more effort. Here we see that education work is carried mostly by software development and sales. Switch to salary cost and the same grid shows where the money goes.',
    actions: 'Toggle Hours and Salary cost.', expected: 'Heat map.',
    run: async (page) => { await scroll(page, 500, 3); await page.waitForTimeout(3000); await click(page.getByRole('button', { name: 'Salary cost' })); await page.waitForTimeout(4500) } },
  { chapter: 'Chapter 1 - The organization', title: 'Margins and what to act on',
    narration: 'Projects are ranked by margin, with flags for thin margins, projects below target and projects that depend on one person. At the bottom, what to act on lists the decisions for the CEO: a project with nobody allocated, an organization target not covered, free people, and a fully booked department.',
    actions: 'Scroll to margins and signals.', expected: 'Ranking and signals.',
    run: async (page) => { await scroll(page, 700, 4); await page.waitForTimeout(4500); await scroll(page, 900, 4); await page.waitForTimeout(5500) } },
  { chapter: 'Chapter 2 - Workbook layout', title: 'The workbook matrix',
    narration: 'The effort and cost screen keeps the workbook layout. Employees run across the top, grouped under their department, and every project has allocation, effort and cost rows with its industry tag. The reconciliation proves that allocated cost plus bench equals the salary pool.',
    actions: 'Open Effort and Cost, Workbook matrix.', expected: 'Matrix with departments.',
    run: async (page) => { await nav(page, 'Effort & Cost'); await click(page.getByRole('tab', { name: 'Workbook matrix' })); await page.waitForTimeout(4000); await scroll(page, 500, 4); await page.waitForTimeout(3000) } },
  { chapter: 'Chapter 3 - Product Owner', title: 'Product owner view',
    narration: 'Tanvi Joshi is a product owner. She sees only her own products, in hours, with no salary or margin. For each product the bar shows who builds, markets and sells it. The signals tell her that the platform product has no marketing or sales effort, and that one growth product has no engineering effort.',
    actions: 'Sign in as Tanvi Joshi.', expected: 'Product Owner lens.',
    run: async (page) => { await signOut(page); await as(page, 'Tanvi Joshi'); await nav(page, 'Decision Insights'); await page.waitForTimeout(4500); await scroll(page, 700, 4); await page.waitForTimeout(3500); await scroll(page, 900, 4); await page.waitForTimeout(5000) } },
  { chapter: 'Chapter 4 - Project Manager', title: 'Project manager view',
    narration: 'Anil Deshpande is a project manager. His view shows the people and the department mix on his projects, which projects depend on a single person, and projects with nobody allocated. He also sees free capacity, so he knows whom to ask to fill a gap. Still no salary figures reach his screen.',
    actions: 'Sign in as Anil Deshpande.', expected: 'Project Manager lens.',
    run: async (page) => { await signOut(page); await as(page, 'Anil Deshpande'); await nav(page, 'Decision Insights'); await page.waitForTimeout(4500); await scroll(page, 700, 4); await page.waitForTimeout(5000) } },
  { chapter: 'Chapter 5 - Limits', title: 'Employees are blocked',
    narration: 'Employees have no access to these views. A direct call to the insights service is refused by the server with a forbidden error.',
    actions: 'Sign in as Omkar Pawar is not listed; use Ishaan Dixit and probe the API.', expected: 'HTTP 403.',
    run: async (page) => { await signOut(page); await as(page, 'Ishaan Dixit'); await apiProbe(page, 'GET /api/insights as Employee', '/api/insights'); await page.waitForTimeout(4500) } },
  { chapter: 'Chapter 6 - Wrap up', title: 'What is next',
    narration: 'In short: functional departments, industry tags, a workbook-style matrix, and three decision views with the money hidden from roles that should not see it. Next, expenses and shared costs from the workbook targets sheet will join in sprint four.',
    actions: 'Closing summary.', expected: 'Sign-in page.',
    run: async (page) => { await page.evaluate(() => sessionStorage.clear()); await page.goto(origin + '/'); await page.waitForTimeout(2500) } },
]

await recordVideo({ name: NAME, scenes, check: assertNoSecret, password: undefined })
