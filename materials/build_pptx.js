// EginAI қорғау презентациясы (қазақша, 16:9) → materials/EginAI_Prezentatsia.pptx
// Іске қосу: NODE_PATH=<node_modules> node materials/build_pptx.js
const fs = require('fs')
const path = require('path')
const pptxgen = require('pptxgenjs')
const { applyTheme } = require(process.env.PPTX_SKILL + '/scripts/apply_theme.js')

const ROOT = path.resolve(__dirname, '..')
const FIG = (f) => path.join(ROOT, 'materials/figures', f)
const PITCH = require('./pitch.js')
const NOTE = (n) => PITCH.slides.filter((x) => x.n === n || (n === 3 && x.demo)).map((x) => `${PITCH.speakers[x.who]} (~${x.sec} с${x.demo ? ', тірі демо' : ''}): ${x.text}`).join('\n\n')
const M = JSON.parse(fs.readFileSync(path.join(ROOT, 'ml/metrics.json'), 'utf8'))
const p1 = (x) => (x * 100).toFixed(1).replace('.', ',') + '%'

const THEME = {
  name: 'EginAI', headFontFace: 'Arial', bodyFontFace: 'Arial',
  colors: {
    dk1: '1B2A1F', lt1: 'FFFFFF', dk2: '2F6B3A', lt2: 'EEF2EC',
    accent1: 'E8B931', accent2: '2F6B3A', accent3: 'B5471B', accent4: '55625A', accent5: 'CCD5CE', accent6: '6E7B8B',
    hlink: '2F6B3A', folHlink: '55625A',
  },
}
const INK = '1B2A1F', WHEAT = 'E8B931', LEAF = '2F6B3A', RUST = 'B5471B', FIELD = 'EEF2EC', MUTED = '55625A', LINE = 'CCD5CE'

const pres = new pptxgen()
pres.layout = 'LAYOUT_16x9' // 10 × 5.625 дюйм
pres.theme = { headFontFace: 'Arial', bodyFontFace: 'Arial' }
pres.title = 'EginAI — бидай ауруларын фото бойынша анықтау'
pres.author = 'EginAI командасы'
const C = pres.SchemeColor

// --- Макеттер ---
pres.defineSlideMaster({
  title: 'EG_TITLE', background: { color: INK },
  objects: [{ placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 1.5, w: 8.8, h: 1.2, fontSize: 54, bold: true, color: C.background1, valign: 'top', margin: 0, align: 'left' }, text: '' } }],
})
pres.defineSlideMaster({
  title: 'EG_CONTENT', background: { color: 'FFFFFF' },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.5, y: 0.3, w: 9.0, h: 0.75, fontSize: 28, bold: true, color: C.text1, valign: 'top', margin: 0, align: 'left' }, text: '' } },
    { text: { text: 'EginAI', options: { x: 0.5, y: 5.2, w: 2, h: 0.25, fontSize: 10, color: MUTED, margin: 0 } } },
  ],
  slideNumber: { x: 9.1, y: 5.2, w: 0.4, h: 0.25, fontSize: 10, color: MUTED, align: 'right' },
})

const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, fontFace: 'Arial', color: INK, ...o })
const box = (s, x, y, w, h, fill = FIELD, name) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: LINE, width: 1 }, objectName: name })
const title = (s, t) => s.addText(t, { placeholder: 'title' })
const content = (sec) => pres.addSlide({ masterName: 'EG_CONTENT', sectionTitle: sec })

// Логотип (масақ) — тұтас түс
function logo(s, x, y, size, bg = INK) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: size, h: size, rectRadius: size * 0.2, fill: { color: bg }, line: { color: WHEAT, width: 1 }, objectName: 'logo-bg' })
  const k = size / 32
  s.addShape(pres.shapes.LINE, { x: x + 16 * k, y: y + 9 * k, w: 0, h: 18 * k, line: { color: WHEAT, width: 2 } })
  for (const yy of [11, 15, 19]) {
    s.addShape(pres.shapes.OVAL, { x: x + 9.6 * k, y: y + (yy - 1.8) * k, w: 6 * k, h: 3.6 * k, fill: { color: WHEAT }, line: { color: WHEAT, width: 0 }, rotate: -35 })
    s.addShape(pres.shapes.OVAL, { x: x + 16.4 * k, y: y + (yy - 1.8) * k, w: 6 * k, h: 3.6 * k, fill: { color: WHEAT }, line: { color: WHEAT, width: 0 }, rotate: 35 })
  }
  s.addShape(pres.shapes.OVAL, { x: x + 14.2 * k, y: y + 4 * k, w: 3.6 * k, h: 6 * k, fill: { color: WHEAT }, line: { color: WHEAT, width: 0 } })
}

