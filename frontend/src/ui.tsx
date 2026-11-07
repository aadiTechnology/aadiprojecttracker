import { ReactNode, useEffect, useRef, useState } from 'react'
import { download } from './api'

export const chipTone: Record<string, string> = {
  Active: 'ok', Planned: 'info', 'On Hold': 'warn', Completed: 'ok', Draft: '', Cancelled: 'bad', Green: 'ok', Amber: 'warn', Red: 'bad',
  Done: 'ok', 'In progress': 'info', Blocked: 'bad', Pending: 'warn', Acknowledged: 'ok', Submitted: 'info', Closed: '', Requested: 'warn', Approved: 'ok', Rejected: 'bad', active: 'ok', invited: 'info', suspended: 'bad', trial: 'info',
}
export const Chip = ({ text, tone }: { text: string; tone?: string }) => <span className={`chip ${tone ?? chipTone[text] ? 'c-' + (tone ?? chipTone[text]) : ''}`}>{text}</span>

export function Modal({ title, onClose, children, footer, wide }: { title: string; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  const close = useRef(onClose)
  close.current = onClose // the parent may pass a new function on every render; focus must move into the dialog only once
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null
    ref.current?.focus()
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && close.current()
    window.addEventListener('keydown', esc)
    return () => { window.removeEventListener('keydown', esc); prev?.focus() }
  }, [])
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref}>
        <div className="mh"><h2>{title}</h2><button className="x" onClick={onClose} aria-label="Close">×</button></div>
        <div className="mb2">{children}</div>
        {footer && <div className="mf">{footer}</div>}
      </div>
    </div>
  )
}

let toastTimer: number | undefined
export function toast(msg: string) {
  let el = document.getElementById('toast')
  if (!el) { el = document.createElement('div'); el.id = 'toast'; el.setAttribute('role', 'status'); el.setAttribute('aria-live', 'polite'); document.body.appendChild(el) }
  el.textContent = msg
  el.style.display = 'block'
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { if (el) el.style.display = 'none' }, 3600)
}

export const Kpi = ({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) => (
  <div className="card kpi"><div className="l">{label}</div><div className="v">{value}</div><div className="s">{sub}</div></div>
)

export const Loading = () => <div className="empty" role="status">Loading…</div>
export const ErrorBox = ({ msg }: { msg: string }) => <div className="note e" role="alert">{msg}</div>

export function PageHead({ title, sub }: { title: string; sub?: string }) {
  return <><h1>{title}</h1>{sub && <p className="sub">{sub}</p>}</>
}

export function Restricted({ what, role }: { what: string; role: string }) {
  return (
    <div className="lock" role="alert"><div style={{ fontSize: 34 }} aria-hidden="true">🔒</div><h1>Access restricted</h1>
      <p><b>{what}</b> is not part of the access given to <b>{role}</b>.</p>
      <p>Permissions are configurable by the Organization Owner and enforced by the API on every request. No data from this area was loaded.</p></div>
  )
}

export function useDebounced<T>(v: T, ms = 250) {
  const [d, setD] = useState(v)
  useEffect(() => { const t = setTimeout(() => setD(v), ms); return () => clearTimeout(t) }, [v, ms])
  return d
}

export function ExportButton({ report, month }: { report: string; month?: string }) {
  const [busy, setBusy] = useState(false)
  return <button className="btn" disabled={busy} title={`Download ${report} as a CSV file`} onClick={async () => {
    setBusy(true)
    try { await download(`/api/export/${report}${month ? `?month=${month}` : ''}`, `${report}.csv`); toast('CSV downloaded') } catch (x) { toast((x as Error).message) } finally { setBusy(false) }
  }}><span aria-hidden="true">⬇</span> Export CSV</button>
}
