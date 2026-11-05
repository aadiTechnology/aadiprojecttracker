/**
 * Explainer video: the multi-tenant foundation. Shows creating a subscriber organization, subscription switches (entitlements),
 * data isolation, platform-admin separation, suspension, and what is reusable for another product.
 * Run against a freshly seeded LOCAL demo database with no SMTP configured (so the owner invitation link is shown on screen).
 */
import { apiProbe, assertNoSecret, click, nav, origin, scroll, signOut, typeSlow } from './common.mjs'
import { recordVideo } from './lib.mjs'

const NAME = 'multitenant-foundation-explained'
const ORG = 'Sunrise Software Studio'
const OWNER_EMAIL = 'owner@sunrise-studio.demo.test'
const OWNER_PW = 'Subscriber#Demo2026' // test value typed into masked fields of this local demo only
let inviteToken = ''

const platformSignOut = (page) => click(page.getByRole('button', { name: 'Sign out', exact: true }))
async function asPlatform(page) {
  await page.goto(origin + '/', { waitUntil: 'domcontentloaded' })
  await click(page.getByRole('button', { name: 'Use Platform Admin' }))
  await click(page.getByRole('button', { name: 'Sign in', exact: true }))
  await page.getByRole('heading', { name: 'Tenants & entitlements' }).waitFor()
}
async function asOwner(page) {
  await page.getByLabel('Email').fill(OWNER_EMAIL)
  await typeSlow(page.getByLabel('Password'), OWNER_PW)
  await click(page.getByRole('button', { name: 'Sign in', exact: true }))
  await page.getByRole('navigation').first().waitFor()
}
const row = (page) => page.getByRole('row', { name: new RegExp(ORG) })