// 1. Титул
pres.addSection({ title: 'Кіріспе' })
let s = pres.addSlide({ masterName: 'EG_TITLE', sectionTitle: 'Кіріспе' })
logo(s, 0.6, 0.55, 0.7)
s.addText('EginAI', { placeholder: 'title' })
T(s, 'Бидай ауруларын фото бойынша ерте анықтау', { x: 0.6, y: 2.55, w: 8.5, h: 0.5, fontSize: 24, color: 'FFFFFF' })
T(s, 'Телефонмен түсір → бірнеше секундта диагноз → қазақша не орысша кеңес → аурулар картасы', { x: 0.6, y: 3.15, w: 8.6, h: 0.4, fontSize: 14, color: 'C9D3CC' })
T(s, [
  { text: 'Конкурс «AI autumn» 2026  |  Бағыт: Агротех, экология және ақылды қала', options: { breakLine: true } },
  { text: 'С. Сейфуллин атындағы ҚАТЗУ  |  Ғылыми жетекші: Таберхан Роман' },
], { x: 0.6, y: 4.5, w: 8.6, h: 0.6, fontSize: 12, color: 'C9D3CC', paraSpaceAfter: 4 })
s.addNotes(NOTE(1))

// 2. Мәселе
pres.addSection({ title: 'Мәселе және шешім' })
s = content('Мәселе және шешім')
title(s, 'Ауру кеш байқалады — өнім жоғалады')
box(s, 0.5, 1.25, 3.4, 3.7, INK, 'stat')
T(s, '40%-ға дейін', { x: 0.75, y: 1.55, w: 3.0, h: 0.9, fontSize: 34, bold: true, color: WHEAT })
T(s, 'әлемдік егін зиянкестер мен аурулардан жоғалады (ФАО)', { x: 0.75, y: 2.6, w: 2.9, h: 1.0, fontSize: 15, color: 'FFFFFF' })
T(s, 'Қазақстан — өңірдегі ең ірі бидай өндірушілердің бірі; солтүстікте басты қауіп — тат, септориоз, ақ ұнтақ ауруы.', { x: 0.75, y: 3.65, w: 2.9, h: 1.1, fontSize: 12, color: 'C9D3CC' })
const pains = [
  ['Агроном жетпейді', 'Шалғай ауылдарда ауруды көзбен ажырататын маман жоқ.'],
  ['Кеш немесе қате диагноз', 'Өнім жоғалады, фунгицид «қалай болса да» шашылады.'],
  ['Көрші не біледі?', 'Ауру қай ауданға тарап жатқанын ешкім көрмейді.'],
  ['Қолданбалар бізге жат', 'Plantix, Agrio — қазақ тілі жоқ, жарнама, «білмеймін».'],
]
pains.forEach(([h, t], i) => {
  const y = 1.25 + i * 0.95
  s.addShape(pres.shapes.OVAL, { x: 4.25, y: y + 0.08, w: 0.42, h: 0.42, fill: { color: i === 3 ? RUST : WHEAT }, line: { color: INK, width: 1 } })
  T(s, String(i + 1), { x: 4.25, y: y + 0.08, w: 0.42, h: 0.42, fontSize: 14, bold: true, align: 'center', valign: 'middle', color: i === 3 ? 'FFFFFF' : INK })
  T(s, h, { x: 4.9, y, w: 4.6, h: 0.35, fontSize: 16, bold: true })
  T(s, t, { x: 4.9, y: y + 0.36, w: 4.6, h: 0.45, fontSize: 13, color: MUTED })
})
s.addNotes(NOTE(2))

