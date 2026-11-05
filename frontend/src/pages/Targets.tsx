import { useState } from 'react'
import { Me, api, inr, thisMonth, useApi } from '../api'
import { Chip, ErrorBox, Loading, PageHead, toast } from '../ui'

interface T {
  month: string; can_manage: boolean; note: string; org_target_minor?: number | null
  projects: { project_id: number; code: string; name: string; tags: { id: number; name: string }[]; target_minor: number | null; value_minor?: number; cost_minor?: number; hours?: number }[]
  tags?: { tag_id: number; tag: string; target_minor: number | null }[]
}

export default function Targets({ me }: { me: Me }) {
  const [month, setMonth] = useState(thisMonth())
  const { data, error, loading, reload } = useApi<T>(`/api/targets?month=${month}`)
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load targets.'} />
  const save = async (body: Record<string, unknown>) => { try { await api('/api/targets', { method: 'PUT', body: { ...body, month } }); toast('Target saved'); reload() } catch (x) { toast((x as Error).message) } }
  const withCost = data.projects.some((p) => p.value_minor !== undefined)
  const set = data.projects.filter((p) => p.target_minor !== null)
  const sumT = set.reduce((s, p) => s + (p.target_minor ?? 0), 0), sumV = set.reduce((s, p) => s + (p.value_minor ?? 0), 0)
  return (
    <>
      <PageHead title="Revenue Targets" sub="Monthly planning targets per project, tag and for the whole organization, compared with planned value and cost." />
      <div className="tools"><label>Month <input type="month" value={month} onChange={(e) => setMonth(e.target.value || thisMonth())} /></label></div>
      <div className="grid g4 mb">
        <div className="card kpi"><div className="l">Projects with a target</div><div className="v">{set.length} of {data.projects.length}</div><div className="s">Others show “Not set”</div></div>
        <div className="card kpi"><div className="l">Sum of project targets</div><div className="v">{inr(sumT)}</div><div className="s">{data.org_target_minor !== undefined ? `Organization target ${inr(data.org_target_minor)}` : 'In your scope'}</div></div>
        {withCost && <div className="card kpi"><div className="l">Standard value, same projects</div><div className="v">{inr(sumV)}</div><div className="s">Hours × rate</div></div>}
        {withCost && <div className="card kpi"><div className="l">Gap to target</div><div className="v"><span className={sumV - sumT >= 0 ? 'pos' : 'neg'}>{inr(sumV - sumT)}</span></div><div className="s">{sumV >= sumT ? 'Planned effort covers the targets' : 'Planned effort falls short'}</div></div>}
      </div>
      <div className="card flat"><div className="tw"><table>
        <thead><tr><th>Project</th><th>Tags</th><th className="n">Target (₹)</th>{withCost && <><th className="n">Standard value</th><th className="n">Value − target</th><th>Planned value vs target</th><th className="n">Salary cost</th><th className="n">Margin at target</th></>}</tr></thead>
        <tbody>{data.projects.map((p) => {
          const pct = p.target_minor && p.value_minor !== undefined ? Math.round((p.value_minor * 100) / p.target_minor) : null
          return <tr key={p.project_id}><td><b>{p.name}</b><br /><small>{p.code}</small></td><td>{p.tags.map((t) => <Chip key={t.id} text={t.name} tone="acc" />)}</td>
            <td className="n">{data.can_manage ? <TargetInput label={`Target for ${p.name}`} value={p.target_minor} onSave={(v) => save({ level: 'project', project_id: p.project_id, amount_minor: v })} /> : (p.target_minor === null ? 'Not set' : inr(p.target_minor))}</td>
            {withCost && <><td className="n">{inr(p.value_minor)}</td><td className="n">{p.target_minor === null ? '—' : <span className={(p.value_minor ?? 0) >= p.target_minor ? 'pos' : 'neg'}>{inr((p.value_minor ?? 0) - p.target_minor)}</span>}</td>
              <td>{pct === null ? <Chip text="No target set" tone="warn" /> : <><div className="bar" style={{ display: 'inline-block', width: 80, verticalAlign: 'middle' }}><i style={{ width: `${Math.min(100, pct)}%` }} /></div> <small>{pct}%</small></>}</td>
              <td className="n">{inr(p.cost_minor)}</td><td className="n">{p.target_minor === null ? '—' : inr(p.target_minor - (p.cost_minor ?? 0))}</td></>}</tr>
        })}</tbody></table></div></div>
      {data.tags && <div className="grid g2" style={{ marginTop: 14 }}>
        <div className="card"><h2>Organization target</h2><TargetInput label="Organization target" value={data.org_target_minor ?? null} disabled={!data.can_manage} onSave={(v) => save({ level: 'org', amount_minor: v })} /></div>
        <div className="card flat"><div style={{ padding: '14px 16px 0' }}><h2>Targets by tag</h2></div><div className="tw"><table><tbody>{data.tags.map((t) => <tr key={t.tag_id}><td><Chip text={t.tag} tone="acc" /></td><td className="n">{data.can_manage ? <TargetInput label={`Target for tag ${t.tag}`} value={t.target_minor} onSave={(v) => save({ level: 'tag', tag_id: t.tag_id, amount_minor: v })} /> : (t.target_minor === null ? 'Not set' : inr(t.target_minor))}</td></tr>)}</tbody></table></div></div>
      </div>}
      <p className="note" style={{ marginTop: 12 }}>{data.note}</p>
    </>
  )
}

function TargetInput({ label, value, onSave, disabled }: { label: string; value: number | null; onSave: (v: number | null) => void; disabled?: boolean }) {
  const [v, setV] = useState(value === null ? '' : String(value / 100))
  return <input aria-label={label} style={{ width: 110, textAlign: 'right' }} inputMode="decimal" placeholder="Not set" disabled={disabled} value={v} onChange={(e) => setV(e.target.value)}
    onBlur={() => { const n = v.trim() === '' ? null : Math.round(Number(v) * 100); if (n !== value) onSave(n) }} onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }} />
}