const scenes = [
  {
    title: 'Why this foundation',
    narration: 'This video explains one thing: the multi tenant foundation of Aadi Project Tracker. It is built so that you can do two things. First, create a new organization, give it a subscription, and let it run on the same platform without seeing anyone else. Second, reuse the same foundation to build a different product. We start as the platform administrator.',
    run: async (page) => { await page.goto(origin + '/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(1500); await asPlatform(page) },
  },
  {
    title: 'One platform, many organizations',
    narration: 'The platform administrator sees organizations, not their business data. Today there is one, the Aadi Technology demo, with thirteen people. Each organization has a status, a plan, and a set of optional modules. Those module switches are the subscription: they decide which features an organization has paid for.',
    run: async (page) => { await page.waitForTimeout(1500); await scroll(page, 200, 3) },
  },
  {
    title: 'Create a subscriber',
    narration: 'We create a new subscriber organization, Sunrise Software Studio, and name its owner. In production the owner receives an invitation by email. Behind the scenes the system creates the organization, its seven default roles, its module entitlements, and the first owner, all in one step.',
    run: async (page) => {
      await click(page.getByRole('button', { name: '+ New organization' }))
      const d = page.getByRole('dialog')
      await typeSlow(d.getByLabel('Organization name'), ORG)
      await typeSlow(d.getByLabel('Owner name'), 'Rahul Menon')
      await typeSlow(d.getByLabel('Owner email'), OWNER_EMAIL)
      await click(d.getByRole('button', { name: 'Create and invite owner' }))
      await page.locator('.mono').waitFor()
      const link = await page.locator('.mono').innerText()
      inviteToken = new URL(link.trim()).searchParams.get('token') ?? ''
      if (!inviteToken) throw new Error('No invitation token found')
      await page.waitForTimeout(1500)
    },
  },
  {
    title: 'Subscription switches',
    narration: 'Now the subscription. For this subscriber we switch off sprint and handover, and switch on the optional sales module. These are entitlements, stored per organization and checked by the server on every request. Changes apply immediately, and each one is written to the audit log.',
    run: async (page) => {
      await click(row(page).getByLabel('Sprint & handover'))
      await page.getByText('Sprint & handover disabled').waitFor(); await page.waitForTimeout(1200)
      await click(row(page).getByLabel('Sales (P2)'))
      await page.getByText('Sales (P2) enabled').waitFor(); await page.waitForTimeout(1500)
    },
  },
  {
    title: 'Owner accepts the invitation',
    narration: 'The new owner opens the one time link from the invitation, and chooses a password. The link works once and expires. Only a hash of the token is stored, so it cannot be read from the database.',
    run: async (page) => {
      await platformSignOut(page)
      await page.goto(`${origin}/reset?token=${inviteToken}`, { waitUntil: 'domcontentloaded' })
      await typeSlow(page.getByLabel('New password', { exact: true }), OWNER_PW)
      await typeSlow(page.getByLabel('Repeat password'), OWNER_PW)
      await click(page.getByRole('button', { name: 'Save password' }))
      await page.getByText('Password saved').waitFor(); await page.waitForTimeout(1200)
      await click(page.getByRole('button', { name: 'Go to sign in' }))
    },
  },
  {
    title: 'A clean organization',
    narration: 'Rahul signs in. This is a completely empty organization, with its own name in the sidebar. None of the Aadi Technology projects, customers or people are here. He is the owner, so he has full control inside his own organization.',
    run: async (page) => { await asOwner(page); await page.getByRole('heading', { name: 'Overview Dashboard' }).waitFor(); await page.waitForTimeout(2500) },
  },
  {
    title: 'Roles and modules per organization',
    narration: 'Every organization gets its own copy of the roles, stored as data. Rahul can edit permissions for his own roles without affecting any other organization. The modules tab shows what his subscription includes, with sprint and handover switched off.',
    run: async (page) => {
      await nav(page, 'Organization Admin'); await page.waitForTimeout(1500)
      await click(page.getByRole('tab', { name: 'Roles & permissions' })); await page.waitForTimeout(2200)
      await click(page.getByRole('tab', { name: 'Modules' })); await page.waitForTimeout(2200)
    },
  },
  {
    title: 'Data isolation',
    narration: 'Customers and projects are empty for this organization. To prove isolation, we call the server directly for project number one, which belongs to Aadi Technology. The answer is not found, the same answer as for a project that does not exist, so nothing leaks between organizations.',
    run: async (page) => {
      await nav(page, 'Customers'); await page.waitForTimeout(1800)
      await nav(page, 'Projects'); await page.waitForTimeout(1800)
      await apiProbe(page, "GET /api/projects/1 (Aadi's project) as Sunrise owner", '/api/projects/1'); await page.waitForTimeout(3500)
    },
  },
  {
    title: 'Entitlement enforced by the server',
    narration: 'Sprint planning is locked in the menu. More important, the server refuses it too. A direct call for tasks returns forbidden, with the reason that the module is not enabled for this organization. A hidden button is never the only protection.',
    run: async (page) => {
      await page.getByRole('navigation').getByRole('link', { name: 'Sprint Planning' }).click({ force: true })
      await page.getByText('Access restricted').first().waitFor(); await page.waitForTimeout(1800)
      await apiProbe(page, 'GET /api/tasks, sprint module switched off', '/api/tasks'); await page.waitForTimeout(3500)
    },
  },
  {
    title: 'The first organization is untouched',
    narration: 'Now we sign in to the Aadi Technology organization as the C E O. Eleven projects, thirteen people, all intact. Same application, same database, different organization. A call to the platform administration service is refused, because organization owners are not platform administrators.',
    run: async (page) => {
      await signOut(page)
      await page.getByLabel('Email').waitFor()
      await click(page.getByRole('button', { name: 'Use Priya Rao' })); await click(page.getByRole('button', { name: 'Sign in', exact: true }))
      await page.getByRole('heading', { name: 'Overview Dashboard' }).waitFor(); await page.waitForTimeout(2200)
      await nav(page, 'Projects'); await page.waitForTimeout(2200)
      await apiProbe(page, 'GET /api/platform/tenants as an organization owner', '/api/platform/tenants'); await page.waitForTimeout(3500)
    },
  },
  {
    title: 'Platform admin cannot read business data',
    narration: 'The reverse also holds. The platform administrator can manage organizations, but a direct call for projects is refused. Whoever operates the platform does not automatically read customer data.',
    run: async (page) => {
      await signOut(page); await asPlatform(page); await page.waitForTimeout(1200)
      await apiProbe(page, 'GET /api/projects as Platform Admin', '/api/projects'); await page.waitForTimeout(3500)
    },
  },
  {
    title: 'Suspend a subscriber',
    narration: 'If a subscription lapses, the administrator suspends the organization. Its users lose access at once, existing sessions included, but the data is kept, so the organization can be reactivated later.',
    run: async (page) => {
      await click(row(page).getByRole('button', { name: 'Suspend' }))
      await page.getByText('Suspended', { exact: true }).first().waitFor(); await page.waitForTimeout(2000)
      await platformSignOut(page)
      await page.getByLabel('Email').fill(OWNER_EMAIL)
      await page.getByLabel('Password').fill(OWNER_PW)
      await click(page.getByRole('button', { name: 'Sign in', exact: true }))
      await page.getByRole('alert').first().waitFor(); await page.waitForTimeout(3500)
    },
  },
  {
    title: 'Reuse for another product',
    narration: 'Now the second goal, a different product on the same foundation. What you reuse unchanged: sign in and lockout, invitations and password reset by email, organizations, roles and permissions stored as data, module entitlements, the audit log, platform administration, the deployment setup, the test harness, and this video pipeline. What you replace is the business layer: the capability catalogue, the modules, the data tables and the screens.',
    run: async (page) => {
      await page.goto(origin + '/', { waitUntil: 'domcontentloaded' })
      await click(page.getByRole('button', { name: 'Use Priya Rao' })); await click(page.getByRole('button', { name: 'Sign in', exact: true }))
      await page.getByRole('navigation').first().waitFor()
      await nav(page, 'Role & Permission Matrix'); await page.waitForTimeout(2500); await scroll(page, 600, 5)
    },
  },
  {
    title: 'The API surface',
    narration: 'This is the interactive A P I documentation, available in the demo environment only. Authentication, organization administration and platform administration are the reusable parts. The work endpoints, such as projects, sprints and timesheets, are what a new product would swap out.',
    run: async (page) => { await page.goto(origin + '/docs', { waitUntil: 'networkidle' }); await page.waitForTimeout(2000); await scroll(page, 500, 4) },
  },
  {
    title: 'What is still needed',
    narration: 'To be honest about readiness. Today the platform administrator creates organizations by hand and the plan is only a label. Before selling subscriptions you would add self service sign up, billing and plan limits, per organization branding and domains, and data export and deletion. Database level row security would add a second layer of isolation. The foundation is ready for these, but they are not built yet.',
    run: async (page) => { await page.goto(origin + '/'); await page.waitForTimeout(2500) },
  },
]

for (const sc of scenes) { sc.chapter ??= 'Multi-tenant foundation'; sc.actions ??= sc.title; sc.expected ??= sc.title }
await recordVideo({ name: NAME, scenes, check: assertNoSecret, password: undefined })
