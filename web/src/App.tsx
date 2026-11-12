import { useEffect, useState } from 'react'
import About from './About'
import Diagnose from './Diagnose'
import MapView from './MapView'
import { T, type Lang } from './i18n'

type Tab = 'diagnose' | 'map' | 'about'
const TABS: Tab[] = ['diagnose', 'map', 'about']

function readTab(): Tab {
  const h = location.hash.slice(1) as Tab
  return TABS.includes(h) ? h : 'diagnose'
}

function readLang(): Lang {
  try { return (localStorage.getItem('lang') as Lang) || 'kk' } catch { return 'kk' }
}

export default function App() {
  const [tab, setTab] = useState<Tab>(readTab)
  const [lang, setLang] = useState<Lang>(readLang)
  const t = T[lang]

  useEffect(() => {
    const on = () => setTab(readTab())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  useEffect(() => {
    document.documentElement.lang = lang
    try { localStorage.setItem('lang', lang) } catch { /* жеке режим */ }
  }, [lang])

  const label = { diagnose: t.tabDiagnose, map: t.tabMap, about: t.tabAbout }

  return (
    <div className="app">
      <header className="top">
        <a href="#diagnose" className="brand" aria-label="EginAI">
          <Logo /><span>Egin<b>AI</b></span>
        </a>
        <span className="tagline">{t.appTagline}</span>
        <div className="lang" role="group" aria-label="Тіл / Язык">
          {(['kk', 'ru'] as Lang[]).map((l) => (
            <button key={l} aria-pressed={lang === l} onClick={() => setLang(l)}>{l === 'kk' ? 'Қаз' : 'Рус'}</button>
          ))}
        </div>
      </header>

      <main>
        {tab === 'diagnose' && <Diagnose lang={lang} t={t} />}
        {tab === 'map' && <MapView lang={lang} t={t} />}
        {tab === 'about' && <About lang={lang} />}
      </main>

      <nav className="tabs" aria-label="Навигация">
        {TABS.map((x) => (
          <a key={x} href={`#${x}`} aria-current={tab === x ? 'page' : undefined}>{label[x]}</a>
        ))}
      </nav>
    </div>
  )
}

// Логотип: стилизацияланған бидай масағы (тұтас түс)
function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="7" fill="#1B2A1F" />
      <path d="M16 27V9" stroke="#E8B931" strokeWidth="2" strokeLinecap="round" />
      {[11, 15, 19].map((y) => (
        <g key={y} fill="#E8B931">
          <ellipse cx="12.6" cy={y} rx="3.2" ry="1.8" transform={`rotate(-35 12.6 ${y})`} />
          <ellipse cx="19.4" cy={y} rx="3.2" ry="1.8" transform={`rotate(35 19.4 ${y})`} />
        </g>
      ))}
      <ellipse cx="16" cy="7" rx="1.8" ry="3" fill="#E8B931" />
    </svg>
  )
}
