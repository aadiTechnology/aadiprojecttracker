/**
 * Sprint 2 demo video (web): sprints and tasks, status updates, timesheets and approval, handover with acknowledgement,
 * notifications, and role boundaries. Run against a freshly seeded RECORDING database (dates are relative to today).
 */
import { apiProbe, assertNoSecret, click, nav, origin, scroll, signInViaDemoList, signOut, typeSlow } from './common.mjs'
import { recordVideo } from './lib.mjs'

const NAME = '02-sprint-2-delivery-web'
const today = new Date()
const iso = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const as = async (page, name) => { await signInViaDemoList(page, name); await page.getByRole('heading', { name: 'Overview Dashboard' }).waitFor(); await page.waitForTimeout(1200) }

const scenes = [
  {
    chapter: 'Chapter 1 - Employee', title: 'Employee dashboard',
    narration: 'Welcome to Sprint two of Aadi Project Tracker: delivery. We sign in as Meera Nair, a software engineer. Last sprint her dashboard was almost empty. Now it shows her open tasks, her hours this week against the target, and any handover waiting for her. Everything is limited to her own work.',
    actions: 'Sign in as Meera Nair.', expected: 'Dashboard with delivery cards.',
    run: async (page) => { await page.goto(origin + '/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(1500); await as(page, 'Meera Nair'); await page.waitForTimeout(2500) },
  },
  {
    chapter: 'Chapter 1 - Employee', title: 'My tasks and blocking a task',
    narration: 'In Sprint Planning she sees only tasks assigned to her. She cannot see other engineers work. She is stuck on the sprint and task board, so she marks it Blocked. The project manager is notified immediately.',
    actions: 'Open Sprint Planning, set a task to Blocked.', expected: 'Status updated.',
    run: async (page) => {
      await nav(page, 'Sprint Planning'); await page.waitForTimeout(2200)
      await page.getByLabel('Status of Sprint and task board').selectOption('Blocked')
      await page.getByText('Status updated').waitFor(); await page.waitForTimeout(2500)
    },
  },
  {
    chapter: 'Chapter 1 - Employee', title: 'Log and submit time',
    narration: 'Next, her timesheet. She adds two hours for today against the Project Tracker product, choosing the task she worked on. The system only lets her log time on projects she is assigned to, never in the future, and never more than twenty four hours a day. Then she submits the week for approval.',
    actions: 'Add time and submit the week.', expected: 'Entry added; week submitted.',
    run: async (page) => {
      await nav(page, 'Timesheets'); await page.waitForTimeout(2200)
      await click(page.getByRole('button', { name: '+ Add time' }))
      const d = page.getByRole('dialog')
      await d.getByLabel('Project').selectOption({ label: 'PRJ-101 Aadi Project Tracker Product' })
      await d.getByLabel('Task').selectOption({ label: 'Sprint and task board' })
      await d.getByLabel('Hours').fill('2')
      await page.waitForTimeout(1200)
      await click(d.getByRole('button', { name: 'Save' }))
      await page.getByText('Time saved').waitFor(); await page.waitForTimeout(1800)
      await click(page.getByRole('button', { name: 'Submit week' }))
      await page.getByText('submitted for approval').waitFor(); await page.waitForTimeout(2500)
    },
  },
  {
    chapter: 'Chapter 1 - Employee', title: 'Boundaries are enforced by the server',
    narration: 'An employee cannot approve time. A direct call to the approvals service is refused by the server, not just hidden in the screen.',
    actions: 'Probe the approvals API.', expected: 'HTTP 403.',
    run: async (page) => { await apiProbe(page, 'GET /api/timesheets/approvals as Employee', '/api/timesheets/approvals'); await page.waitForTimeout(4000) },
  },
  {
    chapter: 'Chapter 2 - Team lead', title: 'Approve team time',
    narration: 'Rohan Mehta is the team lead. His dashboard counts the timesheet entries waiting for him. On the approvals tab he sees only his own team, never his own time. He selects everything and approves. Rejecting needs a written reason, which the employee sees.',
    actions: 'Sign in as Rohan Mehta and approve.', expected: 'Time approved.',
    run: async (page) => {
      await signOut(page); await as(page, 'Rohan Mehta'); await page.waitForTimeout(1800)
      await nav(page, 'Timesheets'); await click(page.getByRole('tab', { name: 'Approvals' })); await page.waitForTimeout(2500)
      await page.getByLabel('Select all').check(); await page.waitForTimeout(1200)
      await click(page.getByRole('button', { name: 'Approve selected' }))
      await page.getByText('Time approved').waitFor(); await page.waitForTimeout(2200)
    },
  },
  {
    chapter: 'Chapter 3 - Project manager', title: 'Notification and blocked work',
    narration: 'Asha Kulkarni is a project manager. The bell shows what needs her attention, including the blocked task from Meera. Notifications are private to each person and are marked as read when opened.',
    actions: 'Sign in as Asha Kulkarni and open the bell.', expected: 'Notification list.',
    run: async (page) => {
      await signOut(page); await as(page, 'Asha Kulkarni')
      await click(page.getByTestId('bell')); await page.waitForTimeout(3500); await page.keyboard.press('Escape')
      await click(page.getByTestId('bell')); await page.waitForTimeout(500)
    },
  },
  {
    chapter: 'Chapter 3 - Project manager', title: 'Create and assign a task',
    narration: 'Asha plans work. She creates a task in the active Retail Portal sprint. The assignee list contains only the project team. She assigns it to Dev Patel.',
    actions: 'Create a task and assign it.', expected: 'Task created.',
    run: async (page) => {
      await nav(page, 'Sprint Planning'); await page.waitForTimeout(1800)
      await click(page.getByRole('button', { name: '+ New task' }))
      const d = page.getByRole('dialog')
      await d.getByLabel('Project').selectOption({ label: 'PRJ-103 Retail Portal Revamp' })
      await typeSlow(d.getByLabel('Title'), 'Wishlist page')
      await d.getByLabel('Sprint').selectOption({ label: 'Checkout beta' })
      await d.getByLabel('Assignee').selectOption({ label: 'Dev Patel' })
      await d.getByLabel('Priority').selectOption('High')
      await d.getByLabel('Estimate (hours)').fill('6')
      await page.waitForTimeout(800)
      await click(d.getByRole('button', { name: 'Create task' }))
      await page.getByText('Task created').waitFor(); await page.waitForTimeout(1800)
    },
  },
  {
    chapter: 'Chapter 3 - Project manager', title: 'Reassign with history',
    narration: 'Plans change, so she reassigns the task to Isha Kapoor and records why. Every assignment is kept in the task history: who, to whom, by whom and the reason.',
    actions: 'Open the task and reassign.', expected: 'History shows two rows.',
    run: async (page) => {
      await click(page.getByRole('button', { name: 'Wishlist page' }))
      const d = page.getByRole('dialog')
      await d.getByLabel('Assign to').selectOption({ label: 'Isha Kapoor' })
      await typeSlow(d.getByLabel('Reason'), 'Rebalancing the sprint')
      await click(d.getByRole('button', { name: 'Assign', exact: true }))
      await page.getByText('Task assigned').waitFor(); await page.waitForTimeout(3500)
      await page.keyboard.press('Escape')
    },
  },
  {
    chapter: 'Chapter 4 - Handover', title: 'Hand work over',
    narration: 'When a person moves to other work, the project manager creates a handover. She chooses the project, who hands over and who receives, selects the open tasks, and writes a note with context and next steps. The note is mandatory. Ownership of the tasks moves to the receiver, and the receiver is notified.',
    actions: 'Create a handover.', expected: 'Handover sent.',
    run: async (page) => {
      await nav(page, 'Team Handover'); await page.waitForTimeout(2000)
      await click(page.getByRole('button', { name: '+ New handover' }))
      const d = page.getByRole('dialog')
      await d.getByLabel('Project').selectOption({ label: 'PRJ-102 Aadi SpendOS Expense Platform' })
      await d.getByLabel('From').selectOption({ label: 'Dev Patel' })
      await d.getByLabel('To').selectOption({ label: 'Isha Kapoor' })
      await d.getByLabel('Fix report export timeout').check()
      await typeSlow(d.getByLabel('Handover note (context, status, next steps)'), 'Export fix is half done. See the branch notes; next step is paging the query.')
      await page.waitForTimeout(1000)
      await click(d.getByRole('button', { name: 'Send handover' }))
      await page.getByText('Handover sent for acknowledgement').waitFor(); await page.waitForTimeout(2500)
    },
  },
  {
    chapter: 'Chapter 4 - Handover', title: 'Receiver acknowledges',
    narration: 'Isha Kapoor receives two handovers. A handover stays pending until the receiver acknowledges it. Only the receiver can do that, not the manager and not the sender. She reads the note and acknowledges, and the project manager is told.',
    actions: 'Sign in as Isha Kapoor and acknowledge.', expected: 'Status Acknowledged.',
    run: async (page) => {
      await signOut(page); await as(page, 'Isha Kapoor'); await page.waitForTimeout(1800)
      await nav(page, 'Team Handover'); await page.waitForTimeout(2200)
      await click(page.getByRole('button', { name: 'Acknowledge' }).first())
      await typeSlow(page.getByRole('dialog').getByLabel('Your note (optional)'), 'Understood, I will continue from the branch.')
      await click(page.getByRole('button', { name: 'I have received this' }))
      await page.getByText('Handover acknowledged').waitFor(); await page.waitForTimeout(2500)
    },
  },
  {
    chapter: 'Chapter 4 - Handover', title: 'Rejected time',
    narration: 'Isha also has time that was rejected, with the reason shown right next to it. She can correct the entry and submit the week again.',
    actions: 'Open Timesheets.', expected: 'Rejected entry with reason.',
    run: async (page) => { await nav(page, 'Timesheets'); await page.waitForTimeout(3500); await scroll(page, 300, 3) },
  },
  {
    chapter: 'Chapter 5 - Role limits', title: 'Sales has no delivery access',
    narration: 'Finally, role limits. Kabir Sethi from sales has no access to sprints, tasks or timesheet approvals. The menu locks them, and the server refuses direct calls to the task service.',
    actions: 'Sign in as Kabir Sethi.', expected: 'Locked screen and HTTP 403.',
    run: async (page) => {
      await signOut(page); await as(page, 'Kabir Sethi')
      await page.getByRole('navigation').getByRole('link', { name: 'Sprint Planning' }).click({ force: true })
      await page.getByText('Access restricted').first().waitFor(); await page.waitForTimeout(1800)
      await apiProbe(page, 'GET /api/tasks as Sales', '/api/tasks'); await page.waitForTimeout(3500)
    },
  },
  {
    chapter: 'Chapter 6 - Wrap up', title: 'What is next',
    narration: 'Sprint two delivers sprints, tasks, assignment history, handover with acknowledgement, timesheets with approval and notifications, with a companion mobile app shown in the next video. Sprint three adds revenue targets, expenses, invoices and the performance matrix.',
    actions: 'Closing summary.', expected: 'Sign-in page.',
    run: async (page) => { await page.evaluate(() => sessionStorage.clear()); await page.goto(origin + '/'); await page.waitForTimeout(2500) },
  },
]

await recordVideo({ name: NAME, scenes, check: assertNoSecret, password: undefined })
