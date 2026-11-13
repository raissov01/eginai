// Интернетсіз режим: сол ONNX модель браузерде (onnxruntime-web, WASM) іске қосылады.
// Логика backend/app/inference.py-мен бірдей: 224 px, ImageNet нормализациясы, softmax,
// «өсімдік емес» сүзгісі (HSV үлесі + текстура), бірнеше фото орташасы, CAM.
// Модель мен кеңестер бумасы Cache Storage-та сақталады; жүктеуді пайдаланушы өзі бастайды.
import type { Advice, KeyGroup, Prediction } from './api'
import type { Lang } from './i18n'

const CACHE = 'eginai-offline-v1'
const MODEL_URL = '/api/offline/model.onnx'
const BUNDLE_URL = '/api/offline/bundle'
const WASM = ['/ort/ort-wasm-simd-threaded.wasm', '/ort/ort-wasm-simd-threaded.mjs']
const MEAN = [0.485, 0.456, 0.406]
const STD = [0.229, 0.224, 0.225]
const SIZE = 224

export type Bundle = {
  version: string; labels: string[]; classifier_w: number[][]
  thresholds: { min_conf: number; min_plant: number; min_texture: number }
  names: Record<Lang, Record<string, string>>
  advice: Record<Lang, Record<string, Advice>>
  key: Record<Lang, KeyGroup[]>
}

async function cached(url: string): Promise<Response | undefined> {
  try { return await (await caches.open(CACHE)).match(url) } catch { return undefined }
}

export async function isReady(): Promise<boolean> {
  if (!('caches' in window)) return false
  const all = await Promise.all([MODEL_URL, BUNDLE_URL, ...WASM].map(cached))
  return all.every(Boolean)
}

// Бір рет жүктеу (~27 МБ: модель 16 + WASM 11). progress: 0..1
export async function download(progress?: (p: number) => void): Promise<void> {
  const c = await caches.open(CACHE)
  const urls = [BUNDLE_URL, ...WASM, MODEL_URL]
  for (let i = 0; i < urls.length; i++) {
    const r = await fetch(urls[i], { cache: 'reload' })
    if (!r.ok) throw new Error(`${urls[i]}: ${r.status}`)
    await c.put(urls[i], r)
    progress?.((i + 1) / urls.length)
  }
  session = null
  bundle = null
}

export async function remove(): Promise<void> { await caches.delete(CACHE); session = null; bundle = null }

let bundle: Bundle | null = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let session: any = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let ort: any = null

export async function getBundle(): Promise<Bundle | null> {
  if (bundle) return bundle
  const r = await cached(BUNDLE_URL)
  bundle = r ? await r.json() : null
  return bundle
}

async function getSession() {
  if (session) return session
  const r = await cached(MODEL_URL)
  if (!r) throw new Error('offline model not downloaded')
  ort = ort ?? await import('onnxruntime-web/wasm')
  ort.env.wasm.wasmPaths = '/ort/'
  ort.env.wasm.numThreads = 1          // SharedArrayBuffer-сіз (COOP/COEP жоқ) жұмыс істеу үшін
  session = await ort.InferenceSession.create(new Uint8Array(await r.arrayBuffer()), { executionProviders: ['wasm'] })
  return session
}

function canvasOf(w: number, h: number) {
  const c = document.createElement('canvas'); c.width = w; c.height = h
  return c
}

function draw(src: CanvasImageSource, w: number, h: number): ImageData {
  const c = canvasOf(w, h)
  const g = c.getContext('2d', { willReadFrequently: true })!
  g.imageSmoothingQuality = 'high'
  g.drawImage(src, 0, 0, w, h)
  return g.getImageData(0, 0, w, h)
}

// inference.py: plant_fraction (HSV, PIL шкаласы) және texture (сұр түстің std, 96×96)
function plantAndTexture(img: CanvasImageSource): { pf: number; tex: number } {
  const d = draw(img, 96, 96).data
  let plant = 0, sum = 0, sum2 = 0
  const n = 96 * 96
  for (let i = 0; i < d.length; i += 4) {
    const r = d[i] / 255, g = d[i + 1] / 255, b = d[i + 2] / 255
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), df = mx - mn
    let h = 0
    if (df > 0) h = mx === r ? ((g - b) / df) % 6 : mx === g ? (b - r) / df + 2 : (r - g) / df + 4
    const hue = ((h * 60) + 360) % 360
    const sat = mx > 0 ? df / mx : 0
    if (sat > 0.12 && mx > 0.12 && hue >= 20 && hue <= 170) plant++
    const L = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000
    sum += L; sum2 += L * L
  }
  const mean = sum / n
  return { pf: plant / n, tex: Math.sqrt(Math.max(0, sum2 / n - mean * mean)) }
}

