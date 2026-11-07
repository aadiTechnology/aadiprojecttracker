import { FormEvent, useState } from 'react'
import { Me, api, inr, thisMonth, toMinor, useApi } from '../api'
import { Chip, ErrorBox, Kpi, Loading, Modal, PageHead, toast } from '../ui'

interface Row { id: number; category: string; vendor: string; description: string; amount_minor: number; spent_on: string; project: string | null; shared: boolean; alloc_method: string | null; status: string }
interface D {
  month: string; can_manage: boolean; categories: string[]; methods: Record<string, string>; projects: { id: number; name: string }[]; rows: Row[]
  totals: { all_minor: number; direct_minor: number; shared_minor: number; unpaid_minor: number }
  by_category: { category: string; amount_minor: number }[]
  allocation: { project_id: number; project: string; direct_minor: number; shared_minor: number; total_minor: number }[]
  unallocated_minor: number; note: string
}
const METHOD_SHORT: Record<string, string> = { equal: 'Equal share', hours: 'By planned hours', headcount: 'By people' }

export default function Expenses({ me }: { me: Me }) {
  const [month, setMonth] = useState(thisMonth())
  const { data, error, loading, reload } = useApi<D>(`/api/expenses?month=${month}`)
  const [adding, setAdding] = useState(false)
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load expenses.'} />
  const act = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); toast(ok); reload() } catch (x) { toast((x as Error).message) } }
  const max = Math.max(1, ...data.by_category.map((c) => c.amount_minor))
  return (
    <>
      <PageHead title="Expenses & Cost Allocation" sub={`Non-salary costs for ${me.tenant.name}. Direct costs belong to one project; shared costs are split between projects with the method you pick.`} />
      <div className="tools"><label>Month <input type="month" value={month} onChange={(e) => setMonth(e.target.value || thisMonth())} /></label><span style={{ flex: 1 }} />
        {data.can_manage && <button className="btn pri" onClick={() => setAdding(true)}>+ Add expense</button>}</div>
      <div className="grid g4 mb">
        <Kpi label="Total expenses" value={inr(data.totals.all_minor)} sub={`${data.rows.length} entries`} />
        <Kpi label="Direct to a project" value={inr(data.totals.direct_minor)} sub="Charged to one project" />
        <Kpi label="Shared overhead" value={inr(data.totals.shared_minor)} sub="Split across projects" />
        <Kpi label="Not paid yet" value={inr(data.totals.unpaid_minor)} sub="Status Planned" />
      </div>
      <div className="grid g2 mb">
        <div className="card"><h2>Spend by category</h2>{data.by_category.length === 0 ? <div className="empty">No expenses this month.</div> : data.by_category.map((c) => (
          <div key={c.category} style={{ margin: '8px 0' }}><div style={{ display: 'flex', justifyContent: 'space-between' }}><span>{c.category}</span><b>{inr(c.amount_minor)}</b></div>
            <div className="bar"><i style={{ width: `${(100 * c.amount_minor) / max}%` }} /></div></div>))}</div>
        <div className="card flat"><div style={{ padding: '14px 16px 0' }}><h2>Cost charged to each project</h2></div><div className="tw"><table>
          <thead><tr><th>Project</th><th className="n">Direct</th><th className="n">Shared share</th><th className="n">Total</th></tr></thead>
          <tbody>{data.allocation.length === 0 ? <tr><td colSpan={4}><div className="empty">Nothing to allocate.</div></td></tr> : data.allocation.map((a) => <tr key={a.project_id}><td>{a.project}</td><td className="n">{inr(a.direct_minor)}</td><td className="n">{inr(a.shared_minor)}</td><td className="n"><b>{inr(a.total_minor)}</b></td></tr>)}
            {data.allocation.length > 0 && <tr><td><b>Total charged</b></td><td className="n">{inr(data.totals.direct_minor)}</td><td className="n">{inr(data.allocation.reduce((s, a) => s + a.shared_minor, 0))}</td><td className="n"><b>{inr(data.allocation.reduce((s, a) => s + a.total_minor, 0))}</b></td></tr>}</tbody></table></div>
          {data.unallocated_minor > 0 && <p className="note w" style={{ margin: 12 }}>{inr(data.unallocated_minor)} of shared cost could not be split because no project has planned effort this month.</p>}</div>
      </div>
      <div className="card flat"><div className="tw"><table>
        <thead><tr><th>Date</th><th>Category</th><th>Vendor and note</th><th>Charged to</th><th className="n">Amount</th><th>Status</th>{data.can_manage && <th />}</tr></thead>
        <tbody>{data.rows.length === 0 ? <tr><td colSpan={7}><div className="empty">No expenses this month.</div></td></tr> : data.rows.map((r) => (
          <tr key={r.id}><td>{r.spent_on}</td><td>{r.category}</td><td><b>{r.vendor || '—'}</b><br /><small>{r.description}</small></td>
            <td>{r.shared ? <><Chip text="Shared" tone="acc" /> <small>{METHOD_SHORT[r.alloc_method ?? ''] ?? ''}</small></> : r.project}</td>
            <td className="n">{inr(r.amount_minor)}</td><td><Chip text={r.status} tone={r.status === 'Paid' ? 'ok' : 'warn'} /></td>
            {data.can_manage && <td><button className="btn sm" onClick={() => act(() => api(`/api/expenses/${r.id}`, { method: 'PATCH', body: { status: r.status === 'Paid' ? 'Planned' : 'Paid' } }), 'Status updated')}>{r.status === 'Paid' ? 'Mark unpaid' : 'Mark paid'}</button>{' '}
              <button className="btn sm danger" aria-label={`Delete ${r.vendor || r.category}`} onClick={() => act(() => api(`/api/expenses/${r.id}`, { method: 'DELETE' }), 'Expense deleted')}>Delete</button></td>}</tr>))}</tbody></table></div></div>
      <p className="note" style={{ marginTop: 12 }}>{data.note}</p>
      {adding && <AddExpense d={data} month={month} onClose={() => setAdding(false)} onSaved={() => { setAdding(false); reload() }} />}
    </>
  )
}

