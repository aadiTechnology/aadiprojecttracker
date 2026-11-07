/** The "Build Aadi Technology" series: 12 chapters, each under 3 minutes, one feature at a time, on the live organization. Every chapter shows ONE example on screen
 * (department Software Development, tag Education, person Kalyani, project RITe School); the rest of the business is created in the background by build-background.mjs.
 * Figures are read from the workbook data at record time; none are written in this file. */
import { click, scroll, typeSlow } from '../common.mjs'
import { FEATURED as F, ORIGIN, TENANT_NAME, activate, creds, data, signInForm, state, save } from './live-lib.mjs'

const rs = (n) => `${Math.round(n).toLocaleString('en-IN')} rupees`
const person = (n) => data.people.find((p) => p.name === n)
const proj = (n) => data.projects.find((p) => p.name === n)
const nav = async (page, name) => { await page.getByRole('navigation').getByRole('link', { name }).click(); await page.waitForTimeout(1800) }
const tab = async (page, name) => { await click(page.getByRole('tab', { name, exact: true })); await page.waitForTimeout(1800) }
const btn = async (page, name, wait = 2200, opt = {}) => { await click(page.getByRole('button', { name, exact: true, ...opt })); await page.waitForTimeout(wait) }
const choose = async (loc, text) => { const v = await loc.locator('option', { hasText: text }).first().getAttribute('value'); await loc.selectOption(v) }
const signOut = async (page) => { await page.getByTestId('signout').click(); await page.waitForTimeout(1200) }
const weekday = () => { const d = new Date(); while ([0, 6].includes(d.getDay())) d.setDate(d.getDate() - 1); return d.toLocaleDateString('en-CA') }
const pool = data.people.reduce((t, p) => t + p.salary, 0), cost = data.projects.reduce((t, p) => t + p.cost, 0)
const totals = { pool, cost, bench: pool - cost, sheetCost: data.totals.cost }
const kalyani = person(F.member), prajakta = data.people.find((p) => p.department === 'Management'), rite = proj(F.project)
const sc = (chapter, title, narration, actions, run) => ({ chapter, title, narration, actions, expected: title, run })

