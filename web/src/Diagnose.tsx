import { useEffect, useRef, useState } from 'react'
import { api, ApiError, shrink, type Prediction } from './api'
import { Feedback, Share, SymptomKey, ThresholdCalc, WeatherPanel } from './Extras'
import * as H from './history'
import type { Lang, Texts } from './i18n'

type Props = { lang: Lang; t: Texts }
type State =
  | { kind: 'idle' }
  | { kind: 'loading'; preview: string }
  | { kind: 'done'; preview: string; res: Prediction; files: Blob[] }
  | { kind: 'error'; preview?: string; message: string; files?: Blob[] }

export default function Diagnose({ lang, t }: Props) {
  const [st, setSt] = useState<State>({ kind: 'idle' })
  const camRef = useRef<HTMLInputElement>(null)
  const galRef = useRef<HTMLInputElement>(null)

  async function run(files: Blob[], preview: string) {
    setSt({ kind: 'loading', preview })
    try {
      const res = await api.predict(files, lang)
      setSt({ kind: 'done', preview, res, files })
    } catch (e) {
      // Желі жоқ (ApiError емес) және модель жүктелген болса — құрылғының өзінде талдаймыз
      if (!(e instanceof ApiError)) {
        try {
          const off = await import('./offline')
          if (await off.isReady()) {
            setSt({ kind: 'done', preview, res: await off.predictOffline(files, lang), files })
            return
          }
        } catch { /* төмендегі желі қатесін көрсетеміз */ }
      }
      const message = e instanceof ApiError && e.message ? e.message : t.netError
      setSt({ kind: 'error', preview, message, files })
    }
  }

  // Бірінші фото — жаңа талдау; нәтиже бетінде «тағы фото қосу» — сол өсімдіктің 2–3-фотосы
  const adding = useRef(false)
  async function onFile(f?: File) {
    if (!f) return
    const small = await shrink(f)
    if (adding.current && st.kind === 'done') run([...st.files, small].slice(0, 3), st.preview)
    else run([small], URL.createObjectURL(small))
    adding.current = false
  }

  // Тіл ауысқанда нәтижені сол тілде қайта сұраймыз (кеңес мәтіні өзгереді)
  const lastLang = useRef(lang)
  useEffect(() => {
    if (lastLang.current !== lang && st.kind === 'done') run(st.files, st.preview)
    lastLang.current = lang
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang])

  const reset = () => setSt({ kind: 'idle' })
  const inputs = (
    <>
      <input ref={camRef} type="file" accept="image/*" capture="environment" hidden
        onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = '' }} />
      <input ref={galRef} type="file" accept="image/*" hidden
        onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = '' }} />
    </>
  )

  if (st.kind === 'idle') {
    return (
      <section className="hero">
        {inputs}
        <h1>{t.heroTitle}</h1>
        <p className="lead">{t.heroText}</p>
        <button className="btn-primary big" onClick={() => camRef.current?.click()}>
          <CameraIcon /> {t.takePhoto}
        </button>
        <button className="btn-secondary" onClick={() => galRef.current?.click()}>{t.pickFile}</button>
        <div className="tips">
          <h2>{t.tipsTitle}</h2>
          <ul>{t.tips.map((x) => <li key={x}>{x}</li>)}</ul>
        </div>
        <SymptomKey lang={lang} t={t} />
        <OfflineMode t={t} />
      </section>
    )
  }

  if (st.kind === 'loading') {
    return (
      <section>
        <figure className="photo"><img src={st.preview} alt="" /><div className="scanline" aria-hidden /></figure>
        <p className="status" role="status">{t.analyzing}</p>
      </section>
    )
  }

  if (st.kind === 'error') {
    return (
      <section>
        {inputs}
        {st.preview && <figure className="photo"><img src={st.preview} alt="" /></figure>}
        <div className="notice error" role="alert">{st.message}</div>
        <div className="row">
          {st.files && <button className="btn-primary" onClick={() => run(st.files!, st.preview!)}>{t.retry}</button>}
          <button className="btn-secondary" onClick={reset}>{t.newPhoto}</button>
        </div>
      </section>
    )
  }

  const addMore = st.files.length < 3
    ? () => { adding.current = true; camRef.current?.click() }
    : undefined
  return (
    <>
      {inputs}
      <Result lang={lang} t={t} preview={st.preview} res={st.res} onNew={reset} onAdd={addMore} nFiles={st.files.length} />
    </>
  )
}

