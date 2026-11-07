/** Runs the whole series in order as a rehearsal (FAST: no voice, no video) with the background builds placed exactly as for the real recording. Use a throwaway database. */
import { spawnSync } from 'node:child_process'
const BEFORE = { 6: 6, 7: 7, 8: 8, 10: 10 }, AFTER = { 2: 2, 3: 3, 5: 5 }
const from = Number(process.argv[2] ?? 1), to = Number(process.argv[3] ?? 12), fast = process.env.REAL ? {} : { FAST: '1' }
const run = (args) => { const r = spawnSync('node', args, { stdio: 'inherit', env: { ...process.env, ...fast } }); if (r.status !== 0) { console.error('FAILED:', args.join(' ')); process.exit(1) } }
for (let n = from; n <= to; n++) {
  console.log(`\n=== chapter ${n}`)
  if (BEFORE[n]) run(['build-background.mjs', String(BEFORE[n])])
  run(['record-live.mjs', String(n)])
  if (AFTER[n]) run(['build-background.mjs', String(AFTER[n])])
}
console.log('\nALL CHAPTERS OK')