// 3. Шешім + экрандар
s = content('Мәселе және шешім')
title(s, 'EginAI: фото → диагноз → кеңес → карта')
const shots = [['ui-1-home-kk.png', 'Суретке түсіру'], ['ui-2-result-kk.png', 'Диагноз және белгілер аймағы'], ['ui-3-advice-kk.png', 'Кеңес: не істеу, қашан'], ['ui-7-map-ru.png', 'Аурулар ошақтарының картасы']]
shots.forEach(([f, cap], i) => {
  const x = 0.5 + i * 2.3
  s.addImage({ path: FIG(f), x: x + 0.1, y: 1.15, w: 1.85, h: 3.86, objectName: 'shot-' + i, altText: cap })
  s.addShape(pres.shapes.RECTANGLE, { x: x + 0.1, y: 1.15, w: 1.85, h: 3.86, fill: { type: 'none' }, line: { color: LINE, width: 1 } })
  T(s, cap, { x, y: 5.03, w: 2.05, h: 0.2, fontSize: 10, color: MUTED, align: 'center' })
})
s.addNotes(NOTE(3))

// 4. Архитектура
pres.addSection({ title: 'Технология' })
s = content('Технология')
title(s, 'Қалай жұмыс істейді')
s.addImage({ path: FIG('architecture.png'), x: 0.5, y: 1.1, w: 6.2, h: 3.18, objectName: 'arch', altText: 'Архитектура сызбасы' })
const tech = [['ML', 'PyTorch, timm, EfficientNet-B0 → ONNX'], ['Backend', 'FastAPI, PostgreSQL, ONNX Runtime'], ['Кеңес', 'kk/ru білім базасы, BM25 (RAG), Claude — қалауы бойынша'], ['Клиенттер', 'React + Leaflet, aiogram 3 бот'], ['Іске қосу', 'docker compose up — бір команда']]
tech.forEach(([h, t], i) => {
  T(s, h, { x: 7.0, y: 1.15 + i * 0.78, w: 2.5, h: 0.28, fontSize: 13, bold: true, color: LEAF })
  T(s, t, { x: 7.0, y: 1.43 + i * 0.78, w: 2.5, h: 0.45, fontSize: 11, color: INK })
})
T(s, 'Фото серверде сақталмайды. Модель 16 МБ, кәдімгі процессорда жұмыс істейді.', { x: 0.5, y: 4.5, w: 6.2, h: 0.4, fontSize: 13, color: MUTED })
s.addNotes(NOTE(4))

// 5. Деректер мен модель
s = content('Технология')
title(s, 'Деректер және модельді үйрету')
const stats = [['4156', 'далалық фото\n(CC-BY-4.0)'], ['5845', 'белгіленген\nзақымдану аймағы'], ['7', 'класс: 5 ауру\n+ сау жапырақ/масақ']]
stats.forEach(([n, l], i) => {
  box(s, 0.5 + i * 1.6, 1.2, 1.45, 1.6, FIELD, 'stat-' + i)
  T(s, n, { x: 0.6 + i * 1.6, y: 1.35, w: 1.25, h: 0.6, fontSize: 30, bold: true, color: LEAF })
  T(s, l, { x: 0.6 + i * 1.6, y: 2.0, w: 1.3, h: 0.7, fontSize: 11, color: MUTED })
})
T(s, [
  { text: 'Датасет детекцияға арналған — біз бокстарды 25% жиекпен қиып, классификация датасетіне айналдырдық.', options: { bullet: true, breakLine: true } },
  { text: 'Train / val / test бөлінісі сурет бойынша: бір фотоның бөліктері әрі оқуда, әрі тестте болмайды.', options: { bullet: true, breakLine: true } },
  { text: 'EfficientNet-B0 (ImageNet) + transfer learning, 15 эпоха, GTX 1650 (4 ГБ), ~15 минут.', options: { bullet: true, breakLine: true } },
  { text: 'Аугментация далалық түсірілімді имитациялайды: қию, бұру, жарық, контраст.', options: { bullet: true } },
], { x: 0.5, y: 3.05, w: 4.7, h: 1.9, fontSize: 13, paraSpaceAfter: 6, valign: 'top' })
const cls = [['Қоңыр тат', RUST], ['Сары тат', 'D99A00'], ['Ақ ұнтақ ауруы', '6E7B8B'], ['Масақ фузариозы', 'C2417A'], ['Масақ септориозы', '7A4E2D'], ['Сау жапырақ', LEAF], ['Сау масақ', '5E8C3A']]
box(s, 5.6, 1.2, 3.9, 3.75, 'FFFFFF', 'classes')
T(s, 'Модель танитын кластар', { x: 5.85, y: 1.35, w: 3.5, h: 0.35, fontSize: 15, bold: true })
cls.forEach(([n, c], i) => {
  s.addShape(pres.shapes.OVAL, { x: 5.9, y: 1.9 + i * 0.42, w: 0.2, h: 0.2, fill: { color: c }, line: { color: INK, width: 0.75 } })
  T(s, n, { x: 6.25, y: 1.84 + i * 0.42, w: 3.1, h: 0.32, fontSize: 13 })
})
s.addNotes(NOTE(5))

