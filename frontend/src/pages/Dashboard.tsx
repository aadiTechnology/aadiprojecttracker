import { Link } from 'react-router-dom'
import { Me, money, useApi } from '../api'
import { Chip, ErrorBox, Kpi, Loading, PageHead } from '../ui'

interface D {
  role: string; scope: string
  projects?: { total: number; by_status: Record<string, number>; health: Record<string, number> }
  project_list?: { id: number; code: string; name: string; status: string; health: string }[]
  budget_minor?: number; contract_value_minor?: number; customers?: number; people?: number; open_decisions: string[]
}

export default function Dashboard({ me }: { me: Me }) {
  const { data, error, loading } = useApi<D>('/api/dashboard')
  if (loading) return <Loading />
  if (error || !data) return <ErrorBox msg={error ?? 'Could not load the dashboard.'} />
  const p = data.projects
  return (
    <>
      <PageHead title="Overview Dashboard" sub={`${data.role} · ${data.scope}`} />
      <div className="grid g4 mb">
        {p && <Kpi label="Projects" value={p.total} sub={Object.entries(p.by_status).map(([k, v]) => `${v} ${k}`).join(' · ')} />}
        {p && <Kpi label="Active delivery health" value={<>{p.health.Green} <span style={{ color: 'var(--ok)' }}>G</span> · {p.health.Amber} <span style={{ color: 'var(--warn)' }}>A</span> · {p.health.Red} <span style={{ color: 'var(--bad)' }}>R</span></>} sub="Green / Amber / Red" />}
        {data.budget_minor !== undefined && <Kpi label="Total project budget" value={money(data.budget_minor)} sub="Planned spend, not actual cost" />}
        {data.contract_value_minor !== undefined && <Kpi label="Contract value" value={money(data.contract_value_minor)} sub="Expected revenue, not recognized revenue" />}
        {data.customers !== undefined && <Kpi label="Customers & business units" value={data.customers} sub="In your scope" />}
        {data.people !== undefined && <Kpi label="Active people" value={data.people} sub="Members of this organization" />}
      </div>
      {!p && <div className="card mb"><h2>Welcome, {me.user.name.split(' ')[0]}</h2>
        <p>Your role ({me.role.name}) is focused on your own work. Your tasks, sprint commitments, handovers and timesheets arrive in Sprint 2. Until then you can review what your role can access in the <Link to="/matrix">permission matrix</Link>.</p></div>}
      {data.project_list && data.project_list.length > 0 && <div className="card flat mb"><div style={{ padding: '14px 16px 0' }}><h2>Projects in your scope</h2></div>
        <div className="tw"><table><thead><tr><th>Code</th><th>Project</th><th>Status</th><th>Health</th></tr></thead><tbody>
          {data.project_list.map((x) => <tr key={x.id}><td>{x.code}</td><td><Link to="/projects">{x.name}</Link></td><td><Chip text={x.status} /></td><td><Chip text={x.health} /></td></tr>)}</tbody></table></div></div>}
      {data.open_decisions.length > 0 && <div className="note w"><b>Open customer decisions:</b> {data.open_decisions.join('; ')}. See <Link to="/assumptions">Assumptions &amp; Decisions</Link>.</div>}
    </>
  )
}
