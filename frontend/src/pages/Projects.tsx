import { FormEvent, useState } from 'react'
import { Me, api, money, toMinor, useApi } from '../api'
import { Chip, ErrorBox, Loading, Modal, PageHead, toast, useDebounced } from '../ui'

interface P {
  id: number; code: string; name: string; category: string; customer_id: number; customer: string; pm: string | null; pm_user_id: number | null; status: string
  tags: { id: number; name: string }[]
  health?: string; billing_model?: string; start_date?: string | null; end_date?: string | null; est_hours?: number; budget_minor?: number; contract_value_minor?: number
}
interface Detail extends P {
  scope: string; can_manage: boolean; transitions: string[]
  members: { user_id: number; name: string; allocation_pct: number; role_label: string }[]
  milestones: { id: number; name: string; due_date: string | null; status: string; amount_minor?: number }[]
  scope_changes: { id: number; description: string; reason: string; requested_by: string; approved_by: string | null; status: string; at: string }[]
}
const CATS = ['Software Development', 'Software Services', 'Marketing', 'Sales']
type Person = { id: number; name: string; title: string }

export default function Projects({ me }: { me: Me }) {
  const [q, setQ] = useState(''); const [status, setStatus] = useState(''); const [cat, setCat] = useState('')
  const [tagIds, setTagIds] = useState<number[]>([])
  const allTags = useApi<{ id: number; name: string; archived: boolean }[]>('/api/tags')
  const dq = useDebounced(q)
  const { data, error, loading, reload } = useApi<P[]>(`/api/projects?q=${encodeURIComponent(dq)}&status=${status}&category=${encodeURIComponent(cat)}&tags=${tagIds.join(',')}`)
  const canCreate = me.perms.includes('projects.manage:all')
  const [open, setOpen] = useState<number | null>(null)
  const [creating, setCreating] = useState(false)
  const sample = data?.[0]
  const hasBudget = sample?.budget_minor !== undefined, hasContract = sample?.contract_value_minor !== undefined, hasDelivery = sample?.health !== undefined

  return (
    <>
      <PageHead title="Projects" sub="Software development, software services, marketing and sales initiatives. You see only what your role allows." />
      <div className="tools">
        <input type="search" aria-label="Search projects" placeholder="Search projects or code…" value={q} onChange={(e) => setQ(e.target.value)} />
        <label>Category <select value={cat} onChange={(e) => setCat(e.target.value)}><option value="">All</option>{CATS.map((c) => <option key={c}>{c}</option>)}</select></label>
        <label>Status <select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All</option>{['Draft', 'Planned', 'Active', 'On Hold', 'Completed', 'Cancelled'].map((c) => <option key={c}>{c}</option>)}</select></label>
        {canCreate && <button className="btn pri" onClick={() => setCreating(true)}>+ New project</button>}
      </div>
      {allTags.data && allTags.data.length > 0 && <div className="tools" role="group" aria-label="Filter by tag"><b>Tags</b>{allTags.data.filter((t) => !t.archived).map((t) => <button key={t.id} type="button" className={`chip ${tagIds.includes(t.id) ? 'on' : ''}`} aria-pressed={tagIds.includes(t.id)} onClick={() => setTagIds((s) => s.includes(t.id) ? s.filter((x) => x !== t.id) : [...s, t.id])}>{t.name}</button>)}{tagIds.length > 0 && <button className="btn sm" onClick={() => setTagIds([])}>Clear tags</button>}</div>}
      {loading ? <Loading /> : error ? <ErrorBox msg={error} /> : (
        <div className="card flat"><div className="tw"><table>
          <thead><tr><th>Project</th><th>Category</th><th>Customer / unit</th><th>Tags</th><th>PM</th><th>Status</th>{hasDelivery && <th>Health</th>}{hasBudget && <th className="n">Budget</th>}{hasContract && <th className="n">Contract value</th>}{hasDelivery && <th className="n">Est. hours</th>}</tr></thead>
          <tbody>{data!.length === 0 ? <tr><td colSpan={10}><div className="empty">No projects match the filters, or none are assigned to you.</div></td></tr> : data!.map((p) => (
            <tr key={p.id} className="click" onClick={() => setOpen(p.id)}>
              <td><button className="btn sm" style={{ border: 0, padding: 0, fontWeight: 700, color: 'var(--acc)' }} onClick={(e) => { e.stopPropagation(); setOpen(p.id) }}>{p.name}</button><br /><small>{p.code}</small></td>
              <td>{p.category}</td><td>{p.customer}</td><td>{p.tags.map((t) => <Chip key={t.id} text={t.name} tone="acc" />)}</td><td>{p.pm ?? '—'}</td><td><Chip text={p.status} /></td>
              {hasDelivery && <td><Chip text={p.health!} /></td>}{hasBudget && <td className="n">{money(p.budget_minor)}</td>}{hasContract && <td className="n">{money(p.contract_value_minor)}</td>}{hasDelivery && <td className="n">{p.est_hours}</td>}</tr>))}</tbody></table></div></div>)}
      {hasContract && <p className="note" style={{ marginTop: 12 }}>Contract value is expected revenue. Recognized revenue arrives with invoicing in Sprint 4 and depends on the customer’s revenue-basis decision.</p>}
      {open !== null && <ProjectModal id={open} me={me} onClose={() => setOpen(null)} onChanged={reload} />}
      {creating && <ProjectForm onClose={() => setCreating(false)} onSaved={() => { setCreating(false); reload() }} />}
    </>
  )
}