// 6. Нәтижелер
pres.addSection({ title: 'Нәтижелер' })
s = content('Нәтижелер')
title(s, 'Тест жиынында: 97% дәлдік')
const big = [[p1(M.accuracy), 'дәлдік (accuracy)'], [p1(M.macro_f1), 'macro-F1'], [Math.round(M.cpu_ms_per_image_median) + ' мс', 'бір фото, CPU']]
big.forEach(([n, l], i) => {
  T(s, n, { x: 0.5, y: 1.15 + i * 1.25, w: 3.2, h: 0.75, fontSize: 40, bold: true, color: i === 0 ? LEAF : INK })
  T(s, l, { x: 0.5, y: 1.85 + i * 1.25, w: 3.2, h: 0.3, fontSize: 13, color: MUTED })
})
const order = ['stripe_rust', 'fusarium_head_blight', 'leaf_rust', 'healthy_leaf', 'healthy_ear', 'powdery_mildew', 'glume_blotch']
const kk = { stripe_rust: 'Сары тат', fusarium_head_blight: 'Масақ фузариозы', leaf_rust: 'Қоңыр тат', healthy_leaf: 'Сау жапырақ', healthy_ear: 'Сау масақ', powdery_mildew: 'Ақ ұнтақ ауруы', glume_blotch: 'Масақ септориозы' }
s.addChart(pres.charts.BAR, [{ name: 'F1', labels: order.map((k) => kk[k]), values: order.map((k) => Math.round(M.per_class[k]['f1-score'] * 100)) }], {
  x: 3.9, y: 1.05, w: 5.6, h: 3.95, barDir: 'bar', chartColors: [LEAF],
  showTitle: true, title: `Әр класс бойынша F1, % (тест: ${M.n_test} сурет)`, titleFontSize: 12, titleColor: INK, titleFontFace: '+mn-lt',
  showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 11, dataLabelColor: INK, dataLabelFontFace: '+mn-lt',
  catAxisLabelColor: INK, catAxisLabelFontSize: 11, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin',
  valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 100, valGridLine: { style: 'none' }, catGridLine: { style: 'none' }, showLegend: false,
})
T(s, 'Мақсат (өтінімде): ≥ 90%. Жетті.', { x: 0.5, y: 4.85, w: 3.3, h: 0.3, fontSize: 12, bold: true, color: RUST })
s.addNotes(NOTE(6))

