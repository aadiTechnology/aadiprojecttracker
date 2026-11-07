import { FormEvent, useState } from 'react'
import { Me, api, thisMonth, useApi } from '../api'
import { Chip, ErrorBox, ExportButton, Kpi, Loading, Modal, PageHead, toast } from '../ui'

interface Row {
  user_id: number; name: string; title: string; team: string
  tasks: { assigned: number; done: number; open: number; blocked: number; overdue: number; completion_pct: number | null }
  estimates: { tasks_compared: number; estimated_hours: number; approved_hours: number; accuracy_pct: number | null }
  hours: { planned: number; approved: number; utilization_pct: number | null }
  handover: { received: number; acknowledged: number; given: number }
  timesheets: { decided: number; rejected: number }
  reviews: { count: number; unacknowledged: number }
}
interface List { month: string; scope: string; can_review: boolean; me: number; dimensions: string[]; definitions: string[]; rows: Row[] }
interface Detail extends Omit<Row, 'reviews'> { projects: { project: string; planned_hours: number; approved_hours: number }[]; can_review: boolean; reviews: { id: number; month: string; dimension: string; comment: string; by: string; at: string; acknowledged: boolean; ack_note: string; mine: boolean }[] }
const pct = (v: number | null) => (v === null ? '—' : `${v}%`)

export default function Performance({ me }: { me: Me }) {
  const [month, setMonth] = useState(thisMonth())
  const { data, error, loading, reload } = useApi<List>(`/api/performance?month=${month}`)
  const [open, setOpen] = useState<number | null>(null)
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load the performance matrix.'} />
  const rows = data.rows
  const sum = (f: (r: Row) => number) => rows.reduce((s, r) => s + f(r), 0)
  const pending = sum((r) => r.reviews.unacknowledged)
  return (
    <>
      <PageHead title="Employee Performance" sub={data.scope === 'own' ? 'Your own delivery measures and review comments.' : 'Transparent delivery measures per person, with evidence-based review comments. There is no score and no ranking.'} />
      <div className="tools"><label>Month <input type="month" value={month} onChange={(e) => setMonth(e.target.value || thisMonth())} /></label><span style={{ flex: 1 }} /><ExportButton report="performance" month={month} /></div>
      <div className="grid g4 mb">
        <Kpi label="People shown" value={rows.length} sub={`Scope: ${data.scope}`} />
        <Kpi label="Tasks done" value={`${sum((r) => r.tasks.done)} of ${sum((r) => r.tasks.assigned)}`} sub={`${sum((r) => r.tasks.overdue)} overdue · ${sum((r) => r.tasks.blocked)} blocked`} />
        <Kpi label="Approved hours" value={`${Math.round(sum((r) => r.hours.approved))} h`} sub={`Planned ${Math.round(sum((r) => r.hours.planned))} h this month`} />
        <Kpi label="Review comments" value={sum((r) => r.reviews.count)} sub={pending ? `${pending} waiting for acknowledgement` : 'All acknowledged'} />
      </div>
      <div className="card flat"><div className="tw"><table>
        <thead><tr><th>Person</th><th className="n">Tasks done</th><th className="n">Completion</th><th className="n">Overdue</th><th className="n">Estimate accuracy</th><th className="n">Approved / planned h</th><th className="n">Handovers ack.</th><th className="n">Rejected entries</th><th>Reviews</th><th /></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.user_id}><td><b>{r.name}</b>{r.user_id === data.me && <> <Chip text="You" tone="acc" /></>}<br /><small>{r.title}</small></td>
          <td className="n">{r.tasks.done} / {r.tasks.assigned}</td><td className="n">{pct(r.tasks.completion_pct)}</td><td className="n">{r.tasks.overdue ? <span className="neg">{r.tasks.overdue}</span> : 0}</td>
          <td className="n">{pct(r.estimates.accuracy_pct)}<br /><small>{r.estimates.tasks_compared} tasks</small></td><td className="n">{r.hours.approved} / {r.hours.planned}<br /><small>{pct(r.hours.utilization_pct)}</small></td>
          <td className="n">{r.handover.acknowledged} / {r.handover.received}</td><td className="n">{r.timesheets.rejected} of {r.timesheets.decided}</td>
          <td>{r.reviews.count}{r.reviews.unacknowledged > 0 && <> <Chip text={`${r.reviews.unacknowledged} to acknowledge`} tone="warn" /></>}</td>
          <td><button className="btn sm" onClick={() => setOpen(r.user_id)}>Open</button></td></tr>)}</tbody></table></div></div>
      <details className="card" style={{ marginTop: 14 }} open><summary><b>How each measure is defined</b></summary><ul>{data.definitions.map((d) => <li key={d}>{d}</li>)}</ul></details>
      {open !== null && <Profile uid={open} month={month} dims={data.dimensions} onClose={() => setOpen(null)} onChanged={reload} />}
    </>
  )
}