function ProjectForm({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const cust = useApi<{ id: number; name: string }[]>('/api/customers')
  const people = useApi<Person[]>('/api/people')
  const [f, setF] = useState({ name: '', category: 'Software Services', customer_id: 0, pm_user_id: 0, billing_model: 'fixed', start_date: '', end_date: '', scope: '', budget: '', contract: '', est_hours: '' })
  const [err, setErr] = useState('')
  const set = (k: string, v: string | number) => setF((s) => ({ ...s, [k]: v }))
  async function save(e: FormEvent) {
    e.preventDefault(); setErr('')
    try {
      await api('/api/projects', { method: 'POST', body: { name: f.name, category: f.category, customer_id: +f.customer_id, pm_user_id: +f.pm_user_id || null, billing_model: f.billing_model, start_date: f.start_date || null, end_date: f.end_date || null, scope: f.scope, budget_minor: toMinor(f.budget), contract_value_minor: toMinor(f.contract), est_hours: parseFloat(f.est_hours || '0') } })
      toast('Project created as Draft'); onSaved()
    } catch (x) { setErr((x as Error).message) }
  }
  return (
    <Modal title="New project" onClose={onClose}>
      <form className="f" onSubmit={save}>
        <label>Project name<input required value={f.name} onChange={(e) => set('name', e.target.value)} /></label>
        <div className="row">
          <label>Category<select value={f.category} onChange={(e) => set('category', e.target.value)}>{CATS.map((c) => <option key={c}>{c}</option>)}</select></label>
          <label>Customer / business unit<select required value={f.customer_id} onChange={(e) => set('customer_id', +e.target.value)}><option value={0}>Choose…</option>{cust.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
        </div>
        <div className="row">
          <label>Project manager<select value={f.pm_user_id} onChange={(e) => set('pm_user_id', +e.target.value)}><option value={0}>— assign later —</option>{people.data?.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.title}</option>)}</select></label>
          <label>Billing model<select value={f.billing_model} onChange={(e) => set('billing_model', e.target.value)}><option value="fixed">Fixed price</option><option value="time_and_material">Time &amp; material</option><option value="milestone">Milestone</option></select></label>
        </div>
        <div className="row"><label>Start date<input type="date" value={f.start_date} onChange={(e) => set('start_date', e.target.value)} /></label><label>End date<input type="date" value={f.end_date} onChange={(e) => set('end_date', e.target.value)} /></label></div>
        <div className="row"><label>Budget (₹)<input inputMode="decimal" value={f.budget} onChange={(e) => set('budget', e.target.value)} /></label><label>Contract value (₹, expected revenue)<input inputMode="decimal" value={f.contract} onChange={(e) => set('contract', e.target.value)} /></label></div>
        <label>Estimated hours<input inputMode="decimal" value={f.est_hours} onChange={(e) => set('est_hours', e.target.value)} /></label>
        <label>Scope and deliverables<textarea value={f.scope} onChange={(e) => set('scope', e.target.value)} /></label>
        {err && <div className="err" role="alert">{err}</div>}
        <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn pri">Create project</button></div>
      </form>
    </Modal>
  )
}

