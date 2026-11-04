import { FormEvent, useState } from 'react'
import { Me, api, useApi } from '../api'
import { Chip, ErrorBox, Loading, Modal, PageHead, toast, useDebounced } from '../ui'

interface C { id: number; name: string; kind: string; status: string; contact_name: string; contact_email: string; owner: string | null; owner_user_id: number | null; projects: number; billing_details?: string; notes: string }

export default function Customers({ me }: { me: Me }) {
  const [q, setQ] = useState('')
  const dq = useDebounced(q)
  const { data, error, loading, reload } = useApi<C[]>(`/api/customers?q=${encodeURIComponent(dq)}`)
  const users = useApi<{ id: number; name: string }[]>(me.perms.includes('org.admin') || me.perms.includes('org.users.view') ? '/api/org/users' : null)
  const canManage = me.perms.some((p) => p.startsWith('customers.manage'))
  const [edit, setEdit] = useState<Partial<C> | null>(null)
  const [err, setErr] = useState('')

  async function save(e: FormEvent) {
    e.preventDefault(); setErr('')
    try {
      const body = { name: edit!.name, kind: edit!.kind ?? 'customer', contact_name: edit!.contact_name ?? '', contact_email: edit!.contact_email ?? '', billing_details: edit!.billing_details ?? '', owner_user_id: edit!.owner_user_id ?? null, notes: edit!.notes ?? '', status: edit!.status ?? 'active' }
      if (edit!.id) await api(`/api/customers/${edit!.id}`, { method: 'PATCH', body }); else await api('/api/customers', { method: 'POST', body })
      toast('Customer saved'); setEdit(null); reload()
    } catch (x) { setErr((x as Error).message) }
  }

  return (
    <>
      <PageHead title="Customers" sub="Customers and internal business units. Every project belongs to one of them." />
      <div className="tools">
        <input type="search" aria-label="Search customers" placeholder="Search customers…" value={q} onChange={(e) => setQ(e.target.value)} />
        {canManage && <button className="btn pri" onClick={() => { setEdit({ kind: 'customer' }); setErr('') }}>+ New customer</button>}
      </div>
      {loading ? <Loading /> : error ? <ErrorBox msg={error} /> : (
        <div className="card flat"><div className="tw"><table>
          <thead><tr><th>Name</th><th>Type</th><th>Contact</th><th>Account owner</th><th className="n">Projects</th><th>Status</th>{canManage && <th />}</tr></thead>
          <tbody>{data!.length === 0 ? <tr><td colSpan={7}><div className="empty">No customers match.</div></td></tr> : data!.map((c) => (
            <tr key={c.id}><td><b>{c.name}</b></td><td>{c.kind === 'internal' ? 'Internal business unit' : 'Customer'}</td><td>{c.contact_name}<br /><small>{c.contact_email}</small></td>
              <td>{c.owner ?? '—'}</td><td className="n">{c.projects}</td><td><Chip text={c.status} /></td>
              {canManage && <td><button className="btn sm" onClick={() => { setEdit(c); setErr('') }}>Edit</button></td>}</tr>))}</tbody></table></div></div>)}
      {edit && (
        <Modal title={edit.id ? 'Edit customer' : 'New customer'} onClose={() => setEdit(null)}>
          <form className="f" onSubmit={save} id="cform">
            <label>Name<input required value={edit.name ?? ''} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></label>
            <div className="row">
              <label>Type<select value={edit.kind ?? 'customer'} onChange={(e) => setEdit({ ...edit, kind: e.target.value })}><option value="customer">Customer</option><option value="internal">Internal business unit</option></select></label>
              <label>Status<select value={edit.status ?? 'active'} onChange={(e) => setEdit({ ...edit, status: e.target.value })}><option>active</option><option>inactive</option></select></label>
            </div>
            <div className="row">
              <label>Contact name<input value={edit.contact_name ?? ''} onChange={(e) => setEdit({ ...edit, contact_name: e.target.value })} /></label>
              <label>Contact email<input type="email" value={edit.contact_email ?? ''} onChange={(e) => setEdit({ ...edit, contact_email: e.target.value })} /></label>
            </div>
            {users.data && <label>Account owner<select value={edit.owner_user_id ?? ''} onChange={(e) => setEdit({ ...edit, owner_user_id: e.target.value ? +e.target.value : null })}><option value="">— none —</option>{users.data.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}</select></label>}
            <label>Billing details<textarea value={edit.billing_details ?? ''} onChange={(e) => setEdit({ ...edit, billing_details: e.target.value })} /></label>
            {err && <div className="err" role="alert">{err}</div>}
            <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={() => setEdit(null)}>Cancel</button><button className="btn pri">Save</button></div>
          </form>
        </Modal>)}
    </>
  )
}
