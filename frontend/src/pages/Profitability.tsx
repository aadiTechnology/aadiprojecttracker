import { useState } from 'react'
import { Me, inr, thisMonth, useApi } from '../api'
import { Chip, ErrorBox, Kpi, Loading, Modal, PageHead } from '../ui'

interface Row { id: number; code: string; name: string; tags: { id: number; name: string }[]; hours: number; revenue_minor: number | null; cost_minor: number; target_minor: number | null; value_minor: number; margin_minor: number | null; margin_pct: number | null; warnings: string[] }
interface Prof { rows: Row[]; excluded_without_revenue: number; note: string; totals: { revenue_minor: number; cost_minor: number; margin_minor: number; margin_pct: number | null; bench_cost_minor: number | null; result_after_bench_minor: number | null; salary_pool_minor: number } }
interface TagRow { tag_id: number; tag: string; projects: number; hours: number; value_minor: number; cost_minor: number; margin_minor: number; project_list: { id: number; code: string; name: string; hours: number; value_minor: number; cost_minor: number }[] }

const marginTone = (p: number | null) => (p === null ? '' : p >= 50 ? 'ok' : p >= 25 ? 'warn' : 'bad')

export default function Profitability({ me }: { me: Me }) {
  const [tab, setTab] = useState('Projects')
  const [month, setMonth] = useState(thisMonth())
  const [basis, setBasis] = useState('standard')
  const [primary, setPrimary] = useState(false)
  const [open, setOpen] = useState<TagRow | null>(null)
  const pr = useApi<Prof>(tab === 'Projects' ? `/api/costing/profitability?month=${month}&basis=${basis}` : null)
  const tg = useApi<{ rows: TagRow[]; note: string; additive: boolean }>(tab === 'Tags' ? `/api/costing/tags?month=${month}&primary=${primary}` : null)
  return (
    <>
      <PageHead title="Project Profitability" sub="Revenue basis minus salary cost, with the unallocated salary shown on its own line." />
      <div className="tools"><label>Month <input type="month" value={month} onChange={(e) => setMonth(e.target.value || thisMonth())} /></label></div>
      <div className="tabs" role="tablist">{['Projects', 'Tags'].map((t) => <button key={t} role="tab" aria-selected={tab === t} className="tab" onClick={() => setTab(t)}>{t === 'Tags' ? 'Tag-wise analysis' : 'By project'}</button>)}</div>
      {tab === 'Projects' && <>
        <div className="tools"><label>Revenue basis <select value={basis} onChange={(e) => setBasis(e.target.value)}><option value="standard">Standard value (hours × rate)</option><option value="target">Revenue target (where set)</option></select></label></div>
        {pr.loading && !pr.data ? <Loading /> : pr.error || !pr.data ? <ErrorBox msg={pr.error ?? 'Could not load.'} /> : <>
          <div className="grid g4 mb">
            <Kpi label="Revenue basis" value={inr(pr.data.totals.revenue_minor)} sub={pr.data.excluded_without_revenue ? `${pr.data.excluded_without_revenue} projects without a target are excluded` : 'All projects included'} />
            <Kpi label="Salary cost" value={inr(pr.data.totals.cost_minor)} sub="Allocation × salary" />
            <Kpi label="Margin" value={<span className={pr.data.totals.margin_minor >= 0 ? 'pos' : 'neg'}>{inr(pr.data.totals.margin_minor)}</span>} sub={pr.data.totals.margin_pct !== null ? `${pr.data.totals.margin_pct}% of revenue basis` : ''} />
            <Kpi label="Unallocated salary (bench)" value={inr(pr.data.totals.bench_cost_minor)} sub={`Salary pool ${inr(pr.data.totals.salary_pool_minor)}`} />
          </div>
          <div className="card flat"><div className="tw"><table>
            <thead><tr><th>Project</th><th>Tags</th><th className="n">Hours</th><th className="n">Revenue basis</th><th className="n">Salary cost</th><th className="n">Margin</th><th>Margin %</th><th>Status</th></tr></thead>
            <tbody>{pr.data.rows.map((r) => <tr key={r.id}><td><b>{r.name}</b><br /><small>{r.code}</small></td><td>{r.tags.map((t) => <Chip key={t.id} text={t.name} tone="acc" />)}</td><td className="n">{r.hours}</td>
              <td className="n">{inr(r.revenue_minor)}</td><td className="n">{inr(r.cost_minor)}</td><td className="n">{r.margin_minor === null ? '—' : <span className={r.margin_minor >= 0 ? 'pos' : 'neg'}>{inr(r.margin_minor)}</span>}</td>
              <td>{r.margin_pct === null ? '—' : <><div className="bar" style={{ display: 'inline-block', width: 80, verticalAlign: 'middle' }}><i style={{ width: `${Math.max(0, Math.min(100, r.margin_pct))}%` }} /></div> <small>{r.margin_pct}%</small></>}</td>
              <td>{r.warnings.length ? r.warnings.map((w) => <Chip key={w} text={w} tone="warn" />) : <Chip text={r.margin_minor !== null && r.margin_minor < 0 ? 'Loss' : 'Profit'} tone={r.margin_minor !== null && r.margin_minor < 0 ? 'bad' : 'ok'} />}</td></tr>)}</tbody>
            <tfoot><tr><td><b>Allocated work</b></td><td /><td /><td className="n">{inr(pr.data.totals.revenue_minor)}</td><td className="n">{inr(pr.data.totals.cost_minor)}</td><td className="n">{inr(pr.data.totals.margin_minor)}</td><td /><td /></tr>
              <tr><td>Unallocated salary (bench)</td><td /><td /><td /><td className="n">{inr(pr.data.totals.bench_cost_minor)}</td><td className="n"><span className="neg">{pr.data.totals.bench_cost_minor === null ? '—' : inr(-pr.data.totals.bench_cost_minor)}</span></td><td /><td /></tr>
              <tr><td><b>Result after bench</b></td><td /><td /><td /><td /><td className="n"><b>{inr(pr.data.totals.result_after_bench_minor)}</b></td><td /><td /></tr></tfoot></table></div></div>
          <p className="note" style={{ marginTop: 12 }}>{pr.data.note} The revenue basis is an open business decision.</p></>}</>}
      {tab === 'Tags' && <>
        <div className="tools"><label style={{ display: 'inline-flex', gap: 6 }}><input type="checkbox" checked={primary} onChange={(e) => setPrimary(e.target.checked)} /> Count each project once under its primary tag (additive)</label></div>
        {tg.data && <div className={`note ${tg.data.additive ? '' : 'w'} mb`}>{tg.data.note}</div>}
        {tg.loading && !tg.data ? <Loading /> : tg.error || !tg.data ? <ErrorBox msg={tg.error ?? 'Could not load.'} /> : <div className="card flat"><div className="tw"><table>
          <thead><tr><th>Tag</th><th className="n">Projects</th><th className="n">Hours</th><th className="n">Standard value</th><th className="n">Salary cost</th><th className="n">Margin</th><th>%</th><th /></tr></thead>
          <tbody>{tg.data.rows.map((r) => { const pct = r.value_minor ? Math.round((r.margin_minor * 1000) / r.value_minor) / 10 : null; return <tr key={r.tag_id}><td><Chip text={r.tag} tone="acc" /></td><td className="n">{r.projects}</td><td className="n">{r.hours}</td><td className="n">{inr(r.value_minor)}</td><td className="n">{inr(r.cost_minor)}</td>
            <td className="n"><span className={r.margin_minor >= 0 ? 'pos' : 'neg'}>{inr(r.margin_minor)}</span></td><td><Chip text={pct === null ? '—' : `${pct}%`} tone={marginTone(pct)} /></td><td><button className="btn sm" onClick={() => setOpen(r)}>Projects</button></td></tr> })}</tbody></table></div></div>}</>}
      {open && <Modal title={`Projects tagged ${open.tag}`} onClose={() => setOpen(null)}><table><thead><tr><th>Project</th><th className="n">Hours</th><th className="n">Value</th><th className="n">Cost</th></tr></thead>
        <tbody>{open.project_list.map((p) => <tr key={p.id}><td>{p.code} {p.name}</td><td className="n">{p.hours}</td><td className="n">{inr(p.value_minor)}</td><td className="n">{inr(p.cost_minor)}</td></tr>)}</tbody></table></Modal>}
    </>
  )
}
