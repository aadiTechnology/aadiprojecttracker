import { useState } from 'react'
import { Me, inr, thisMonth, useApi } from '../api'
import { Chip, ErrorBox, Kpi, Loading, Modal, PageHead } from '../ui'

interface Tag { id: number; name: string }
interface EmpRow { id: number; name: string; department: string | null; hours: number; monthly_hours: number; allocated_pct?: number; bench_pct?: number; bench_hours?: number; status?: string; salary_minor?: number | null; cost_minor?: number | null; bench_cost_minor?: number | null; cost_per_hour_minor?: number | null }
interface ProjRow { id: number; code: string; name: string; status: string; tags: Tag[]; people: number; hours: number; rate_overridden: boolean; rate_minor?: number; value_minor?: number; cost_minor?: number; missing_salary?: boolean }
interface TagRow { tag_id: number; tag: string; projects: number; hours: number; value_minor?: number; cost_minor?: number; margin_minor?: number; project_list: { id: number; code: string; name: string; hours: number; value_minor?: number; cost_minor?: number }[] }
interface MatrixData {
  partial: boolean
  employees: { id: number; name: string; department?: string | null; monthly_hours: number; allocated_pct?: number; hours?: number; status?: string; salary_minor?: number | null; cost_minor?: number | null; bench_cost_minor?: number | null }[]
  projects: { id: number; code: string; name: string; tags?: string[]; allocation: Record<string, number>; effort: Record<string, number>; hours: number; cost?: Record<string, number | null>; cost_minor?: number; value_minor?: number }[]
  reconciliation?: { salary_pool_minor: number; allocated_cost_minor: number; bench_cost_minor: number; value_minor: number; hours: number; check: string }
}
interface Summary { hours: number; projects: number; partial: boolean; value_minor?: number; cost_minor?: number; bench_cost_minor?: number; salary_pool_minor?: number; margin_minor?: number; reconciles?: boolean; missing_salary?: string[] }

const TABS = ['By employee', 'By project', 'By tag', 'Workbook matrix']
const stTone: Record<string, string> = { 'Fully allocated': 'ok', Bench: 'warn', 'Partly allocated': 'info', 'Over-allocated': 'bad' }

