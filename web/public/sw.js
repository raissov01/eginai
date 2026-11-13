// EginAI service worker: интернетсіз ашылу үшін қосымша қабығын кэштейді.
// Модель мен кеңестер бумасын offline.ts өзі 'eginai-offline-v1' кэшіне салады —
// мұнда тек сол кэштен беріледі. API (диагноз, карта) әрқашан желі арқылы.
const SHELL = 'eginai-shell-v1'

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(['/', '/favicon.svg'])).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys()
    .then((ks) => Promise.all(ks.filter((k) => k.startsWith('eginai-shell-') && k !== SHELL).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()))
})

self.addEventListener('fetch', (e) => {
  const req = e.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  if (url.origin !== location.origin) return

  // Бет: алдымен желі (жаңа нұсқа), желі жоқ болса — кэштегі қабық
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).then((r) => {
      const copy = r.clone(); caches.open(SHELL).then((c) => c.put('/', copy)); return r
    }).catch(() => caches.match('/')))
    return
  }
  // Хэштелген ассеттер, WASM, офлайн бума: алдымен кэш
  if (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/ort/') || url.pathname.startsWith('/api/offline/')) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((r) => {
      if (r.ok && url.pathname.startsWith('/assets/')) { const copy = r.clone(); caches.open(SHELL).then((c) => c.put(req, copy)) }
      return r
    })))
  }
})
