/** Shared helpers for the live walkthrough series: workbook data (local, git-ignored), saved credentials, API client, sign-in. No figures live in this file. */
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
export const ORIGIN = process.env.TRACKER_URL ?? 'http://localhost:8000'
export const API = process.env.TRACKER_API ?? (ORIGIN.includes('aadiprojecttracker.aaditechnology.com') ? 'https://aadiprojecttrackerapi.aaditechnology.com' : ORIGIN)
export const TENANT_NAME = process.env.LIVE_TENANT ?? 'Aadi Technology - live'
const statePath = path.join(here, process.env.LIVE_STATE ?? '.state.json')
export const data = JSON.parse(fs.readFileSync(path.join(here, '.data.json'), 'utf8'))

export const state = fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath, 'utf8')) : {}
export const save = () => fs.writeFileSync(statePath, JSON.stringify(state, null, 1))
const pw = () => 'Aadi-' + crypto.randomBytes(6).toString('base64url') + '#9'

// The three people on camera. Everyone else is created in the background without email.
export const FEATURED = { dept: 'Software Development', tag: 'Education', member: 'Kalyani', project: 'RITe School', ceo: 'Prajakta', pm: 'Anjali' }
export const ceoPerson = () => data.people.find((p) => p.department === 'Management')
export function creds() {
  if (!state.users) {
    state.users = {
      ceo: { name: FEATURED.ceo, email: process.env.LIVE_CEO_EMAIL ?? 'ajitsagale+prajakta@gmail.com', password: pw(), role: 'owner', title: 'CEO' },
      pm: { name: FEATURED.pm, email: 'anjali@aadi-live.demo.test', password: pw(), role: 'pm', title: 'Project Manager' },
      member: { name: FEATURED.member, email: process.env.LIVE_MEMBER_EMAIL ?? 'ajitsagale+kalyani@gmail.com', password: pw(), role: 'employee', title: 'Software Engineer' },
    }
    save()
  }
  return state.users
}
export const emailOf = (name) => (Object.values(creds()).find((u) => u.name === name)?.email) ?? `${name.toLowerCase()}@aadi-live.demo.test`

export async function call(method, p, token, body) {
  const r = await fetch(API + p, { method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) })
  const j = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(`${method} ${p} -> ${r.status} ${j.detail?.message ?? ''}`)
  return j
}
export async function login(email, password) {
  const j = await call('POST', '/api/auth/login', null, { email, password })
  return j.token
}
export const ceoToken = () => login(creds().ceo.email, creds().ceo.password)

/** Sets a password from an invitation link (what the person does in the browser) so the account can sign in. */
export async function activate(link, password) {
  const token = new URL(link).searchParams.get('token')
  await call('POST', '/api/auth/reset', null, { token, password })
}

/** Types the email and password into the real sign-in form (the password field is masked on screen). */
export async function signInForm(page, who, { slow = false } = {}) {
  const u = creds()[who]
  await page.goto(ORIGIN + '/', { waitUntil: 'domcontentloaded' })
  await page.evaluate(() => sessionStorage.clear())
  await page.goto(ORIGIN + '/', { waitUntil: 'domcontentloaded' })
  await page.getByLabel('Email').fill(u.email)
  await page.getByLabel('Password').fill(u.password)
  await page.waitForTimeout(slow ? 1500 : 300)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('navigation').first().waitFor()
  await page.waitForTimeout(1200)
}
