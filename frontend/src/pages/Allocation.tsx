import { useState } from 'react'
import { Me, api, thisMonth, useApi } from '../api'
import { Chip, ErrorBox, Loading, PageHead, toast } from '../ui'

interface Matrix {
  month: string; can_manage: boolean; partial: boolean
  employees: { id: number; name: string; department: string | null; total_pct: number; hours: number }[]
  projects: { id: number; code: string; name: string; status: string; can_edit: boolean }[]
  cells: { user_id: number; project_id: number; percent: number }[]
}

export default function Allocation({ me }: { me: Me }) {
  const [month, setMonth] = useState(thisMonth())
  const { data, error, loading, reload } = useApi<Matrix>(`/api/allocations?month=${month}`)
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [bad, setBad] = useState<string | null>(null)
  if (loading && !data) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load allocation.'} />
  const cell = (u: number, p: number) => data.cells.find((c) => c.user_id === u && c.project_id === p)?.percent ?? 0
  const colTotal = (p: number) => data.cells.filter((c) => c.project_id === p).reduce((s, c) => s + c.percent, 0)
  async function save(u: number, p: number) {
    const key = `${u}_${p}`, raw = (draft[key] ?? '').trim()
    if (draft[key] === undefined) return
    const v = raw === '' ? 0 : Number(raw)
    try {
      if (!Number.isInteger(v)) throw new Error('Enter a whole number from 0 to 100.')
      await api('/api/allocations', { method: 'PUT', body: { user_id: u, project_id: p, month, percent: v } })
      setBad(null); toast('Allocation saved')
    } catch (x) { setBad(key); toast((x as Error).message) }
    setDraft((d) => { const n = { ...d }; delete n[key]; return n })
    reload()
  }
  async function copyForward() {
    const [y, m] = month.split('-').map(Number), next = new Date(y, m, 1)
    const to = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}`
    try { const r = await api<{ added: number; skipped: number }>('/api/allocations/copy', { method: 'POST', body: { from_month: month, to_month: to } }); toast(`Copied to ${to}: ${r.added} added, ${r.skipped} skipped`) } catch (x) { toast((x as Error).message) }
  }
  const canCopy = me.perms.includes('allocation.manage:all')
  return (
    <>
      <PageHead title="Employee Allocation" sub="Percent of each employee's month spent on each project. A person can work on many projects but never above 100% in total." />
      <div className="formula"><b>Rules:</b> an employee's total in a month is at most <code>100%</code> · allocating adds the person to the project team · anything under 100% is <b>bench</b> capacity.</div>
      <div className="tools">
        <label>Month <input type="month" value={month} onChange={(e) => setMonth(e.target.value || thisMonth())} /></label>
        <span style={{ flex: 1 }} />
        {canCopy && <button className="btn" onClick={copyForward}>Copy to next month</button>}
      </div>
      {data.partial && <div className="note mb">Showing only the projects in your scope.</div>}
      <div className="card flat"><div className="tw"><table className="alloc">
        <thead><tr><th className="nm">Employee</th>{data.projects.map((p) => <th key={p.id} className="n" title={p.name}>{p.code.replace('PRJ-', 'P')}</th>)}<th className="n">Total</th><th className="n">Hours</th><th>Capacity</th></tr></thead>
        <tbody>{data.employees.map((e) => (
          <tr key={e.id}><td className="nm"><b>{e.name}</b><br /><small>{e.department ?? ''}</small></td>
            {data.projects.map((p) => {
              const key = `${e.id}_${p.id}`, v = cell(e.id, p.id)
              return <td key={p.id} className="n">{data.can_manage && p.can_edit
                ? <input aria-label={`${e.name} on ${p.name}, percent`} className={bad === key ? 'bad' : ''} inputMode="numeric" placeholder="–" value={draft[key] ?? (v ? String(v) : '')}
                    onChange={(ev) => setDraft((d) => ({ ...d, [key]: ev.target.value }))} onBlur={() => save(e.id, p.id)} onKeyDown={(ev) => { if (ev.key === 'Enter') (ev.target as HTMLInputElement).blur() }} />
                : (v ? `${v}%` : '–')}</td>
            })}
            <td className="n"><b className={e.total_pct > 100 ? 'neg' : ''}>{e.total_pct}%</b></td><td className="n">{e.hours}</td>
            <td>{e.total_pct === 0 ? <Chip text="Bench" tone="warn" /> : e.total_pct < 100 ? <Chip text={`${100 - e.total_pct}% free`} tone="warn" /> : <Chip text="Full" tone="ok" />}</td></tr>))}</tbody>
        <tfoot><tr><td className="nm"><b>Project total (%)</b></td>{data.projects.map((p) => <td key={p.id} className="n"><b>{colTotal(p.id)}</b></td>)}<td /><td /><td /></tr></tfoot>
      </table></div></div>
      <p className="sub" style={{ marginTop: 10 }}>{data.projects.map((p) => `${p.code.replace('PRJ-', 'P')} ${p.name}`).join(' · ')}</p>
      {data.can_manage && <p className="note">Type a percentage and press Enter or leave the field. Entries that would put a person above 100% are rejected by the server with the reason.</p>}
    </>
  )
}
