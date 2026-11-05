import { FormEvent, useState } from 'react'
import { Me, api, useApi } from '../api'
import { Chip, ErrorBox, Loading, Modal, PageHead, toast } from '../ui'
import type { Task } from './Sprint'

interface H {
  id: number; project_id: number; project: string; from: string; to: string; note: string; status: string; created_at: string
  ack_at: string | null; ack_note: string; tasks: { id: number; title: string }[]; can_ack: boolean
}

export default function Handover({ me }: { me: Me }) {
  const { data, error, loading, reload } = useApi<H[]>('/api/handovers')
  const [ack, setAck] = useState<H | null>(null)
  const [adding, setAdding] = useState(false)
  const canCreate = me.perms.some((p) => p.startsWith('handover.manage'))
  return (
    <>
      <PageHead title="Team Handover" sub="Hand work from one person to another. The receiver must acknowledge it; ownership and the reason are kept in the task history." />
      <div className="tools"><span style={{ flex: 1 }} />{canCreate && <button className="btn pri" onClick={() => setAdding(true)}>+ New handover</button>}</div>
      {loading ? <Loading /> : error ? <ErrorBox msg={error} /> : data!.length === 0 ? <div className="card empty">No handovers in your scope.</div> : (
        <div className="grid g2">{data!.map((h) => (
          <div className="card" key={h.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}><b>{h.from} → {h.to}</b><Chip text={h.status} tone={h.status === 'Pending' ? 'warn' : 'ok'} /></div>
            <small>{h.project} · {h.created_at.slice(0, 10)}</small>
            <p style={{ margin: '8px 0' }}>{h.note}</p>
            {h.tasks.length > 0 && <ul style={{ margin: '0 0 8px 18px', padding: 0 }}>{h.tasks.map((t) => <li key={t.id}>{t.title}</li>)}</ul>}
            {h.status === 'Acknowledged' && <small>Acknowledged {h.ack_at?.slice(0, 10)}{h.ack_note ? `: “${h.ack_note}”` : ''}</small>}
            {h.can_ack && <button className="btn pri sm" onClick={() => setAck(h)}>Acknowledge</button>}
          </div>))}</div>)}
      {ack && <AckModal h={ack} onClose={() => setAck(null)} onDone={() => { setAck(null); reload() }} />}
      {adding && <NewHandover onClose={() => setAdding(false)} onSaved={() => { setAdding(false); reload() }} />}
    </>
  )
}

function AckModal({ h, onClose, onDone }: { h: H; onClose: () => void; onDone: () => void }) {
  const [note, setNote] = useState('')
  const [err, setErr] = useState('')
  async function go(e: FormEvent) { e.preventDefault(); try { await api(`/api/handovers/${h.id}/ack`, { method: 'POST', body: { note } }); toast('Handover acknowledged'); onDone() } catch (x) { setErr((x as Error).message) } }
  return (
    <Modal title="Acknowledge handover" onClose={onClose}><form className="f" onSubmit={go}>
      <p><b>{h.from}</b> hands over {h.tasks.length} task(s) on {h.project}:</p><p>{h.note}</p>
      <label>Your note (optional)<textarea value={note} onChange={(e) => setNote(e.target.value)} /></label>
      {err && <div className="err" role="alert">{err}</div>}
      <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn pri">I have received this</button></div>
    </form></Modal>
  )
}

function NewHandover({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const tasks = useApi<Task[]>('/api/tasks')
  const [f, setF] = useState({ project_id: 0, from: 0, to: 0, note: '' })
  const [picked, setPicked] = useState<number[]>([])
  const [err, setErr] = useState('')
  const people = useApi<{ id: number; name: string }[]>(f.project_id ? `/api/projects/${f.project_id}/assignable` : null)
  const projects = [...new Map((tasks.data ?? []).filter((t) => t.can_manage).map((t) => [t.project_id, t.project])).entries()]
  const mine = (tasks.data ?? []).filter((t) => t.project_id === f.project_id && t.assignee_id === f.from && t.status !== 'Done')
  async function save(e: FormEvent) {
    e.preventDefault(); setErr('')
    try { await api('/api/handovers', { method: 'POST', body: { project_id: f.project_id, from_user_id: f.from, to_user_id: f.to, task_ids: picked, note: f.note } }); toast('Handover sent for acknowledgement'); onSaved() } catch (x) { setErr((x as Error).message) }
  }
  return (
    <Modal title="New handover" onClose={onClose}><form className="f" onSubmit={save}>
      <label>Project<select required value={f.project_id} onChange={(e) => { setF({ ...f, project_id: +e.target.value, from: 0, to: 0 }); setPicked([]) }}><option value={0}>Choose…</option>{projects.map(([id, n]) => <option key={id} value={id}>{n}</option>)}</select></label>
      <div className="row">
        <label>From<select required value={f.from} onChange={(e) => { setF({ ...f, from: +e.target.value }); setPicked([]) }}><option value={0}>Choose…</option>{people.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label>To<select required value={f.to} onChange={(e) => setF({ ...f, to: +e.target.value })}><option value={0}>Choose…</option>{people.data?.filter((p) => p.id !== f.from).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      </div>
      {f.from > 0 && <fieldset style={{ border: '1px solid var(--line)', borderRadius: 8 }}><legend>Tasks to hand over</legend>
        {mine.length === 0 ? <small>This person holds no open tasks on the project (you can still hand over knowledge).</small> : mine.map((t) => (
          <label key={t.id} style={{ display: 'flex', gap: 6, fontWeight: 400 }}><input type="checkbox" checked={picked.includes(t.id)} onChange={(e) => setPicked(e.target.checked ? [...picked, t.id] : picked.filter((x) => x !== t.id))} />{t.title}</label>))}</fieldset>}
      <label>Handover note (context, status, next steps)<textarea required value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></label>
      {err && <div className="err" role="alert">{err}</div>}
      <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn pri">Send handover</button></div>
    </form></Modal>
  )
}