export const chapters = {
  1: { name: 'live-01-create-the-organization', title: 'Create the organization', scenes: [
    sc('Create the organization', 'Platform administrator signs in', 'Welcome to the build series for Aadi Project Tracker. In twelve short videos we build the Aadi Technology business plan, from an empty organization to the planning summary. The first step belongs to the platform administrator, who creates organizations and manages plans, but never sees a customer\'s projects, people or money. We sign in as the platform administrator.', 'Sign in as the platform administrator.',
      async (page) => { await page.goto(ORIGIN + '/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(2500); await click(page.getByRole('button', { name: 'Use Platform Admin' })); await page.waitForTimeout(1200); await btn(page, 'Sign in', 3000); await page.getByRole('heading', { name: /Tenants/ }).waitFor() }),
    sc('Create the organization', 'New organization', `Choose New organization. Enter the organization name, ${TENANT_NAME}, and the owner. The owner is the person who will run the business in the product, so we enter Prajakta, the CEO from the workbook, with her email address. The owner always gets every capability, including finance. Create and invite the owner.`, 'Fill the new organization form.',
      async (page) => { await btn(page, '+ New organization', 1200); await typeSlow(page.getByLabel('Organization name'), TENANT_NAME); await typeSlow(page.getByLabel('Owner name'), creds().ceo.name); await typeSlow(page.getByLabel('Owner email'), creds().ceo.email); await page.waitForTimeout(1500); await btn(page, 'Create and invite owner', 3500) }),
    sc('Create the organization', 'The owner sets a password', 'The owner receives an invitation by email. In this demonstration environment the same one-time link is also shown on screen, so we can continue. Opening the link asks for a new password of at least ten characters, with upper and lower case letters and a number. Save the password, and go to sign in.', 'Open the link and set a password.',
      async (page) => {
        const link = (await page.locator('.mono').first().innerText()).trim(); state.ceoLink = 'shown'; save()
        await page.goto(link, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(2000)
        await page.getByLabel('New password').fill(creds().ceo.password); await page.getByLabel('Repeat password').fill(creds().ceo.password); await page.waitForTimeout(1500)
        await btn(page, 'Save password', 3000); await btn(page, 'Go to sign in', 1500)
      }),
    sc('Create the organization', 'First sign-in', `Now Prajakta signs in with her email and her new password. The organization is empty: no departments, no people, no projects. The menu already lists everything an owner can use, including the costing and finance groups. In the next video we create the first department.`, 'Sign in as the CEO.',
      async (page) => { await signInForm(page, 'ceo', { slow: true }); await page.waitForTimeout(6000) }),
  ] },

  2: { name: 'live-02-departments', title: 'Departments', scenes: [
    sc('Departments', 'Open departments', 'A department is a function in the business. The workbook has three: management, software development, and marketing and sales. Every employee belongs to exactly one. Prajakta signs in and opens Employees and Departments, then the Departments tab. It is empty.', 'Sign in as the CEO, open Departments.',
      async (page) => { await signInForm(page, 'ceo'); await nav(page, 'Employees & Departments'); await tab(page, 'Departments'); await page.waitForTimeout(4000) }),
    sc('Departments', 'Add Software Development', `Type the department name, ${F.dept}, and choose Add department. It appears at once, with no employees and no head. The other two departments are added the same way, so we will not repeat the steps.`, 'Add the department.',
      async (page) => { await typeSlow(page.getByLabel('New department name'), F.dept); await page.waitForTimeout(1200); await btn(page, 'Add department', 5000) }),
    sc('Departments', 'Head of department', 'A department has a Head of Department. The head must be an employee of that department, so we choose the head after the people exist, in the employee master video. The head is a relationship only: it gives no access to salaries. Next, tags and costing rules.', 'Show the table.',
      async (page) => { await page.waitForTimeout(9000) }),
  ] },

  3: { name: 'live-03-tags-and-costing-rules', title: 'Tags and costing rules', scenes: [
    sc('Tags and costing rules', 'Costing settings', `Costing Settings holds two organization defaults. A month has ${data.hours} working hours per employee, and the standard hourly rate is ${data.rate} rupees. Standard rate is the internal value of an hour of effort. It is not a customer invoice rate, and changing it never changes salary cost. These match the business workbook, so we only confirm and save them.`, 'Open Costing Settings, save defaults.',
      async (page) => { await signInForm(page, 'ceo'); await nav(page, 'Costing Settings'); await page.waitForTimeout(5500); await btn(page, 'Save defaults', 4000) }),
    sc('Tags and costing rules', 'Project tags', `Tags classify projects for analysis. The workbook tags projects by industry and by the functions involved, for example ${F.tag}. A project can carry several tags, and the first is the primary tag, so roll-ups by tag add up. Type ${F.tag} and choose Add tag. The remaining tags from the workbook are added the same way.`, 'Add one tag.',
      async (page) => { await scroll(page, 400, 3); await page.waitForTimeout(1500); await typeSlow(page.getByLabel('New tag name'), F.tag); await page.waitForTimeout(1200); await btn(page, 'Add tag', 5500) }),
    sc('Tags and costing rules', 'Why tags matter', 'Later, tags let the CEO compare margins by industry and see which kind of work earns the most. Departments say who does the work. Tags say what kind of work it is. With both in place, we can set up roles.', 'Show the tag list.',
      async (page) => { await page.waitForTimeout(8500) }),
  ] },

  4: { name: 'live-04-roles', title: 'Roles', scenes: [
    sc('Roles', 'The roles list', 'Roles decide what each person can open and do. We use three: CEO, Project Manager and Team Member. Open Organization Admin, then Roles and permissions. The CEO is the Organization Owner role. It is protected and holds every capability, including all finance features. Team Member is the Employee role: own tasks, own timesheet, and nothing about money.', 'Open Roles and permissions.',
      async (page) => { await signInForm(page, 'ceo'); await nav(page, 'Organization Admin'); await tab(page, 'Roles & permissions'); await page.waitForTimeout(6000) }),
    sc('Roles', 'Give the Project Manager lead features', 'The Project Manager role already manages assigned projects, sprints, handovers and timesheet approvals. We give it one lead feature more: writing performance review comments for people on those projects. Choose Edit permissions on Project Manager, set performance management to assigned, and save. Changes are audited, and the role applies to everyone who holds it.', 'Edit the Project Manager role.',
      async (page) => { await page.locator('tr', { hasText: 'Project Manager' }).first().getByRole('button', { name: 'Edit permissions' }).click(); await page.waitForTimeout(2500); await page.getByLabel('perf.manage', { exact: true }).selectOption('assigned'); await page.waitForTimeout(2500); await btn(page, 'Save', 4500) }),
    sc('Roles', 'Scopes', 'Each capability has a scope: all, team, assigned or own. Assigned means only the projects the person is a member of or manages. That is why the Project Manager sees the projects they run, and the CEO sees everything. Salary and cost are separate capabilities that the Project Manager and the Team Member never receive.', 'Show the table.',
      async (page) => { await page.waitForTimeout(9000) }),
  ] },

  5: { name: 'live-05-invite-the-team', title: 'Invite the team', scenes: [
    sc('Invite the team', 'Invite a person', `Now the people. Open Organization Admin, People, and choose Invite person. We invite ${F.member}, a software engineer, as a Team Member in the ${F.dept} team. The workbook has fifteen people, but this video shows one invitation, and the others follow the same steps.`, 'Open the invite form.',
      async (page) => { await signInForm(page, 'ceo'); await nav(page, 'Organization Admin'); await tab(page, 'People'); await btn(page, '+ Invite person', 1500); const d = page.getByRole('dialog'); await typeSlow(d.getByRole('textbox', { name: 'Name' }), F.member); await typeSlow(d.getByRole('textbox', { name: 'Email' }), creds().member.email); await d.locator('select').first().selectOption({ label: 'Employee / Contributor' }); await page.waitForTimeout(800); await typeSlow(d.getByRole('textbox', { name: 'Title' }), creds().member.title); await typeSlow(d.getByRole('textbox', { name: 'Team' }), F.dept); await page.waitForTimeout(1500) }),
    sc('Invite the team', 'Send the invitation', 'Choose Send invitation. The person is added as invited, and an email goes out. In this demonstration environment the one-time link is shown too. Nothing is active until the person sets a password, and an invitation expires after seven days.', 'Send the invitation.',
      async (page) => { await btn(page, 'Send invitation', 5000) }),
    sc('Invite the team', 'The person activates', `${F.member} opens the link and chooses a password. The status changes from invited to active. From now on ${F.member} can sign in and will see only the screens a Team Member may use.`, 'Open the link, set a password.',
      async (page) => {
        const link = (await page.locator('.mono').first().innerText()).trim()
        await page.goto(link, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(2000)
        await page.getByLabel('New password').fill(creds().member.password); await page.getByLabel('Repeat password').fill(creds().member.password); await page.waitForTimeout(1500)
        await btn(page, 'Save password', 4500)
      }),
  ] },

  6: { name: 'live-06-employee-master', title: 'Employee master', scenes: [
    sc('Employee master', 'The employee list', 'The employee master joins each person to a department, monthly hours and a salary. Open Employees and Departments. Everyone is listed with their title and department. The salary columns are visible only to roles that hold the salary capability: the CEO here, never the Project Manager or Team Member.', 'Open Employees.',
      async (page) => { await signInForm(page, 'ceo'); await nav(page, 'Employees & Departments'); await page.waitForTimeout(7000) }),
    sc('Employee master', 'Department and salary', `We complete one person, ${F.member}. Choose her department, ${F.dept}. Then Set salary. Salary is the monthly cost to the company, effective from a date, and it keeps history. Enter her monthly figure from the workbook and save.`, 'Set department and salary for one person.',
      async (page) => {
        await page.getByLabel(`Department of ${F.member}`).selectOption({ label: F.dept }); await page.waitForTimeout(2500)
        await page.locator('tr', { hasText: F.member }).getByRole('button', { name: 'Set salary' }).click(); await page.waitForTimeout(1500)
        await typeSlow(page.getByLabel(/Monthly salary/), String(kalyani.salary)); await page.getByLabel('Effective from').fill(new Date().toISOString().slice(0, 7) + '-01'); await page.waitForTimeout(1500)
        await btn(page, 'Save salary', 4000)
      }),
    sc('Employee master', 'Head of department', `Now the Departments tab. For ${F.dept}, choose the head from the people in that department. We pick ${F.pm}. The head is a data relationship only and gives no salary access. The other departments already have their heads.`, 'Choose the head.',
      async (page) => { await tab(page, 'Departments'); await choose(page.getByLabel(`Head of ${F.dept}`), F.pm); await page.waitForTimeout(6000) }),
  ] },

  7: { name: 'live-07-customer-and-project', title: 'Customer and project', scenes: [
    sc('Customer and project', 'Create the customer', `A project always belongs to a customer or an internal business unit. Open Customers and choose New customer. Our first example is ${F.project}, an education customer. Enter the name and save. The other customers from the workbook are already in the list.`, 'Create the customer.',
      async (page) => { await signInForm(page, 'ceo'); await nav(page, 'Customers'); await btn(page, '+ New customer', 1500); await typeSlow(page.getByRole('dialog').getByRole('textbox', { name: 'Name', exact: true }), F.project); await page.waitForTimeout(1500); await btn(page, 'Save', 4500) }),
    sc('Customer and project', 'Create the project', `Open Projects and choose New project. Enter the name, ${F.project}, choose the customer, and the project manager, ${F.pm}. Add a short scope, then Create project. Projects get a code automatically.`, 'Create the project.',
      async (page) => {
        await nav(page, 'Projects'); await btn(page, '+ New project', 1500); await typeSlow(page.getByLabel('Project name'), F.project)
        await page.getByLabel('Customer / business unit').selectOption({ label: F.project }); await choose(page.getByLabel('Project manager'), F.pm)
        await typeSlow(page.getByLabel('Scope and deliverables'), 'School platform, AI chatbot integration and consultation, planned monthly.'); await page.waitForTimeout(1500)
        await btn(page, 'Create project', 4500)
      }),
    sc('Customer and project', 'Tags and team', `Open the project. Edit tags: choose ${F.tag} first, so it becomes the primary tag, and Software Services second. Then the Team tab: add ${F.member} to the project. Finally move the project from Draft to Active, so people can log time on it.`, 'Tag the project and add the team.',
      async (page) => {
        await page.getByRole('button', { name: F.project, exact: true }).first().click(); await page.waitForTimeout(2500)
        await btn(page, 'Edit tags', 1200); await page.getByLabel(F.tag, { exact: true }).check(); await page.waitForTimeout(700); await page.getByLabel('Software Services', { exact: true }).check(); await page.waitForTimeout(1200); await btn(page, 'Save tags', 3000)
        await tab(page, 'Team'); await choose(page.getByLabel('Person'), F.member); await page.getByLabel('Allocation percent').fill('50'); await page.getByLabel('Role on project').fill('Developer'); await page.waitForTimeout(1200); await btn(page, 'Add', 4500)
        await tab(page, 'Overview').catch(() => {}); await btn(page, 'Active', 4000)
      }),
  ] },

  8: { name: 'live-08-monthly-allocation', title: 'Monthly allocation', scenes: [
    sc('Monthly allocation', 'The allocation grid', `Allocation is the heart of the workbook. Each cell is the share of an employee's month that goes to a project. ${F.pm}, the project manager, signs in and opens Employee Allocation. She sees the people on her project. Totals at the right show how full each person is.`, 'Sign in as the project manager.',
      async (page) => { await signInForm(page, 'pm'); await nav(page, 'Employee Allocation'); await page.waitForTimeout(7000) }),
    sc('Monthly allocation', 'The one hundred percent rule', `The server refuses anyone above one hundred percent in a month. ${F.member} already has other work, so we try one hundred percent on ${F.project}. It is rejected, with the reason.`, 'Try 100 percent.',
      async (page) => { const i = page.getByLabel(`${F.member} on ${F.project}, percent`); await i.scrollIntoViewIfNeeded(); await i.click(); await i.pressSequentially('100', { delay: 120 }); await page.keyboard.press('Enter'); await page.waitForTimeout(5500) }),
    sc('Monthly allocation', 'Fifty percent', `Now the planned figure, ${kalyani ? rite.alloc[F.member] : 50} percent. The cell is saved, her total is updated, and effort and cost follow from it. The rest of the grid for the business is already filled in, from the workbook.`, 'Enter the planned percent.',
      async (page) => { const i = page.getByLabel(`${F.member} on ${F.project}, percent`); await i.click(); await i.fill(''); await i.pressSequentially(String(rite.alloc[F.member]), { delay: 120 }); await page.keyboard.press('Enter'); await page.waitForTimeout(7000) }),
  ] },

  9: { name: 'live-09-effort-and-cost', title: 'Effort and cost', scenes: [
    sc('Effort and cost', 'By employee', `Prajakta opens Effort and Cost. From the allocations, the product calculates effort hours, salary cost and standard value for every person. Salary cost is the allocation share of each person's own salary, never one salary for everyone.`, 'Open Effort and Cost.',
      async (page) => { await signInForm(page, 'ceo'); await nav(page, 'Effort & Cost'); await page.waitForTimeout(9000) }),
    sc('Effort and cost', 'By project and tag', 'The By project tab adds up each project. The By tag tab shows the same work by tag, where a project counts under its primary tag, so totals add up.', 'Switch tabs.',
      async (page) => { await tab(page, 'By project'); await page.waitForTimeout(6000); await tab(page, 'By tag'); await page.waitForTimeout(5500) }),
    sc('Effort and cost', 'The workbook matrix and reconciliation', `The Workbook matrix tab reproduces the layout of your Excel: employees across, projects down, with allocation, effort and cost rows. The reconciliation proves the numbers. Cost allocated to projects is ${rs(totals.cost)}, and unallocated bench salary is ${rs(totals.bench)}. Together they equal the salary pool of ${rs(totals.pool)}. One more thing the reconciliation reveals: the total row in the workbook leaves out the eCommerce project, so it shows ${rs(totals.sheetCost)} instead of ${rs(totals.cost)}. The product adds every project.`, 'Open the workbook matrix.',
      async (page) => { await tab(page, 'Workbook matrix'); await page.waitForTimeout(5000); await scroll(page, 700, 4); await page.waitForTimeout(8000) }),
  ] },

  10: { name: 'live-10-targets-and-profitability', title: 'Targets and profitability', scenes: [
    sc('Targets and profitability', 'Revenue targets', `Revenue Targets compares what the business plans to earn with the effort planned. Targets are set per project, per tag and for the organization, month by month. We set one: ${F.project}, ${rs(rite.revenue)}. The other projects already have theirs from the workbook.`, 'Set one project target.',
      async (page) => { await signInForm(page, 'ceo'); await nav(page, 'Revenue Targets'); await page.waitForTimeout(3500); const i = page.getByLabel(`Target for ${F.project}`); await i.scrollIntoViewIfNeeded(); await i.click(); await i.pressSequentially(String(rite.revenue), { delay: 90 }); await page.keyboard.press('Enter'); await page.waitForTimeout(6000) }),
    sc('Targets and profitability', 'Project profitability', 'Project Profitability puts standard value against salary cost, and shows the margin. Bench salary is a separate line and is never hidden. A project with no target shows a warning, not zero.', 'Open Project Profitability.',
      async (page) => { await nav(page, 'Project Profitability'); await page.waitForTimeout(8000); await scroll(page, 500, 3); await page.waitForTimeout(6000) }),
  ] },

  11: { name: 'live-11-timesheets-and-approval', title: 'Timesheets and approval', scenes: [
    sc('Timesheets and approval', 'Log time', `Plans become actuals through timesheets. ${F.member}, a Team Member, signs in and sees only her own screens. In Timesheets she chooses Add time, picks ${F.project}, enters the hours and a note, and saves.`, 'Sign in as the team member, log time.',
      async (page) => {
        await signInForm(page, 'member'); await nav(page, 'Timesheets'); await btn(page, '+ Add time', 1500)
        const opt = await page.getByLabel('Project').locator('option', { hasText: F.project }).first().getAttribute('value'); await page.getByLabel('Project').selectOption(opt)
        await page.getByLabel('Date').fill(weekday()); await typeSlow(page.getByLabel('Hours'), '6'); await typeSlow(page.getByLabel('Note'), 'Chatbot integration testing'); await page.waitForTimeout(1500)
        await btn(page, 'Save', 3500)
      }),
    sc('Timesheets and approval', 'Submit the week', 'At the end of the week she submits it. Until then the entries are drafts she can edit. Submitted time waits for approval, and it does not count as actual yet.', 'Submit the week.',
      async (page) => { await btn(page, 'Submit week', 6500) }),
    sc('Timesheets and approval', 'Approve', `${F.pm}, the project manager, signs in. Under Timesheets, the Approvals tab lists submitted time from her projects. She selects the entry and approves it. Rejecting needs a reason that the person sees. Approved hours are now the actual effort.`, 'Sign in as the project manager, approve.',
      async (page) => { await signOut(page); await signInForm(page, 'pm'); await nav(page, 'Timesheets'); await tab(page, 'Approvals'); await page.getByRole('checkbox').nth(1).check().catch(async () => { await page.getByRole('checkbox').first().check() }); await page.waitForTimeout(2500); await btn(page, 'Approve selected', 6000) }),
  ] },

  12: { name: 'live-12-business-planning-summary', title: 'Business planning summary', scenes: [
    sc('Business planning summary', 'Decision insights', 'Everything we built comes together for the CEO. Decision Insights shows the portfolio by department and by industry tag, the heat map of departments against industries, project margins, and what to act on, such as projects without a team or a thin margin.', 'Open Decision Insights.',
      async (page) => { await signInForm(page, 'ceo'); await nav(page, 'Decision Insights'); await page.waitForTimeout(7000); await scroll(page, 600, 4); await page.waitForTimeout(6000); await scroll(page, 900, 4); await page.waitForTimeout(6000) }),
    sc('Business planning summary', 'Planned against actual', 'Planned versus Actual compares the allocation with approved timesheet hours, month to date. Hours still waiting for approval are shown apart and never counted.', 'Open Planned vs Actual.',
      async (page) => { await nav(page, 'Planned vs Actual'); await page.waitForTimeout(8000); await scroll(page, 450, 3); await page.waitForTimeout(4000) }),
    sc('Business planning summary', 'Contribution and export', 'The Project contribution tab shows, for each project, planned value, salary cost, shared and direct expenses, and the contribution left. Export CSV downloads the report that the screen shows, and the download is audited. That completes the business plan: from an empty organization to a decision-ready summary.', 'Open contribution, export.',
      async (page) => { await tab(page, 'Project contribution'); await page.waitForTimeout(6000); await click(page.getByRole('button', { name: /Export CSV/ })); await page.waitForTimeout(5000) }),
  ] },
}
