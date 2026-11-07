import { FormEvent, useState } from 'react'
import { Me, api, inr, toMinor, useApi } from '../api'
import { Chip, ErrorBox, Kpi, Loading, Modal, PageHead, toast } from '../ui'

interface Inv {
  id: number; number: string; project: string; customer: string; issue_date: string; due_date: string; status: string; subtotal_minor: number; tax_pct: number; tax_minor: number
  total_minor: number; paid_minor: number; outstanding_minor: number; days_overdue: number; created_by: string; approved_by: string | null
}
interface List {
  rows: Inv[]; can_manage: boolean; can_approve: boolean; projects: { id: number; name: string }[]; note: string
  summary: { invoiced_minor: number; collected_minor: number; outstanding_minor: number; overdue_minor: number; overdue_count: number; drafts: number; awaiting_issue: number }
}
interface Detail extends Inv { lines: { description: string; amount_minor: number }[]; billing_details: string; payments: { id: number; amount_minor: number; paid_on: string; reference: string; by: string }[] }
const tone: Record<string, string> = { Draft: '', Approved: 'info', Issued: 'info', 'Partially Paid': 'warn', Paid: 'ok', Overdue: 'bad', Void: '' }
const today = () => new Date().toISOString().slice(0, 10)
const plus = (d: number) => { const x = new Date(); x.setDate(x.getDate() + d); return x.toISOString().slice(0, 10) }

export default function Invoices({ me }: { me: Me }) {
  const { data, error, loading, reload } = useApi<List>('/api/invoices')
  const [adding, setAdding] = useState(false)
  const [open, setOpen] = useState<number | null>(null)
  const [filter, setFilter] = useState('All')
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load invoices.'} />
  const s = data.summary
  const rows = filter === 'All' ? data.rows : data.rows.filter((r) => r.status === filter)
  const act = async (id: number, what: 'approve' | 'issue' | 'void', ok: string) => { try { await api(`/api/invoices/${id}/${what}`, { method: 'POST' }); toast(ok); reload() } catch (x) { toast((x as Error).message) } }
  return (
    <>
      <PageHead title="Invoices & Receivables" sub={`Draft, approve, issue and collect for ${me.tenant.name}. Invoiced and collected stay separate from planned value.`} />
      <div className="grid g4 mb">
        <Kpi label="Invoiced" value={inr(s.invoiced_minor)} sub="Issued, incl. tax" />
        <Kpi label="Collected" value={inr(s.collected_minor)} sub="Payments recorded" />
        <Kpi label="Outstanding" value={inr(s.outstanding_minor)} sub="Issued less paid" />
        <Kpi label="Overdue" value={<span className={s.overdue_count ? 'neg' : ''}>{inr(s.overdue_minor)}</span>} sub={`${s.overdue_count} invoice(s) · ${s.drafts} draft · ${s.awaiting_issue} to issue`} />
      </div>
      <div className="tools">
        <div className="tabs" role="tablist" style={{ margin: 0 }}>{['All', 'Draft', 'Approved', 'Issued', 'Partially Paid', 'Paid', 'Overdue'].map((t) => <button key={t} role="tab" aria-selected={filter === t} className="tab" onClick={() => setFilter(t)}>{t}</button>)}</div>
        <span style={{ flex: 1 }} />{data.can_manage && <button className="btn pri" onClick={() => setAdding(true)}>+ New invoice</button>}</div>
      <div className="card flat"><div className="tw"><table>
        <thead><tr><th>Number</th><th>Customer and project</th><th>Issued</th><th>Due</th><th className="n">Total</th><th className="n">Paid</th><th className="n">Outstanding</th><th>Status</th><th /></tr></thead>
        <tbody>{rows.length === 0 ? <tr><td colSpan={9}><div className="empty">No invoices here.</div></td></tr> : rows.map((r) => (
          <tr key={r.id}><td><b>{r.number}</b></td><td>{r.customer}<br /><small>{r.project}</small></td><td>{r.issue_date}</td><td>{r.due_date}</td>
            <td className="n">{inr(r.total_minor)}</td><td className="n">{inr(r.paid_minor)}</td><td className="n">{r.outstanding_minor ? inr(r.outstanding_minor) : '—'}</td>
            <td><Chip text={r.status} tone={tone[r.status]} />{r.days_overdue > 0 && <><br /><small style={{ color: 'var(--bad)' }}>{r.days_overdue} days late</small></>}</td>
            <td style={{ whiteSpace: 'nowrap' }}><button className="btn sm" onClick={() => setOpen(r.id)}>Open</button>
              {r.status === 'Draft' && data.can_approve && <> <button className="btn sm pri" onClick={() => act(r.id, 'approve', `${r.number} approved`)}>Approve</button></>}
              {r.status === 'Approved' && data.can_manage && <> <button className="btn sm pri" onClick={() => act(r.id, 'issue', `${r.number} issued`)}>Issue</button></>}</td></tr>))}</tbody></table></div></div>
      <p className="note" style={{ marginTop: 12 }}>{data.note}</p>
      {adding && <NewInvoice projects={data.projects} onClose={() => setAdding(false)} onSaved={() => { setAdding(false); reload() }} />}
      {open !== null && <DetailModal id={open} can={data.can_manage} onClose={() => setOpen(null)} onChanged={reload} onVoid={(id) => act(id, 'void', 'Invoice voided').then(() => setOpen(null))} />}
    </>
  )
}