function Result({ lang, t, preview, res, onNew, onAdd, nFiles }: {
  lang: Lang; t: Texts; preview: string; res: Prediction; onNew: () => void; onAdd?: () => void; nFiles: number
}) {
  const [classes, setClasses] = useState<{ id: string; name: string }[]>([])
  useEffect(() => { api.classes(lang).then(setClasses).catch(() => {}) }, [lang])
  const [showCam, setShowCam] = useState(true)
  const top = res.top[0]
  const a = res.advice
  const pct = Math.round(top.prob * 100)

  return (
    <section className="result">
      <figure className="photo">
        <img src={showCam && res.cam ? res.cam : preview} alt={a ? a.title : ''} />
        {res.cam && (
          <div className="seg" role="group">
            <button aria-pressed={!showCam} onClick={() => setShowCam(false)}>{t.original}</button>
            <button aria-pressed={showCam} onClick={() => setShowCam(true)}>{t.symptoms}</button>
          </div>
        )}
      </figure>

      {res.unsure && (
        <div className="notice warn" role="alert">
          <strong>{t.unsureTitle}</strong>
          <p>{res.reason === 'not_plant' ? t.unsureNotPlant : t.unsureLow}</p>
        </div>
      )}

      {res.offline && <p className="notice" role="status">{t.offBadge}</p>}
      {res.n_images > 1 && <p className="fine">{t.photosUsed(res.n_used, res.n_images)}</p>}
      {res.reason !== 'not_plant' && <FieldTag t={t} res={res} preview={preview} />}
      {onAdd && res.reason !== 'not_plant' && (
        <div className="addphoto">
          <button className="btn-secondary" onClick={onAdd}>{t.addPhoto(nFiles + 1)}</button>
          <p className="fine">{t.addPhotoHint}</p>
        </div>
      )}
      {res.unsure && <SymptomKey lang={lang} t={t} />}

      {a && (
        <header className={`diag sev-${a.severity}`}>
          <span className="sev">{t.severity[a.severity]}</span>
          <h1>{a.title}</h1>
          <p className="latin">{a.pathogen !== '—' ? a.pathogen : ''}</p>
          <div className="meter" aria-label={`${t.confidence}: ${pct}%`}>
            <div className="meter-bar"><span style={{ width: `${pct}%` }} /></div>
            <span>{t.confidence} {pct}%</span>
          </div>
          {res.affected_pct != null && a.severity !== 'none' && (
            <p className="affected"><b>{Math.round(res.affected_pct)}%</b> {t.affected}</p>
          )}
        </header>
      )}

      {res.top.length > 1 && res.reason !== 'not_plant' && (
        <div className="alts">
          <h2>{t.alternatives}</h2>
          <ul>
            {res.top.slice(1).map((x) => (
              <li key={x.id}><span>{x.name}</span><span>{Math.round(x.prob * 100)}%</span></li>
            ))}
          </ul>
        </div>
      )}

      {a && (
        <div className="advice">
          <details open={a.severity !== 'none'}>
            <summary>{t.sec.actions}</summary>
            <h3>{t.agro}</h3><p>{a.actions.agro}</p>
            {a.severity !== 'none' && <><h3>{t.chemical}</h3><p>{a.actions.chemical}</p></>}
            <p className="fine">{t.disclaimer}</p>
          </details>
          <Sec title={t.sec.symptoms} text={a.symptoms} open />
          <Sec title={t.sec.timing} text={a.timing} />
          <Sec title={t.sec.threshold} text={a.threshold} />
          {a.threshold_pct && <ThresholdCalc t={t} range={a.threshold_pct} />}
          <Sec title={t.sec.conditions} text={a.conditions} />
          <Sec title={t.sec.prevention} text={a.prevention} />
          <Sec title={t.sec.similar} text={a.similar} />
          <details>
            <summary>{t.sec.sources}</summary>
            <ul className="sources">{a.sources.map((s) => <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a></li>)}</ul>
          </details>
        </div>
      )}

      {a && <Share t={t} name={top.name} prob={top.prob} preview={preview} />}
      {a && a.severity !== 'none' && <WeatherPanel lang={lang} t={t} focus={top.id} />}
      {a && !res.unsure && <Feedback t={t} predicted={top.id} confidence={top.prob} options={classes} />}
      {a && !res.unsure && <MapConsent t={t} disease={top.id} confidence={top.prob} />}
      {a && <Ask lang={lang} t={t} classId={top.id} />}

      <button className="btn-secondary wide" onClick={onNew}>{t.newPhoto}</button>
    </section>
  )
}

function OfflineMode({ t }: { t: Texts }) {
  const [st, setSt] = useState<'unknown' | 'none' | 'ready' | 'err' | number>('unknown')
  useEffect(() => {
    if (!('caches' in window)) return
    import('./offline').then((m) => m.isReady()).then((ok) => setSt(ok ? 'ready' : 'none')).catch(() => setSt('none'))
  }, [])
  if (st === 'unknown') return null
  async function get() {
    setSt(0)
    try { const m = await import('./offline'); await m.download((p) => setSt(Math.round(p * 100))); setSt('ready') } catch { setSt('err') }
  }
  async function del() { const m = await import('./offline'); await m.remove(); setSt('none') }
  return (
    <div className="panel offline">
      <h2>{t.offTitle}</h2>
      {st === 'ready' ? (
        <div className="row"><p className="grow">{t.offReady}</p><button className="btn-link" onClick={del}>{t.offRemove}</button></div>
      ) : typeof st === 'number' ? <p role="status">{t.offBusy(st)}</p> : (
        <>
          <p className="muted">{t.offText}</p>
          <button className="btn-secondary" onClick={get}>{t.offGet}</button>
          {st === 'err' && <p className="notice error" role="alert">{t.offErr}</p>}
        </>
      )}
    </div>
  )
}

