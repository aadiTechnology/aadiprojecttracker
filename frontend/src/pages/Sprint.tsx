import { FormEvent, useMemo, useState } from 'react'
import { Me, api, useApi } from '../api'
import { Chip, ErrorBox, Loading, Modal, PageHead, toast } from '../ui'

export interface Task {
  id: number; project_id: number; project: string; sprint_id: number | null; sprint: string | null; title: string; description: string
  status: string; priority: string; est_hours: number; assignee_id: number | null; assignee: string | null; due_date: string | null; can_manage: boolean
}
export interface Sprint {
  id: number; project_id: number; project: string; name: string; goal: string; start_date: string | null; end_date: string | null
  status: string; total: number; done: number; hours: number; can_manage: boolean
}
const STATUSES = ['Todo', 'In progress', 'Blocked', 'Done']
const prioTone: Record<string, string> = { High: 'bad', Medium: 'warn', Low: '' }

export default function SprintPage({ me }: { me: Me }) {
  const sp = useApi<Sprint[]>('/api/sprints')
  const [project, setProject] = useState('')
  const [sprintId, setSprintId] = useState('')
  const [mine, setMine] = useState(false)
  const qs = `/api/tasks?${mine ? 'mine=true&' : ''}${project ? `project_id=${project}&` : ''}${sprintId ? `sprint_id=${sprintId}` : ''}`
  const tk = useApi<Task[]>(qs)
  const [detail, setDetail] = useState<number | null>(null)
  const [newTask, setNewTask] = useState(false)
  const [newSprint, setNewSprint] = useState(false)
  const canUpdate = me.perms.some((p) => p.startsWith('sprint.update'))
  const canManage = me.perms.some((p) => p.startsWith('sprint.manage'))
  const projects = useMemo(() => {
    const map = new Map<number, string>()
    sp.data?.forEach((s) => map.set(s.project_id, s.project))
    tk.data?.forEach((t) => map.set(t.project_id, t.project))
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [sp.data, tk.data])
  const shownSprints = (sp.data ?? []).filter((s) => !project || s.project_id === +project)
  const reload = () => { sp.reload(); tk.reload() }
  const run = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); toast(ok); reload() } catch (x) { toast((x as Error).message) } }

  return (
    <>
      <PageHead title="Sprint Planning" sub="Sprints and tasks for the projects in your scope. You see only the work your role allows." />
      <div className="tools">
        <label>Project <select value={project} onChange={(e) => { setProject(e.target.value); setSprintId('') }}><option value="">All</option>{projects.map(([id, n]) => <option key={id} value={id}>{n}</option>)}</select></label>
        <label>Sprint <select value={sprintId} onChange={(e) => setSprintId(e.target.value)}><option value="">All</option>{shownSprints.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
        <label style={{ display: 'inline-flex', gap: 4 }}><input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} />My tasks only</label>
        <span style={{ flex: 1 }} />
        {canManage && <button className="btn" onClick={() => setNewSprint(true)}>+ New sprint</button>}
        {canManage && <button className="btn pri" onClick={() => setNewTask(true)}>+ New task</button>}
      </div>
      {sp.loading ? <Loading /> : sp.error ? <ErrorBox msg={sp.error} /> : shownSprints.length > 0 && (
        <div className="grid g3 mb">{shownSprints.slice(0, 6).map((s) => (
          <div className="card" key={s.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}><b>{s.name}</b><Chip text={s.status} tone={s.status === 'Active' ? 'ok' : s.status === 'Planned' ? 'info' : ''} /></div>
            <small>{s.project}</small>
            <div className="bar" style={{ margin: '8px 0 4px' }} role="img" aria-label={`${s.done} of ${s.total} tasks done`}><i style={{ width: `${s.total ? (100 * s.done) / s.total : 0}%` }} /></div>
            <small>{s.done}/{s.total} done · {s.hours.toFixed(0)} h planned · {s.start_date ?? '—'} to {s.end_date ?? '—'}</small>
            {s.can_manage && s.status !== 'Closed' && <div style={{ marginTop: 8 }}>
              <button className="btn sm" onClick={() => run(() => api(`/api/sprints/${s.id}/status`, { method: 'POST', body: { status: s.status === 'Planned' ? 'Active' : 'Closed' } }), s.status === 'Planned' ? 'Sprint started' : 'Sprint closed')}>{s.status === 'Planned' ? 'Start sprint' : 'Close sprint'}</button></div>}
          </div>))}</div>)}
      {tk.loading ? <Loading /> : tk.error ? <ErrorBox msg={tk.error} /> : (
        <div className="card flat"><div className="tw"><table>
          <thead><tr><th>Task</th><th>Project</th><th>Sprint</th><th>Assignee</th><th>Priority</th><th className="n">Est. h</th><th>Due</th><th>Status</th></tr></thead>
          <tbody>{tk.data!.length === 0 ? <tr><td colSpan={8}><div className="empty">No tasks match.</div></td></tr> : tk.data!.map((t) => (
            <tr key={t.id}>
              <td><button className="btn sm" style={{ border: 0, fontWeight: 600 }} onClick={() => setDetail(t.id)}>{t.title}</button></td>
              <td>{t.project}</td><td>{t.sprint ?? '—'}</td><td>{t.assignee ?? <i>Unassigned</i>}</td><td><Chip text={t.priority} tone={prioTone[t.priority]} /></td>
              <td className="n">{t.est_hours}</td><td>{t.due_date ?? '—'}</td>
              <td>{canUpdate ? <select aria-label={`Status of ${t.title}`} value={t.status} onChange={(e) => run(() => api(`/api/tasks/${t.id}/status`, { method: 'POST', body: { status: e.target.value } }), 'Status updated')}>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select> : <Chip text={t.status} />}</td>
            </tr>))}</tbody></table></div></div>)}
      {detail && <TaskModal id={detail} onClose={() => setDetail(null)} onChanged={reload} />}
      {newTask && <NewTask sprints={sp.data ?? []} projects={projects} onClose={() => setNewTask(false)} onSaved={() => { setNewTask(false); reload() }} />}
      {newSprint && <NewSprint projects={projects} onClose={() => setNewSprint(false)} onSaved={() => { setNewSprint(false); reload() }} />}
    </>
  )
}

