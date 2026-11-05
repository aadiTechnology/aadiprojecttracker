import { FormEvent, useEffect, useState } from 'react'
import { api, token } from '../api'

interface Demo { password: string; notice: string; accounts: { name: string; role: string; title: string; email: string; hint: string; org?: string }[] }

export default function Login({ onDone }: { onDone: (platform: boolean) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [demo, setDemo] = useState<Demo | null>(null)
  const [forgot, setForgot] = useState(false)
  const [info, setInfo] = useState('')

  useEffect(() => { api<Demo>('/api/demo/accounts').then(setDemo).catch(() => setDemo(null)) }, [])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true); setErr(''); setInfo('')
    try {
      if (forgot) {
        const r = await api<{ message: string }>('/api/auth/forgot', { method: 'POST', body: { email } })
        setInfo(r.message)
      } else {
        const r = await api<{ token: string; platform_admin: boolean }>('/api/auth/login', { method: 'POST', body: { email, password } })
        token.set(r.token)
        onDone(r.platform_admin)
      }
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }

  const byRole = demo ? demo.accounts : []
  return (
    <main className="login">
      <div className="box">
        <div className="brand" style={{ color: 'var(--ink)' }}><div className="logo">A</div><div><b>Aadi Project Tracker</b><small style={{ color: 'var(--mute)' }}>Business Performance &amp; Project Profitability</small></div></div>
        <form className="card f" onSubmit={submit} aria-label="Sign in">
          <h1>{forgot ? 'Reset your password' : 'Sign in'}</h1>
          <label>Email<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          {!forgot && <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>}
          {err && <div className="err" role="alert">{err}</div>}
          {info && <div className="note" role="status">{info}</div>}
          <button className="btn pri" disabled={busy}>{forgot ? 'Send reset link' : 'Sign in'}</button>
          <button type="button" className="btn sm" style={{ justifySelf: 'start', border: 0 }} onClick={() => { setForgot(!forgot); setErr(''); setInfo('') }}>{forgot ? 'Back to sign in' : 'Forgot password?'}</button>
        </form>

        {demo && (
          <section className="card" aria-labelledby="demo-h">
            <h2 id="demo-h">Demo accounts (test users for every role)</h2>
            <p className="sub" style={{ marginBottom: 8 }}>{demo.notice} Choose <b>Use</b> to fill the form, then press Sign in. Each role sees different data.</p>
            <div className="tw demo"><table>
              <thead><tr><th>Person</th><th>Role</th><th>What to try</th><th /></tr></thead>
              <tbody>{byRole.map((a, i) => (
                <tr key={a.email} style={a.org === 'matrix' && byRole[i - 1]?.org !== 'matrix' ? { borderTop: '3px solid var(--acc)' } : undefined}>
                  <td><b>{a.name}</b>{a.org === 'matrix' && <> <span className="chip c-info">Matrix org</span></>}<br /><span className="mono">{a.email}</span></td>
                  <td>{a.role}</td><td>{a.hint}</td>
                  <td><button type="button" className="btn sm" onClick={() => { setForgot(false); setEmail(a.email); setPassword(demo.password); window.scrollTo(0, 0) }} aria-label={`Use ${a.name}`}>Use</button></td>
                </tr>))}</tbody>
            </table></div>
            <p className="note" style={{ marginTop: 10 }}>Shared demo password for every account: <span className="mono">{demo.password}</span> (disposable, demo environment only).</p>
          </section>
        )}
      </div>
    </main>
  )
}
