import { FormEvent, useState } from 'react'
import { Me, api, inr, useApi } from '../api'
import { Chip, ErrorBox, Loading, Modal, PageHead, toast } from '../ui'

interface Emp { id: number; name: string; title: string; team: string; department_id: number | null; department: string | null; is_head: boolean; hours: number; hours_override: number | null; allocated_pct?: number; bench_pct?: number; salary_minor?: number | null; cost_per_hour_minor?: number | null }
interface Dept { id: number; name: string; head_user_id: number | null; head: string | null; employees: number }

const status = (e: Emp) => e.allocated_pct === undefined ? null : e.allocated_pct > 100 ? <Chip text="Over-allocated" tone="bad" /> : e.allocated_pct === 100 ? <Chip text="Fully allocated" tone="ok" /> : e.allocated_pct === 0 ? <Chip text="Bench" tone="warn" /> : <Chip text={`${e.allocated_pct}% allocated`} tone="info" />

export default function Employees({ me }: { me: Me }) {
  const [tab, setTab] = useState('Employees')
  const emps = useApi<Emp[]>('/api/employees')
  const depts = useApi<Dept[]>('/api/departments')
  const manage = me.perms.includes('employees.manage'), manageDept = me.perms.includes('departments.manage'), manageSalary = me.perms.includes('salary.manage')
  const [salaryFor, setSalaryFor] = useState<Emp | null>(null)
  const [newDept, setNewDept] = useState('')
  const reload = () => { emps.reload(); depts.reload() }
  const run = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); toast(ok); reload() } catch (x) { toast((x as Error).message) } }
  const showSalary = emps.data?.some((e) => e.salary_minor !== undefined)
  return (
    <>
      <PageHead title="Employees & Departments" sub="Employee master with department and Head of Department. Salary is restricted to roles that hold salary access." />
      <div className="tabs" role="tablist">{['Employees', 'Departments'].map((t) => <button key={t} role="tab" aria-selected={tab === t} className="tab" onClick={() => setTab(t)}>{t}</button>)}</div>
      {tab === 'Employees' && (emps.loading ? <Loading /> : emps.error ? <ErrorBox msg={emps.error} /> : (
        <div className="card flat"><div className="tw"><table>
          <thead><tr><th>Employee</th><th>Title</th><th>Department</th><th>Monthly hours</th>{showSalary && <><th className="n">Monthly salary</th><th className="n">Cost / hour</th></>}<th>This month</th><th /></tr></thead>
          <tbody>{emps.data!.map((e) => (
            <tr key={e.id}><td><b>{e.name}</b></td><td>{e.title}</td>
              <td>{manage ? <select aria-label={`Department of ${e.name}`} value={e.department_id ?? ''} onChange={(ev) => run(() => api(`/api/employees/${e.id}`, { method: 'PATCH', body: { department_id: ev.target.value ? +ev.target.value : null } }), 'Department updated')}><option value="">— none —</option>{depts.data?.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select> : (e.department ?? '—')}{e.is_head && <> <Chip text="Head" tone="acc" /></>}</td>
              <td>{e.hours}{e.hours_override ? ' (override)' : ''}</td>
              {showSalary && <><td className="n">{e.salary_minor === null ? <Chip text="Missing" tone="warn" /> : inr(e.salary_minor)}</td><td className="n">{e.cost_per_hour_minor ? inr(e.cost_per_hour_minor) : '—'}</td></>}
              <td>{status(e) ?? '—'}</td>
              <td>{manageSalary && <button className="btn sm" onClick={() => setSalaryFor(e)}>Set salary</button>}</td></tr>))}</tbody></table></div></div>))}
      {tab === 'Departments' && (depts.loading ? <Loading /> : depts.error ? <ErrorBox msg={depts.error} /> : <>
        <div className="card flat"><div className="tw"><table>
          <thead><tr><th>Department</th><th>Head of Department</th><th className="n">Employees</th></tr></thead>
          <tbody>{depts.data!.map((d) => (
            <tr key={d.id}><td><b>{d.name}</b></td>
              <td>{manageDept ? <select aria-label={`Head of ${d.name}`} value={d.head_user_id ?? ''} onChange={(ev) => run(() => api(`/api/departments/${d.id}`, { method: 'PATCH', body: { name: d.name, head_user_id: ev.target.value ? +ev.target.value : null } }), 'Head of Department updated')}><option value="">— not set —</option>{emps.data?.filter((e) => e.department_id === d.id).map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}</select> : (d.head ?? '—')}</td>
              <td className="n">{d.employees}</td></tr>))}</tbody></table></div></div>
        {manageDept && <form className="tools" style={{ marginTop: 12 }} onSubmit={(e) => { e.preventDefault(); run(async () => { await api('/api/departments', { method: 'POST', body: { name: newDept } }); setNewDept('') }, 'Department added') }}>
          <input aria-label="New department name" placeholder="New department" value={newDept} onChange={(e) => setNewDept(e.target.value)} /><button className="btn pri" disabled={!newDept.trim()}>Add department</button></form>}
        <p className="note" style={{ marginTop: 12 }}>A Head of Department must be an employee of that department. To change who heads a department, pick another person first.</p></>)}
      {salaryFor && <SalaryModal e={salaryFor} onClose={() => setSalaryFor(null)} onSaved={() => { setSalaryFor(null); reload() }} />}
    </>
  )
}

function SalaryModal({ e, onClose, onSaved }: { e: Emp; onClose: () => void; onSaved: () => void }) {
  const hist = useApi<{ effective_from: string; amount_minor: number }[]>(`/api/employees/${e.id}/salary`)
  const [amount, setAmount] = useState('')
  const [from, setFrom] = useState(new Date().toISOString().slice(0, 10))
  const [err, setErr] = useState('')
  async function save(ev: FormEvent) {
    ev.preventDefault(); setErr('')
    try { await api(`/api/employees/${e.id}/salary`, { method: 'PUT', body: { amount_minor: Math.round(parseFloat(amount) * 100), effective_from: from } }); toast('Salary saved (effective-dated, audited)'); onSaved() } catch (x) { setErr((x as Error).message) }
  }
  return (
    <Modal title={`Salary · ${e.name}`} onClose={onClose}>
      <form className="f" onSubmit={save}>
        <label>Monthly salary, cost to company (₹)<input required inputMode="decimal" value={amount} onChange={(x) => setAmount(x.target.value)} /></label>
        <label>Effective from<input type="date" required value={from} onChange={(x) => setFrom(x.target.value)} /></label>
        {err && <div className="err" role="alert">{err}</div>}
        <div className="mf" style={{ padding: 0, border: 0 }}><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn pri">Save salary</button></div>
      </form>
      <h3>History</h3>
      <table><thead><tr><th>Effective from</th><th className="n">Monthly salary</th></tr></thead><tbody>{hist.data?.map((h) => <tr key={h.effective_from}><td>{h.effective_from}</td><td className="n">{inr(h.amount_minor)}</td></tr>)}</tbody></table>
      <p className="note" style={{ marginTop: 10 }}>A new salary applies from its effective date. Earlier months keep the salary that was valid then. Amounts are not written to the audit log.</p>
    </Modal>
  )
}