function Profile({ uid, month, dims, onClose, onChanged }: { uid: number; month: string; dims: string[]; onClose: () => void; onChanged: () => void }) {
  const { data, loading, reload } = useApi<Detail>(`/api/performance/${uid}?month=${month}`)
  const [dim, setDim] = useState(dims[0])
  const [text, setText] = useState('')
  const [err, setErr] = useState('')
  if (loading && !data) return <Modal title="Profile" onClose={onClose}><Loading /></Modal>
  if (!data) return <Modal title="Profile" onClose={onClose}><ErrorBox msg="Could not load this profile." /></Modal>
  const done = () => { reload(); onChanged() }
  async function add(e: FormEvent) { e.preventDefault(); try { await api('/api/performance/reviews', { method: 'POST', body: { user_id: uid, month, dimension: dim, comment: text } }); toast('Review comment added'); setText(''); setErr(''); done() } catch (x) { setErr((x as Error).message) } }
  async function ack(id: number) { try { await api(`/api/performance/reviews/${id}/ack`, { method: 'POST', body: { note: 'Read and understood.' } }); toast('Acknowledged'); done() } catch (x) { toast((x as Error).message) } }
  return (
    <Modal title={`${data.name} · ${data.title}`} onClose={onClose} wide>
      <div className="grid g3 mb">
        <Kpi label="Tasks" value={`${data.tasks.done} / ${data.tasks.assigned}`} sub={`${data.tasks.overdue} overdue, ${data.tasks.blocked} blocked`} />
        <Kpi label="Estimate accuracy" value={pct(data.estimates.accuracy_pct)} sub={`${data.estimates.approved_hours} h against ${data.estimates.estimated_hours} h estimated`} />
        <Kpi label="Hours this month" value={`${data.hours.approved} / ${data.hours.planned}`} sub={`Approved / planned (${pct(data.hours.utilization_pct)})`} />
      </div>
      <h2>Projects this month</h2>
      {data.projects.length === 0 ? <div className="empty">No allocation or approved hours.</div> : <div className="tw"><table><thead><tr><th>Project</th><th className="n">Planned h</th><th className="n">Approved h</th></tr></thead><tbody>{data.projects.map((p) => <tr key={p.project}><td>{p.project}</td><td className="n">{p.planned_hours}</td><td className="n">{p.approved_hours}</td></tr>)}</tbody></table></div>}
      <h2 style={{ marginTop: 14 }}>Review comments</h2>
      {data.reviews.length === 0 ? <div className="empty">No comments yet.</div> : data.reviews.map((r) => (
        <div className="card" key={r.id} style={{ margin: '8px 0' }}><b>{r.dimension}</b> <small>· {r.by} · {r.at}</small><p style={{ margin: '6px 0' }}>{r.comment}</p>
          {r.acknowledged ? <Chip text={`Acknowledged${r.ack_note ? ': ' + r.ack_note : ''}`} tone="ok" /> : r.mine ? <button className="btn sm pri" onClick={() => ack(r.id)}>Acknowledge</button> : <Chip text="Waiting for the employee" tone="warn" />}</div>))}
      {data.can_review && <form className="f" onSubmit={add} style={{ marginTop: 10 }}>
        <label>Dimension<select value={dim} onChange={(e) => setDim(e.target.value)}>{dims.map((d) => <option key={d}>{d}</option>)}</select></label>
        <label>Evidence-based comment<textarea required value={text} onChange={(e) => setText(e.target.value)} placeholder="What happened, when, and what you expect next." /></label>
        {err && <div className="note e" role="alert">{err}</div>}<div className="mf" style={{ padding: 0, border: 0 }}><button className="btn pri">Add comment</button></div></form>}
    </Modal>
  )
}
