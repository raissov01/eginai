// Таза функциялар (компоненттерсіз): экономика, бүрку журналын сақтау, ауа райы ескертулері.
import type { Texts } from './i18n'

// Өңдеу ақталады ма: шығын = өнім (т/га) × баға × шығын %, салыстыру — өңдеу құны.
// Шығын пайызын фермер агрономмен өзі бағалайды (дерексіз сан ойлап таппаймыз).
export function economics(yieldCph: number, priceT: number, costHa: number, lossPct: number) {
  const revenue = (yieldCph / 10) * priceT
  const loss = Math.round(revenue * lossPct / 100)
  const breakEven = revenue > 0 ? Math.round((costHa / revenue) * 1000) / 10 : null
  return { loss, worth: loss > costHa, breakEven }
}

export type Spray = {
  id: string; date: string; field: string; product: string; ai: string; dose: string; area: string; note: string
  wx?: { temperature_2m: number; relative_humidity_2m: number; wind_speed_10m: number; precipitation: number }
}
const KEY = 'eginai.spray.v1'

export function loadSprays(): Spray[] {
  try { const v = JSON.parse(localStorage.getItem(KEY) || '[]'); return Array.isArray(v) ? v : [] } catch { return [] }
}
export function saveSprays(v: Spray[]) { try { localStorage.setItem(KEY, JSON.stringify(v.slice(0, 500))) } catch { /* жеке режим */ } }

// Бүрку ережелері weather.py-дағымен бірдей: жел 1–4,5 м/с, 8–25 °C, жаңбырсыз
export function wxWarnings(w: NonNullable<Spray['wx']>, t: Texts): string[] {
  const out = []
  if (w.wind_speed_10m > 4.5) out.push(t.spWindHigh)
  if (w.wind_speed_10m < 1) out.push(t.spWindLow)
  if (w.temperature_2m < 8 || w.temperature_2m > 25) out.push(t.spTemp)
  if (w.precipitation >= 0.1) out.push(t.spRain)
  return out
}

