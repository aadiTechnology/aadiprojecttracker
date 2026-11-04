import { FormEvent, useState } from 'react'
import { Me, api, useApi } from '../api'
import { Chip, ErrorBox, Loading, Modal, PageHead, toast } from '../ui'

interface U { id: number; name: string; email: string; status: string; role_key: string; role: string; title: string; team: string }
interface Roles { roles: { id: number; key: string; name: string; perms: string[]; members: number }[]; catalog: string[]; note: string }

export default function Admin({ me }: { me: Me }) {
  const full = me.perms.includes('org.admin')
  const tabs = ['People', 'Roles & permissions', 'Modules', 'Settings', ...(me.perms.some((p) => p.startsWith('audit.view')) ? ['Audit log'] : [])]
  const [tab, setTab] = useState('People')
  return (
    <>
      <PageHead title="Organization Admin" sub={full ? 'Manage people, roles, settings and review the audit trail.' : 'View-only: you can see the team and roles but not change them.'} />
      <div className="tabs" role="tablist">{tabs.map((t) => <button key={t} role="tab" aria-selected={tab === t} className="tab" onClick={() => setTab(t)}>{t}</button>)}</div>
      {tab === 'People' && <People full={full} />}
      {tab === 'Roles & permissions' && <RolesTab full={full} />}
      {tab === 'Modules' && <Modules />}
      {tab === 'Settings' && <Settings full={full} />}
      {tab === 'Audit log' && <Audit />}
    </>
  )
}

function People({ full }: { full: boolean }) {
  const { data, error, loading, reload } = useApi<U[]>('/api/org/users')
  const roles = useApi<Roles>('/api/org/roles')
  const [inv, setInv] = useState(false)
  const [f, setF] = useState({ name: '', email: '', role_key: 'employee', title: '', team: '' })
  const [err, setErr] = useState('')
  const [link, setLink] = useState<string | null>(null)
  async function invite(e: FormEvent) {
    e.preventDefault(); setErr('')
    try { const r = await api<{ email_sent: boolean; invite_link: string | null }>('/api/org/users', { method: 'POST', body: f }); toast(r.email_sent ? 'Invitation email sent' : 'User added'); setLink(r.invite_link); setInv(false); reload() } catch (x) { setErr((x as Error).message) }
  }
  const patch = async (id: number, body: object, ok: string) => { try { await api(`/api/org/users/${id}`, { method: 'PATCH', body }); toast(ok); reload() } catch (x) { toast((x as Error).message) } }
  if (loading) return <Loading />
  if (error) return <ErrorBox msg={error} />
  return (
    <>
      {full && <div className="tools"><button className="btn pri" onClick={() => { setInv(true); setErr('') }}>+ Invite person</button></div>}
      {link && <div className="note w mb">Email is not configured on this server, so share this one-time link manually (demo only): <span className="mono">{link}</span></div>}
      <div className="card flat"><div className="tw"><table>
        <thead><tr><th>Name</th><th>Role</th><th>Title / team</th><th>Status</th>{full && <th />}</tr></thead>
        <tbody>{data!.map((u) => <tr key={u.id}><td><b>{u.name}</b><br /><small>{u.email}</small></td>
          <td>{full ? <select aria-label={`Role for ${u.name}`} value={u.role_key} onChange={(e) => patch(u.id, { role_key: e.target.value }, 'Role updated')}>{roles.data?.roles.map((r) => <option key={r.key} value={r.key}>{r.name}</option>)}</select> : u.role}</td>
          <td>{u.title}<br /><small>{u.team}</small></td><td><Chip text={u.status} /></td>
          {full && <td>{u.status === 'suspended' ? <button className="btn sm" onClick={() => patch(u.id, { status: 'active' }, 'Reactivated')}>Reactivate</button> : <button className="btn sm danger" onClick={() => patch(u.id, { status: 'suspended' }, 'Suspended; sessions revoked')}>Suspend</button>}</td>}</tr>)}</tbody></table></div></div>
      {inv && <Modal title="Invite a person" onClose={() => setInv(false)}>
        <form className="f" onSubmit={invite}>
          <div className="row"><label>Name<input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label><label>Email<input type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label></div>
          <label>Role<select value={f.role_key} onChange={(e) => setF({ ...f, role_key: e.target.value })}>{roles.data?.roles.map((r) => <option key={r.key} value={r.key}>{r.name}</option>)}</select></label>
          <div className="row"><label>Title<input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></label><label>Team<input value={f.team} onChange={(e) => setF({ ...f, team: e.target.value })} /></label></div>
          {err && <div className="err" role="alert">{err}</div>}
          <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={() => setInv(false)}>Cancel</button><button className="btn pri">Send invitation</button></div>
        </form></Modal>}
    </>
  )
}

