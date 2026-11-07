import { FormEvent, useState } from 'react'
import { api, useApi } from '../api'
import { Chip, ErrorBox, Loading, Modal, PageHead, toast } from '../ui'

interface T { id: number; name: string; plan: string; users: number; status: string; demo: boolean; modules: Record<string, boolean> }
const OPT = [['sprint', 'Sprint & handover'], ['timesheet', 'Timesheets'], ['revenue', 'Revenue'], ['expenses', 'Expenses'], ['performance', 'Performance'], ['invoices', 'Invoices'], ['sales', 'Sales (P2)'], ['ai', 'AI (P3)']]

export default function Platform() {
  const { data, error, loading, reload } = useApi<T[]>('/api/platform/tenants')
  const [add, setAdd] = useState(false)
  const [f, setF] = useState({ name: '', owner_name: '', owner_email: '' })
  const [err, setErr] = useState('')
  const [link, setLink] = useState<string | null>(null)
  async function create(e: FormEvent) {
    e.preventDefault(); setErr('')
    try { const r = await api<{ invite_link: string | null; email_sent: boolean }>('/api/platform/tenants', { method: 'POST', body: f }); toast(r.email_sent ? 'Owner invited by email' : 'Organization created'); setLink(r.invite_link); setAdd(false); reload() } catch (x) { setErr((x as Error).message) }
  }
  const run = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); toast(ok); reload() } catch (x) { toast((x as Error).message) } }
  return (
    <>
      <PageHead title="Tenants & entitlements" sub="Platform administrators manage organizations and plans only. Tenant projects, customers, employees and financials are never shown here." />
      <div className="tools"><button className="btn pri" onClick={() => setAdd(true)}>+ New organization</button></div>
      {link && <div className="note w mb">Demo environment: one-time owner link (also emailed when email is configured): <span className="mono">{link}</span></div>}
      {loading ? <Loading /> : error ? <ErrorBox msg={error} /> : <div className="card flat"><div className="tw"><table>
        <thead><tr><th>Organization</th><th>Plan</th><th className="n">People</th><th>Status</th><th>Optional modules</th><th /></tr></thead>
        <tbody>{data!.map((t) => <tr key={t.id}><td><b>{t.name}</b></td><td>{t.plan}</td><td className="n">{t.users}</td><td><Chip text={t.status} /></td>
          <td>{OPT.map(([k, l]) => <label key={k} style={{ display: 'inline-flex', gap: 4, marginRight: 10, fontSize: 12 }}><input type="checkbox" checked={!!t.modules[k]} onChange={(e) => run(() => api(`/api/platform/tenants/${t.id}/modules/${k}`, { method: 'PUT', body: { enabled: e.target.checked } }), `${l} ${e.target.checked ? 'enabled' : 'disabled'}`)} />{l}</label>)}</td>
          <td>{t.status === 'suspended' ? <button className="btn sm" onClick={() => run(() => api(`/api/platform/tenants/${t.id}/status`, { method: 'POST', body: { status: 'active' } }), 'Activated')}>Activate</button> : <button className="btn sm danger" onClick={() => run(() => api(`/api/platform/tenants/${t.id}/status`, { method: 'POST', body: { status: 'suspended' } }), 'Suspended')}>Suspend</button>}</td></tr>)}</tbody></table></div></div>}
      {add && <Modal title="New organization" onClose={() => setAdd(false)}><form className="f" onSubmit={create}>
        <label>Organization name<input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
        <div className="row"><label>Owner name<input required value={f.owner_name} onChange={(e) => setF({ ...f, owner_name: e.target.value })} /></label><label>Owner email<input type="email" required value={f.owner_email} onChange={(e) => setF({ ...f, owner_email: e.target.value })} /></label></div>
        {err && <div className="err" role="alert">{err}</div>}<div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={() => setAdd(false)}>Cancel</button><button className="btn pri">Create and invite owner</button></div></form></Modal>}
    </>
  )
}
