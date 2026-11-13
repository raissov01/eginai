// Диагноздан кейінгі қосымша құралдар: кері байланыс, шек есептегіші, ауа райы, белгілер анықтағышы.
import { useState } from 'react'
import { api, type Advice, type KeyGroup, type Weather } from './api'
import { economics } from './calc'
import type { Lang, Texts } from './i18n'

export function Feedback({ t, predicted, confidence, options }: {
  t: Texts; predicted: string; confidence: number; options: { id: string; name: string }[]
}) {
  const [st, setSt] = useState<'ask' | 'which' | 'busy' | 'done' | 'err'>('ask')
  const [actual, setActual] = useState('')

  async function send(correct: boolean) {
    setSt('busy')
    try {
      await api.feedback({ predicted, confidence, correct, actual: correct ? null : actual || null })
      setSt('done')
    } catch { setSt('err') }
  }

  if (st === 'done') return <p className="notice ok" role="status">{t.fbThanks}</p>
  return (
    <div className="panel">
      <h2>{t.fbTitle}</h2>
      {st === 'which' ? (
        <>
          <label className="field">
            <span>{t.fbWhich}</span>
            <select value={actual} onChange={(e) => setActual(e.target.value)}>
              <option value="">{t.fbUnknown}</option>
              {options.filter((o) => o.id !== predicted).map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
          </label>
          <button className="btn-primary" onClick={() => send(false)}>{t.fbSend}</button>
        </>
      ) : (
        <div className="row">
          <button className="btn-secondary" disabled={st === 'busy'} onClick={() => send(true)}>{t.fbYes}</button>
          <button className="btn-secondary" disabled={st === 'busy'} onClick={() => setSt('which')}>{t.fbNo}</button>
        </div>
      )}
      {st === 'err' && <p className="notice error" role="alert">{t.netError}</p>}
    </div>
  )
}

export function ThresholdCalc({ t, range }: { t: Texts; range: [number, number] }) {
  const [text, setText] = useState('')
  const nums = text.split(/[\s,;]+/).map((x) => Number(x.replace(',', '.'))).filter((x) => x >= 0 && x <= 100 && Number.isFinite(x))
  const mean = nums.length ? Math.round((nums.reduce((a, b) => a + b, 0) / nums.length) * 10) / 10 : null
  const [lo, hi] = range
  const verdict = mean == null ? null : mean >= hi ? 'above' : mean >= lo ? 'near' : 'below'
  return (
    <details className="calc">
      <summary>{t.thrTitle}</summary>
      <p>{t.thrText(lo, hi)}</p>
      <label className="field">
        <span>{t.thrInput}</span>
        <input inputMode="decimal" value={text} onChange={(e) => setText(e.target.value)} placeholder="0 2 5 1 0 3" />
      </label>
      {mean != null && (
        <p className={`notice ${verdict === 'above' ? 'error' : verdict === 'near' ? 'warn' : 'ok'}`} role="status">
          <strong>{t.thrMean(mean, nums.length)}</strong><br />
          {verdict === 'above' ? t.thrAbove : verdict === 'near' ? t.thrNear : t.thrBelow}
        </p>
      )}
      <Economics t={t} />
    </details>
  )
}

const ECO_KEY = 'eginai.eco.v1'

function Economics({ t }: { t: Texts }) {
  const [v, setV] = useState<Record<string, string>>(() => {
    try { return JSON.parse(localStorage.getItem(ECO_KEY) || '{}') } catch { return {} }
  })
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const n = { ...v, [k]: e.target.value }
    setV(n)
    try { localStorage.setItem(ECO_KEY, JSON.stringify(n)) } catch { /* жеке режим */ }
  }
  const num = (k: string) => Number((v[k] || '').replace(',', '.').replace(/\s/g, ''))
  const [y, p, c, l] = [num('y'), num('p'), num('c'), num('l')]
  const ok = y > 0 && p > 0 && c >= 0 && l >= 0 && l <= 100 && v.c && v.l
  const r = ok ? economics(y, p, c, l) : null
  return (
    <div className="eco">
      <h3>{t.ecoTitle}</h3>
      <div className="row">
        <label className="field grow"><span>{t.ecoYield}</span><input inputMode="decimal" value={v.y || ''} onChange={set('y')} /></label>
        <label className="field grow"><span>{t.ecoPrice}</span><input inputMode="numeric" value={v.p || ''} onChange={set('p')} /></label>
      </div>
      <div className="row">
        <label className="field grow"><span>{t.ecoCost}</span><input inputMode="numeric" value={v.c || ''} onChange={set('c')} /></label>
        <label className="field grow"><span>{t.ecoLoss}</span><input inputMode="decimal" value={v.l || ''} onChange={set('l')} /></label>
      </div>
      <p className="fine">{t.ecoLossHint}</p>
      {r && (
        <p className={`notice ${r.worth ? 'ok' : 'warn'}`} role="status">
          {t.ecoResult(r.loss, c)}<br /><strong>{r.worth ? t.ecoYes : t.ecoNo}</strong>
          {r.breakEven != null && <><br />{t.ecoBreakEven(r.breakEven)}</>}
        </p>
      )}
    </div>
  )
}

