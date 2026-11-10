import { FormEvent, useState } from 'react'
import { Me, api, useApi } from '../api'
import { Chip, ErrorBox, Loading, Modal, PageHead, toast } from '../ui'
import OrgAdmin from '../aadi-org/OrgAdmin'
import { token } from '../api'


/** The shared organisation screens (people, departments, roles, activity) sign their calls with Tracker's bearer token. */
const authHeaders = (): Record<string, string> => (token.get() ? { Authorization: `Bearer ${token.get()}` } : {})

export default function Admin({ me }: { me: Me }) {
  const full = me.perms.includes('org.admin')
  const tabs = ['People & roles', 'Modules', 'Settings']
  const [tab, setTab] = useState('People & roles')
  return (
    <>
      <PageHead title="Organization Admin" sub={full ? 'Manage people, roles, settings and review the audit trail.' : 'View-only: you can see the team and roles but not change them.'} />
      <div className="tabs" role="tablist">{tabs.map((t) => <button key={t} role="tab" aria-selected={tab === t} className="tab" onClick={() => setTab(t)}>{t}</button>)}</div>
      {tab === 'People & roles' && <OrgAdmin base="/api/kit" title="People and roles" headers={authHeaders} />}
      {tab === 'Modules' && <Modules />}
      {tab === 'Settings' && <Settings full={full} />}
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

