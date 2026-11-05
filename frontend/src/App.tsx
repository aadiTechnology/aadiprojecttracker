import { Fragment, useCallback, useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Me, api, token } from './api'
import Login from './pages/Login'
import Reset from './pages/Reset'
import Dashboard from './pages/Dashboard'
import Customers from './pages/Customers'
import Projects from './pages/Projects'
import Admin from './pages/Admin'
import SprintPage from './pages/Sprint'
import Handover from './pages/Handover'
import Timesheets from './pages/Timesheets'
import Employees from './pages/Employees'
import Allocation from './pages/Allocation'
import Costing from './pages/Costing'
import Insights from './pages/Insights'
import CostSettings from './pages/CostSettings'
import Profitability from './pages/Profitability'
import Targets from './pages/Targets'
import Platform from './pages/Platform'
import { Assumptions, Matrix, Workflow } from './pages/Info'
import { Loading, PageHead, Restricted } from './ui'
import Bell from './Bell'

const NAV: { key: string; label: string; icon: string; path: string; group?: string }[] = [
  { key: 'dash', label: 'Overview Dashboard', icon: '▦', path: '/', group: 'Workspace' },
  { key: 'customers', label: 'Customers', icon: '🏢', path: '/customers' },
  { key: 'projects', label: 'Projects', icon: '📁', path: '/projects' },
  { key: 'sprint', label: 'Sprint Planning', icon: '🗓', path: '/sprint' },
  { key: 'handover', label: 'Team Handover', icon: '⇄', path: '/handover' },
  { key: 'timesheets', label: 'Timesheets', icon: '⏱', path: '/timesheets' },
  { key: 'insights', label: 'Decision Insights', icon: '🎯', path: '/insights', group: 'Costing & Profitability' },
  { key: 'employees', label: 'Employees & Departments', icon: '👥', path: '/employees' },
  { key: 'allocation', label: 'Employee Allocation', icon: '🧩', path: '/allocation' },
  { key: 'costing', label: 'Effort & Cost', icon: '🧮', path: '/costing' },
  { key: 'profit', label: 'Project Profitability', icon: '📈', path: '/profitability' },
  { key: 'revenue', label: 'Revenue Targets', icon: '◎', path: '/revenue' },
  { key: 'costset', label: 'Costing Settings', icon: '⚙', path: '/costing-settings' },
  { key: 'perf', label: 'Employee Performance', icon: '★', path: '/performance', group: 'Finance & Performance' },
  { key: 'expenses', label: 'Expenses & Cost', icon: '₹', path: '/expenses' },
  { key: 'invoices', label: 'Invoices', icon: '🧾', path: '/invoices' },
  { key: 'admin', label: 'Organization Admin', icon: '⚙', path: '/admin', group: 'Administration' },
  { key: 'matrix', label: 'Role & Permission Matrix', icon: '🔐', path: '/matrix', group: 'Product' },
  { key: 'workflow', label: 'Product Workflow', icon: '➜', path: '/workflow' },
  { key: 'assumptions', label: 'Assumptions & Decisions', icon: '❓', path: '/assumptions' },
]

function Planned({ item, sprint, role }: { item: (typeof NAV)[number]; sprint: number; role: string }) {
  return <><PageHead title={item.label} /><div className="card empty" role="status"><h2>Planned for Sprint {sprint}</h2>
    <p>This screen is not built yet. Your role ({role}) does have access to it in the proposed permission model; it will be delivered in Sprint {sprint} with its own demo video.</p></div></>
}

