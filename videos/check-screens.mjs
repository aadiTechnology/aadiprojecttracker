/** Signs in as every demo persona through the browser and opens every screen in the menu. Fails on any error banner or blank page. */
import { createRequire } from 'node:module'
import { email, password, origin } from './common.mjs'
const require = createRequire('C:/Users/lenovo/AadiTech/Product/AadiProduct/MultiTenant/Aadi-MultiTenant-Platform/frontend/package.json')
const { chromium } = require('playwright')

const people = ['priya.rao', 'sameer.joshi', 'vikram.shah', 'asha.kulkarni', 'nisha.verma', 'rohan.mehta', 'meera.nair', 'dev.patel', 'isha.kapoor', 'nina.iyer', 'arjun.singh', 'kabir.sethi', 'tara.menon', 'platform.admin']
const browser = await chromium.launch({ headless: true, channel: 'chrome' }).catch(() => chromium.launch({ headless: true }))
let failures = 0
for (const key of people) {
  const page = await (await browser.newContext({ viewport: { width: 1400, height: 900 } })).newPage()
  const problems = []
  page.on('pageerror', (e) => problems.push('script error: ' + e.message))
  page.on('response', (r) => { if (r.status() >= 500) problems.push(`HTTP ${r.status()} ${r.url()}`) })
  await page.goto(origin + '/')
  await page.getByLabel('Email').fill(email(key)); await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  let shown = 0, locked = 0
  if (key === 'platform.admin') {
    await page.getByRole('heading', { name: 'Tenants & entitlements' }).waitFor(); shown = 1
  } else {
    await page.getByRole('navigation').first().waitFor()
    const links = await page.getByRole('navigation').getByRole('link').evaluateAll((a) => a.map((x) => ({ href: x.getAttribute('href'), off: x.getAttribute('aria-disabled') === 'true' })))
    for (const l of links) {
      await page.goto(origin + l.href)
      await page.getByRole('heading', { level: 1 }).first().waitFor()
      await page.waitForLoadState('networkidle')
      const alerts = await page.locator('[role=alert]').allInnerTexts()
      const text = await page.locator('main').innerText()
      if (l.off) { if (!text.includes('Access restricted')) problems.push(`${l.href}: restricted page not shown`); locked++ }
      else { shown++; if (alerts.length) problems.push(`${l.href}: ${alerts.join(' | ')}`) }
    }
    // screens hidden from the menu must still be refused when the address is typed in
    for (const path of ['/profitability', '/costing-settings', '/admin']) {
      if (links.some((l) => l.href === path)) continue
      await page.goto(origin + path)
      await page.getByRole('heading', { level: 1 }).first().waitFor()
      if (!(await page.locator('main').innerText()).includes('Access restricted')) problems.push(`${path}: hidden screen not refused`)
      locked++
    }
  }
  console.log(`${problems.length ? 'FAIL' : 'ok  '} ${key.padEnd(15)} screens=${shown} restricted=${locked}${problems.length ? '\n   ' + problems.join('\n   ') : ''}`)
  failures += problems.length
  await page.context().close()
}
await browser.close()
process.exit(failures ? 1 : 0)
