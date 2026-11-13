import { useRef, useState } from 'react'
import * as H from './history'
import SprayLog from './Spray'
import type { Lang, Texts } from './i18n'

export default function History({ lang, t }: { lang: Lang; t: Texts }) {
  const [items, setItems] = useState(H.load)
  const [field, setField] = useState('')
  const [msg, setMsg] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const shown = field ? items.filter((e) => e.field === field) : items
  const refresh = () => setItems(H.load())
  const stamp = new Date().toISOString().slice(0, 10)

  async function onImport(f?: File) {
    if (!f) return
    try { setMsg(t.hImported(H.importJson(await f.text()))); refresh() } catch { setMsg(t.hBadFile) }
  }

  return (
    <section className="history">
      <h1>{t.hTitle}</h1>
      <p className="muted">{t.hText}</p>

      {items.length > 0 && (
        <div className="row no-print">
          <label className="field grow">
            <span>{t.hField}</span>
            <select value={field} onChange={(e) => setField(e.target.value)}>
              <option value="">{t.all} ({items.length})</option>
              {H.fields(items).map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>
        </div>
      )}

      {shown.length === 0 ? <p className="notice">{t.hEmpty}</p> : (
        <ul className="hist">
          {shown.map((e) => (
            <li key={e.id}>
              {e.thumb ? <img src={e.thumb} alt="" /> : <span className="ph" aria-hidden />}
              <span className="body">
                <b>{e.name}</b>{e.unsure && <span className="muted"> · {t.hUnsure}</span>}
                <br />
                <small className="muted">
                  {new Date(e.date).toLocaleString(lang === 'kk' ? 'kk-KZ' : 'ru-RU', { dateStyle: 'short', timeStyle: 'short' })}
                  {e.field && ` · ${e.field}`} · {Math.round(e.prob * 100)}%
                </small>
              </span>
              <button className="icon no-print" aria-label={t.hDelete} onClick={() => { H.remove(e.id); refresh() }}>×</button>
            </li>
          ))}
        </ul>
      )}

      <div className="row no-print">
        <button className="btn-secondary" disabled={!shown.length}
          onClick={() => H.download(`eginai-${field || 'all'}-${stamp}.csv`, H.toCsv(shown), 'text/csv;charset=utf-8')}>CSV (Excel)</button>
        <button className="btn-secondary" disabled={!shown.length} onClick={() => window.print()}>{t.hPrint}</button>
        <button className="btn-secondary" disabled={!items.length}
          onClick={() => H.download(`eginai-backup-${stamp}.json`, JSON.stringify({ version: 1, items }, null, 1), 'application/json')}>{t.hBackup}</button>
        <button className="btn-secondary" onClick={() => fileRef.current?.click()}>{t.hRestore}</button>
        <input ref={fileRef} type="file" accept="application/json,.json" hidden
          onChange={(e) => { onImport(e.target.files?.[0]); e.target.value = '' }} />
      </div>
      {msg && <p className="notice ok no-print" role="status">{msg}</p>}
      {items.length > 0 && (
        <button className="btn-link no-print" onClick={() => { if (confirm(t.hClearAsk)) { H.clear(); refresh() } }}>{t.hClear}</button>
      )}
      <datalist id="fields">{H.fields(items).map((f) => <option key={f} value={f} />)}</datalist>
      <SprayLog t={t} lang={lang} />
      <p className="fine">{t.hPrivacy}</p>
    </section>
  )
}
