/** Checks the built organization against the workbook totals (cost allocated, bench, salary pool). */
import { call, ceoToken, data } from './live-lib.mjs'
const t = await ceoToken()
const j = await call('GET', '/api/insights', t)
const k = j.kpi
const pool = data.people.reduce((t, p) => t + p.salary, 0), cost = data.projects.reduce((t, p) => t + p.cost, 0)  // sum of every project, not the workbook total row (it skips one project)
const rows = [['cost allocated', k.cost_minor / 100, cost], ['bench', k.bench_cost_minor / 100, pool - cost], ['salary pool', k.salary_pool_minor / 100, pool]]
let bad = 0
for (const [n, got, want] of rows) { const ok = Math.abs(got - want) < 1; if (!ok) bad++; console.log(ok ? 'ok  ' : 'FAIL', n, 'app', got, 'workbook', want) }
console.log('projects', j.projects.length, 'people', k.people, 'reconciles', k.reconciles)
process.exit(bad ? 1 : 0)
