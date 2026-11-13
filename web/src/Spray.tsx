// Бүрку журналы: не, қай алқапқа, қанша, сол сәттегі ауа райы автоматты түрде.
// Тек осы браузерде сақталады (тарих сияқты), CSV етіп алуға болады.
import { useState } from 'react'
import { api } from './api'
import * as H from './history'
import { loadSprays, saveSprays, wxWarnings, type Spray } from './calc'
import type { Texts } from './i18n'

const nowLocal = () => {
  const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}
const cell = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : /^[=+\-@]/.test(v) ? `'${v}` : v)

export default function SprayLog({ t, lang }: { t: Texts; lang: 'kk' | 'ru' }) {
  const [items, setItems] = useState(loadSprays)
  const [f, setF] = useState<Omit<Spray, 'id'>>({ date: nowLocal(), field: '', product: '', ai: '', dose: '', area: '', note: '' })
  const [wxState, setWxState] = useState<'idle' | 'busy' | 'err'>('idle')
  const set = (k: keyof Spray) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value })

  function getWx() {
    if (!navigator.geolocation) return setWxState('err')
    setWxState('busy')
    navigator.geolocation.getCurrentPosition(async (p) => {
      try {
        const r = await api.weather(p.coords.latitude, p.coords.longitude, lang)
        if (!r.current) throw new Error('no current')
        setF((x) => ({ ...x, wx: r.current! })); setWxState('idle')
      } catch { setWxState('err') }
    }, () => setWxState('err'), { timeout: 10000, maximumAge: 600000 })
  }

  function add(e: React.FormEvent) {
    e.preventDefault()
    const next = [{ ...f, id: crypto.randomUUID?.() ?? String(Date.now()) }, ...items]
    saveSprays(next); setItems(next)
    setF({ date: nowLocal(), field: f.field, product: '', ai: '', dose: '', area: '', note: '' })
  }

  function csv() {
    const head = 'date,field,product,active_ingredient,dose,area_ha,temp_c,rh_pct,wind_ms,precip_mm,note'
    const rows = items.map((s) => [s.date.replace('T', ' '), s.field, s.product, s.ai, s.dose, s.area,
      s.wx?.temperature_2m ?? '', s.wx?.relative_humidity_2m ?? '', s.wx?.wind_speed_10m ?? '', s.wx?.precipitation ?? '', s.note]
      .map(String).map(cell).join(','))
    H.download(`eginai-spray-${new Date().toISOString().slice(0, 10)}.csv`, '﻿' + [head, ...rows].join('\n'), 'text/csv;charset=utf-8')
  }

  const warn = f.wx ? wxWarnings(f.wx, t) : []
  return (
    <section className="spray">
      <h2>{t.spTitle}</h2>
      <p className="muted">{t.spText}</p>
      <form className="panel no-print" onSubmit={add}>
        <label className="field"><span>{t.spDate}</span><input type="datetime-local" required value={f.date} onChange={set('date')} /></label>
        <label className="field"><span>{t.hField}</span><input list="fields" maxLength={60} value={f.field} onChange={set('field')} placeholder={t.fieldPh} /></label>
        <label className="field"><span>{t.spProduct}</span><input required maxLength={80} value={f.product} onChange={set('product')} /></label>
        <label className="field"><span>{t.spAi}</span><input maxLength={80} value={f.ai} onChange={set('ai')} placeholder={t.spAiPh} /></label>
        <div className="row">
          <label className="field grow"><span>{t.spDose}</span><input maxLength={40} value={f.dose} onChange={set('dose')} placeholder={t.spDosePh} /></label>
          <label className="field grow"><span>{t.spArea}</span><input inputMode="decimal" maxLength={10} value={f.area} onChange={set('area')} /></label>
        </div>
        <label className="field"><span>{t.spNote}</span><input maxLength={200} value={f.note} onChange={set('note')} /></label>
        <div className="row">
          <button type="button" className="btn-secondary" disabled={wxState === 'busy'} onClick={getWx}>{t.spWx}</button>
          <button className="btn-primary">{t.spAdd}</button>
        </div>
        {wxState === 'err' && <p className="notice error" role="alert">{t.wxDown}</p>}
        {f.wx && (
          <p className={`notice ${warn.length ? 'warn' : 'ok'}`} role="status">
            {f.wx.temperature_2m} °C · {f.wx.relative_humidity_2m} % · {f.wx.wind_speed_10m} м/с · {f.wx.precipitation} мм
            {warn.map((w) => <span key={w}><br />{w}</span>)}
          </p>
        )}
      </form>
      {items.length > 0 && (
        <>
          <ul className="hist">
            {items.map((s) => (
              <li key={s.id}>
                <span className="body">
                  <b>{s.product}</b>{s.ai && ` (${s.ai})`}{s.dose && ` · ${s.dose}`}
                  <br />
                  <small className="muted">{s.date.replace('T', ' ')}{s.field && ` · ${s.field}`}{s.area && ` · ${s.area} га`}
                    {s.wx && ` · ${s.wx.temperature_2m} °C, ${s.wx.wind_speed_10m} м/с`}</small>
                </span>
                <button className="icon no-print" aria-label={t.hDelete}
                  onClick={() => { const n = items.filter((x) => x.id !== s.id); saveSprays(n); setItems(n) }}>×</button>
              </li>
            ))}
          </ul>
          <button className="btn-secondary no-print" onClick={csv}>CSV (Excel)</button>
        </>
      )}
    </section>
  )
}