// Әр диагноз тарихқа автоматты жазылады (тек браузерде); алқап атауын қосуға болады
function FieldTag({ t, res, preview }: { t: Texts; res: Prediction; preview: string }) {
  const [id, setId] = useState<string | null>(null)
  const [field, setField] = useState(() => H.load()[0]?.field ?? '')
  const [saved, setSaved] = useState(false)
  const done = useRef<Prediction | null>(null)
  useEffect(() => {
    if (done.current === res) return   // бір нәтиже — бір жазба (StrictMode/қайта рендер)
    done.current = res
    const top = res.top[0]
    H.thumb(preview).then((th) => {
      const e = H.add({ field, disease: top.id, name: top.name, prob: top.prob, unsure: res.unsure, thumb: th })
      setId(e.id)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [res])
  return (
    <form className="fieldtag" onSubmit={(e) => { e.preventDefault(); if (id) { H.update(id, { field: field.trim() }); setSaved(true) } }}>
      <label className="field">
        <span>{t.fieldLabel}</span>
        <span className="ask-row">
          <input value={field} maxLength={60} placeholder={t.fieldPh} list="fields"
            onChange={(e) => { setField(e.target.value); setSaved(false) }} />
          <button className="btn-secondary" disabled={!id}>{t.fieldSave}</button>
        </span>
      </label>
      <datalist id="fields">{H.fields().map((f) => <option key={f} value={f} />)}</datalist>
      {saved && <p className="fine" role="status">{t.fieldSaved}</p>}
    </form>
  )
}

function Sec({ title, text, open }: { title: string; text: string; open?: boolean }) {
  if (!text || text === '—') return null
  return <details open={open}><summary>{title}</summary><p>{text}</p></details>
}

function MapConsent({ t, disease, confidence }: { t: Texts; disease: string; confidence: number }) {
  const [ok, setOk] = useState(false)
  const [state, setState] = useState<'idle' | 'busy' | 'done' | 'geo' | 'err'>('idle')

  function submit() {
    if (!navigator.geolocation) return setState('geo')
    setState('busy')
    navigator.geolocation.getCurrentPosition(
      async (p) => {
        try {
          await api.addCase({ disease, confidence, lat: p.coords.latitude, lon: p.coords.longitude })
          setState('done')
        } catch { setState('err') }
      },
      () => setState('geo'),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    )
  }

  return (
    <div className="panel">
      <h2>{t.mapTitle}</h2>
      <p className="muted">{t.mapText}</p>
      {state === 'done' ? <p className="notice ok" role="status">{t.added}</p> : (
        <>
          <label className="check">
            <input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} />
            <span>{t.consent}</span>
          </label>
          <button className="btn-primary" disabled={!ok || state === 'busy'} onClick={submit}>{t.addToMap}</button>
          {state === 'geo' && <p className="notice error" role="alert">{t.geoDenied}</p>}
          {state === 'err' && <p className="notice error" role="alert">{t.mapDown}</p>}
        </>
      )}
    </div>
  )
}

function Ask({ lang, t, classId }: { lang: Lang; t: Texts; classId: string }) {
  const [q, setQ] = useState('')
  const [ans, setAns] = useState<{ answer: string; generated_by: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function go(e: React.FormEvent) {
    e.preventDefault()
    if (q.trim().length < 2) return
    setBusy(true); setError('')
    try { setAns(await api.ask(q.trim(), lang, classId)) } catch { setError(t.netError) } finally { setBusy(false) }
  }

  return (
    <form className="panel" onSubmit={go}>
      <h2><label htmlFor="ask">{t.askTitle}</label></h2>
      <div className="ask-row">
        <input id="ask" value={q} maxLength={500} placeholder={t.askPlaceholder} onChange={(e) => setQ(e.target.value)} />
        <button className="btn-primary" disabled={busy || q.trim().length < 2}>{t.askBtn}</button>
      </div>
      {error && <p className="notice error" role="alert">{error}</p>}
      {ans && (
        <div className="answer" aria-live="polite">
          {ans.answer.split('\n').map((l, i) => <p key={i}>{l}</p>)}
          <p className="fine">{ans.generated_by === 'llm' ? t.askFromLlm : t.askFromKb}</p>
        </div>
      )}
    </form>
  )
}

function CameraIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" />
    </svg>
  )
}
