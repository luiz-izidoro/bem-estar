import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api, DaySummary, getCsrf, Ingestion, Profile } from './api'
import { Language, strings } from './i18n'

type Tab = 'overview' | 'training' | 'data' | 'settings'

const fmt = (value: number | null | undefined, digits = 0) => value == null ? '—' : value.toFixed(digits)

function MetricCard({label, value, unit, detail}: {label: string; value: string; unit?: string; detail?: string}) {
  return <article className="metric-card">
    <div className="metric-label">{label}</div>
    <div className="metric-value">{value}<span>{unit}</span></div>
    {detail && <div className="metric-detail">{detail}</div>}
  </article>
}

function Login({language, onSuccess}: {language: Language; onSuccess: () => void}) {
  const t = strings[language]
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('')
    try {
      await api('/auth/login', {method: 'POST', body: JSON.stringify({username, password})})
      onSuccess()
    } catch (err) { setError(err instanceof Error ? err.message : 'Login failed') }
    finally { setBusy(false) }
  }
  return <main className="login-shell">
    <section className="login-card">
      <div className="brand-mark">⌁</div>
      <h1>Bem Estar</h1>
      <p>{t.privacy}</p>
      <form onSubmit={submit}>
        <label>{t.username}<input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} /></label>
        <label>{t.password}<input autoComplete="current-password" type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
        {error && <div className="error">{error}</div>}
        <button disabled={busy}>{busy ? '…' : t.signIn}</button>
      </form>
    </section>
  </main>
}

