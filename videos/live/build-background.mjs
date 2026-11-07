/** Builds the rest of the organization in the background (API, as the CEO) so the summary chapters show the whole business, while each chapter's own video
 * shows only one example on screen (one department, one tag, one person, one project). Idempotent: run it again after every chapter.
 * Usage: node build-background.mjs <phase>   phases: 2 departments, 3 tags, 5 people, 6 employee master, 7 customers+projects, 8 allocations, 10 targets, all */
import { FEATURED, call, activate, ceoToken, creds, data, save, state } from './live-lib.mjs'

const phase = process.argv[2] ?? 'all'
const want = (n) => phase === 'all' || phase === String(n)
const token = await ceoToken()
const g = (p) => call('GET', p, token)
const month = new Date().toISOString().slice(0, 7)
const log = (...a) => console.log(...a)
const depts = [...new Set(data.people.map((p) => p.department))]
const tags = [...new Set(data.projects.flatMap((p) => p.tags))]
const MGMT = data.people.find((p) => p.department === 'Management')

const members = async () => Object.fromEntries((await g('/api/org/users')).map((u) => [u.name, u]))

if (want(2)) {
  const have = new Set((await g('/api/departments')).map((d) => d.name))
  for (const d of depts) if (d !== FEATURED.dept && !have.has(d)) { await call('POST', '/api/departments', token, { name: d }); log('department', d) }
}
if (want(3)) {
  const have = new Set((await g('/api/tags')).map((t) => t.name))
  for (const t of tags) if (t !== FEATURED.tag && !have.has(t)) { await call('POST', '/api/tags', token, { name: t }); log('tag', t) }
}
if (want(5)) {
  const u = await members()
  for (const p of data.people) {
    if (u[p.name]) continue
    const c = Object.values(creds()).find((x) => x.name === p.name)
    const role = c?.role ?? 'employee'
    const r = await call('POST', '/api/org/users', token, { email: c?.email ?? `${p.name.toLowerCase()}@aadi-live.demo.test`, name: p.name, role_key: role, title: c?.title ?? 'Team member', team: p.department, send_email: false })
    log('invited', p.name, role)
    if (c && r.invite_link) { await activate(r.invite_link, c.password); log('  activated', p.name) }
  }
}
if (want(6)) {
  const u = await members()
  const dep = Object.fromEntries((await g('/api/departments')).map((d) => [d.name, d]))
  const hasSalary = Object.fromEntries((await g('/api/employees')).map((e) => [e.name, e.salary_minor != null]))
  for (const p of data.people) {
    const id = u[p.name].id
    if (p.name !== FEATURED.member) {  // the featured person is set up on camera in chapter 6
      await call('PATCH', `/api/employees/${id}`, token, { department_id: dep[p.department].id })
      if (!hasSalary[p.name]) await call('PUT', `/api/employees/${id}/salary`, token, { amount_minor: p.salary * 100, effective_from: `${month}-01` })
    }
  }
  const heads = { Management: MGMT.name, 'Marketing & Sales': data.people.find((x) => x.department === 'Marketing & Sales').name }
  for (const [d, who] of Object.entries(heads)) await call('PATCH', `/api/departments/${dep[d].id}`, token, { name: d, head_user_id: u[who].id })
  log('employee master done')
}
if (want(7)) {
  const cust = Object.fromEntries((await g('/api/customers')).map((c) => [c.name, c]))
  const proj = Object.fromEntries((await g('/api/projects')).map((p) => [p.name, p]))
  const u = await members()
  const tg = Object.fromEntries((await g('/api/tags')).map((t) => [t.name, t.id]))
  const internal = new Set(['Product', 'Internship', 'Aadi Technology', 'Marketing Product'])
  for (const p of data.projects) {
    if (p.name === FEATURED.project) continue
    if (!cust[p.name]) cust[p.name] = { id: (await call('POST', '/api/customers', token, { name: p.name, kind: internal.has(p.name) ? 'internal' : 'customer', owner_user_id: u[MGMT.name].id })).id }
    if (!proj[p.name]) {
      const pm = p.name === FEATURED.project ? u[FEATURED.pm] : u[MGMT.name]
      const r = await call('POST', '/api/projects', token, { name: p.name, customer_id: cust[p.name].id, pm_user_id: pm.id, category: p.tags[0] === 'Marketing' ? 'Marketing' : p.tags[0] === 'Sales' ? 'Sales' : p.tags.includes('Digital Product') ? 'Software Development' : 'Software Services', start_date: `${month}-01`, scope: `${p.name}: monthly plan from the business workbook.` })
      proj[p.name] = { id: r.id }
      await call('PUT', `/api/projects/${r.id}/tags`, token, { tag_ids: p.tags.map((t) => tg[t]) })
      for (const st of ['Planned', 'Active']) await call('POST', `/api/projects/${r.id}/status`, token, { status: st }).catch(() => {})
      log('project', p.name)
    }
  }
}
if (want(8)) {
  const u = await members()
  const proj = Object.fromEntries((await g('/api/projects')).map((p) => [p.name, p]))
  for (const p of data.projects) for (const [who, pct] of Object.entries(p.alloc)) {
    if (p.name === FEATURED.project && who === FEATURED.member) continue // set on camera in chapter 8
    await call('PUT', '/api/allocations', token, { user_id: u[who].id, project_id: proj[p.name].id, month, percent: pct })
  }
  log('allocations done')
}
if (want(10)) {
  const proj = Object.fromEntries((await g('/api/projects')).map((p) => [p.name, p]))
  for (const p of data.projects) if (p.name !== FEATURED.project) await call('PUT', '/api/targets', token, { level: 'project', project_id: proj[p.name].id, month, amount_minor: p.revenue * 100 })
  log('targets done')
}
save()
log('phase', phase, 'ok')
