/** Helpers shared by the sprint recorders. The demo password is typed only into masked fields. */
import { click, loadPassword, origin } from './lib.mjs'

export const password = loadPassword()
export const email = (key) => `${key}@aadi.demo.test`

export async function signInTyped(page, key) {
  await page.goto(origin + '/', { waitUntil: 'domcontentloaded' })
  await page.getByLabel('Email').fill(email(key))
  const field = page.getByLabel('Password')
  await field.fill(password)
  if ((await field.getAttribute('type')) !== 'password') throw new Error('The password field is not masked')
  await click(page.getByRole('button', { name: 'Sign in', exact: true }))
  await page.getByRole('navigation').first().waitFor()
}

/** Sign in using the "Use" button of the demo account list under the login form. */
export async function signInViaDemoList(page, name) {
  await page.goto(origin + '/', { waitUntil: 'domcontentloaded' })
  await click(page.getByRole('button', { name: `Use ${name}` }))
  await click(page.getByRole('button', { name: 'Sign in', exact: true }))
  await page.getByRole('navigation').first().waitFor()
}

export async function signOut(page) {
  while (await page.locator('.overlay').count()) {
    await page.keyboard.press('Escape')
    await page.waitForTimeout(400)
  }
  await click(page.getByTestId('signout'))
  await page.getByRole('button', { name: 'Sign in', exact: true }).waitFor()
}

export const nav = async (page, name) => {
  await click(page.getByRole('navigation').getByRole('link', { name }))
  await page.waitForLoadState('networkidle')
}

export async function scroll(page, pixels, steps = 6) {
  for (let i = 0; i < steps; i += 1) {
    await page.mouse.wheel(0, pixels / steps)
    await page.waitForTimeout(220)
  }
}

export async function typeSlow(locator, text) {
  await locator.click()
  await locator.pressSequentially(text, { delay: 55 })
}

export async function assertNoSecret(page) {
  // the shared demo password is intentionally printed in the demo-accounts panel on the sign-in page only
  if (page.url().includes('/reset')) return
  const signedIn = (await page.getByTestId('signout').count()) > 0
  if (signedIn && (await page.locator('body').innerText()).includes(password)) throw new Error('The demo password is visible on screen')
}

export const heading = (page, name) => page.getByRole('heading', { name, exact: true }).waitFor()
export { click, origin }

/** Call an API path from the signed-in page and show the raw status on screen (proves server-side enforcement). */
export async function apiProbe(page, label, path) {
  return page.evaluate(async ({ label, path }) => {
    const r = await fetch(path, { headers: { Authorization: `Bearer ${sessionStorage.getItem('tracker.token')}` } })
    const b = await r.json().catch(() => ({}))
    const d = b.detail
    const text = `Direct API call - ${label}: HTTP ${r.status}${d ? ' - ' + (typeof d === 'object' ? `${d.code}: ${d.message}` : d) : ''}`
    document.getElementById('probe')?.remove()
    const el = document.createElement('div')
    el.id = 'probe'
    el.textContent = text
    el.setAttribute('style', 'position:fixed;left:20px;right:20px;bottom:20px;z-index:99999;background:#1b1f3b;color:#fff;padding:16px 20px;border-radius:10px;font:600 16px Segoe UI')
    document.body.appendChild(el)
    return text
  }, { label, path })
}