export default function App() {
  const [language, setLanguage] = useState<Language>((localStorage.getItem('bemestar.lang') as Language) || 'pt-BR')
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [summary, setSummary] = useState<DaySummary | null>(null)
  const [ingestions, setIngestions] = useState<Ingestion[]>([])
  const [insight, setInsight] = useState('')
  const [profile, setProfile] = useState<Profile | null>(null)
  const [profileStatus, setProfileStatus] = useState('')
  const [tab, setTab] = useState<Tab>('overview')
  const [loading, setLoading] = useState(false)
  const t = strings[language]

  async function checkAuth() {
    try { await api('/api/v1/me'); setAuthenticated(true); await load() }
    catch { setAuthenticated(false) }
  }
  async function load() {
    setLoading(true)
    try {
      const [s, i, ins, p] = await Promise.all([
        api<DaySummary>('/api/v1/dashboard/today'),
        api<Ingestion[]>('/api/v1/ingestions?limit=8'),
        api<{insight: string}>(`/api/v1/insights/daily?language=${encodeURIComponent(language)}`),
        api<Profile>('/api/v1/settings/profile')
      ])
      setSummary(s); setIngestions(i); setInsight(ins.insight); setProfile(p)
    } finally { setLoading(false) }
  }
  async function saveProfile(e: FormEvent) {
    e.preventDefault()
    if (!profile) return
    setProfileStatus('…')
    try {
      await api<Profile>('/api/v1/settings/profile', {method: 'PUT', headers: {'X-CSRF-Token': getCsrf()}, body: JSON.stringify(profile)})
      await api('/api/v1/admin/recompute', {method: 'POST', headers: {'X-CSRF-Token': getCsrf()}})
      setProfileStatus(t.saved)
      await load()
    } catch (err) {
      setProfileStatus(err instanceof Error ? err.message : 'Error')
    }
  }
  useEffect(() => { checkAuth() }, [])
  useEffect(() => { localStorage.setItem('bemestar.lang', language); if (authenticated) load() }, [language])
  const d = summary?.derived || {}
  const r = summary?.raw || {}
  const readinessDetail = useMemo(() => {
    const version = summary?.versions?.readiness_live || ''
    const confidence = summary?.derived?.readiness_confidence
    return confidence == null ? version : `${version} · ${Math.round(confidence)}% data`
  }, [summary])

  if (authenticated === null) return <div className="splash">Bem Estar</div>
  if (!authenticated) return <Login language={language} onSuccess={() => {setAuthenticated(true); load()}} />

  return <div className="app-shell">
    <header>
      <div><div className="eyebrow">BEM ESTAR</div><h1>{t.welcome}</h1><p>{summary?.date || ''}</p></div>
      <button className="ghost" onClick={load} disabled={loading}>{loading ? '…' : t.refresh}</button>
    </header>

    <nav className="tabs">
      {(['overview','training','data','settings'] as Tab[]).map(x => <button key={x} className={tab === x ? 'active' : ''} onClick={() => setTab(x)}>{t[x]}</button>)}
    </nav>

    {tab === 'overview' && <>
      <section className="hero-grid">
        <MetricCard label={t.readiness} value={fmt(d.readiness_live)} unit="/100" detail={readinessDetail}/>
        <MetricCard label={t.recovery} value={fmt(d.recovery)} unit="/100" />
        <MetricCard label={t.sleep} value={fmt(d.sleep_hours, 1)} unit="h" />
        <MetricCard label={t.hrv} value={fmt(r.heart_rate_variability)} unit="ms" />
        <MetricCard label={t.restingHr} value={fmt(r.resting_heart_rate)} unit="bpm" />
        <MetricCard label={t.trainingLoad} value={fmt(d.training_load, 1)} unit="TRIMP" />
      </section>
      <section className="panel insight"><div className="panel-title">{t.insight}</div><p>{insight || t.noData}</p></section>
      <section className="panel"><div className="panel-title">{t.recentWorkouts}</div>
        <div className="workout-list">{summary?.workouts?.length ? summary.workouts.map(w => <div className="row" key={w.id}><div><strong>{w.name}</strong><small>{new Date(w.start).toLocaleString(language)}</small></div><div className="row-value">{Math.round(w.duration_seconds/60)} min{w.distance_km ? ` · ${w.distance_km.toFixed(1)} km` : ''}</div></div>) : <div className="empty">{t.noData}</div>}</div>
      </section>
    </>}

    {tab === 'training' && <>
      <section className="hero-grid training-grid">
        <MetricCard label={t.trainingLoad} value={fmt(d.training_load,1)} unit="TRIMP" />
        <MetricCard label={t.fitness} value={fmt(d.ctl,1)} />
        <MetricCard label={t.fatigue} value={fmt(d.atl,1)} />
        <MetricCard label={t.balance} value={fmt(d.tsb,1)} />
        <MetricCard label={t.acwr} value={fmt(d.acwr,2)} />
      </section>
      <section className="panel"><p>{t.profileHint}</p></section>
    </>}

    {tab === 'data' && <section className="panel"><div className="panel-title">{t.ingestion}</div>
      <div className="ingestion-list">{ingestions.length ? ingestions.map(i => <div className="row" key={i.id}><div><strong>{i.stream}</strong><small>{new Date(i.received_at).toLocaleString(language)}</small></div><div className={`status ${i.status}`}>{(t as any)[i.status] || i.status} · {i.records_inserted}/{i.records_received}</div></div>) : <div className="empty">{t.noData}</div>}</div>
    </section>}

    {tab === 'settings' && <section className="panel settings-panel">
      <div className="panel-title">{t.settings}</div>
      <label>{t.language}<select value={language} onChange={e => setLanguage(e.target.value as Language)}><option value="pt-BR">Português (Brasil)</option><option value="en">English</option></select></label>
      <p className="settings-help">{t.profileHint}</p>
      {profile && <form className="profile-form" onSubmit={saveProfile}>
        <div className="form-grid">
          <label>{t.maxHr}<input type="number" min="80" max="260" value={profile.hr_max ?? ''} onChange={e => setProfile({...profile, hr_max: e.target.value ? Number(e.target.value) : null})}/></label>
          <label>{t.restingHrSetting}<input type="number" min="25" max="140" value={profile.hr_rest ?? ''} onChange={e => setProfile({...profile, hr_rest: e.target.value ? Number(e.target.value) : null})}/></label>
          <label>{t.targetSleep}<input type="number" min="4" max="12" step="0.1" value={profile.target_sleep_hours} onChange={e => setProfile({...profile, target_sleep_hours: Number(e.target.value)})}/></label>
          <label>{t.trimpCoefficient}<input type="number" min="0.5" max="4" step="0.01" value={profile.trimp_exponential_coefficient} onChange={e => setProfile({...profile, trimp_exponential_coefficient: Number(e.target.value)})}/></label>
        </div>
        <button>{t.saveProfile}</button>
        {profileStatus && <small className="profile-status">{profileStatus}</small>}
      </form>}
      <a className="button-link" href="/grafana/" target="_blank" rel="noreferrer">{t.grafana}</a>
      <button className="danger-light" onClick={async () => {await api('/auth/logout',{method:'POST',headers:{'X-CSRF-Token':getCsrf()}}); setAuthenticated(false)}}>Logout</button>
    </section>}

    <footer>{t.privacy}</footer>
  </div>
}