function ProjectModal({ id, me, onClose, onChanged }: { id: number; me: Me; onClose: () => void; onChanged: () => void }) {
  const { data: d, error, reload } = useApi<Detail>(`/api/projects/${id}`)
  const people = useApi<Person[]>(d?.can_manage ? '/api/people' : null)
  const [tab, setTab] = useState('Overview')
  const [err, setErr] = useState('')
  const [m, setM] = useState({ user_id: 0, allocation_pct: '100', role_label: '' })
  const [ms, setMs] = useState({ name: '', due_date: '' })
  const [sc, setSc] = useState({ description: '', reason: '' })
  const run = async (fn: () => Promise<unknown>, ok: string) => { setErr(''); try { await fn(); toast(ok); reload(); onChanged() } catch (x) { setErr((x as Error).message) } }
  if (error) return <Modal title="Project" onClose={onClose}><ErrorBox msg={error} /></Modal>
  if (!d) return <Modal title="Project" onClose={onClose}><Loading /></Modal>
  const money_ = d.budget_minor !== undefined || d.contract_value_minor !== undefined
  return (
    <Modal wide title={`${d.code} · ${d.name}`} onClose={onClose}>
      <div className="tabs" role="tablist">{['Overview', 'Team', 'Milestones', 'Scope changes'].map((t) => <button key={t} role="tab" aria-selected={tab === t} className="tab" onClick={() => setTab(t)}>{t}</button>)}</div>
      {err && <div className="err" role="alert">{err}</div>}
      {tab === 'Overview' && <div>
        <p><Chip text={d.status} /> {d.health && <Chip text={`Health: ${d.health}`} tone={d.health === 'Green' ? 'ok' : d.health === 'Amber' ? 'warn' : 'bad'} />} <Chip text={d.category} tone="acc" /></p>
        <TagEditor id={id} tags={d.tags} canTag={me.perms.some((x) => x.startsWith('projects.tag'))} onChanged={() => { reload(); onChanged() }} />
        <p><b>Customer / unit:</b> {d.customer} · <b>Project manager:</b> {d.pm ?? 'not assigned'}</p>
        {d.billing_model && <p><b>Billing:</b> {d.billing_model.replace(/_/g, ' ')} · <b>Dates:</b> {d.start_date ?? '—'} to {d.end_date ?? '—'} · <b>Estimate:</b> {d.est_hours} h</p>}
        {money_ && <p>{d.budget_minor !== undefined && <><b>Budget:</b> {money(d.budget_minor)} </>}{d.contract_value_minor !== undefined && <>· <b>Contract value (expected):</b> {money(d.contract_value_minor)}</>}</p>}
        <h3>Scope</h3><p style={{ whiteSpace: 'pre-wrap' }}>{d.scope || 'Scope not defined yet.'}</p>
        {d.can_manage && d.transitions.length > 0 && <div className="tools"><b>Move to:</b>{d.transitions.map((t) => <button key={t} className="btn sm" onClick={() => run(() => api(`/api/projects/${id}/status`, { method: 'POST', body: { status: t } }), `Status changed to ${t}`)}>{t}</button>)}</div>}
        {d.can_manage && <div className="tools"><b>Health:</b>{['Green', 'Amber', 'Red'].map((h) => <button key={h} className="btn sm" onClick={() => run(() => api(`/api/projects/${id}/status`, { method: 'POST', body: { status: d.status, health: h } }), `Health set to ${h}`)}>{h}</button>)}</div>}
      </div>}
      {tab === 'Team' && <div>
        <table><thead><tr><th>Person</th><th>Role on project</th><th className="n">Allocation</th>{d.can_manage && <th />}</tr></thead><tbody>
          {d.members.map((x) => <tr key={x.user_id}><td>{x.name}</td><td>{x.role_label}</td><td className="n">{x.allocation_pct}%</td>{d.can_manage && <td>{x.user_id !== d.pm_user_id && <button className="btn sm danger" onClick={() => run(() => api(`/api/projects/${id}/members/${x.user_id}`, { method: 'DELETE' }), 'Removed from project')}>Remove</button>}</td>}</tr>)}</tbody></table>
        {d.can_manage && <form className="tools" style={{ marginTop: 12 }} onSubmit={(e) => { e.preventDefault(); run(() => api(`/api/projects/${id}/members`, { method: 'POST', body: { user_id: m.user_id, allocation_pct: +m.allocation_pct, role_label: m.role_label } }), 'Added to project') }}>
          <select aria-label="Person" value={m.user_id} onChange={(e) => setM({ ...m, user_id: +e.target.value })}><option value={0}>Add person…</option>{people.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
          <input aria-label="Allocation percent" style={{ width: 80 }} value={m.allocation_pct} onChange={(e) => setM({ ...m, allocation_pct: e.target.value })} />%
          <input aria-label="Role on project" placeholder="Role" value={m.role_label} onChange={(e) => setM({ ...m, role_label: e.target.value })} /><button className="btn pri" disabled={!m.user_id}>Add</button></form>}
      </div>}
      {tab === 'Milestones' && <div>
        {d.milestones.length === 0 ? <div className="empty">No milestones yet.</div> : <table><thead><tr><th>Milestone</th><th>Due</th><th>Status</th>{d.milestones.some((x) => x.amount_minor !== undefined) && <th className="n">Amount</th>}</tr></thead><tbody>
          {d.milestones.map((x) => <tr key={x.id}><td>{x.name}</td><td>{x.due_date ?? '—'}</td><td><Chip text={x.status} /></td>{x.amount_minor !== undefined && <td className="n">{money(x.amount_minor)}</td>}</tr>)}</tbody></table>}
        {d.can_manage && <form className="tools" style={{ marginTop: 12 }} onSubmit={(e) => { e.preventDefault(); run(() => api(`/api/projects/${id}/milestones`, { method: 'POST', body: { name: ms.name, due_date: ms.due_date || null } }), 'Milestone added'); setMs({ name: '', due_date: '' }) }}>
          <input aria-label="Milestone name" placeholder="New milestone" value={ms.name} onChange={(e) => setMs({ ...ms, name: e.target.value })} required /><input aria-label="Due date" type="date" value={ms.due_date} onChange={(e) => setMs({ ...ms, due_date: e.target.value })} /><button className="btn pri">Add</button></form>}
      </div>}
      {tab === 'Scope changes' && <div>
        {d.scope_changes.length === 0 ? <div className="empty">No scope changes recorded.</div> : d.scope_changes.map((x) => (
          <div className="card mb" key={x.id}><p style={{ margin: 0 }}><Chip text={x.status} /> {x.description}</p><small>Requested by {x.requested_by} on {x.at.slice(0, 10)}{x.reason ? ` · Reason: ${x.reason}` : ''}{x.approved_by ? ` · Decided by ${x.approved_by}` : ''}</small>
            {d.can_manage && x.status === 'Requested' && <div className="tools" style={{ marginTop: 8 }}>
              <button className="btn sm pri" onClick={() => run(() => api(`/api/projects/${id}/scope-changes/${x.id}/decision`, { method: 'POST', body: { approve: true } }), 'Scope change approved')}>Approve</button>
              <button className="btn sm" onClick={() => run(() => api(`/api/projects/${id}/scope-changes/${x.id}/decision`, { method: 'POST', body: { approve: false } }), 'Scope change rejected')}>Reject</button></div>}</div>))}
        {d.can_manage && <form className="f" onSubmit={(e) => { e.preventDefault(); run(() => api(`/api/projects/${id}/scope-changes`, { method: 'POST', body: sc }), 'Scope change requested'); setSc({ description: '', reason: '' }) }}>
          <label>Describe the change<input value={sc.description} onChange={(e) => setSc({ ...sc, description: e.target.value })} required /></label>
          <label>Reason<input value={sc.reason} onChange={(e) => setSc({ ...sc, reason: e.target.value })} /></label><button className="btn pri" style={{ justifySelf: 'start' }}>Request scope change</button></form>}
        <p className="note" style={{ marginTop: 10 }}>Every scope change records date, reason, requester and approver. The requester cannot approve their own change unless they manage all projects.</p>
      </div>}
      {!d.can_manage && <p className="note" style={{ marginTop: 10 }}>{me.role.name}: view only for this project.</p>}
    </Modal>
  )
}

function TagEditor({ id, tags, canTag, onChanged }: { id: number; tags: { id: number; name: string }[]; canTag: boolean; onChanged: () => void }) {
  const all = useApi<{ id: number; name: string; archived: boolean }[]>(canTag ? '/api/tags' : null)
  const [editing, setEditing] = useState(false)
  const [sel, setSel] = useState<number[]>([])
  async function save() {
    try { await api(`/api/projects/${id}/tags`, { method: 'PUT', body: { tag_ids: sel } }); toast('Tags saved'); setEditing(false); onChanged() } catch (x) { toast((x as Error).message) }
  }
  return (
    <div className="tools" style={{ marginBottom: 6 }}><b>Tags</b>
      {!editing && (tags.length ? tags.map((t, i) => <Chip key={t.id} text={i === 0 ? `${t.name} (primary)` : t.name} tone="acc" />) : <small>No tags yet</small>)}
      {canTag && !editing && <button className="btn sm" onClick={() => { setSel(tags.map((t) => t.id)); setEditing(true) }}>Edit tags</button>}
      {editing && <>{all.data?.filter((t) => !t.archived).map((t) => <label key={t.id} style={{ display: 'inline-flex', gap: 4 }}><input type="checkbox" checked={sel.includes(t.id)} onChange={(e) => setSel((s) => e.target.checked ? [...s, t.id] : s.filter((x) => x !== t.id))} />{t.name}</label>)}
        <button className="btn sm pri" onClick={save}>Save tags</button><button className="btn sm" onClick={() => setEditing(false)}>Cancel</button><small>The first tag selected is the primary tag.</small></>}
    </div>
  )
}
