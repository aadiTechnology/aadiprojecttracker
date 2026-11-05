/** Smoke test for the HTML prototype: opens every screen for every role and fails on script errors or empty screens. */
import { createRequire } from 'node:module'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import { here } from './lib.mjs'
const require = createRequire('C:/Users/lenovo/AadiTech/Product/AadiProduct/MultiTenant/Aadi-MultiTenant-Platform/frontend/package.json')
const { chromium } = require('playwright')
const url = pathToFileURL(path.resolve(here, '../docs/Aadi_Role_Based_Feature_Proposal.html')).href
const browser = await chromium.launch({ headless: true, channel: 'chrome' }).catch(() => chromium.launch({ headless: true }))
const page = await (await browser.newContext({ viewport: { width: 1600, height: 900 } })).newPage()
const errors = []
page.on('pageerror', (e) => errors.push(e.message))
page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
await page.goto(url)
const roles = await page.$$eval('#roles .rp', (b) => b.map((x) => x.dataset.role))
let screens = 0
for (const r of roles) {
  await page.click(`#roles [data-role="${r}"]`)
  const views = await page.$$eval('#nav .nav', (b) => b.map((x) => [x.dataset.view, x.getAttribute('aria-disabled') === 'true']))
  for (const [v, off] of views) {
    await page.click(`#nav [data-view="${v}"]`, { force: true })
    const text = await page.locator('#view').innerText()
    if (!text.trim()) errors.push(`${r}/${v}: empty screen`)
    if (off && !text.includes('Access restricted')) errors.push(`${r}/${v}: restricted screen not shown`)
    screens++
  }
}
console.log(`roles=${roles.length} screens opened=${screens} errors=${errors.length}`)
errors.forEach((e) => console.log(' -', e))
await browser.close()
process.exit(errors.length ? 1 : 0)