function tensorOf(img: CanvasImageSource): Float32Array {
  const d = draw(img, SIZE, SIZE).data
  const x = new Float32Array(3 * SIZE * SIZE)
  for (let p = 0, i = 0; p < SIZE * SIZE; p++, i += 4)
    for (let c = 0; c < 3; c++) x[c * SIZE * SIZE + p] = (d[i + c] / 255 - MEAN[c]) / STD[c]
  return x
}

type Run = { p: number[]; feats: Float32Array; bmp: ImageBitmap; pf: number; flat: boolean }

async function infer(blob: Blob, b: Bundle): Promise<Run> {
  const bmp = await createImageBitmap(blob, { imageOrientation: 'from-image' })
  const s = await getSession()
  const out = await s.run({ image: new ort.Tensor('float32', tensorOf(bmp), [1, 3, SIZE, SIZE]) })
  const logits = Array.from(out.logits.data as Float32Array)
  const mx = Math.max(...logits)
  const e = logits.map((v) => Math.exp(v - mx))
  const z = e.reduce((a, v) => a + v, 0)
  const { pf, tex } = plantAndTexture(bmp)
  return { p: e.map((v) => v / z), feats: out.features.data as Float32Array, bmp, pf, flat: tex < b.thresholds.min_texture }
}

// CAM = ReLU(Σ_k W[c,k]·F_k), 7×7 → суретке қабаттау (inference.py `_cam`)
function cam(run: Run, w: number[], maxSide = 512): { url: string; affected: number } {
  const hw = 49
  const m = new Float32Array(hw)
  for (let k = 0; k < w.length; k++) for (let j = 0; j < hw; j++) m[j] += w[k] * run.feats[k * hw + j]
  let top = 0
  for (let j = 0; j < hw; j++) { m[j] = Math.max(0, m[j]); top = Math.max(top, m[j]) }
  const k = Math.min(1, maxSide / Math.max(run.bmp.width, run.bmp.height))
  const W = Math.round(run.bmp.width * k), H = Math.round(run.bmp.height * k)
  const small = canvasOf(7, 7), sg = small.getContext('2d')!
  const hm = sg.createImageData(7, 7)
  for (let j = 0; j < hw; j++) { const v = top > 0 ? (m[j] / top) * 255 : 0; hm.data.set([v, v, v, 255], j * 4) }
  sg.putImageData(hm, 0, 0)
  const heat = draw(small, W, H).data
  const base = draw(run.bmp, W, H)
  let hot = 0
  for (let i = 0; i < base.data.length; i += 4) {
    const h = heat[i] / 255
    if (h > 0.5) hot++
    const a = Math.min(1, Math.max(0, (h - 0.25) / 0.75)) * 0.6
    base.data[i] = base.data[i] * (1 - a) + 255 * a
    base.data[i + 1] = base.data[i + 1] * (1 - a) + 120 * a
    base.data[i + 2] = base.data[i + 2] * (1 - a)
  }
  const c = canvasOf(W, H)
  c.getContext('2d')!.putImageData(base, 0, 0)
  return { url: c.toDataURL('image/jpeg', 0.82), affected: Math.round((hot / (W * H)) * 1000) / 10 }
}

export async function predictOffline(blobs: Blob[], lang: Lang): Promise<Prediction & { offline: true }> {
  const t0 = performance.now()
  const b = await getBundle()
  if (!b) throw new Error('offline bundle not downloaded')
  const runs = []
  for (const blob of blobs) runs.push(await infer(blob, b))
  const plant = runs.filter((r) => !(r.pf < b.thresholds.min_plant || r.flat))
  const used = plant.length ? plant : runs
  const p = b.labels.map((_, i) => used.reduce((a, r) => a + r.p[i], 0) / used.length)
  const order = p.map((v, i) => [v, i] as const).sort((x, y) => y[0] - x[0]).slice(0, 3)
  const top = order.map(([v, i]) => ({ id: b.labels[i], name: b.names[lang][b.labels[i]], prob: Math.round(v * 10000) / 10000 }))
  const reason = !plant.length ? 'not_plant' : top[0].prob < b.thresholds.min_conf ? 'low_confidence' : null
  let camUrl: string | null = null, affected: number | null = null
  if (reason !== 'not_plant') {
    const ci = order[0][1]
    const best = used.reduce((a, r) => (r.p[ci] > a.p[ci] ? r : a))
    const c = cam(best, b.classifier_w[ci]); camUrl = c.url; affected = c.affected
  }
  return {
    top, unsure: reason !== null, reason, cam: camUrl, affected_pct: affected,
    advice: reason === 'not_plant' ? null : b.advice[lang][top[0].id],
    n_images: blobs.length, n_used: plant.length, ms: Math.round(performance.now() - t0), offline: true,
  }
}
