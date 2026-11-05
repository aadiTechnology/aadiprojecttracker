import { useEffect, useState } from 'react'
import { Me, inr, thisMonth, useApi } from '../api'
import { Chip, ErrorBox, Kpi, Loading, PageHead } from '../ui'

interface Mix { [dept: string]: number }
interface Dept { department: string; head?: string | null; people: number; capacity_h: number; hours: number; utilization_pct: number; bench_people: number; cost_minor?: number; bench_cost_minor?: number; value_minor?: number; margin_minor?: number }
interface Group { name: string; projects: number; hours: number; mix: Mix; value_minor?: number; cost_minor?: number; margin_minor?: number; margin_pct?: number | null; target_minor?: number | null; mix_cost?: Mix }
interface Proj { id: number; code: string; name: string; category: string; tags: { id: number; name: string }[]; status: string; people: number; hours: number; mix: Mix; flags: string[]; key_person?: string; value_minor?: number; cost_minor?: number; margin_minor?: number; margin_pct?: number | null; target_minor?: number | null }
interface Signal { lens: string; severity: string; title: string; detail: string }
interface Data {
  month: string; partial: boolean; money: boolean; default_lens: string; note: string
  kpi: { people: number; projects: number; hours: number; capacity_h: number; utilization_pct: number; bench_people: number; value_minor?: number; cost_minor?: number; bench_cost_minor?: number; margin_minor?: number; salary_pool_minor?: number; org_target_minor?: number | null; reconciles?: boolean }
  departments: Dept[]; tags: Group[]; categories: Group[]; projects: Proj[]; signals: Signal[]
  heat: { department: string; tag: string; hours: number; cost_minor?: number }[]
  bench: { id: number; name: string; department: string; free_pct: number; free_h: number; bench_cost_minor?: number }[]
}

const LENSES = [
  { key: 'ceo', label: 'CEO · Portfolio', sub: 'Where capacity and salary go, which industries and projects pay back, what to act on.' },
  { key: 'po', label: 'Product Owner · Products & industries', sub: 'Effort by product and industry, who builds, markets and sells each, and where coverage is missing.' },
  { key: 'pm', label: 'Project Manager · Delivery & team', sub: 'Who is on each project, key-person risks and free capacity to staff gaps.' },
]
const PALETTE = ['#2f5bea', '#12805c', '#d97706', '#9333ea', '#0b6e99', '#b42318', '#64748b']
const sevTone: Record<string, string> = { high: 'bad', med: 'warn', info: 'info' }

function Stack({ mix, colors, total }: { mix: Mix; colors: Record<string, string>; total?: number }) {
  const sum = total ?? Object.values(mix).reduce((a, b) => a + b, 0)
  if (!sum) return <small>No effort</small>
  return <div className="stack" role="img" aria-label={Object.entries(mix).map(([k, v]) => `${k} ${Math.round(v)} hours`).join(', ')}>
    {Object.entries(mix).map(([k, v]) => <i key={k} title={`${k}: ${Math.round(v)} h`} style={{ width: `${(v * 100) / sum}%`, background: colors[k] ?? '#94a3b8' }} />)}</div>
}
const Legend = ({ colors }: { colors: Record<string, string> }) => <div className="legend">{Object.entries(colors).map(([k, c]) => <span key={k}><i style={{ background: c }} />{k}</span>)}</div>
const Pct = ({ v, tone }: { v: number; tone?: string }) => <div className="meter"><div className="bar"><i style={{ width: `${Math.min(100, Math.max(0, v))}%`, background: tone }} /></div><small>{v}%</small></div>
const marginTone = (p?: number | null) => (p === null || p === undefined ? '' : p >= 50 ? 'ok' : p >= 30 ? 'warn' : 'bad')

