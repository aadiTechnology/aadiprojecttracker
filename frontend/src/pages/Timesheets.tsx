import { FormEvent, useState } from 'react'
import { Me, api, useApi } from '../api'
import { Chip, ErrorBox, Loading, Modal, PageHead, toast } from '../ui'

interface Entry { id: number; user: string; project: string; project_id: number; task_id: number | null; task: string | null; work_date: string; hours: number; note: string; status: string; reject_reason: string; decided_by: string | null; editable: boolean }
interface Week { week_start: string; week_end: string; entries: Entry[]; total: number; target: number; submittable: boolean }
interface Proj { id: number; label: string; tasks: { id: number; title: string }[] }
const tone: Record<string, string> = { Draft: '', Submitted: 'info', Approved: 'ok', Rejected: 'bad' }
const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const shift = (s: string, days: number) => { const d = new Date(s + 'T00:00:00'); d.setDate(d.getDate() + days); return iso(d) }

export default function Timesheets({ me }: { me: Me }) {
  const approver = me.perms.some((p) => p.startsWith('timesheet.approve'))
  const [tab, setTab] = useState('My timesheet')
  return (
    <>
      <PageHead title="Timesheets" sub="Log time on the projects you are assigned to, submit the week, and approvers review it." />
      {approver && <div className="tabs" role="tablist">{['My timesheet', 'Approvals'].map((t) => <button key={t} role="tab" aria-selected={tab === t} className="tab" onClick={() => setTab(t)}>{t}</button>)}</div>}
      {tab === 'My timesheet' ? <Mine /> : <Approvals />}
    </>
  )
}

function Mine() {
  const [week, setWeek] = useState(iso(new Date()))
  const { data, error, loading, reload } = useApi<Week>(`/api/timesheets?week=${week}`)
  const [edit, setEdit] = useState<Partial<Entry> | null>(null)
  async function submit() { try { const r = await api<{ submitted: number }>('/api/timesheets/submit', { method: 'POST', body: { week } }); toast(`${r.submitted} entries submitted for approval`); reload() } catch (x) { toast((x as Error).message) } }
  async function del(id: number) { try { await api(`/api/timesheets/${id}`, { method: 'DELETE' }); toast('Entry deleted'); reload() } catch (x) { toast((x as Error).message) } }
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load the timesheet.'} />
  const pct = Math.min(100, (100 * data.total) / data.target)
  return (
    <>
      <div className="tools">
        <button className="btn" onClick={() => setWeek(shift(data.week_start, -7))} aria-label="Previous week">‹</button>
        <b>Week of {data.week_start} to {data.week_end}</b>
        <button className="btn" onClick={() => setWeek(shift(data.week_start, 7))} aria-label="Next week">›</button>
        <span style={{ flex: 1 }} />
        <button className="btn" onClick={() => setEdit({ work_date: iso(new Date()) <= data.week_end && iso(new Date()) >= data.week_start ? iso(new Date()) : data.week_start })}>+ Add time</button>
        <button className="btn pri" disabled={!data.submittable} onClick={submit}>Submit week</button>
      </div>
      <div className="card mb"><b>{data.total} of {data.target} hours</b><div className="bar" style={{ marginTop: 6 }}><i style={{ width: `${pct}%` }} /></div></div>
      <div className="card flat"><div className="tw"><table>
        <thead><tr><th>Date</th><th>Project</th><th>Task</th><th className="n">Hours</th><th>Status</th><th /></tr></thead>
        <tbody>{data.entries.length === 0 ? <tr><td colSpan={6}><div className="empty">No time logged this week.</div></td></tr> : data.entries.map((e) => (
          <tr key={e.id}><td>{e.work_date}</td><td>{e.project}</td><td>{e.task ?? e.note}</td><td className="n">{e.hours}</td>
            <td><Chip text={e.status} tone={tone[e.status]} />{e.reject_reason && <><br /><small style={{ color: 'var(--bad)' }}>{e.reject_reason}</small></>}</td>
            <td>{e.editable && <><button className="btn sm" onClick={() => setEdit(e)}>Edit</button> <button className="btn sm danger" onClick={() => del(e.id)}>Delete</button></>}</td></tr>))}</tbody></table></div></div>
      {edit && <EntryModal entry={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); reload() }} />}
    </>
  )
}