export default function App() {
  const nav = useNavigate()
  const loc = useLocation()
  const [me, setMe] = useState<Me | null>(null)
  const [platform, setPlatform] = useState(false)
  const [ready, setReady] = useState(false)

  const load = useCallback(async () => {
    if (!token.get()) { setMe(null); setPlatform(false); setReady(true); return }
    try { setMe(await api<Me>('/api/me')); setPlatform(false) } catch {
      try { const p = await api<{ platform_admin: boolean }>('/api/me/platform'); setPlatform(p.platform_admin); setMe(null) } catch { token.clear() }
    }
    setReady(true)
  }, [])
  useEffect(() => { load() }, [load])
  useEffect(() => { const f = () => { setMe(null); setPlatform(false) }; window.addEventListener('tracker:signout', f); return () => window.removeEventListener('tracker:signout', f) }, [])
  useEffect(() => { document.body.classList.remove('nav-open') }, [loc.pathname])

  const signOut = () => { token.clear(); setMe(null); setPlatform(false); nav('/') }

  if (!ready) return <Loading />
  if (loc.pathname === '/reset') return <Reset />
  if (!me && !platform) return <Login onDone={() => load()} />

  if (platform) {
    return (
      <div className="content"><div className="top" style={{ position: 'static', marginBottom: 14 }}><b>Aadi Project Tracker · Platform administration</b><span className="spacer" /><button className="btn" onClick={signOut}>Sign out</button></div>
        <Platform /></div>
    )
  }

  const m = me!
  const acc = (k: string) => m.access[k]
  let lastGroup = ''
  return (
    <div className="app">
      <a className="skip" href="#main">Skip to content</a>
      <aside className="sb" aria-label="Primary">
        <div className="brand"><div className="logo">A</div><div><b>Aadi Project Tracker</b><small>{m.tenant.name}</small></div></div>
        <nav aria-label="Main navigation">
          {NAV.map((n) => {
            const a = acc(n.key)
            const ok = !!a?.level
            const head = n.group && n.group !== lastGroup ? <div className="navh" key={'h' + n.key}>{n.group}</div> : null
            if (n.group) lastGroup = n.group
            return <Fragment key={n.key}>{head}
              <NavLink to={n.path} end={n.path === '/'} className={({ isActive }) => `nav ${isActive ? 'active' : ''} ${ok ? '' : 'off'}`} aria-disabled={!ok} title={ok ? undefined : 'Access restricted for your role'}>
                <span className="ic" aria-hidden="true">{n.icon}</span>{n.label}
                {!ok ? <span className="tag" aria-hidden="true">🔒</span> : !a.built ? <span className="tag">Sprint {a.sprint}</span> : null}
              </NavLink></Fragment>
          })}
        </nav>
        <div className="sbfoot">Menu shows what your role is proposed to access. Permissions are enforced by the API.</div>
      </aside>
      <main id="main" tabIndex={-1}>
        <header className="top">
          <button className="menu-btn" aria-label="Open menu" onClick={() => document.body.classList.toggle('nav-open')}>☰ Menu</button>
          {m.tenant.demo && <span className="banner">Illustrative demo data — not real records</span>}
          <span className="spacer" />
          {m.tenants.length > 1 && <label>Organization <select value={m.tenant.id} onChange={async (e) => { const r = await api<{ token: string }>('/api/auth/switch', { method: 'POST', body: { tenant_id: +e.target.value } }); token.set(r.token); load() }}>{m.tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>}
          <Bell />
          <div className="who"><b>{m.user.name}</b>{m.role.name}{m.team ? ` · ${m.team}` : ''}</div>
          <button className="btn" onClick={signOut} data-testid="signout">Sign out</button>
        </header>
        <div className="content">
          <Routes>
            <Route path="/" element={<Dashboard me={m} />} />
            {NAV.filter((n) => !['dash'].includes(n.key)).map((n) => {
              const a = acc(n.key)
              let el
              if (!a?.level) el = <Restricted what={n.label} role={m.role.name} />
              else if (!a.built) el = <Planned item={n} sprint={a.sprint} role={m.role.name} />
              else if (n.key === 'customers') el = <Customers me={m} />
              else if (n.key === 'projects') el = <Projects me={m} />
              else if (n.key === 'sprint') el = <SprintPage me={m} />
              else if (n.key === 'handover') el = <Handover me={m} />
              else if (n.key === 'timesheets') el = <Timesheets me={m} />
              else if (n.key === 'insights') el = <Insights me={m} />
              else if (n.key === 'employees') el = <Employees me={m} />
              else if (n.key === 'allocation') el = <Allocation me={m} />
              else if (n.key === 'costing') el = <Costing me={m} />
              else if (n.key === 'profit') el = <Profitability me={m} />
              else if (n.key === 'revenue') el = <Targets me={m} />
              else if (n.key === 'costset') el = <CostSettings me={m} />
              else if (n.key === 'admin') el = <Admin me={m} />
              else if (n.key === 'matrix') el = <Matrix />
              else if (n.key === 'workflow') el = <Workflow me={m} />
              else el = <Assumptions me={m} />
              return <Route key={n.key} path={n.path} element={el} />
            })}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}