export default function Insights({ me }: { me: Me }) {
  const [month, setMonth] = useState(thisMonth())
  const { data, error, loading } = useApi<Data>(`/api/insights?month=${month}`)
  const [lens, setLens] = useState<string | null>(null)
  const [metric, setMetric] = useState<'hours' | 'cost'>('hours')
  useEffect(() => { if (data && !lens) setLens(data.default_lens) }, [data, lens])
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load insights.'} />
  const L = lens ?? data.default_lens
  const colors: Record<string, string> = {}
  data.departments.forEach((d, i) => { colors[d.department] = PALETTE[i % PALETTE.length] })
  const sigs = data.signals.filter((s) => s.lens === L)
  const k = data.kpi
  const cur = LENSES.find((l) => l.key === L)!
  return (
    <>
      <PageHead title="Decision Insights" sub="Departments and industry tags turned into decisions, shaped for the CEO, the Product Owner and the Project Manager." />
      <div className="tools"><label>Month <input type="month" value={month} onChange={(e) => setMonth(e.target.value || thisMonth())} /></label></div>
      <div className="tabs" role="tablist">{LENSES.map((l) => <button key={l.key} role="tab" aria-selected={L === l.key} className="tab" onClick={() => setLens(l.key)}>{l.label}</button>)}</div>
      <p className="sub">{cur.sub}{data.partial && ' You see the projects assigned to you.'}{!data.money && ' Salary, cost and margin are hidden for your role: effort is shown in hours.'}</p>

      <div className="grid g4 mb">
        {L === 'ceo' && data.money ? <>
          <Kpi label="Planned value" value={inr(k.value_minor)} sub={k.org_target_minor ? `Target ${inr(k.org_target_minor)}` : 'Hours × standard rate'} />
          <Kpi label="Salary cost on projects" value={inr(k.cost_minor)} sub={`Pool ${inr(k.salary_pool_minor)}`} />
          <Kpi label="Margin" value={<span className={(k.margin_minor ?? 0) >= 0 ? 'pos' : 'neg'}>{inr(k.margin_minor)}</span>} sub="Value − salary cost" />
          <Kpi label="Bench salary" value={inr(k.bench_cost_minor)} sub={`${k.bench_people} people unallocated`} />
        </> : <>
          <Kpi label={data.partial ? 'People on your projects' : 'People'} value={k.people} sub={`${k.projects} projects`} />
          <Kpi label="Planned effort" value={`${k.hours} h`} sub={`of ${k.capacity_h} h capacity`} />
          <Kpi label={data.partial ? 'Share of their month' : 'Utilization'} value={`${k.utilization_pct}%`} sub={data.partial ? 'spent on your projects' : 'allocated hours ÷ capacity'} />
          <Kpi label="Free people" value={data.partial ? '—' : k.bench_people} sub={data.partial ? 'Needs organization-wide view' : 'No allocation this month'} />
        </>}
      </div>

      <div className="grid g2 mb">
        <div className="card"><h2>Departments</h2>
          <Legend colors={colors} />
          <table><thead><tr><th>Department</th><th className="n">People</th><th>{data.partial ? 'Share of month on your projects' : 'Utilization'}</th>{L === 'ceo' && data.money && <><th className="n">Salary cost</th><th className="n">Bench</th></>}</tr></thead>
            <tbody>{data.departments.map((d) => <tr key={d.department}><td><i className="dot" style={{ background: colors[d.department] }} /> <b>{d.department}</b>{d.head && <><br /><small>Head: {d.head}</small></>}</td><td className="n">{d.people}</td>
              <td><Pct v={d.utilization_pct} tone={d.utilization_pct >= 100 ? 'var(--ok)' : d.utilization_pct < 60 ? 'var(--warn)' : undefined} /></td>
              {L === 'ceo' && data.money && <><td className="n">{inr(d.cost_minor)}</td><td className="n">{d.bench_cost_minor ? <span className="neg">{inr(d.bench_cost_minor)}</span> : '—'}</td></>}</tr>)}</tbody></table></div>

        <div className="card"><h2>{L === 'pm' ? 'Free capacity to staff gaps' : 'Industries (tags)'}</h2>
          {L === 'pm' ? (data.partial ? <p className="sub">Free-capacity lists need an organization-wide view. Ask the delivery manager for bench names.</p> :
            <table><thead><tr><th>Person</th><th>Department</th><th>Free</th></tr></thead><tbody>{data.bench.map((b) => <tr key={b.id}><td>{b.name}</td><td>{b.department}</td><td><Chip text={`${b.free_pct}% · ${b.free_h} h`} tone={b.free_pct === 100 ? 'warn' : 'info'} /></td></tr>)}{data.bench.length === 0 && <tr><td colSpan={3}>Everyone is fully booked.</td></tr>}</tbody></table>) :
            <table><thead><tr><th>Industry</th><th className="n">Projects</th><th className="n">Hours</th>{data.money ? <><th>Value vs cost</th><th className="n">Margin</th></> : <th>Effort mix</th>}</tr></thead>
              <tbody>{data.tags.map((g) => { const top = Math.max(...data.tags.map((x) => Math.max(x.value_minor ?? 0, x.cost_minor ?? 0)), 1); return <tr key={g.name}><td><Chip text={g.name} tone="acc" /></td><td className="n">{g.projects}</td><td className="n">{g.hours}</td>
                {data.money ? <><td><div className="vc"><i className="v" style={{ width: `${((g.value_minor ?? 0) * 100) / top}%` }} /><i className="c" style={{ width: `${((g.cost_minor ?? 0) * 100) / top}%` }} /></div><small>{inr(g.value_minor)} vs {inr(g.cost_minor)}{g.target_minor ? ` · target ${inr(g.target_minor)}` : ''}</small></td>
                  <td className="n"><Chip text={g.margin_pct === null || g.margin_pct === undefined ? '—' : `${g.margin_pct}%`} tone={marginTone(g.margin_pct)} /></td></> : <td><Stack mix={g.mix} colors={colors} /></td>}</tr> })}</tbody></table>}
          {L !== 'pm' && data.money && <p className="note" style={{ marginTop: 8 }}><span className="sw v" /> Planned value <span className="sw c" /> Salary cost</p>}
        </div>
      </div>

      {L !== 'pm' && <div className="card mb"><h2>Department × industry</h2>
        <div className="tools" style={{ marginBottom: 8 }}><span className="sub">Darker cells mean more {metric === 'cost' ? 'salary cost' : 'hours'}.</span><span style={{ flex: 1 }} />
          {data.money && <><button className={`chip ${metric === 'hours' ? 'on' : ''}`} onClick={() => setMetric('hours')}>Hours</button><button className={`chip ${metric === 'cost' ? 'on' : ''}`} onClick={() => setMetric('cost')}>Salary cost</button></>}</div>
        <Heat data={data} metric={data.money ? metric : 'hours'} /></div>}

      {(L === 'po' || L === 'pm') && <div className="card mb"><h2>{L === 'po' ? 'Products and projects: who builds, markets and sells' : 'Projects: team and department mix'}</h2>
        <Legend colors={colors} />
        <div className="tw"><table><thead><tr><th>Project</th><th>Type</th><th>Industry</th><th className="n">People</th><th className="n">Hours</th><th>Effort by department</th><th>Watch</th></tr></thead>
          <tbody>{data.projects.filter((p) => L === 'pm' || p.category === 'Own Product' || data.partial).map((p) => <tr key={p.id}><td><b>{p.name}</b><br /><small>{p.code}</small></td><td>{p.category}</td><td>{p.tags.map((t) => <Chip key={t.id} text={t.name} tone="acc" />)}</td><td className="n">{p.people}</td><td className="n">{p.hours}</td>
            <td style={{ minWidth: 180 }}><Stack mix={p.mix} colors={colors} /></td>
            <td>{p.flags.length ? p.flags.map((f) => <Chip key={f} text={f === 'Depends on one person' && p.key_person ? `Depends on ${p.key_person}` : f} tone={f === 'No one allocated' ? 'bad' : 'warn'} />) : <Chip text="No flags" tone="ok" />}</td></tr>)}</tbody></table></div></div>}

      {L === 'po' && <div className="card mb"><h2>Portfolio by type</h2>
        <div className="grid g3">{data.categories.map((c) => <div key={c.name} className="card flat" style={{ padding: 14 }}><b>{c.name}</b><br /><small>{c.projects} projects · {c.hours} h</small><div style={{ marginTop: 8 }}><Stack mix={c.mix} colors={colors} /></div>
          {data.money && <p className="sub" style={{ marginTop: 6 }}>{inr(c.value_minor)} value · {c.margin_pct ?? '—'}% margin</p>}</div>)}</div></div>}

      {L === 'ceo' && <div className="card mb"><h2>Projects by margin</h2>
        {data.money ? <div className="tw"><table><thead><tr><th>Project</th><th>Type</th><th>Industry</th><th className="n">Hours</th><th className="n">Value</th><th className="n">Salary cost</th><th>Margin</th><th>Watch</th></tr></thead>
          <tbody>{[...data.projects].sort((a, b) => (a.margin_pct ?? 999) - (b.margin_pct ?? 999)).map((p) => <tr key={p.id}><td><b>{p.name}</b><br /><small>{p.code}</small></td><td>{p.category}</td><td>{p.tags.map((t) => <Chip key={t.id} text={t.name} tone="acc" />)}</td><td className="n">{p.hours}</td><td className="n">{inr(p.value_minor)}</td><td className="n">{inr(p.cost_minor)}</td>
            <td>{p.margin_pct === null || p.margin_pct === undefined ? '—' : <Pct v={p.margin_pct} tone={p.margin_pct < 30 ? 'var(--bad)' : undefined} />}</td><td>{p.flags.map((f) => <Chip key={f} text={f} tone={f === 'No one allocated' ? 'bad' : 'warn'} />)}</td></tr>)}</tbody></table></div>
          : <p className="sub">Your role does not include salary cost, so margins are not shown.</p>}</div>}

      <div className="card"><h2>What to act on</h2>
        {sigs.length === 0 ? <p className="sub">Nothing needs a decision for this view right now.</p> :
          <ul className="signals">{sigs.map((s, i) => <li key={i}><Chip text={s.severity === 'high' ? 'Act' : s.severity === 'med' ? 'Review' : 'Note'} tone={sevTone[s.severity]} /> <b>{s.title}</b><br /><small>{s.detail}</small></li>)}</ul>}
      </div>
      <p className="note" style={{ marginTop: 12 }}>{data.note} Signals are rule-based and advisory.</p>
    </>
  )
}

function Heat({ data, metric }: { data: Data; metric: 'hours' | 'cost' }) {
  const depts = data.departments.map((d) => d.department), tags = data.tags.map((t) => t.name)
  const val = (d: string, t: string) => { const c = data.heat.find((x) => x.department === d && x.tag === t); return c ? (metric === 'cost' ? c.cost_minor ?? 0 : c.hours) : 0 }
  const max = Math.max(...depts.flatMap((d) => tags.map((t) => val(d, t))), 1)
  return <div className="tw"><table className="heat"><thead><tr><th>Department</th>{tags.map((t) => <th key={t} className="n">{t}</th>)}</tr></thead>
    <tbody>{depts.map((d) => <tr key={d}><td><b>{d}</b></td>{tags.map((t) => { const v = val(d, t); return <td key={t} className="n" style={{ background: v ? `rgba(47,91,234,${0.1 + (0.75 * v) / max})` : undefined, color: v / max > 0.55 ? '#fff' : undefined }}>{v ? (metric === 'cost' ? inr(v) : `${Math.round(v)} h`) : ''}</td> })}</tr>)}</tbody></table></div>
}
