/** Accessibility sweep: opens every menu screen for several roles and runs axe-core (WCAG 2.1 A/AA). Fails on serious or critical findings. TRACKER_URL selects the target. */
import { createRequire } from 'node:module'
import fs from 'node:fs'
const require = createRequire('C:/Users/lenovo/AadiTech/Product/AadiProduct/MultiTenant/Aadi-MultiTenant-Platform/frontend/package.json')
const { chromium } = require('playwright')
const axeSrc = fs.readFileSync(new URL('./node_modules/axe-core/axe.min.js', import.meta.url), 'utf8')
const origin = process.env.TRACKER_URL ?? 'http://localhost:8000'
const who = (process.env.A11Y_USERS ?? 'Priya Rao,Sameer Joshi,Meera Nair').split(',')
const browser = await chromium.launch({ headless: true, channel: 'chrome' }).catch(() => chromium.launch({ headless: true }))
let bad = 0
const scan = async (page, label) => {
  await page.evaluate(axeSrc)
  const r = await page.evaluate(() => axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } }))
  const hard = r.violations.filter((v) => ['serious', 'critical'].includes(v.impact))
  for (const v of r.violations) console.log(`  ${hard.includes(v) ? 'FAIL' : 'note'} [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length}) @ ${label}  e.g. ${v.nodes[0].target.join(' ')}`)
  bad += hard.length
}
const login = await browser.newPage()
await login.goto(origin + '/'); await login.waitForTimeout(800); await scan(login, 'sign-in'); await login.close()
for (const name of who) {
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } }); const page = await ctx.newPage()
  await page.goto(origin + '/', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: `Use ${name}` }).click(); await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('navigation').first().waitFor()
  const links = await page.getByRole('navigation').getByRole('link').evaluateAll((a) => a.map((x) => [x.textContent.trim(), x.getAttribute('href')]))
  console.log(name, links.length, 'screens')
  for (const [label, href] of links) { await page.goto(origin + href, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(1200); await scan(page, `${name} / ${label}`) }
  await ctx.close()
}
await browser.close()
console.log(bad ? `FAILED: ${bad} serious or critical findings` : 'PASS: no serious or critical accessibility findings')
process.exit(bad ? 1 : 0)
