import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from './api'

interface N { unread: number; items: { id: number; text: string; link: string; read: boolean; at: string }[] }

export default function Bell() {
  const [n, setN] = useState<N | null>(null)
  const [open, setOpen] = useState(false)
  const nav = useNavigate()
  const load = () => api<N>('/api/notifications').then(setN).catch(() => setN(null))
  useEffect(() => { load(); const t = setInterval(load, 60000); return () => clearInterval(t) }, [])
  if (!n) return null
  async function toggle() {
    const next = !open
    setOpen(next)
    if (next && n!.unread) { await api('/api/notifications/read', { method: 'POST' }).catch(() => {}); setTimeout(load, 1500) }
  }
  return (
    <div style={{ position: 'relative' }}>
      <button className="btn" onClick={toggle} aria-label={`Notifications, ${n.unread} unread`} aria-expanded={open} data-testid="bell">🔔{n.unread > 0 && <b style={{ marginLeft: 4, color: 'var(--bad)' }}>{n.unread}</b>}</button>
      {open && <div className="card" role="dialog" aria-label="Notifications" style={{ position: 'absolute', right: 0, top: 40, width: 360, maxHeight: 380, overflow: 'auto', zIndex: 30 }}>
        {n.items.length === 0 ? <small>No notifications.</small> : n.items.map((x) => (
          <div key={x.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--line)', cursor: x.link ? 'pointer' : 'default', fontWeight: x.read ? 400 : 600 }} onClick={() => { if (x.link) { setOpen(false); nav(x.link) } }}>
            {x.text}<br /><small>{x.at.slice(0, 16).replace('T', ' ')}</small></div>))}</div>}
    </div>
  )
}
