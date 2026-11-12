import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { api, DISEASE_COLOR, type DiseaseClass, type Feature } from './api'
import type { Lang, Texts } from './i18n'

const PERIODS = [7, 30, 90]

export default function MapView({ lang, t }: { lang: Lang; t: Texts }) {
  const [days, setDays] = useState(30)
  const [filter, setFilter] = useState<string>('')
  const [feats, setFeats] = useState<Feature[] | null>(null)
  const [classes, setClasses] = useState<DiseaseClass[]>([])
  const [down, setDown] = useState(false)

  useEffect(() => { api.classes(lang).then(setClasses).catch(() => {}) }, [lang])
  useEffect(() => {
    setDown(false)
    api.map(days, lang).then((r) => setFeats(r.features)).catch(() => { setDown(true); setFeats([]) })
  }, [days, lang])

  const shown = useMemo(() => (feats ?? []).filter((f) => !filter || f.properties.disease === filter), [feats, filter])
  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const f of feats ?? []) c[f.properties.disease] = (c[f.properties.disease] ?? 0) + 1
    return c
  }, [feats])

  return (
    <section className="mapview">
      <h1>{t.mapPageTitle}</h1>
      <p className="muted">{t.mapPageText}</p>

      <div className="filters">
        <label>{t.period}
          <select value={days} onChange={(e) => setDays(+e.target.value)}>
            {PERIODS.map((d) => <option key={d} value={d}>{t.days(d)}</option>)}
          </select>
        </label>
        <div className="chips" role="group">
          <button aria-pressed={!filter} onClick={() => setFilter('')}>{t.all} {feats?.length ?? 0}</button>
          {classes.filter((c) => counts[c.id]).map((c) => (
            <button key={c.id} aria-pressed={filter === c.id} onClick={() => setFilter(c.id)}>
              <i style={{ background: DISEASE_COLOR[c.id] }} aria-hidden />{c.name} {counts[c.id]}
            </button>
          ))}
        </div>
      </div>

      {down && <p className="notice error" role="alert">{t.mapDown}</p>}
      {!down && feats && feats.length === 0 && <p className="notice">{t.mapEmpty}</p>}

      <div className="map">
        <MapContainer center={[51.2, 69.5]} zoom={5} scrollWheelZoom style={{ height: '100%' }}>
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {shown.map((f, i) => (
            <CircleMarker key={i} center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]} radius={8}
              pathOptions={{ color: '#1B2A1F', weight: 1, fillColor: DISEASE_COLOR[f.properties.disease] ?? '#888', fillOpacity: 0.9 }}>
              <Popup><b>{f.properties.name}</b><br />{f.properties.date} · {Math.round(f.properties.confidence * 100)}%</Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </section>
  )
}
