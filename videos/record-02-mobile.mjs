/**
 * Sprint 2 mobile demo: the Expo app (exported for web, shown in a 390 x 844 touch viewport). Same API and same permissions as the web app.
 * Needs: the mobile app exported with EXPO_PUBLIC_API_URL pointing at the API and served on MOBILE_URL (default http://localhost:8082).
 */
import { click, assertNoSecret } from './common.mjs'
import { recordVideo } from './lib.mjs'

const MOBILE = process.env.MOBILE_URL ?? 'http://localhost:8082'
const NAME = '02-sprint-2-mobile-app'
const signIn = async (page, name) => {
  await click(page.getByRole('button', { name: `Use ${name}` }))
  await click(page.getByRole('button', { name: 'Sign in', exact: true }))
  await page.getByRole('tab', { name: 'Tasks' }).waitFor(); await page.waitForTimeout(1200)
}
const signOut = async (page) => { await click(page.getByRole('button', { name: 'Sign out' })); await page.getByRole('button', { name: 'Sign in', exact: true }).waitFor() }
const scenes = [
  {
    chapter: 'Mobile app', title: 'Sign in on the phone', actions: 'Open the app and sign in.', expected: 'Task list.',
    narration: 'This is the first version of the Aadi Project Tracker mobile app, built with Expo and React Native. It uses the same server and the same permissions as the web app. The demo accounts are listed under the sign in button here too. We sign in as Meera Nair.',
    run: async (page) => { await page.goto(MOBILE + '/', { waitUntil: 'domcontentloaded' }); await page.getByRole('button', { name: 'Use Meera Nair' }).waitFor(); await page.waitForTimeout(2000); await signIn(page, 'Meera Nair') },
  },
  {
    chapter: 'Mobile app', title: 'My tasks', actions: 'Change a task status.', expected: 'Status changes.',
    narration: 'My tasks shows only the work assigned to her, with project, sprint, priority and due date. One tap changes the status. She starts the invoice register task, and the change is saved on the server.',
    run: async (page) => {
      await page.getByText('Invoice register').first().waitFor(); await page.waitForTimeout(2000)
      await click(page.locator('div').filter({ hasText: 'Invoice register' }).getByRole('button', { name: 'In progress' }).last())
      await page.waitForTimeout(2500)
    },
  },
  {
    chapter: 'Mobile app', title: 'Timesheet', actions: 'Add time and submit.', expected: 'Entry saved.',
    narration: 'On the timesheet tab she sees the week against the forty hour target. She adds one hour on the Project Tracker product, and submits the week for approval. The same rules apply as on the web: only assigned projects, no future dates, no more than twenty four hours a day.',
    run: async (page) => {
      await click(page.getByRole('tab', { name: 'Timesheet' })); await page.waitForTimeout(2200)
      await click(page.getByRole('button', { name: 'Add time' }))
      await click(page.getByText('PRJ-101 Aadi Project Tracker Product', { exact: true }).last()); await page.waitForTimeout(900)
      await page.getByLabel('Hours').fill('1'); await page.waitForTimeout(1000)
      await click(page.getByRole('button', { name: 'Save time' })); await page.waitForTimeout(2200)
      await click(page.getByRole('button', { name: 'Submit week' })); await page.waitForTimeout(2500)
    },
  },
  {
    chapter: 'Mobile app', title: 'Acknowledge a handover', actions: 'Sign in as Isha Kapoor and acknowledge.', expected: 'Acknowledged.',
    narration: 'Now Isha Kapoor, who has a handover waiting. The handover tab shows who is handing over, the project, the note and the tasks. Only the receiver sees the acknowledge button. One tap, and the project manager is notified.',
    run: async (page) => {
      await signOut(page); await signIn(page, 'Isha Kapoor')
      await click(page.getByRole('tab', { name: 'Handover' })); await page.waitForTimeout(2800)
      await click(page.getByRole('button', { name: 'Acknowledge handover' }).first()); await page.waitForTimeout(2500)
    },
  },
  {
    chapter: 'Mobile app', title: 'Alerts', actions: 'Open Alerts.', expected: 'Notifications.',
    narration: 'The alerts tab lists her notifications, such as new handovers and rejected time, and marks them as read. That completes the first mobile version: tasks, timesheet, handover and alerts. Push notifications and offline use are planned for later sprints.',
    run: async (page) => { await click(page.getByRole('tab', { name: 'Alerts' })); await page.waitForTimeout(3500) },
  },
]
await recordVideo({ name: NAME, scenes, check: undefined, password: undefined, mobile: true })
