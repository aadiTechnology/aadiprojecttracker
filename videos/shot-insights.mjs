/** Dev helper: sign in as matrix-organization personas and save a full-page screenshot of Decision Insights per lens. */
import { createRequire } from 'node:module'
import fs from 'node:fs'
const require = createRequire('C:/Users/lenovo/AadiTech/Product/AadiProduct/MultiTenant/Aadi-MultiTenant-Platform/frontend/package.json')
const { chromium } = require('playwright')
const origin = process.env.TRACKER_URL ?? 'http://localhost:8000'
const out = process.argv[2]
fs.mkdirSync(out, { recursive: true })
const browser = await chromium.launch({ headless: true, channel: 'chrome' }).catch(() => chromium.launch({ headless: true }))
const plan = [['Rhea Kulkarni', 'ceo', 'CEO'], ['Tanvi Joshi', 'po', 'Product Owner'], ['Anil Deshpande', 'pm', 'Project Manager']]
for (const [name, key, lens] of plan) {
  const ctx = await browser.newContext({ viewport: { width: 1500, height: 900 } })
  const page = await ctx.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(String(e)))
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  await page.goto(origin + '/', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: `Use ${name}` }).click()
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('navigation').first().waitFor()
  await page.getByRole('navigation').getByRole('link', { name: 'Decision Insights' }).click()
  await page.getByRole('heading', { name: 'Decision Insights' }).waitFor()
  for (const l of ['CEO', 'Product Owner', 'Project Manager']) {
    await page.getByRole('tab', { name: new RegExp('^' + l) }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${out}/${key}-as-${l.replace(' ', '')}.png`, fullPage: true })
  }
  console.log(name, 'errors:', errors.length ? errors : 'none')
  await ctx.close()
}
await browser.close()