export function Share({ t, name, prob, preview }: { t: Texts; name: string; prob: number; preview: string }) {
  const [copied, setCopied] = useState(false)
  async function go() {
    const field = (() => { try { return JSON.parse(localStorage.getItem('eginai.history.v1') || '[]')[0]?.field ?? '' } catch { return '' } })()
    const text = t.shareText(name, Math.round(prob * 100), field, new Date().toLocaleDateString('ru-RU')) + `\n${location.origin}`
    try {
      const blob = await (await fetch(preview)).blob()
      const file = new File([blob], 'eginai.jpg', { type: 'image/jpeg' })
      const data: ShareData = navigator.canShare?.({ files: [file] }) ? { text, files: [file] } : { text }
      if (navigator.share) { await navigator.share(data); return }
    } catch (e) {
      if ((e as DOMException)?.name === 'AbortError') return
    }
    try { await navigator.clipboard.writeText(text); setCopied(true) } catch { /* көшіру мүмкін емес */ }
    window.open(`https://t.me/share/url?url=${encodeURIComponent(location.origin)}&text=${encodeURIComponent(text)}`, '_blank', 'noopener')
  }
  return (
    <div className="share">
      <button className="btn-secondary" onClick={go}>{t.shareBtn}</button>
      {copied && <p className="fine" role="status">{t.shareCopied}</p>}
    </div>
  )
}

// Уақыт — алқаптың жергілікті уақыты (API белдеусіз ISO береді); локальға тәуелсіз форматтаймыз
const hm = (iso: string) => iso.slice(11, 16)
const span = (w: { start: string; end: string }, t: Texts) => {
  const d = new Date(w.start.slice(0, 10) + 'T00:00')
  return `${t.wd[d.getDay()]}, ${d.getDate()} · ${hm(w.start)}–${hm(w.end)}`
}

export function WeatherPanel({ lang, t, focus }: { lang: Lang; t: Texts; focus?: string }) {
  const [st, setSt] = useState<'idle' | 'busy' | 'geo' | 'err'>('idle')
  const [wx, setWx] = useState<Weather | null>(null)

  function load() {
    if (!navigator.geolocation) return setSt('geo')
    setSt('busy')
    navigator.geolocation.getCurrentPosition(
      async (p) => {
        try { setWx(await api.weather(p.coords.latitude, p.coords.longitude, lang)); setSt('idle') } catch { setSt('err') }
      },
      () => setSt('geo'),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    )
  }

  const risk = wx ? [...wx.risk].sort((a, b) => Number(b.id === focus) - Number(a.id === focus)) : []
  return (
    <div className="panel">
      <h2>{t.wxTitle}</h2>
      {!wx && (
        <>
          <p className="muted">{t.wxText}</p>
          <button className="btn-primary" disabled={st === 'busy'} onClick={load}>{t.wxBtn}</button>
          {st === 'geo' && <p className="notice error" role="alert">{t.geoDenied}</p>}
          {st === 'err' && <p className="notice error" role="alert">{t.wxDown}</p>}
        </>
      )}
      {wx && (
        <>
          {!wx.in_season && <p className="notice">{t.wxOff}</p>}
          <h3>{t.wxRisk}</h3>
          <ul className="risk">
            {risk.map((r) => (
              <li key={r.id} className={r.id === focus ? 'focus' : ''}>
                <span className={`lvl lvl-${r.level}`}>{t.wxLevel[r.level]}</span>
                <span><b>{r.name}</b><br /><small className="muted">{r.reason}</small></span>
              </li>
            ))}
          </ul>
          <h3>{t.wxSpray}</h3>
          {wx.spray_windows.length === 0 ? <p className="muted">{t.wxNoSpray}</p> : (
            <ul className="windows">
              {wx.spray_windows.map((w) => (
                <li key={w.start}>
                  <b>{span(w, t)}</b>
                  <span className="muted">{t.wxWin(w.hours, w.wind_max, w.t_min, w.t_max)}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="fine">{t.wxNote} · {wx.source}</p>
        </>
      )}
    </div>
  )
}

export function SymptomKey({ lang, t }: { lang: Lang; t: Texts }) {
  const [key, setKey] = useState<KeyGroup[] | null>(null)
  const [where, setWhere] = useState<KeyGroup | null>(null)
  const [adv, setAdv] = useState<Advice | null>(null)
  const [error, setError] = useState(false)

  async function open(e: React.SyntheticEvent<HTMLDetailsElement>) {
    if (!e.currentTarget.open || key) return
    try { setKey(await api.symptomKey(lang)) } catch { setError(true) }
  }
  async function pick(id: string) {
    try { setAdv(await api.advice(id, lang)) } catch { setError(true) }
  }

  return (
    <details className="panel key" onToggle={open}>
      <summary><b>{t.keyTitle}</b></summary>
      <p className="muted">{t.keyText}</p>
      {error && <p className="notice error" role="alert">{t.netError}</p>}
      {key && !where && (
        <div className="row">{key.map((g) => <button key={g.id} className="btn-secondary" onClick={() => setWhere(g)}>{g.name}</button>)}</div>
      )}
      {where && !adv && (
        <>
          <h3>{where.name}: {t.keyPick}</h3>
          <ul className="options">
            {where.options.map((o) => (
              <li key={o.id}><button onClick={() => pick(o.id)}>{o.look}</button></li>
            ))}
          </ul>
          <button className="btn-secondary" onClick={() => setWhere(null)}>{t.keyBack}</button>
        </>
      )}
      {adv && (
        <div className="answer">
          <h3>{adv.title}</h3>
          <p>{adv.symptoms}</p>
          {adv.severity !== 'none' && <><h4>{t.sec.actions}</h4><p>{adv.actions.agro}</p><p className="fine">{t.disclaimer}</p></>}
          <button className="btn-secondary" onClick={() => setAdv(null)}>{t.keyBack}</button>
        </div>
      )}
    </details>
  )
}