function TaskModal({ id, onClose, onChanged }: { id: number; onClose: () => void; onChanged: () => void }) {
  const { data: d, error, reload } = useApi<Task & { history: { from: string | null; to: string | null; by: string; reason: string; at: string }[]; logged_hours: number | null }>(`/api/tasks/${id}`)
  const people = useApi<{ id: number; name: string }[]>(d?.can_manage ? `/api/projects/${d.project_id}/assignable` : null)
  const [who, setWho] = useState(0)
  const [reason, setReason] = useState('')
  const [err, setErr] = useState('')
  if (error) return <Modal title="Task" onClose={onClose}><ErrorBox msg={error} /></Modal>
  if (!d) return <Modal title="Task" onClose={onClose}><Loading /></Modal>
  async function assign(e: FormEvent) {
    e.preventDefault(); setErr('')
    try { await api(`/api/tasks/${id}/assign`, { method: 'POST', body: { user_id: who, reason } }); toast('Task assigned'); setWho(0); setReason(''); reload(); onChanged() } catch (x) { setErr((x as Error).message) }
  }
  return (
    <Modal wide title={d.title} onClose={onClose}>
      <p><Chip text={d.status} /> <Chip text={d.priority} tone={prioTone[d.priority]} /> {d.project}{d.sprint ? ` · ${d.sprint}` : ''}</p>
      <p><b>Assignee:</b> {d.assignee ?? 'Unassigned'} · <b>Estimate:</b> {d.est_hours} h{d.logged_hours !== null && <> · <b>Logged:</b> {d.logged_hours} h</>} · <b>Due:</b> {d.due_date ?? '—'}</p>
      {d.description && <p>{d.description}</p>}
      <h3>Assignment history</h3>
      <table><thead><tr><th>When</th><th>From</th><th>To</th><th>By</th><th>Reason</th></tr></thead><tbody>
        {d.history.map((h, i) => <tr key={i}><td>{h.at.slice(0, 10)}</td><td>{h.from ?? '—'}</td><td>{h.to}</td><td>{h.by}</td><td>{h.reason}</td></tr>)}</tbody></table>
      {d.can_manage && <form className="tools" style={{ marginTop: 12 }} onSubmit={assign}>
        <select aria-label="Assign to" value={who} onChange={(e) => setWho(+e.target.value)}><option value={0}>Reassign to…</option>{people.data?.filter((p) => p.id !== d.assignee_id).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
        <input aria-label="Reason" placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} /><button className="btn pri" disabled={!who}>Assign</button></form>}
      {err && <div className="err" role="alert">{err}</div>}
    </Modal>
  )
}

