// Питч мәтіні Word-та → materials/EginAI_Pitch_matini.docx
// NODE_PATH=<node_modules> node materials/build_pitch_docx.js
const fs = require('fs')
const path = require('path')
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber,
} = require('docx')
const P = require('./pitch.js')

const FONT = 'Times New Roman'
const COLOR = { B: '2F6B3A', E: '8A5A00', R: 'B5471B' }
const FILL = { B: 'E4F0E5', E: 'FFF4D6', R: 'FBE9E2' }
const mmss = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
const who = (k) => P.speakers[k]
const para = (runs, o = {}) => new Paragraph({ spacing: { after: o.after ?? 120, line: 300 }, alignment: o.align, children: runs })
const run = (text, o = {}) => new TextRun({ text, ...o })
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [run(t)] })
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [run(t)] })
const LI = (runs, ref = 'bul') => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60, line: 290 }, children: runs })
const b = { style: BorderStyle.SINGLE, size: 4, color: '9AA59D' }
const borders = { top: b, bottom: b, left: b, right: b }

function table(widths, rows, fills = []) {
  return new Table({
    width: { size: widths.reduce((a, x) => a + x, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0,
      children: r.map((c, ci) => new TableCell({
        width: { size: widths[ci], type: WidthType.DXA }, borders, margins: { top: 50, bottom: 50, left: 90, right: 90 },
        shading: ri === 0 ? { type: ShadingType.CLEAR, fill: 'EEF2EC', color: 'auto' } : fills[ri] ? { type: ShadingType.CLEAR, fill: fills[ri], color: 'auto' } : undefined,
        children: [new Paragraph({ children: [run(String(c), { bold: ri === 0, size: 22 })] })],
      })),
    })),
  })
}

const total = P.slides.reduce((a, s) => a + s.sec, 0)
const per = {}
P.slides.forEach((s) => { per[s.who] = (per[s.who] || 0) + s.sec })
let t = 0
const timeline = P.slides.map((s) => { const r = [s.demo ? '—' : s.pos, s.title, who(s.who), `${mmss(t)}–${mmss(t + s.sec)}`, `${s.sec} с`]; t += s.sec; return r })

const body = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [run('EginAI — қорғау мәтіні (питч)', { bold: true, size: 36 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [run('«AI autumn» 2026  |  сөйлеу 5–7 минут, сұрақтар 3–5 минут', { size: 24, color: '55625A' })] }),

  H1('1. Кім не айтады'),
  para([run(`Жалпы уақыт: ${mmss(total)} (регламент 5–7 мин). `, { bold: true }),
    run(`Бекназар — ${mmss(per.B)}, Ернұр — ${mmss(per.E)}, Рома — ${mmss(per.R)} (тірі демонстрацияны қоса). Кезекпен айтамыз: Бекназар ашады (1–3), Рома шешім мен демоны көрсетеді (4–6), Ернұр модель мен нәтижені айтады (7–9), Бекназар қорытындылайды (10–11). Әр спикер соңында келесі адамды атап, сөзді береді. Арман бұл жолы келмейді: оның бөлігін Рома айтады, финалда команда мүшесі ретінде аталады.`)]),
  table([1000, 2700, 1500, 1700, 1100], [['Слайд', 'Тақырып', 'Кім', 'Уақыт', 'Ұзақтығы'], ...timeline],
    [null, ...P.slides.map((s) => FILL[s.who])]),
  para([], { after: 120 }),

  H1('2. Слайд бойынша мәтін'),
  para([run('Мәтінді сөзбе-сөз жаттау міндетті емес — мағынасын өз сөзіңмен айтуға болады. Сандарды (97,1%, 580 сурет, 57 мс, 98,4%) дәл айту керек.', { italics: true, color: '55625A' })]),
  ...P.slides.flatMap((s) => [
    new Paragraph({
      heading: HeadingLevel.HEADING_2,
      shading: { type: ShadingType.CLEAR, fill: FILL[s.who], color: 'auto' },
      children: [run(s.demo ? `Тірі демонстрация — ${who(s.who)}` : `${s.pos}-слайд. ${s.title} — ${who(s.who)}`), run(`   (~${s.sec} с)`, { bold: false, size: 22, color: '55625A' })],
    }),
    para([run(s.text, { size: 26 })], { after: 200 }),
  ]),

  H1('3. Тірі демонстрацияға дайындық (Рома)'),
  ...[
    'Қорғауға дейін 15 минут бұрын: ~/eginai қалтасында docker compose up, браузерде http://localhost:8000 ашып, тексеріп қою.',
    'Жұмыс үстеліне samples/ қалтасынан 3 фото: leaf_rust_00048_0.jpg, stripe_rust_00273_0.jpg және materials/figures/not_plant.jpg.',
    'Карта үшін интернет керек (OpenStreetMap тайлдары). Интернет болмаса — картаны көрсетпей, слайдтағы скриншотпен айту.',
    'Сақтық нұсқа: бірдеңе істемей қалса, EginAI_Demo.mp4 видеосын қосу (2:11).',
    'Ретпен: фото жүктеу → «Белгілер аймағы» → кеңес → сұрақ «Қай кезде өңдеген дұрыс?» → тілді ауыстыру → өсімдік емес фото → карта.',
  ].map((x) => LI([run(x)], 'num')),

  H1('4. Қазылардың ықтимал сұрақтары'),
  para([run('Әр сұраққа жауап беретін адам көрсетілген. Білмесең — «бұл сұраққа Бекназар толықтырады» деп капитанға беру.', { italics: true, color: '55625A' })]),
  ...P.qa.flatMap(([k, q, a]) => [
    para([run(`${who(k)}: `, { bold: true, color: COLOR[k] }), run(q, { bold: true })], { after: 40 }),
    para([run(a)], { after: 160 }),
  ]),

  H1('5. Еске сақта'),
  ...[
    'Кезек ауысқанда сөзді келесі адамға беру сөйлемі мәтінде бар — үзіліс болмасын.',
    'Бір адам сөйлегенде, екіншісі слайдты ауыстырады — алдын ала келісіп ал.',
    '«Ойдан диагноз қоймайды» және «фото сақталмайды» — қазылар үшін ең күшті екі дәлел, міндетті түрде айту.',
    'Регламенттен асып кетпеу: 6:25 — қор бар, бірақ демонстрацияда ұзақ тұрып қалмау.',
    'Әркім өз бөлігін түсіндіре алуы керек — бұл конкурстың талабы.',
  ].map((x) => LI([run(x)])),
]

const numLevel = (format, text) => ({ level: 0, format, text, alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } })
const doc = new Document({
  creator: 'EginAI', title: 'EginAI — питч мәтіні',
  styles: {
    default: { document: { run: { font: FONT, size: 24 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 30, bold: true, color: '1B2A1F' }, paragraph: { spacing: { before: 320, after: 140 }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 26, bold: true, color: '1B2A1F' }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: 'bul', levels: [numLevel(LevelFormat.BULLET, '•')] }, { reference: 'num', levels: [numLevel(LevelFormat.DECIMAL, '%1.')] }] },
  sections: [{
    properties: { page: { margin: { top: 1000, bottom: 1000, left: 1300, right: 1000 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] }) },
    children: body,
  }],
})
Packer.toBuffer(doc).then((buf) => { const out = path.join(__dirname, 'EginAI_Pitch_matini.docx'); fs.writeFileSync(out, buf); console.log('→', out) })
