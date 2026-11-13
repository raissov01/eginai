// Диагноз тарихы — тек осы браузерде (localStorage). Тіркелусіз, бұлтқа байланбаған:
// фермер CSV/JSON етіп кез келген уақытта алып кете алады, JSON-нан қайта жүктей алады.
export type Entry = {
  id: string; date: string; field: string
  disease: string; name: string; prob: number; unsure: boolean; thumb?: string
}

const KEY = 'eginai.history.v1'
const MAX = 300

export function load(): Entry[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(v) ? v.filter(valid) : []
  } catch { return [] }
}

function save(items: Entry[]) {
  try { localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX))) } catch {
    // Квота толса — суреттерсіз сақтаймыз
    try { localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX).map((e) => ({ ...e, thumb: undefined })))) } catch { /* жеке режим */ }
  }
}

function valid(e: unknown): e is Entry {
  const x = e as Entry
  return !!x && typeof x.id === 'string' && typeof x.date === 'string' && typeof x.disease === 'string'
    && typeof x.name === 'string' && typeof x.prob === 'number' && typeof x.field === 'string'
}

export function add(e: Omit<Entry, 'id' | 'date'>): Entry {
  const entry = { ...e, id: crypto.randomUUID?.() ?? String(Date.now()), date: new Date().toISOString() }
  save([entry, ...load()])
  return entry
}

export function update(id: string, patch: Partial<Entry>) {
  save(load().map((e) => (e.id === id ? { ...e, ...patch } : e)))
}

export function remove(id: string) { save(load().filter((e) => e.id !== id)) }
export function clear() { save([]) }

export function fields(items = load()): string[] {
  return [...new Set(items.map((e) => e.field).filter(Boolean))].sort()
}

const cell = (v: string) => {
  const s = /^[=+\-@\t\r]/.test(v) ? `'${v}` : v          // Excel формула инъекциясынан қорғаныс
  return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

const pad = (n: number) => String(n).padStart(2, '0')
const localStamp = (iso: string) => {
  const d = new Date(iso)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function toCsv(items: Entry[]): string {
  const rows = items.map((e) => [localStamp(e.date), e.field, e.disease, e.name,
    Math.round(e.prob * 100) + '%', e.unsure ? 'unsure' : ''].map(String).map(cell).join(','))
  return '﻿' + ['date,field,disease_id,disease,confidence,flag', ...rows].join('\n')
}

export function importJson(text: string): number {
  const v = JSON.parse(text)
  const incoming = (Array.isArray(v) ? v : v?.items ?? []).filter(valid) as Entry[]
  const have = new Set(load().map((e) => e.id))
  const merged = [...incoming.filter((e) => !have.has(e.id)), ...load()]
    .sort((a, b) => b.date.localeCompare(a.date))
  save(merged)
  return incoming.filter((e) => !have.has(e.id)).length
}

export function download(name: string, data: string, type: string) {
  const url = URL.createObjectURL(new Blob([data], { type }))
  const a = Object.assign(document.createElement('a'), { href: url, download: name })
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// Тарих үшін кішкене сурет (≈ 5 КБ)
export async function thumb(src: string, size = 96): Promise<string | undefined> {
  try {
    const img = new Image()
    img.src = src
    await img.decode()
    const k = size / Math.max(img.width, img.height)
    const c = document.createElement('canvas')
    c.width = Math.round(img.width * k); c.height = Math.round(img.height * k)
    c.getContext('2d')!.drawImage(img, 0, 0, c.width, c.height)
    return c.toDataURL('image/jpeg', 0.7)
  } catch { return undefined }
}
