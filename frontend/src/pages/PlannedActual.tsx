import { useState } from 'react'
import { Me, inr, thisMonth, useApi } from '../api'
import { Chip, ErrorBox, Kpi, Loading, PageHead } from '../ui'

interface PA {
  month: string; elapsed_pct: number; money: boolean; partial: boolean; note: string
  totals: { planned_hours: number; planned_to_date: number; approved_hours: number; pending_hours: number; planned_cost_minor?: number; actual_cost_minor?: number }
  projects: { project_id: number; code: string; name: string; planned_hours: number; planned_to_date: number; approved_hours: number; pending_hours: number; variance_hours: number; variance_pct: number | null; flag: string | null; planned_cost_minor?: number; actual_cost_minor?: number; cost_variance_minor?: number }[]
  people: { user_id: number; name: string; planned_hours: number; planned_to_date: number; approved_hours: number; pending_hours: number; flag: string | null }[]
}
interface C {
  month: string; reconciles: boolean; note: string
  totals: { value_minor: number; salary_cost_minor: number; direct_minor: number; shared_minor: number; contribution_minor: number; invoiced_minor: number; collected_minor: number; outstanding_minor: number; bench_minor: number; shared_unallocated_minor: number; after_bench_minor: number }
  rows: { project_id: number; code: string; name: string; tags: string[]; value_minor: number; salary_cost_minor: number; direct_minor: number; shared_minor: number; contribution_minor: number; margin_pct: number | null; invoiced_minor: number; collected_minor: number; outstanding_minor: number }[]
}
const flagTone: Record<string, string> = { 'Over plan': 'warn', 'Behind on approved hours': 'warn', 'Hours without allocation': 'bad' }

export default function PlannedActual({ me }: { me: Me }) {
  const [month, setMonth] = useState(thisMonth())
  const [tab, setTab] = useState('Planned vs actual')
  const fin = me.perms.includes('costing.cost') && me.perms.includes('salary.view') && me.perms.some((p) => p.startsWith('expenses.view'))
  return (
    <>
      <PageHead title="Planned vs Actual" sub="Compare the monthly allocation with approved timesheet hours. Finance roles also see the full cost and invoice picture per project." />
      <div className="tools"><label>Month <input type="month" value={month} onChange={(e) => setMonth(e.target.value || thisMonth())} /></label></div>
      {fin && <div className="tabs" role="tablist">{['Planned vs actual', 'Project contribution'].map((t) => <button key={t} role="tab" aria-selected={tab === t} className="tab" onClick={() => setTab(t)}>{t}</button>)}</div>}
      {tab === 'Planned vs actual' ? <Hours month={month} /> : <Contribution month={month} />}
    </>
  )
}