export default function Costing({ me }: { me: Me }) {
  const [tab, setTab] = useState(TABS[0])
  const [month, setMonth] = useState(thisMonth())
  const [tagIds, setTagIds] = useState<number[]>([])
  const [primary, setPrimary] = useState(false)
  const [open, setOpen] = useState<TagRow | null>(null)
  const sum = useApi<Summary>(`/api/costing/summary?month=${month}`)
  const tags = useApi<{ id: number; name: string; archived: boolean }[]>('/api/tags')
  const emp = useApi<{ rows: EmpRow[]; partial: boolean }>(tab === TABS[0] ? `/api/costing/employees?month=${month}` : null)
  const prj = useApi<{ rows: ProjRow[]; partial: boolean }>(tab === TABS[1] ? `/api/costing/projects?month=${month}&tags=${tagIds.join(',')}` : null)
  const tg = useApi<{ rows: TagRow[]; note: string; additive: boolean }>(tab === TABS[2] ? `/api/costing/tags?month=${month}&primary=${primary}` : null)
  const mx = useApi<MatrixData>(tab === TABS[3] ? `/api/costing/matrix?month=${month}` : null)
  const s = sum.data
  const cost = s?.cost_minor !== undefined
  return (
    <>
      <PageHead title="Effort & Cost" sub="Effort and salary cost from monthly allocation, by employee, project and tag." />
      <div className="formula"><b>Rules:</b> effort = <code>allocation % × monthly hours</code> · cost = <code>allocation % × the employee's own salary</code> · standard value = <code>hours × hourly rate</code> (a value of effort, not invoiced revenue)</div>
      <div className="tools"><label>Month <input type="month" value={month} onChange={(e) => setMonth(e.target.value || thisMonth())} /></label></div>
      {s && <div className="grid g4 mb">
        <Kpi label="Planned effort" value={`${s.hours.toLocaleString('en-IN')} h`} sub={`${s.projects} projects${s.partial ? ' in your scope' : ''}`} />
        {cost && <Kpi label="Standard value" value={inr(s.value_minor)} sub="Hours × hourly rate" />}
        {cost && <Kpi label="Salary cost (allocated)" value={inr(s.cost_minor)} sub={s.bench_cost_minor !== undefined ? `Bench ${inr(s.bench_cost_minor)}` : ''} />}
        {cost && s.margin_minor !== undefined && <Kpi label="Margin" value={<span className={s.margin_minor >= 0 ? 'pos' : 'neg'}>{inr(s.margin_minor)}</span>} sub={s.reconciles ? 'Salary pool = allocated + bench' : ''} />}
        {!cost && <Kpi label="Cost and value" value="Restricted" sub="Your role sees effort in hours only" />}
      </div>}
      {s?.missing_salary && s.missing_salary.length > 0 && <div className="note w mb">Salary missing for: {s.missing_salary.join(', ')}. Their cost is shown as incomplete.</div>}
      <div className="tabs" role="tablist">{TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} className="tab" onClick={() => setTab(t)}>{t}</button>)}</div>
      {tab === TABS[0] && (emp.loading ? <Loading /> : emp.error ? <ErrorBox msg={emp.error} /> : <div className="card flat"><div className="tw"><table>
        <thead><tr><th>Employee</th><th>Department</th>{!emp.data!.partial && <th className="n">Allocated</th>}<th className="n">Hours</th>{emp.data!.rows[0]?.cost_minor !== undefined && <><th className="n">Salary</th><th className="n">Cost</th><th className="n">Cost / hour</th><th className="n">Bench cost</th></>}{!emp.data!.partial && <th>Status</th>}</tr></thead>
        <tbody>{emp.data!.rows.map((e) => <tr key={e.id}><td><b>{e.name}</b></td><td>{e.department ?? '—'}</td>{!emp.data!.partial && <td className="n">{e.allocated_pct}%</td>}<td className="n">{e.hours}</td>
          {e.cost_minor !== undefined && <><td className="n">{e.salary_minor === null ? <Chip text="Missing" tone="warn" /> : inr(e.salary_minor)}</td><td className="n">{inr(e.cost_minor)}</td><td className="n">{inr(e.cost_per_hour_minor)}</td><td className="n">{inr(e.bench_cost_minor)}</td></>}
          {!emp.data!.partial && <td><Chip text={e.status ?? ''} tone={stTone[e.status ?? '']} /></td>}</tr>)}</tbody></table></div></div>)}
      {tab === TABS[1] && <>
        <div className="tools" role="group" aria-label="Filter by tag"><b>Tags</b>{tags.data?.filter((t) => !t.archived).map((t) => <button key={t.id} type="button" className={`chip ${tagIds.includes(t.id) ? 'on' : ''}`} aria-pressed={tagIds.includes(t.id)} onClick={() => setTagIds((x) => x.includes(t.id) ? x.filter((i) => i !== t.id) : [...x, t.id])}>{t.name}</button>)}{tagIds.length > 0 && <button className="btn sm" onClick={() => setTagIds([])}>Clear</button>}</div>
        {prj.loading ? <Loading /> : prj.error ? <ErrorBox msg={prj.error} /> : <div className="card flat"><div className="tw"><table>
          <thead><tr><th>Project</th><th>Tags</th><th className="n">People</th><th className="n">Hours</th>{prj.data!.rows[0]?.cost_minor !== undefined && <><th className="n">Rate/h</th><th className="n">Standard value</th><th className="n">Salary cost</th></>}</tr></thead>
          <tbody>{prj.data!.rows.length === 0 ? <tr><td colSpan={7}><div className="empty">No project carries all the selected tags.</div></td></tr> : prj.data!.rows.map((p) => <tr key={p.id}><td><b>{p.name}</b><br /><small>{p.code} · {p.status}</small></td><td>{p.tags.map((t) => <Chip key={t.id} text={t.name} tone="acc" />)}</td><td className="n">{p.people}</td><td className="n">{p.hours}</td>
            {p.cost_minor !== undefined && <><td className="n">{inr(p.rate_minor)}{p.rate_overridden ? '*' : ''}</td><td className="n">{inr(p.value_minor)}</td><td className="n">{inr(p.cost_minor)}{p.missing_salary ? ' ⚠' : ''}</td></>}</tr>)}</tbody></table></div></div>}</>}
      {tab === TABS[2] && <>
        <div className="tools"><label style={{ display: 'inline-flex', gap: 6 }}><input type="checkbox" checked={primary} onChange={(e) => setPrimary(e.target.checked)} /> Count each project once, under its primary tag (additive)</label></div>
        {tg.data && <div className={`note ${tg.data.additive ? '' : 'w'} mb`}>{tg.data.note}</div>}
        {tg.loading ? <Loading /> : tg.error ? <ErrorBox msg={tg.error} /> : <div className="card flat"><div className="tw"><table>
          <thead><tr><th>Tag</th><th className="n">Projects</th><th className="n">Hours</th>{tg.data!.rows[0]?.cost_minor !== undefined && <><th className="n">Standard value</th><th className="n">Salary cost</th></>}<th /></tr></thead>
          <tbody>{tg.data!.rows.map((r) => <tr key={r.tag_id}><td><Chip text={r.tag} tone="acc" /></td><td className="n">{r.projects}</td><td className="n">{r.hours}</td>{r.cost_minor !== undefined && <><td className="n">{inr(r.value_minor)}</td><td className="n">{inr(r.cost_minor)}</td></>}<td><button className="btn sm" onClick={() => setOpen(r)}>Projects</button></td></tr>)}</tbody></table></div></div>}</>}
      {tab === TABS[3] && (mx.loading ? <Loading /> : mx.error ? <ErrorBox msg={mx.error} /> : <Matrix d={mx.data!} />)}
      {open && <Modal title={`Projects tagged ${open.tag}`} onClose={() => setOpen(null)}><table><thead><tr><th>Project</th><th className="n">Hours</th>{open.cost_minor !== undefined && <><th className="n">Value</th><th className="n">Cost</th></>}</tr></thead>
        <tbody>{open.project_list.map((p) => <tr key={p.id}><td>{p.code} {p.name}</td><td className="n">{p.hours}</td>{p.cost_minor !== undefined && <><td className="n">{inr(p.value_minor)}</td><td className="n">{inr(p.cost_minor)}</td></>}</tr>)}</tbody></table></Modal>}
    </>
  )
}