function NewTask({ sprints, projects, onClose, onSaved }: { sprints: Sprint[]; projects: [number, string][]; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({ project_id: 0, sprint_id: 0, title: '', description: '', priority: 'Medium', est_hours: '', assignee_id: 0, due_date: '' })
  const [err, setErr] = useState('')
  const people = useApi<{ id: number; name: string }[]>(f.project_id ? `/api/projects/${f.project_id}/assignable` : null)
  const set = (k: string, v: string | number) => setF({ ...f, [k]: v })
  async function save(e: FormEvent) {
    e.preventDefault(); setErr('')
    try {
      await api('/api/tasks', { method: 'POST', body: { project_id: f.project_id, sprint_id: f.sprint_id || null, title: f.title, description: f.description, priority: f.priority, est_hours: parseFloat(f.est_hours || '0'), assignee_id: f.assignee_id || null, due_date: f.due_date || null } })
      toast('Task created'); onSaved()
    } catch (x) { setErr((x as Error).message) }
  }
  return (
    <Modal title="New task" onClose={onClose}><form className="f" onSubmit={save}>
      <label>Project<select required value={f.project_id} onChange={(e) => setF({ ...f, project_id: +e.target.value, sprint_id: 0, assignee_id: 0 })}><option value={0}>Choose…</option>{projects.map(([id, n]) => <option key={id} value={id}>{n}</option>)}</select></label>
      <label>Title<input required value={f.title} onChange={(e) => set('title', e.target.value)} /></label>
      <div className="row">
        <label>Sprint<select value={f.sprint_id} onChange={(e) => set('sprint_id', +e.target.value)}><option value={0}>Backlog</option>{sprints.filter((s) => s.project_id === f.project_id && s.status !== 'Closed').map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
        <label>Assignee<select value={f.assignee_id} onChange={(e) => set('assignee_id', +e.target.value)}><option value={0}>Unassigned</option>{people.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      </div>
      <div className="row">
        <label>Priority<select value={f.priority} onChange={(e) => set('priority', e.target.value)}><option>Low</option><option>Medium</option><option>High</option></select></label>
        <label>Estimate (hours)<input inputMode="decimal" value={f.est_hours} onChange={(e) => set('est_hours', e.target.value)} /></label>
      </div>
      <label>Due date<input type="date" value={f.due_date} onChange={(e) => set('due_date', e.target.value)} /></label>
      <label>Description<textarea value={f.description} onChange={(e) => set('description', e.target.value)} /></label>
      {err && <div className="err" role="alert">{err}</div>}
      <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn pri">Create task</button></div>
    </form></Modal>
  )
}

function NewSprint({ projects, onClose, onSaved }: { projects: [number, string][]; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({ project_id: 0, name: '', goal: '', start_date: '', end_date: '' })
  const [err, setErr] = useState('')
  async function save(e: FormEvent) {
    e.preventDefault(); setErr('')
    try { await api('/api/sprints', { method: 'POST', body: { ...f, start_date: f.start_date || null, end_date: f.end_date || null } }); toast('Sprint created'); onSaved() } catch (x) { setErr((x as Error).message) }
  }
  return (
    <Modal title="New sprint" onClose={onClose}><form className="f" onSubmit={save}>
      <label>Project<select required value={f.project_id} onChange={(e) => setF({ ...f, project_id: +e.target.value })}><option value={0}>Choose…</option>{projects.map(([id, n]) => <option key={id} value={id}>{n}</option>)}</select></label>
      <label>Sprint name<input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
      <label>Goal<input value={f.goal} onChange={(e) => setF({ ...f, goal: e.target.value })} /></label>
      <div className="row"><label>Start<input type="date" value={f.start_date} onChange={(e) => setF({ ...f, start_date: e.target.value })} /></label><label>End<input type="date" value={f.end_date} onChange={(e) => setF({ ...f, end_date: e.target.value })} /></label></div>
      {err && <div className="err" role="alert">{err}</div>}
      <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn pri">Create sprint</button></div>
    </form></Modal>
  )
}