function EntryModal({ entry, onClose, onSaved }: { entry: Partial<Entry>; onClose: () => void; onSaved: () => void }) {
  const projs = useApi<Proj[]>('/api/timesheets/projects')
  const [f, setF] = useState({ project_id: entry.project_id ?? 0, task_id: entry.task_id ?? 0, work_date: entry.work_date ?? iso(new Date()), hours: entry.hours ? String(entry.hours) : '', note: entry.note ?? '' })
  const [err, setErr] = useState('')
  const tasks = projs.data?.find((p) => p.id === f.project_id)?.tasks ?? []
  async function save(e: FormEvent) {
    e.preventDefault(); setErr('')
    const body = { project_id: f.project_id, task_id: f.task_id || null, work_date: f.work_date, hours: parseFloat(f.hours), note: f.note }
    try { if (entry.id) await api(`/api/timesheets/${entry.id}`, { method: 'PATCH', body }); else await api('/api/timesheets', { method: 'POST', body }); toast('Time saved'); onSaved() } catch (x) { setErr((x as Error).message) }
  }
  return (
    <Modal title={entry.id ? 'Edit time' : 'Add time'} onClose={onClose}><form className="f" onSubmit={save}>
      <label>Project<select required value={f.project_id} onChange={(e) => setF({ ...f, project_id: +e.target.value, task_id: 0 })}><option value={0}>Choose…</option>{projs.data?.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}</select></label>
      <label>Task<select value={f.task_id} onChange={(e) => setF({ ...f, task_id: +e.target.value })}><option value={0}>— none —</option>{tasks.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}</select></label>
      <div className="row"><label>Date<input type="date" required value={f.work_date} onChange={(e) => setF({ ...f, work_date: e.target.value })} /></label><label>Hours<input inputMode="decimal" required value={f.hours} onChange={(e) => setF({ ...f, hours: e.target.value })} /></label></div>
      <label>Note<input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></label>
      {err && <div className="err" role="alert">{err}</div>}
      <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn pri">Save</button></div>
    </form></Modal>
  )
}

function Approvals() {
  const { data, error, loading, reload } = useApi<{ can_approve: boolean; entries: Entry[] }>('/api/timesheets/approvals?status=Submitted')
  const [sel, setSel] = useState<number[]>([])
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  async function decide(approve: boolean) {
    try { await api('/api/timesheets/decide', { method: 'POST', body: { ids: sel, approve, reason } }); toast(approve ? 'Time approved' : 'Time rejected'); setSel([]); setRejecting(false); setReason(''); reload() } catch (x) { toast((x as Error).message) }
  }
  if (loading) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load approvals.'} />
  const all = data.entries.map((e) => e.id)
  return (
    <>
      <div className="tools"><b>{data.entries.length} entries waiting</b><span style={{ flex: 1 }} />
        <button className="btn pri" disabled={!sel.length} onClick={() => decide(true)}>Approve selected</button>
        <button className="btn danger" disabled={!sel.length} onClick={() => setRejecting(true)}>Reject selected…</button></div>
      <div className="card flat"><div className="tw"><table>
        <thead><tr><th><input type="checkbox" aria-label="Select all" checked={sel.length > 0 && sel.length === all.length} onChange={(e) => setSel(e.target.checked ? all : [])} /></th><th>Person</th><th>Date</th><th>Project</th><th>Task</th><th className="n">Hours</th></tr></thead>
        <tbody>{data.entries.length === 0 ? <tr><td colSpan={6}><div className="empty">Nothing waiting for approval.</div></td></tr> : data.entries.map((e) => (
          <tr key={e.id}><td><input type="checkbox" aria-label={`Select ${e.user} ${e.work_date}`} checked={sel.includes(e.id)} onChange={(x) => setSel(x.target.checked ? [...sel, e.id] : sel.filter((i) => i !== e.id))} /></td>
            <td>{e.user}</td><td>{e.work_date}</td><td>{e.project}</td><td>{e.task ?? e.note}</td><td className="n">{e.hours}</td></tr>))}</tbody></table></div></div>
      {rejecting && <Modal title="Reject time" onClose={() => setRejecting(false)}><form className="f" onSubmit={(e) => { e.preventDefault(); decide(false) }}>
        <label>Reason (the person sees this)<textarea required value={reason} onChange={(e) => setReason(e.target.value)} /></label>
        <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={() => setRejecting(false)}>Cancel</button><button className="btn danger">Reject {sel.length} entries</button></div></form></Modal>}
    </>
  )
}