function Matrix({ d }: { d: MatrixData }) {
  const costOn = d.reconciliation !== undefined
  return (
    <>
      <p className="sub">Same layout as the business workbook: for each project an Allocation, Efforts and Cost row, employees across the page.</p>
      <div className="card flat"><div className="tw"><table className="alloc">
        <thead><tr><th className="nm">Department</th>{d.employees.map((e) => <th key={e.id} className="n"><small>{e.department ?? ''}</small></th>)}<th /></tr>
          <tr><th className="nm">Project / row</th>{d.employees.map((e) => <th key={e.id} className="n">{e.name.split(' ')[0]}</th>)}<th className="n">Total</th></tr>
          {costOn && <tr><th className="nm">Monthly salary</th>{d.employees.map((e) => <th key={e.id} className="n">{inr(e.salary_minor)}</th>)}<th className="n">{inr(d.reconciliation!.salary_pool_minor)}</th></tr>}</thead>
        <tbody>{d.projects.map((p) => <>
          <tr key={p.id + 'a'}><td className="nm"><b>{p.code} {p.name}</b><br />{p.tags?.map((x) => <Chip key={x} text={x} tone="acc" />)} <small>Allocation</small></td>{d.employees.map((e) => <td key={e.id} className="n">{p.allocation[e.id] ? `${p.allocation[e.id]}%` : ''}</td>)}<td className="n"></td></tr>
          <tr key={p.id + 'e'}><td className="nm"><small>Efforts (h)</small></td>{d.employees.map((e) => <td key={e.id} className="n">{p.effort[e.id] ?? ''}</td>)}<td className="n"><b>{p.hours}</b></td></tr>
          {costOn && <tr key={p.id + 'c'}><td className="nm"><small>Cost</small></td>{d.employees.map((e) => <td key={e.id} className="n">{p.cost?.[e.id] ? inr(p.cost[e.id]) : ''}</td>)}<td className="n"><b>{inr(p.cost_minor)}</b><br /><small>value {inr(p.value_minor)}</small></td></tr>}</>)}</tbody>
        <tfoot><tr><td className="nm">Allocated %</td>{d.employees.map((e) => <td key={e.id} className="n">{e.allocated_pct !== undefined ? `${e.allocated_pct}%` : ''}</td>)}<td /></tr>
          <tr><td className="nm">Status</td>{d.employees.map((e) => <td key={e.id} className="n"><Chip text={e.status ?? ''} tone={e.status === 'OVER' ? 'bad' : e.status === 'Full' ? 'ok' : e.status === 'Bench' ? 'warn' : 'info'} /></td>)}<td /></tr>
          {costOn && <tr><td className="nm">Allocated cost</td>{d.employees.map((e) => <td key={e.id} className="n">{inr(e.cost_minor)}</td>)}<td className="n">{inr(d.reconciliation!.allocated_cost_minor)}</td></tr>}
          {costOn && <tr><td className="nm">Bench (unallocated salary)</td>{d.employees.map((e) => <td key={e.id} className="n">{inr(e.bench_cost_minor)}</td>)}<td className="n">{inr(d.reconciliation!.bench_cost_minor)}</td></tr>}</tfoot>
      </table></div></div>
      {d.reconciliation && <div className="card" style={{ marginTop: 14 }}><h2>Reconciliation</h2>
        <table><tbody><tr><td>Salary (all employees)</td><td className="n">{inr(d.reconciliation.salary_pool_minor)}</td></tr><tr><td>Cost allocated to projects</td><td className="n">{inr(d.reconciliation.allocated_cost_minor)}</td></tr>
          <tr><td>Unallocated salary (bench)</td><td className="n">{inr(d.reconciliation.bench_cost_minor)}</td></tr><tr><td>Check</td><td className="n"><Chip text={d.reconciliation.check} tone={d.reconciliation.check.startsWith('OK') ? 'ok' : 'bad'} /></td></tr></tbody></table></div>}
    </>
  )
}