// 7. Түсіндірілетін және адал
s = content('Нәтижелер')
title(s, 'Түсіндірілетін және адал модель')
s.addImage({ path: FIG('cam_examples2.png'), x: 0.5, y: 1.4, w: 5.2, h: 2.77, objectName: 'cam', altText: 'CAM жылу карталары' })
box(s, 6.0, 1.1, 3.5, 1.65, INK, 'honest')
T(s, '98,4%', { x: 6.25, y: 1.25, w: 3.1, h: 0.65, fontSize: 36, bold: true, color: WHEAT })
T(s, 'модель сенімді болған жауаптардағы дәлдік', { x: 6.25, y: 1.95, w: 3.1, h: 0.6, fontSize: 13, color: 'FFFFFF' })
T(s, [
  { text: 'CAM жылу картасы: модель тат пустулалары мен ақ ұнтақ дақтарына қарайды.', options: { bullet: true, breakLine: true } },
  { text: 'Сенім < 50% → «қайта түсіріңіз» + 3 ықтимал нұсқа.', options: { bullet: true, breakLine: true } },
  { text: 'Қабырға, қағаз, аспан → «суретте өсімдік жоқ».', options: { bullet: true } },
], { x: 6.0, y: 2.95, w: 3.5, h: 1.95, fontSize: 13, paraSpaceAfter: 6, valign: 'top' })
s.addNotes(NOTE(7))

// 8. Аналогтар
pres.addSection({ title: 'Нарық' })
s = content('Нарық')
title(s, 'Аналогтардан айырмашылығы')
const Y = '✓', N = '—'
const rows = [
  ['', 'Қазақ тілі', 'Бидай, СҚО аурулары', 'Аурулар картасы', 'Тегін, жарнамасыз', 'Telegram'],
  ['Plantix', N, Y, N, N, N],
  ['Agrio', N, N, N, N, N],
  ['PlantVillage Nuru', N, 'әзірленуде', N, Y, N],
  ['DoctorP', N, Y, N, Y, N],
  ['EginAI', Y, Y, Y, Y, Y],
]
s.addTable(rows.map((r, ri) => r.map((c, ci) => ({
  text: c, options: {
    bold: ri === 0 || ci === 0 || ri === 5, fontSize: 13, align: ci === 0 ? 'left' : 'center', valign: 'middle',
    color: ri === 5 ? INK : (c === Y ? LEAF : INK), fill: { color: ri === 0 ? FIELD : ri === 5 ? WHEAT : 'FFFFFF' },
  },
}))), { x: 0.5, y: 1.15, w: 9.0, colW: [1.9, 1.3, 1.65, 1.45, 1.5, 1.2], rowH: 0.45, border: { type: 'solid', pt: 1, color: LINE }, fontFace: 'Arial' })
T(s, '77 нақты пікір бойынша басты шағымдар: «ИИ білмейді / қате айтады» (16), жарнама мен жазылым (11), қажет дақыл жоқ (8), «эксперт жауап бермейді» (5).', { x: 0.5, y: 4.2, w: 9.0, h: 0.6, fontSize: 13, color: MUTED })
s.addNotes(NOTE(8))

// 9. Қауіпсіздік және іске қосу
s = content('Нарық')
title(s, 'Қауіпсіздік, деректер, іске қосу')
const sec = [
  ['Жеке деректер', 'Фото сақталмайды. Картаға тек келісіммен: ауру, күн, ~1 км орын. Тіркелу, аты, телефон жоқ.'],
  ['Код', 'Кілттер тек .env-те. Файл шегі 10 МБ, бүлінген файлға 4xx, IP бойынша шектеу, root емес контейнер.'],
  ['Лицензия', 'Код — MIT. Датасет CC-BY-4.0, кітапханалар — THIRD_PARTY.md тізімінде.'],
  ['Тексеру', '52 автотест: қате енгізу, келісім, база құлағанда диагностика жұмысы, LLM-сіз жауап.'],
]
sec.forEach(([h, t], i) => {
  const x = 0.5 + (i % 2) * 4.6, y = 1.15 + Math.floor(i / 2) * 1.45
  box(s, x, y, 4.4, 1.3, FIELD, 'sec-' + i)
  T(s, h, { x: x + 0.25, y: y + 0.15, w: 3.9, h: 0.32, fontSize: 15, bold: true })
  T(s, t, { x: x + 0.25, y: y + 0.5, w: 3.95, h: 0.75, fontSize: 12, color: INK })
})
box(s, 0.5, 4.15, 9.0, 0.75, INK, 'run')
T(s, [{ text: 'git clone …  &&  docker compose up', options: { fontFace: 'Courier New', color: WHEAT, bold: true } }, { text: '   →   http://localhost:8000', options: { color: 'FFFFFF' } }], { x: 0.75, y: 4.15, w: 8.5, h: 0.75, fontSize: 16, valign: 'middle' })
s.addNotes(NOTE(9))