function Hours({ month }: { month: string }) {
  const { data, error, loading } = useApi<PA>(`/api/planned-actual?month=${month}`)
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load the comparison.'} />
  const t = data.totals
  return (
    <>
      <div className="grid g4 mb">
        <Kpi label="Planned this month" value={`${t.planned_hours} h`} sub={`${data.elapsed_pct}% of the month has passed`} />
        <Kpi label="Planned to date" value={`${t.planned_to_date} h`} sub="Prorated for the month so far" />
        <Kpi label="Approved hours" value={`${t.approved_hours} h`} sub={`${t.pending_hours} h waiting for approval`} />
        {data.money ? <Kpi label="Actual salary cost" value={inr(t.actual_cost_minor)} sub={`Planned ${inr(t.planned_cost_minor)}`} /> : <Kpi label="Difference to date" value={`${Math.round((t.approved_hours - t.planned_to_date) * 10) / 10} h`} sub="Approved − planned to date" />}
      </div>
      <div className="card flat mb"><div style={{ padding: '14px 16px 0' }}><h2>By project</h2></div><div className="tw"><table>
        <thead><tr><th>Project</th><th className="n">Planned</th><th className="n">Planned to date</th><th className="n">Approved</th><th className="n">Waiting</th><th className="n">Difference</th><th>Signal</th>{data.money && <><th className="n">Planned cost</th><th className="n">Actual cost</th></>}</tr></thead>
        <tbody>{data.projects.map((p) => <tr key={p.project_id}><td><b>{p.name}</b><br /><small>{p.code}</small></td><td className="n">{p.planned_hours}</td><td className="n">{p.planned_to_date}</td><td className="n">{p.approved_hours}</td><td className="n">{p.pending_hours || '—'}</td>
          <td className="n">{p.variance_pct === null ? '—' : <span className={p.variance_hours > 0 ? 'neg' : 'pos'}>{p.variance_hours > 0 ? '+' : ''}{p.variance_hours} h ({p.variance_pct}%)</span>}</td>
          <td>{p.flag ? <Chip text={p.flag} tone={flagTone[p.flag]} /> : <Chip text="On track" tone="ok" />}</td>
          {data.money && <><td className="n">{inr(p.planned_cost_minor)}</td><td className="n">{inr(p.actual_cost_minor)}</td></>}</tr>)}</tbody></table></div></div>
      <div className="card flat"><div style={{ padding: '14px 16px 0' }}><h2>By person</h2></div><div className="tw"><table>
        <thead><tr><th>Person</th><th className="n">Planned</th><th className="n">To date</th><th className="n">Approved</th><th className="n">Waiting</th><th>Signal</th></tr></thead>
        <tbody>{data.people.map((p) => <tr key={p.user_id}><td>{p.name}</td><td className="n">{p.planned_hours}</td><td className="n">{p.planned_to_date}</td><td className="n">{p.approved_hours}</td><td className="n">{p.pending_hours || '—'}</td><td>{p.flag ? <Chip text={p.flag} tone={flagTone[p.flag]} /> : <Chip text="On track" tone="ok" />}</td></tr>)}</tbody></table></div></div>
      <p className="note" style={{ marginTop: 12 }}>{data.note}{data.partial ? ' Totals cover only the projects you are assigned to.' : ''}</p>
    </>
  )
}

function Contribution({ month }: { month: string }) {
  const { data, error, loading } = useApi<C>(`/api/finance/contribution?month=${month}`)
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load the contribution view.'} />
  const t = data.totals
  return (
    <>
      <div className="grid g4 mb">
        <Kpi label="Planned value" value={inr(t.value_minor)} sub="Hours × hourly rate" />
        <Kpi label="Cost on projects" value={inr(t.salary_cost_minor + t.direct_minor + t.shared_minor)} sub={`Salary ${inr(t.salary_cost_minor)} · direct ${inr(t.direct_minor)} · shared ${inr(t.shared_minor)}`} />
        <Kpi label="Contribution" value={<span className={t.contribution_minor >= 0 ? 'pos' : 'neg'}>{inr(t.contribution_minor)}</span>} sub={`After bench salary ${inr(t.bench_minor)}: ${inr(t.after_bench_minor)}`} />
        <Kpi label="Invoiced · collected" value={`${inr(t.invoiced_minor)} · ${inr(t.collected_minor)}`} sub={`Outstanding ${inr(t.outstanding_minor)}`} />
      </div>
      <div className="card flat"><div className="tw"><table>
        <thead><tr><th>Project</th><th className="n">Planned value</th><th className="n">Salary</th><th className="n">Direct</th><th className="n">Shared</th><th className="n">Contribution</th><th className="n">Margin</th><th className="n">Invoiced</th><th className="n">Collected</th><th className="n">Outstanding</th></tr></thead>
        <tbody>{data.rows.map((r) => <tr key={r.project_id}><td><b>{r.name}</b><br /><small>{r.code}{r.tags.length ? ' · ' + r.tags.join(', ') : ''}</small></td><td className="n">{inr(r.value_minor)}</td><td className="n">{inr(r.salary_cost_minor)}</td><td className="n">{inr(r.direct_minor)}</td><td className="n">{inr(r.shared_minor)}</td>
          <td className="n"><span className={r.contribution_minor >= 0 ? 'pos' : 'neg'}>{inr(r.contribution_minor)}</span></td><td className="n">{r.margin_pct === null ? '—' : `${r.margin_pct}%`}</td>
          <td className="n">{inr(r.invoiced_minor)}</td><td className="n">{inr(r.collected_minor)}</td><td className="n">{inr(r.outstanding_minor)}</td></tr>)}</tbody></table></div></div>
      <p className="note" style={{ marginTop: 12 }}>{data.reconciles ? 'Shared costs reconcile: the amounts charged to projects plus anything unallocated equal the shared expenses. ' : 'Warning: shared costs do not reconcile. '}{data.note}</p>
    </>
  )
}
