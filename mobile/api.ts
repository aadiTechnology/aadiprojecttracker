// API client. The base URL comes from EXPO_PUBLIC_API_URL (set it per environment); the default is the demo deployment.
const BASE = (process.env.EXPO_PUBLIC_API_URL ?? 'https://aadiprojecttrackerapi.aaditechnology.com').replace(/\/$/, '')
// In memory only: signing out or closing the app clears it. A production build should keep it in expo-secure-store.
let token: string | null = null

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const r = await fetch(BASE + path, {
    method: opts.method ?? 'GET',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new ApiError(r.status, data?.detail?.message ?? `Request failed (${r.status})`)
  return data as T
}

export async function signIn(email: string, password: string) {
  const r = await api<{ token: string; platform_admin: boolean }>('/api/auth/login', { method: 'POST', body: { email, password } })
  if (r.platform_admin) throw new ApiError(403, 'Platform administrators use the web app.')
  token = r.token
}
export const signOut = () => { token = null }

export interface Me { user: { name: string }; role: { name: string }; tenant: { name: string; demo: boolean }; perms: string[] }
export interface Task { id: number; project: string; sprint: string | null; title: string; status: string; priority: string; est_hours: number; due_date: string | null; assignee: string | null }
export interface Entry { id: number; project: string; project_id: number; task_id: number | null; task: string | null; work_date: string; hours: number; note: string; status: string; reject_reason: string; editable: boolean }
export interface Week { week_start: string; week_end: string; entries: Entry[]; total: number; target: number; submittable: boolean }
export interface Handover { id: number; project: string; from: string; to: string; note: string; status: string; tasks: { id: number; title: string }[]; can_ack: boolean }
export interface Notice { unread: number; items: { id: number; text: string; read: boolean; at: string }[] }
export interface Proj { id: number; label: string; tasks: { id: number; title: string }[] }