// 10. Келешек
pres.addSection({ title: 'Келешек' })
s = content('Келешек')
title(s, 'Даму жоспары және коммерцияландыру')
const road = [
  ['2027 көктем–жаз', 'Ақмола облысындағы университет алқаптарынан өз фотоларымызды жинап, модельді қайта үйрету; «келіспеймін» батырмасы.'],
  ['2-кезең', 'Арпа, тамыр шірігі, ВИЗР шкаласы бойынша зақымдану дәрежесі; интернетсіз жұмыс (телефондағы модель).'],
  ['3-кезең', 'Аудандар бойынша апталық аналитика фитосанитарлық қызметтерге, ошақ жақындағанда ескерту.'],
]
road.forEach(([h, t], i) => {
  const y = 1.2 + i * 1.15
  s.addShape(pres.shapes.OVAL, { x: 0.5, y, w: 0.5, h: 0.5, fill: { color: WHEAT }, line: { color: INK, width: 1 } })
  T(s, String(i + 1), { x: 0.5, y, w: 0.5, h: 0.5, fontSize: 16, bold: true, align: 'center', valign: 'middle' })
  T(s, h, { x: 1.2, y: y - 0.02, w: 4.0, h: 0.32, fontSize: 15, bold: true })
  T(s, t, { x: 1.2, y: y + 0.32, w: 4.1, h: 0.75, fontSize: 12, color: MUTED })
})
box(s, 5.7, 1.2, 3.8, 3.7, FIELD, 'money')
T(s, 'Табыс көздері', { x: 5.95, y: 1.35, w: 3.4, h: 0.35, fontSize: 16, bold: true })
T(s, [
  { text: 'Фермерлерге — әрқашан тегін', options: { bullet: true, breakLine: true, bold: true } },
  { text: 'Агрохолдингтер мен кеңесшілерге жазылым: есептер, жағдайларды жүктеу', options: { bullet: true, breakLine: true } },
  { text: 'Әкімдіктер мен фитосанитарлық қызметтерге аналитика лицензиясы', options: { bullet: true, breakLine: true } },
  { text: 'АӨК-ті цифрландыру гранттары', options: { bullet: true } },
], { x: 5.95, y: 1.8, w: 3.4, h: 3.0, fontSize: 13, paraSpaceAfter: 6, valign: 'top' })
s.addNotes(NOTE(10))

// 11. Команда
s = pres.addSlide({ masterName: 'EG_TITLE', sectionTitle: 'Келешек' })
s.addText('Команда', { placeholder: 'title' })
const team = [['Әбдімүтәлі Бекназар', 'Капитан: архитектура, интеграция, білім базасы, қорғау'], ['Әбдіқадыр Ернұр', 'ML: датасет, үйрету, бағалау, ONNX'], ['Есен Арман', 'Backend: API, дерекқор, Telegram-бот, Docker'], ['Жақсығұл Рамазан', 'Frontend, UI/UX: веб-қосымша, карта, фото']]
team.forEach(([n, r], i) => {
  const x = 0.6 + (i % 2) * 4.45, y = 2.55 + Math.floor(i / 2) * 1.0
  T(s, n, { x, y, w: 4.2, h: 0.38, fontSize: 18, bold: true, color: WHEAT })
  T(s, r, { x, y: y + 0.4, w: 4.2, h: 0.4, fontSize: 13, color: 'FFFFFF' })
})
T(s, 'Ғылыми жетекші: Таберхан Роман      Рақмет! Сұрақтарыңызды күтеміз.', { x: 0.6, y: 4.75, w: 8.8, h: 0.4, fontSize: 14, color: 'C9D3CC' })
s.addNotes(NOTE(11))

const out = path.join(ROOT, 'materials', 'EginAI_Prezentatsia.pptx')
pres.writeFile({ fileName: out }).then(async () => { await applyTheme(out, THEME); console.log('→', out) })
