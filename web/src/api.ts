// Backend API клиенті. Барлық сұраныстар бір доменде (/api).
import type { Lang } from './i18n'

export type Advice = {
  title: string; pathogen: string; severity: 'high' | 'medium' | 'none'
  symptoms: string; conditions: string; threshold: string
  actions: { agro: string; chemical: string }
  timing: string; prevention: string; similar: string
  sources: { title: string; url: string }[]
}
export type Prediction = {
  top: { id: string; name: string; prob: number }[]
  unsure: boolean
  reason: 'not_plant' | 'low_confidence' | null
  cam: string | null
  affected_pct: number | null
  advice: Advice | null
  ms: number
}
export type Feature = {
  geometry: { coordinates: [number, number] }
  properties: { disease: string; name: string; confidence: number; date: string }
}
export type DiseaseClass = { id: string; name: string; severity: string }

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    let msg = ''
    try { msg = (await r.json()).detail?.message ?? '' } catch { /* JSON емес жауап */ }
    throw new ApiError(r.status, msg)
  }
  return r.status === 204 ? (undefined as T) : r.json()
}

export const api = {
  predict(file: Blob, lang: Lang) {
    const fd = new FormData()
    fd.append('file', file, 'photo.jpg')
    return call<Prediction>(`/api/predict?lang=${lang}`, { method: 'POST', body: fd })
  },
  ask(question: string, lang: Lang, classId?: string) {
    return call<{ answer: string; generated_by: 'kb' | 'llm' }>('/api/ask', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, lang, class_id: classId }),
    })
  },
  addCase(body: { disease: string; confidence: number; lat: number; lon: number }) {
    return call<{ id: number }>('/api/cases', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...body, consent: true, source: 'web' }),
    })
  },
  map(days: number, lang: Lang) {
    return call<{ features: Feature[] }>(`/api/map?days=${days}&lang=${lang}`)
  },
  classes(lang: Lang) { return call<DiseaseClass[]>(`/api/classes?lang=${lang}`) },
}

// Телефон фотолары 5–12 МБ болады: жіберер алдында 1600 px-ке дейін кішірейтеміз
export async function shrink(file: File, max = 1600): Promise<Blob> {
  try {
    const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' })
    const k = Math.min(1, max / Math.max(bmp.width, bmp.height))
    const c = document.createElement('canvas')
    c.width = Math.round(bmp.width * k)
    c.height = Math.round(bmp.height * k)
    c.getContext('2d')!.drawImage(bmp, 0, 0, c.width, c.height)
    return await new Promise((res) => c.toBlob((b) => res(b ?? file), 'image/jpeg', 0.9))
  } catch {
    return file // декодтай алмасақ — серверге түпнұсқасын жібереміз, ол түсінікті қате береді
  }
}

// Ауру → картадағы түс (тұтас түстер, градиентсіз)
export const DISEASE_COLOR: Record<string, string> = {
  leaf_rust: '#B5471B', stripe_rust: '#D99A00', powdery_mildew: '#6E7B8B',
  fusarium_head_blight: '#C2417A', glume_blotch: '#7A4E2D',
  healthy_leaf: '#2F6B3A', healthy_ear: '#5E8C3A',
}
