import { useCallback, useEffect, useState } from 'react'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? ''
const KEY = 'tracker.token'
export const token = {
  get: () => sessionStorage.getItem(KEY),
  set: (t: string) => sessionStorage.setItem(KEY, t),
  clear: () => sessionStorage.removeItem(KEY),
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message) }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const r = await fetch(BASE + path, {
    method: opts.method ?? 'GET',
    headers: { 'Content-Type': 'application/json', ...(token.get() ? { Authorization: `Bearer ${token.get()}` } : {}) },
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) {
    const d = data.detail ?? {}
    if (r.status === 401 && token.get()) { token.clear(); window.dispatchEvent(new Event('tracker:signout')) }
    throw new ApiError(r.status, d.code ?? 'ERROR', d.message ?? `Request failed (${r.status})`)
  }
  return data as T
}

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    if (!path) return
    setLoading(true)
    try { setData(await api<T>(path)); setError(null) } catch (e) { setError((e as Error).message) } finally { setLoading(false) }
  }, [path])
  useEffect(() => { load() }, [load])
  return { data, error, loading, reload: load }
}

// ---- types ----
export type Access = Record<string, { level: string | null; sprint: number; built: boolean }>
export interface Me {
  user: { id: number; name: string; email: string }
  tenant: { id: number; name: string; demo: boolean; currency: string; revenue_basis: string | null }
  role: { key: string; name: string }
  team: string
  perms: string[]
  modules: Record<string, boolean>
  access: Access
  tenants: { id: number; name: string; role: string; demo: boolean }[]
}

/** Amounts are stored in paise. Shown in lakh/crore for readability. */
export function money(minor: number | undefined | null): string {
  if (minor === undefined || minor === null) return '—'
  const rupees = minor / 100
  if (Math.abs(rupees) >= 1e7) return `₹${(rupees / 1e7).toFixed(2)} Cr`
  if (Math.abs(rupees) >= 1e5) return `₹${(rupees / 1e5).toFixed(2)} L`
  return `₹${rupees.toLocaleString('en-IN')}`
}
export const toMinor = (rupees: string) => Math.round(parseFloat(rupees || '0') * 100)
