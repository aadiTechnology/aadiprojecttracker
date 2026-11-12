import { FormEvent, useEffect, useState } from 'react'
import { api, authConfig, AuthConfig, token } from '../api'

interface Demo { password: string; notice: string; accounts: { name: string; role: string; title: string; email: string; hint: string; org?: string; password?: string }[] }

export default function Login({ onDone }: { onDone: (platform: boolean) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [demo, setDemo] = useState<Demo | null>(null)
  const [forgot, setForgot] = useState(false)
  const [info, setInfo] = useState('')

  const [cfg, setCfg] = useState<AuthConfig | null>(null)
  const ssoError = new URLSearchParams(window.location.search).get('sso_error')
  const ssoMessages: Record<string, string> = {
    no_access: 'You are signed in to Aadi, but you have no access to Project Tracker for that company. Ask your administrator.',
    no_account: 'Your Aadi account has no matching Project Tracker user yet. Ask your administrator to add you.',
    no_company: 'That company is not set up in Project Tracker yet.', denied: 'Sign-in was cancelled.',
    expired: 'The sign-in took too long. Please try again.', state: 'The sign-in answer did not match. Please try again.', exchange: 'Aadi sign-in could not be completed. Please try again.' }
  useEffect(() => {
    authConfig().then((c) => {
      setCfg(c)
      // Identity-only environments go straight to Aadi sign-in unless there is something to explain
      if (c.mode === 'platform' && !new URLSearchParams(window.location.search).get('sso_error')) window.location.href = c.start_url
    })
  }, [])
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
        {cfg?.sso && (
          <section className="card f" aria-label="Sign in with Aadi">
            <h1>Sign in with Aadi</h1>
            {ssoError && <div className="err" role="alert">{ssoMessages[ssoError] ?? 'Sign-in failed. Please try again.'}</div>}
            <a className="btn pri" href={cfg.start_url} data-testid="sso-signin">Continue with Aadi sign-in</a>
            {cfg.local && <p className="sub" style={{ margin: 0 }}>Or use your Project Tracker password below.</p>}
          </section>
        )}
        {(!cfg || cfg.local) && <form className="card f" onSubmit={submit} aria-label="Sign in">
          <h1>{forgot ? 'Reset your password' : 'Sign in'}</h1>
          <label>Email<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          {!forgot && <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>}
          {err && <div className="err" role="alert">{err}</div>}
          {info && <div className="note" role="status">{info}</div>}
          <button className="btn pri" disabled={busy}>{forgot ? 'Send reset link' : 'Sign in'}</button>
          <button type="button" className="btn sm" style={{ justifySelf: 'start', border: 0 }} onClick={() => { setForgot(!forgot); setErr(''); setInfo('') }}>{forgot ? 'Back to sign in' : 'Forgot password?'}</button>
        </form>}

        {demo && cfg?.local !== false && (
          <section className="card" aria-labelledby="demo-h">
            <h2 id="demo-h">Demo accounts (test users for every role)</h2>
            <p className="sub" style={{ marginBottom: 8 }}>{demo.notice} Choose <b>Use</b> to fill the form, then press Sign in. Each role sees different data.</p>
            <div className="tw demo"><table>
              <thead><tr><th>Person</th><th>Role</th><th>What to try</th><th /></tr></thead>
              <tbody>{byRole.map((a, i) => (
                <tr key={a.email} style={a.org && byRole[i - 1]?.org !== a.org ? { borderTop: '3px solid var(--acc)' } : undefined}>
                  <td><b>{a.name}</b>{a.org === 'matrix' && <> <span className="chip c-info">Matrix org</span></>}{a.org === 'aadi-test' && <> <span className="chip c-ok">Aadi-Test</span></>}<br /><span className="mono">{a.email}</span></td>
                  <td>{a.role}</td><td>{a.hint}</td>
                  <td><button type="button" className="btn sm" onClick={() => { setForgot(false); setEmail(a.email); setPassword(a.password ?? demo.password); window.scrollTo(0, 0) }} aria-label={`Use ${a.name}`}>Use</button></td>
                </tr>))}</tbody>
            </table></div>
            <p className="note" style={{ marginTop: 10 }}>Shared demo password for every account: <span className="mono">{demo.password}</span>; for the Aadi-Test people: <span className="mono">{byRole.find((x) => x.password)?.password}</span> (disposable, demo environment only).</p>
          </section>
        )}
      </div>
    </main>
  )
}
