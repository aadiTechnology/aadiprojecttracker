import { useState } from 'react'
import { Me, useApi } from '../api'
import { Chip, ErrorBox, Loading, PageHead } from '../ui'

interface M { roles: { key: string; name: string }[]; current: string; rows: { module: string; cap: string; cells: Record<string, string> }[] }

export function Matrix() {
  const { data, error, loading } = useApi<M>('/api/org/matrix')
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  if (loading) return <Loading />
  if (error) return <ErrorBox msg={error} />
  const roles = data!.roles.filter((r) => !role || r.key === role || r.key === data!.current)
  const rows = data!.rows.filter((r) => r.module.toLowerCase().includes(q.toLowerCase()))
  return (
    <>
      <PageHead title="Role & Permission Matrix" sub="Live from this organization’s role settings. Final permissions are configurable and enforced by the API on every request." />
      <div className="tools">
        <input type="search" aria-label="Filter modules" placeholder="Filter modules…" value={q} onChange={(e) => setQ(e.target.value)} />
        <label>Role <select value={role} onChange={(e) => setRole(e.target.value)}><option value="">All roles</option>{data!.roles.map((r) => <option key={r.key} value={r.key}>{r.name}</option>)}</select></label>
        <span>{['All', 'Team', 'Assigned', 'Own', 'Yes', 'No'].map((l) => <span key={l} className={`pv v-${l}`} style={{ marginRight: 6 }}>{l === 'No' ? 'No access' : l}</span>)}</span>
      </div>
      <div className="card flat"><div className="tw"><table className="mx"><thead><tr><th>Module</th>{roles.map((r) => <th key={r.key} className={r.key === data!.current ? 'sel' : ''}>{r.name}{r.key === data!.current && <><br /><small>(you)</small></>}</th>)}</tr></thead>
        <tbody>{rows.length === 0 ? <tr><td colSpan={roles.length + 1}><div className="empty">No modules match.</div></td></tr> : rows.map((r) => <tr key={r.cap}><td><b>{r.module}</b></td>{roles.map((x) => <td key={x.key} className={x.key === data!.current ? 'sel' : ''}><span className={`pv v-${r.cells[x.key]}`}>{r.cells[x.key] === 'No' ? 'No access' : r.cells[x.key]}</span></td>)}</tr>)}</tbody></table></div></div>
      <p className="note" style={{ marginTop: 12 }}><b>All</b> = whole organization · <b>Team</b> = your team and direct reports · <b>Assigned</b> = projects/customers you are assigned to · <b>Own</b> = your own records. HR / People Manager is an optional role awaiting a customer decision and is not part of this matrix. The SaaS Platform Administrator is separate and has no access to tenant business content.</p>
    </>
  )
}

const STEPS: [string, string[]][] = [
  ['Revenue target is defined', ['Owner', 'Finance', 'Sales']], ['Customer / project is created', ['Owner', 'Operations', 'Sales']],
  ['Scope and deliverables defined', ['Operations', 'PM']], ['Sprint and tasks planned', ['PM', 'Team Lead', 'Operations']],
  ['Employees are assigned', ['PM', 'Team Lead', 'Operations']], ['Work recorded in timesheets', ['Employee']],
  ['Manager approves timesheets', ['Team Lead', 'PM', 'Operations']], ['Actual effort and cost calculated', ['Finance', 'Owner']],
  ['Invoice prepared / issued', ['Finance', 'Owner']], ['Management reviews performance', ['Owner', 'Operations', 'Finance']],
]
const DONE = [2, 2, 2, 2, 2, 2, 2, 3, 3, 3] // sprint in which each step becomes usable; step 1 and 2 (projects, scope) already live

export function Workflow({ me }: { me: Me }) {
  const done = (i: number) => i === 1 || i === 2
  return (
    <>
      <PageHead title="Product Workflow" sub="Revenue → Customer/Project → Sprint/Tasks → Employee → Timesheet → Cost → Invoice → Performance" />
      <div className="steps mb">{STEPS.map(([t, roles], i) => (
        <div className="step" key={t}><div className="no">{i + 1}</div><b>{t}</b><div style={{ margin: '6px 0' }}>{roles.map((r) => <Chip key={r} text={r} />)}{' '}</div>
          <small>{done(i) ? 'Available now' : `Delivered in Sprint ${DONE[i]}${i === 0 ? ' (targets)' : ''}`}</small></div>))}</div>
      <div className="card"><h2>Customer notes → proposed capability</h2><table><thead><tr><th>Customer note</th><th>Proposed capability</th><th>Needs confirmation</th><th>Sprint</th></tr></thead><tbody>
        <tr><td>Matrix/Invoice – Employee Performance</td><td>Employee contribution matrix, project/customer cost matrix, invoice preparation and tracking</td><td>Exact invoice scope</td><td>3</td></tr>
        <tr><td>Sprint Planning – To team transition</td><td>Sprint planning, assignment, reassignment and auditable handover</td><td>Cadence and what “transition” requires</td><td>2</td></tr>
        <tr><td>Target – Revenue</td><td>Revenue targets and actual-versus-target dashboard</td><td>Revenue basis and target level</td><td>3</td></tr>
        <tr><td>Timesheet – To capture details</td><td>Work logs, time entry, approval and estimate-versus-actual</td><td>Approval hierarchy</td><td>2</td></tr></tbody></table></div>
      <p className="note" style={{ marginTop: 12 }}>You are signed in as {me.role.name}. Steps become usable as each sprint ships; nothing here is a confirmed requirement until the customer approves it.</p>
    </>
  )
}

const OPEN: [string, string][] = [
  ['What do the daily S / H markers in the November planning sheet mean?', 'Left undefined; configurable once the customer confirms.'],
  ['What does “Matrix/Invoice” mean: performance matrix, invoice matrix, invoice generation, or all?', 'Proposed: performance matrix plus invoice tracking; invoice generation configurable.'],
  ['Are invoice PDF, GST and tax workflows required?', 'Not assumed; needs accountant validation.'],
  ['Revenue basis: invoiced, collected, recognized or milestone-based?', 'Recorded per organization in Settings; no default is applied.'],
  ['How are salary and shared overhead allocated?', 'Proposal: standard hourly rate × approved hours; overhead by approved hours.'],
  ['At what level are revenue targets set?', 'Proposal: organization, customer and project; sales owner optional.'],
  ['Is a native mobile app required?', 'A mobile app is being built in Sprint 2 onward on your instruction; scope per feature stays open.'],
  ['Final role hierarchy and approval delegation', 'Roles shown are a starting set and are editable.'],
]

export function Assumptions({ me }: { me: Me }) {
  const { data } = useApi<{ revenue_basis: string | null }>('/api/org/settings')
  return (
    <>
      <PageHead title="Assumptions & Decisions" sub="Recommended defaults are proposals only. Nothing here is approved by the customer." />
      <div className="card flat"><div className="tw"><table><thead><tr><th>#</th><th>Open question</th><th>Current handling</th></tr></thead><tbody>
        {OPEN.map(([q, a], i) => <tr key={q}><td>{i + 1}</td><td><b>{q}</b></td><td>{a}{i === 3 && data && <> <Chip text={data.revenue_basis ? `Recorded: ${data.revenue_basis}` : 'Not decided'} tone={data.revenue_basis ? 'ok' : 'warn'} /></>}</td></tr>)}</tbody></table></div></div>
      <p className="note" style={{ marginTop: 12 }}>Signed in as {me.role.name}. The Owner records decisions under Organization Admin → Settings.</p>
    </>
  )
}
