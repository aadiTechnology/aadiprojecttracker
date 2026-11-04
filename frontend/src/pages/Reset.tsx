import { FormEvent, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'

export default function Reset() {
  const [q] = useSearchParams()
  const nav = useNavigate()
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const [err, setErr] = useState('')
  const [done, setDone] = useState(false)
  async function submit(e: FormEvent) {
    e.preventDefault()
    if (pw !== pw2) { setErr('The two passwords do not match.'); return }
    try { await api('/api/auth/reset', { method: 'POST', body: { token: q.get('token') ?? '', password: pw } }); setDone(true) } catch (x) { setErr((x as Error).message) }
  }
  return (
    <main className="login"><div className="box" style={{ maxWidth: 440 }}>
      <form className="card f" onSubmit={submit} aria-label="Choose a password">
        <h1>Choose your password</h1>
        {done ? <><div className="note" role="status">Password saved. You can sign in now.</div><button type="button" className="btn pri" onClick={() => nav('/')}>Go to sign in</button></> : <>
          <p className="sub">Use at least 10 characters with upper and lower case letters and a number.</p>
          <label>New password<input type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} required /></label>
          <label>Repeat password<input type="password" autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} required /></label>
          {err && <div className="err" role="alert">{err}</div>}
          <button className="btn pri">Save password</button></>}
      </form></div></main>
  )
}