function RolesTab({ full }: { full: boolean }) {
  const { data, error, loading, reload } = useApi<Roles>('/api/org/roles')
  const [edit, setEdit] = useState<{ id: number; name: string; perms: string[] } | null>(null)
  const [err, setErr] = useState('')
  if (loading) return <Loading />
  if (error) return <ErrorBox msg={error} />
  const areas = Array.from(new Set(data!.catalog))
  const scopes = ['', 'all', 'team', 'assigned', 'own']
  const current = (cap: string) => scopes.slice(1).find((s) => edit!.perms.includes(`${cap}:${s}`)) ?? (edit!.perms.includes(cap) ? 'yes' : '')
  const setCap = (cap: string, v: string) => {
    const rest = edit!.perms.filter((p) => p.split(':')[0] !== cap)
    setEdit({ ...edit!, perms: v === '' ? rest : [...rest, v === 'yes' ? cap : `${cap}:${v}`] })
  }
  const scoped = (cap: string) => data!.roles.some((r) => r.perms.some((p) => p.startsWith(cap + ':')))
  async function save() { try { await api(`/api/org/roles/${edit!.id}`, { method: 'PUT', body: { perms: edit!.perms } }); toast('Permissions saved and audited'); setEdit(null); reload() } catch (x) { setErr((x as Error).message) } }
  return (
    <>
      <div className="note mb">{data!.note} Role names and defaults are a proposal awaiting customer approval.</div>
      <div className="card flat"><div className="tw"><table><thead><tr><th>Role</th><th className="n">People</th><th className="n">Capabilities</th>{full && <th />}</tr></thead><tbody>
        {data!.roles.map((r) => <tr key={r.id}><td><b>{r.name}</b><br /><small>{r.key}</small></td><td className="n">{r.members}</td><td className="n">{r.perms.length}</td>
          {full && <td>{r.key === 'owner' ? <small>Protected</small> : <button className="btn sm" onClick={() => { setErr(''); setEdit({ id: r.id, name: r.name, perms: [...r.perms] }) }}>Edit permissions</button>}</td>}</tr>)}</tbody></table></div></div>
      {edit && <Modal wide title={`Permissions: ${edit.name}`} onClose={() => setEdit(null)} footer={<><button className="btn" onClick={() => setEdit(null)}>Cancel</button><button className="btn pri" onClick={save}>Save</button></>}>
        {err && <div className="err" role="alert">{err}</div>}
        <table><thead><tr><th>Capability</th><th>Level</th></tr></thead><tbody>{areas.map((cap) => <tr key={cap}><td className="mono">{cap}</td><td>
          <select aria-label={cap} value={current(cap)} onChange={(e) => setCap(cap, e.target.value)}>
            <option value="">No access</option>{scoped(cap) ? scopes.slice(1).map((s) => <option key={s} value={s}>{s}</option>) : <option value="yes">Allowed</option>}</select></td></tr>)}</tbody></table>
      </Modal>}
    </>
  )
}

function Modules() {
  const { data, error, loading } = useApi<{ key: string; label: string; pillar: number; priority: string; enabled: boolean }[]>('/api/org/modules')
  if (loading) return <Loading />
  if (error) return <ErrorBox msg={error} />
  return <><div className="note mb">Modules are switched on per organization by the platform (plan entitlements). A disabled module is denied by the API even if a role has the capability.</div>
    <div className="card flat"><div className="tw"><table><thead><tr><th>Module</th><th>Pillar</th><th>Proposed priority</th><th>Entitlement</th></tr></thead><tbody>
      {data!.map((m) => <tr key={m.key}><td><b>{m.label}</b></td><td>Pillar {m.pillar}</td><td>{m.priority}</td><td><Chip text={m.enabled ? 'Enabled' : 'Not enabled'} tone={m.enabled ? 'ok' : ''} /></td></tr>)}</tbody></table></div></div></>
}

function Settings({ full }: { full: boolean }) {
  const { data, error, loading, reload } = useApi<{ name: string; currency: string; timezone: string; week_hours: number; revenue_basis: string | null; planning_markers: Record<string, string> }>('/api/org/settings')
  const [basis, setBasis] = useState('')
  const [hours, setHours] = useState('')
  const [err, setErr] = useState('')
  if (loading) return <Loading />
  if (error) return <ErrorBox msg={error} />
  const save = async (body: object) => { setErr(''); try { await api('/api/org/settings', { method: 'PATCH', body }); toast('Settings saved'); reload() } catch (x) { setErr((x as Error).message) } }
  return (
    <div className="grid g2">
      <div className="card f"><h2>Organization</h2>
        <p style={{ margin: 0 }}><b>{data!.name}</b> · {data!.currency} · {data!.timezone}</p>
        <label>Working week (hours)<input inputMode="numeric" disabled={!full} defaultValue={data!.week_hours} onChange={(e) => setHours(e.target.value)} /></label>
        {full && <button className="btn" style={{ justifySelf: 'start' }} onClick={() => save({ week_hours: +hours || data!.week_hours })}>Save</button>}
        {err && <div className="err" role="alert">{err}</div>}</div>
      <div className="card f"><h2>Open decisions (customer to confirm)</h2>
        <label>Revenue basis<select disabled={!full} value={basis || data!.revenue_basis || ''} onChange={(e) => setBasis(e.target.value)}><option value="">Not decided</option><option value="invoiced">Invoiced</option><option value="collected">Collected</option><option value="recognized">Recognized</option><option value="milestone">Milestone-based</option></select></label>
        {full && <button className="btn" style={{ justifySelf: 'start' }} disabled={!basis} onClick={() => save({ revenue_basis: basis })}>Record decision</button>}
        <label>Meaning of the planning markers “S” and “H”<input disabled value={Object.keys(data!.planning_markers).length ? JSON.stringify(data!.planning_markers) : 'Not defined by the customer yet'} /></label>
        <small>These are deliberately left undecided; nothing assumes a default.</small></div>
    </div>
  )
}

function Audit() {
  const { data, error, loading } = useApi<{ id: number; at: string; actor: string; action: string; entity: string; entity_id: string }[]>('/api/org/audit?limit=100')
  if (loading) return <Loading />
  if (error) return <ErrorBox msg={error} />
  return <div className="card flat"><div className="tw"><table><thead><tr><th>When</th><th>Who</th><th>Action</th><th>Entity</th></tr></thead><tbody>
    {data!.map((a) => <tr key={a.id}><td>{a.at.replace('T', ' ').slice(0, 19)}</td><td>{a.actor}</td><td className="mono">{a.action}</td><td>{a.entity} {a.entity_id}</td></tr>)}</tbody></table></div></div>
}