function NewInvoice({ projects, onClose, onSaved }: { projects: { id: number; name: string }[]; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({ project_id: 0, issue_date: today(), due_date: plus(30), tax: '18', note: '' })
  const [lines, setLines] = useState([{ description: '', amount: '' }])
  const [err, setErr] = useState('')
  const sub = lines.reduce((t, l) => t + toMinor(l.amount), 0)
  const tax = Math.round((sub * (parseFloat(f.tax || '0') * 100)) / 10000)
  async function save(e: FormEvent) {
    e.preventDefault()
    try { const r = await api<{ number: string }>('/api/invoices', { method: 'POST', body: { project_id: f.project_id, issue_date: f.issue_date, due_date: f.due_date, tax_pct: parseFloat(f.tax || '0'), note: f.note, lines: lines.map((l) => ({ description: l.description, amount_minor: toMinor(l.amount) })) } }); toast(`${r.number} saved as a draft`); onSaved() } catch (x) { setErr((x as Error).message) }
  }
  return (
    <Modal title="New invoice (draft)" onClose={onClose} wide><form className="f" onSubmit={save}>
      <label>Project<select required value={f.project_id} onChange={(e) => setF({ ...f, project_id: +e.target.value })}><option value={0}>Choose…</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      <div className="row"><label>Issue date<input type="date" required value={f.issue_date} onChange={(e) => setF({ ...f, issue_date: e.target.value })} /></label><label>Due date<input type="date" required value={f.due_date} onChange={(e) => setF({ ...f, due_date: e.target.value })} /></label></div>
      <b>Lines</b>
      {lines.map((l, i) => <div className="row" key={i}><label>Description<input required value={l.description} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)))} /></label>
        <label>Amount (₹)<input required inputMode="decimal" value={l.amount} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, amount: e.target.value } : x)))} /></label></div>)}
      <div><button type="button" className="btn sm" onClick={() => setLines([...lines, { description: '', amount: '' }])}>+ Add line</button></div>
      <div className="row"><label>Tax % (you decide; none is assumed)<input inputMode="decimal" value={f.tax} onChange={(e) => setF({ ...f, tax: e.target.value })} /></label><label>Note<input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></label></div>
      <div className="card" style={{ background: 'var(--bg2, #f6f7f9)' }}>Subtotal {inr(sub)} · Tax {inr(tax)} · <b>Total {inr(sub + tax)}</b></div>
      {err && <div className="note e" role="alert">{err}</div>}
      <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn pri">Save draft</button></div>
    </form></Modal>
  )
}

function DetailModal({ id, can, onClose, onChanged, onVoid }: { id: number; can: boolean; onClose: () => void; onChanged: () => void; onVoid: (id: number) => void }) {
  const { data, loading, reload } = useApi<Detail>(`/api/invoices/${id}`)
  const [amt, setAmt] = useState('')
  const [ref, setRef] = useState('')
  const [err, setErr] = useState('')
  if (loading && !data) return <Modal title="Invoice" onClose={onClose}><Loading /></Modal>
  if (!data) return <Modal title="Invoice" onClose={onClose}><ErrorBox msg="Could not load the invoice." /></Modal>
  async function pay(e: FormEvent) {
    e.preventDefault()
    try { await api(`/api/invoices/${id}/payments`, { method: 'POST', body: { amount_minor: toMinor(amt), paid_on: today(), reference: ref } }); toast('Payment recorded'); setAmt(''); setRef(''); setErr(''); reload(); onChanged() } catch (x) { setErr((x as Error).message) }
  }
  const canPay = can && ['Issued', 'Partially Paid', 'Overdue'].includes(data.status)
  return (
    <Modal title={`${data.number} · ${data.status}`} onClose={onClose} wide>
      <p><b>{data.customer}</b> · {data.project}<br /><small>{data.billing_details}</small></p>
      <div className="tw"><table><thead><tr><th>Description</th><th className="n">Amount</th></tr></thead><tbody>
        {data.lines.map((l, i) => <tr key={i}><td>{l.description}</td><td className="n">{inr(l.amount_minor)}</td></tr>)}
        <tr><td>Subtotal</td><td className="n">{inr(data.subtotal_minor)}</td></tr><tr><td>Tax ({data.tax_pct}%)</td><td className="n">{inr(data.tax_minor)}</td></tr>
        <tr><td><b>Total</b></td><td className="n"><b>{inr(data.total_minor)}</b></td></tr></tbody></table></div>
      <p><small>Drafted by {data.created_by}{data.approved_by ? ` · approved by ${data.approved_by}` : ''} · issued {data.issue_date} · due {data.due_date}</small></p>
      <h2>Payments</h2>
      {data.payments.length === 0 ? <div className="empty">No payments yet.</div> : <div className="tw"><table><tbody>{data.payments.map((p) => <tr key={p.id}><td>{p.paid_on}</td><td>{p.reference}</td><td>{p.by}</td><td className="n">{inr(p.amount_minor)}</td></tr>)}</tbody></table></div>}
      <p><b>Outstanding {inr(data.outstanding_minor)}</b></p>
      {canPay && <form className="f" onSubmit={pay}><div className="row"><label>Payment amount (₹)<input required inputMode="decimal" value={amt} onChange={(e) => setAmt(e.target.value)} /></label><label>Reference<input value={ref} onChange={(e) => setRef(e.target.value)} /></label></div>
        {err && <div className="note e" role="alert">{err}</div>}<div className="mf" style={{ padding: 0, border: 0 }}><button className="btn pri">Record payment</button></div></form>}
      {can && data.status !== 'Void' && data.payments.length === 0 && <div style={{ marginTop: 10 }}><button className="btn sm danger" onClick={() => onVoid(id)}>Void invoice</button></div>}
    </Modal>
  )
}
