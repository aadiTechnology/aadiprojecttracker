import { FormEvent, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Me, api, useApi } from '../api'
import { Chip, ErrorBox, Loading, PageHead, toast } from '../ui'

interface Reply { intent: string; question: string; answer: string[]; evidence: { label: string; path: string }[]; follow_ups: string[]; caveats: string[]; disclosure: string }
interface Info { examples: string[]; limit: number; used_today: number; provider: string; tenant_questions: number | null; tenant_cost_minor: number | null }

export default function Assistant({ me }: { me: Me }) {
  const info = useApi<Info>('/api/assistant/info')
  const [q, setQ] = useState('')
  const [thread, setThread] = useState<Reply[]>([])
  const [busy, setBusy] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  if (info.loading && !info.data) return <Loading />
  if (info.error || !info.data) return <ErrorBox msg={info.error ?? 'Could not load the assistant.'} />
  const d = info.data
  async function ask(text: string) {
    if (!text.trim()) return
    setBusy(true)
    try {
      const r = await api<Reply>('/api/assistant', { method: 'POST', body: { question: text } })
      setThread((t) => [...t, r]); setQ(''); info.reload()
      setTimeout(() => end.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (x) { toast((x as Error).message) } finally { setBusy(false) }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); ask(q) }
  return (
    <>
      <PageHead title="AI Management Assistant" sub={`Ask about ${me.tenant.name}. Answers come only from the screens your role can open.`} />
      <div className="note" role="note" style={{ marginBottom: 12 }}><b>Advisory only.</b> Answers are rule-based from your permitted data. No language model is used, no data leaves the server, and the assistant never changes records, approves, rates people or sends messages. Every answer names the screen to check.</div>
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="tools" style={{ marginBottom: 6 }}><b>Try asking</b><span style={{ flex: 1 }} /><small>{d.used_today} of {d.limit} questions used today</small></div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>{d.examples.map((e) => <button key={e} className="btn sm" disabled={busy} onClick={() => ask(e)}>{e}</button>)}</div>
      </div>
      <div aria-live="polite">
        {thread.map((r, i) => (
          <div key={i} style={{ marginBottom: 14 }}>
            <div className="card" style={{ background: 'var(--acc-bg, #eef2ff)', marginBottom: 6 }}><b>You:</b> {r.question}</div>
            <div className="card">
              <div style={{ marginBottom: 6 }}><Chip text={`Topic: ${r.intent}`} tone="acc" /></div>
              {r.answer.map((l, j) => <p key={j} style={{ margin: '6px 0' }}>{l}</p>)}
              {r.caveats.map((l) => <p key={l} className="note w" style={{ margin: '6px 0' }}>{l}</p>)}
              {r.evidence.length > 0 && <p style={{ margin: '8px 0 0' }}><small>Check it on: </small>{r.evidence.map((e) => <Link key={e.path + e.label} to={e.path} style={{ marginRight: 12 }}>{e.label}</Link>)}</p>}
              {r.follow_ups.length > 0 && <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 8 }}>{r.follow_ups.map((f) => <button key={f} className="btn sm" disabled={busy} onClick={() => ask(f)}>{f}</button>)}</div>}
            </div>
          </div>))}
        <div ref={end} />
      </div>
      <form onSubmit={submit} className="tools" style={{ position: 'sticky', bottom: 0, background: 'var(--bg, #f6f7fb)', padding: '10px 0' }}>
        <label style={{ flex: 1 }}><span className="sr-only" style={{ position: 'absolute', left: -9999 }}>Your question</span>
          <input style={{ width: '100%' }} value={q} maxLength={300} placeholder="Ask a management question, for example: which projects have a thin margin?" onChange={(e) => setQ(e.target.value)} /></label>
        <button className="btn pri" disabled={busy || q.trim().length < 3}>Ask</button>
      </form>
      {d.tenant_questions !== null && <p className="note" style={{ marginTop: 12 }}>Organization usage: {d.tenant_questions} questions, cost Rs {((d.tenant_cost_minor ?? 0) / 100).toLocaleString('en-IN')} (no model is called).</p>}
    </>
  )
}
