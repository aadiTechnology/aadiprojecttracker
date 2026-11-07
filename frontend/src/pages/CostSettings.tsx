import { useEffect, useState } from 'react'
import { Me, api, inr, useApi } from '../api'
import { Chip, ErrorBox, Loading, PageHead, toast } from '../ui'

interface S {
  monthly_hours: number; hourly_rate_minor?: number; currency: string; can_edit: boolean
  project_rates?: { project_id: number; code: string; name: string; rate_override_minor: number | null }[]
  employee_hours?: { user_id: number; name: string; hours_override: number | null }[]
}

export default function CostSettings({ me }: { me: Me }) {
  const { data, error, loading, reload } = useApi<S>('/api/costing/settings')
  const [hours, setHours] = useState('')
  const [rate, setRate] = useState('')
  useEffect(() => { if (data) { setHours(String(data.monthly_hours)); setRate(data.hourly_rate_minor !== undefined ? String(data.hourly_rate_minor / 100) : '') } }, [data])
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load settings.'} />
  const edit = data.can_edit
  const run = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); toast(ok); reload() } catch (x) { toast((x as Error).message) } }
  return (
    <>
      <PageHead title="Costing Settings" sub="Organization defaults used by every effort and cost calculation, and where they can be overridden." />
      <div className="grid g2 mb">
        <div className="card"><h2>Organization defaults</h2>
          <div className="f">
            <label>Monthly working hours per employee<input inputMode="numeric" value={hours} disabled={!edit} onChange={(e) => setHours(e.target.value)} /></label>
            {data.hourly_rate_minor !== undefined && <label>Standard hourly rate (₹) <small>internal value of effort, not a customer invoice rate</small><input inputMode="decimal" value={rate} disabled={!edit} onChange={(e) => setRate(e.target.value)} /></label>}
            {edit && <button className="btn pri" onClick={() => run(() => api('/api/costing/settings', { method: 'PATCH', body: { monthly_hours: Math.round(Number(hours)), hourly_rate_minor: Math.round(Number(rate) * 100) } }), 'Settings saved and audited')}>Save defaults</button>}
          </div>
          <p className="sub" style={{ marginTop: 10 }}>Hours must be 1 to 300 and the rate above 0. Changing the rate moves standard value, never salary cost.</p></div>
        <div className="card"><h2>How the numbers are used</h2>
          <table><tbody>
            <tr><td>Effort (h)</td><td><code>allocation % × monthly hours</code></td></tr>
            <tr><td>Salary cost</td><td><code>allocation % × the employee's own monthly salary</code></td></tr>
            <tr><td>Standard value</td><td><code>hours × hourly rate</code></td></tr>
            <tr><td>Today</td><td>{data.monthly_hours} h{data.hourly_rate_minor !== undefined ? ` · ${inr(data.hourly_rate_minor)}/h` : ''} · {data.currency}</td></tr></tbody></table></div>
      </div>
      {me.perms.some((p) => p.startsWith('tags.manage')) && <TagsCard />}
      {edit && data.project_rates && data.employee_hours && <div className="grid g2">
        <div className="card flat"><div style={{ padding: '14px 16px 0' }}><h2>Hourly rate per project</h2><small>Empty means inherit the organization rate</small></div><div className="tw"><table>
          <thead><tr><th>Project</th><th className="n">Rate ₹/h</th></tr></thead>
          <tbody>{data.project_rates.map((p) => <RateRow key={p.project_id} p={p} onSave={(v) => run(() => api(`/api/costing/project-rate/${p.project_id}`, { method: 'PUT', body: { rate_minor: v } }), 'Project rate saved')} />)}</tbody></table></div></div>
        <div className="card flat"><div style={{ padding: '14px 16px 0' }}><h2>Monthly hours per employee</h2><small>For part-time staff. Empty means inherit</small></div><div className="tw"><table>
          <thead><tr><th>Employee</th><th className="n">Hours / month</th></tr></thead>
          <tbody>{data.employee_hours.map((e) => <HoursRow key={e.user_id} e={e} onSave={(v) => run(() => api(`/api/costing/employee-hours/${e.user_id}`, { method: 'PUT', body: { hours: v } }), 'Hours saved')} />)}</tbody></table></div></div>
      </div>}
      {!edit && <p className="note">You can see the monthly hours. Changing them needs costing settings access.</p>}
    </>
  )
}

function RateRow({ p, onSave }: { p: NonNullable<S['project_rates']>[number]; onSave: (v: number | null) => void }) {
  const [v, setV] = useState(p.rate_override_minor ? String(p.rate_override_minor / 100) : '')
  return <tr><td>{p.code} {p.name}</td><td className="n"><input style={{ width: 90 }} aria-label={`Rate override for ${p.name}`} inputMode="decimal" value={v} onChange={(e) => setV(e.target.value)}
    onBlur={() => { const n = v.trim() === '' ? null : Math.round(Number(v) * 100); if (n !== (p.rate_override_minor ?? null)) onSave(n) }} />{p.rate_override_minor ? <> <Chip text="override" tone="warn" /></> : null}</td></tr>
}
function HoursRow({ e, onSave }: { e: NonNullable<S['employee_hours']>[number]; onSave: (v: number | null) => void }) {
  const [v, setV] = useState(e.hours_override ? String(e.hours_override) : '')
  return <tr><td>{e.name}</td><td className="n"><input style={{ width: 90 }} aria-label={`Hours override for ${e.name}`} inputMode="numeric" value={v} onChange={(x) => setV(x.target.value)}
    onBlur={() => { const n = v.trim() === '' ? null : Math.round(Number(v)); if (n !== (e.hours_override ?? null)) onSave(n) }} />{e.hours_override ? <> <Chip text="override" tone="warn" /></> : null}</td></tr>
}

function TagsCard() {
  const tags = useApi<{ id: number; name: string; archived: boolean; projects: number }[]>('/api/tags')
  const [name, setName] = useState('')
  const run = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); toast(ok); tags.reload() } catch (x) { toast((x as Error).message) } }
  return (
    <div className="card mb"><h2>Project tags</h2>
      <p className="sub">Tags classify projects for analysis, for example by industry. The first tag on a project is its primary tag, so totals by tag add up.</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, margin: '8px 0' }}>
        {tags.data?.length === 0 && <small>No tags yet.</small>}
        {tags.data?.map((t) => <span key={t.id} className={`chip c-acc`} style={t.archived ? { opacity: 0.5 } : undefined}>{t.name} · {t.projects}{' '}
          <button className="btn sm" aria-label={`${t.archived ? 'Restore' : 'Archive'} tag ${t.name}`} onClick={() => run(() => api(`/api/tags/${t.id}`, { method: 'PATCH', body: { archived: !t.archived } }), t.archived ? 'Tag restored' : 'Tag archived')}>{t.archived ? 'Restore' : 'Archive'}</button></span>)}
      </div>
      <form className="tools" onSubmit={(e) => { e.preventDefault(); if (name.trim()) run(async () => { await api('/api/tags', { method: 'POST', body: { name } }); setName('') }, 'Tag added') }}>
        <input aria-label="New tag name" placeholder="New tag, for example Education" maxLength={40} value={name} onChange={(e) => setName(e.target.value)} />
        <button className="btn pri" disabled={!name.trim()}>Add tag</button></form>
    </div>
  )
}