function AddExpense({ d, month, onClose, onSaved }: { d: D; month: string; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({ category: d.categories[0], vendor: '', description: '', amount: '', spent_on: `${month}-${month === thisMonth() ? new Date().toISOString().slice(8, 10) : '01'}`, project_id: 0, alloc_method: 'hours', status: 'Planned' })
  const [err, setErr] = useState('')
  async function save(e: FormEvent) {
    e.preventDefault()
    try { await api('/api/expenses', { method: 'POST', body: { category: f.category, vendor: f.vendor, description: f.description, amount_minor: toMinor(f.amount), spent_on: f.spent_on, project_id: f.project_id || null, alloc_method: f.alloc_method, status: f.status } }); toast('Expense added'); onSaved() } catch (x) { setErr((x as Error).message) }
  }
  return (
    <Modal title="Add expense" onClose={onClose}><form className="f" onSubmit={save}>
      <div className="row"><label>Category<select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{d.categories.map((c) => <option key={c}>{c}</option>)}</select></label>
        <label>Amount (₹)<input inputMode="decimal" required value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></label></div>
      <div className="row"><label>Vendor<input value={f.vendor} onChange={(e) => setF({ ...f, vendor: e.target.value })} /></label><label>Date<input type="date" required value={f.spent_on} onChange={(e) => setF({ ...f, spent_on: e.target.value })} /></label></div>
      <label>Note<input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></label>
      <label>Charged to<select value={f.project_id} onChange={(e) => setF({ ...f, project_id: +e.target.value })}><option value={0}>Shared by all projects</option>{d.projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      {f.project_id === 0 && <label>How to split a shared cost<select value={f.alloc_method} onChange={(e) => setF({ ...f, alloc_method: e.target.value })}>{Object.entries(d.methods).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>}
      <label>Payment status<select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}><option>Planned</option><option>Paid</option></select></label>
      {err && <div className="note e" role="alert">{err}</div>}
      <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn pri">Save expense</button></div>
    </form></Modal>
  )
}
