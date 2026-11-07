/** Sprint 5 user manual video: advisory AI assistant (rule-based), CSV exports, hardening and the production cut-over. Needs a freshly seeded database. */
import { apiProbe, assertNoSecret, click, nav, origin, scroll, signInViaDemoList, signOut, typeSlow } from './common.mjs'
import { recordVideo } from './lib.mjs'

const NAME = '07-sprint-5-assistant-exports-and-hardening-user-manual'
const as = async (page, name) => { await signInViaDemoList(page, name); await page.getByRole('heading', { name: 'Overview Dashboard' }).waitFor(); await page.waitForTimeout(1200) }
const example = async (page, text, wait = 6500) => { await click(page.getByRole('button', { name: text, exact: true }).first()); await page.waitForTimeout(wait) }
const typed = async (page, text, wait = 6500) => { await typeSlow(page.getByRole('textbox'), text); await page.waitForTimeout(800); await click(page.getByRole('button', { name: 'Ask', exact: true })); await page.waitForTimeout(wait) }

const scenes = [
  { chapter: 'Chapter 1 - The assistant', title: 'Where the assistant lives',
    narration: 'This is the user manual for Sprint five of Aadi Project Tracking: the advisory assistant, exports, and the hardening work. We sign in as Priya Rao, the CEO. A new Intelligence group in the menu holds the AI Assistant. The page opens with a plain statement of what it is: advisory only, rule based, no language model, and no data leaves the server. It never changes records, approves, rates people or sends messages.',
    actions: 'Sign in as Priya Rao, open AI Assistant.', expected: 'Assistant page with disclosure.',
    run: async (page) => { await page.goto(origin + '/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(1500); await as(page, 'Priya Rao'); await page.waitForTimeout(2000); await nav(page, 'AI Assistant'); await page.waitForTimeout(8000) } },
  { chapter: 'Chapter 1 - The assistant', title: 'Ask for a summary',
    narration: 'You can click an example or type your own question. We ask for a summary of this month. The answer gives planned hours and utilization, planned value against salary cost and margin, bench salary, the organization target, and how many high priority signals need a decision. Below it, Check it on links to the screen that holds the numbers, so a person can always verify.',
    actions: 'Ask for a summary.', expected: 'Answer with evidence links.',
    run: async (page) => { await example(page, 'Give me a summary of this month', 9000) } },
  { chapter: 'Chapter 1 - The assistant', title: 'Margins and what to act on',
    narration: 'Now we type a question: which projects have a thin margin? The assistant names the weakest projects with their margin and money. Follow up buttons suggest the next question. We choose what should I act on, and it lists the open signals, overdue invoices and blocked tasks that this role is allowed to see.',
    actions: 'Type a margin question, then follow up.', expected: 'Two more answers.',
    run: async (page) => { await typed(page, 'Which projects have a thin margin?', 9000); await page.getByRole('button', { name: 'What should I act on?', exact: true }).last().click(); await page.waitForTimeout(9000) } },
  { chapter: 'Chapter 2 - Permissions', title: 'Finance gets receivables',
    narration: 'The assistant calls the same reports as the screens, as the signed in user, so it can never show more than the screens do. Sameer Joshi, the Finance Manager, asks which invoices are overdue and gets the overdue invoices, days late, and drafts waiting for approval.',
    actions: 'Sign in as Sameer Joshi, ask about overdue invoices.', expected: 'Receivables answer.',
    run: async (page) => { await signOut(page); await as(page, 'Sameer Joshi'); await nav(page, 'AI Assistant'); await page.waitForTimeout(2000); await example(page, 'What invoices are overdue?', 9000) } },
  { chapter: 'Chapter 2 - Permissions', title: 'Project managers get no money',
    narration: 'Anil Deshpande is a project manager in the second demonstration organization. He asks the same margin question. The assistant says margins need salary cost, which his role cannot see, and offers hours and staffing instead. Numbers that a role must not see are never in the answer.',
    actions: 'Sign in as Anil Deshpande, ask about margin.', expected: 'Masked answer.',
    run: async (page) => { await signOut(page); await as(page, 'Anil Deshpande'); await nav(page, 'AI Assistant'); await page.waitForTimeout(2000); await example(page, 'Which projects have a thin margin?', 9000); await example(page, 'Who is free to take new work?', 8000) } },
  { chapter: 'Chapter 2 - Permissions', title: 'Usage and cost controls',
    narration: 'Every question is logged with its topic, and each person has a daily limit. The counter shows how many questions have been used today. Because no language model is called, the cost recorded is zero. If the business later chooses a model, the same log and limit will meter it.',
    actions: 'Scroll to the usage counter.', expected: 'Questions used today.',
    run: async (page) => { await scroll(page, -2000, 2); await page.waitForTimeout(6500) } },
  { chapter: 'Chapter 3 - Exports', title: 'Export a report to CSV',
    narration: 'Authorized reports can be exported to CSV. Sameer opens Invoices and chooses Export CSV. The file contains exactly the rows the screen shows, nothing more, and the export is recorded in the audit trail. Text that starts with an equals or plus sign is neutralized so a spreadsheet cannot run it as a formula. The same button exists on expenses, planned versus actual, contribution, and performance.',
    actions: 'Sign in as Sameer, export invoices.', expected: 'CSV downloaded toast.',
    run: async (page) => { await signOut(page); await as(page, 'Sameer Joshi'); await nav(page, 'Invoices'); await page.waitForTimeout(3500); await click(page.getByRole('button', { name: /Export CSV/ })); await page.waitForTimeout(6000) } },
  { chapter: 'Chapter 4 - Limits', title: 'Employees',
    narration: 'Meera Nair is an employee. Her menu has no assistant, and the server refuses direct calls to it with a forbidden error.',
    actions: 'Sign in as Meera Nair, probe the assistant.', expected: 'HTTP 403.',
    run: async (page) => { await signOut(page); await as(page, 'Meera Nair'); await page.waitForTimeout(2500); await apiProbe(page, 'GET /api/assistant/info as Employee', '/api/assistant/info'); await apiProbe(page, 'GET /api/export/invoices as Employee', '/api/export/invoices'); await page.waitForTimeout(4500) } },
  { chapter: 'Chapter 5 - Hardening', title: 'Security, accessibility and load',
    narration: 'The hardening pass added a content security policy, frame denial, strict transport security on secure connections, and a per address limit on sign in and password reset, on top of the account lockout. An automated sweep proves one organization can never open another organization invoices or expenses. An accessibility scan with axe core now passes with no serious or critical findings on every screen of three roles, after fixing low contrast status chips and heat map cells. A load check with thirty simultaneous users ran without errors at about fifty five requests per second on one worker.',
    actions: 'Show the sign-in page while narrating.', expected: 'Sign-in page.',
    run: async (page) => { await page.evaluate(() => sessionStorage.clear()); await page.goto(origin + '/'); await page.waitForTimeout(18000) } },
  { chapter: 'Chapter 6 - Go live', title: 'Production cut-over and what remains',
    narration: 'A production cut-over runbook is now in the docs folder. It lists the decisions only the business owner can make: domains, email provider, Backblaze storage keys, tax and revenue rules, and whether to use a language model. It covers environment switches, the database, backups, verification, cut-over day and rollback. Not included yet: file attachments, spreadsheet and PDF export, a language model assistant, and mobile screens for finance. That completes the five sprint plan.',
    actions: 'Closing summary.', expected: 'Sign-in page.',
    run: async (page) => { await page.waitForTimeout(16000) } },
]

await recordVideo({ name: NAME, scenes, check: assertNoSecret, password: undefined })
