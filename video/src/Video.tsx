// EginAI — моушн демо-видео (1920×1080, 30 fps). Тегіс стиль: тұтас түстер, градиентсіз.
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, OffthreadVideo, Sequence, spring, staticFile,
  useCurrentFrame, useVideoConfig, Easing,
} from "remotion";
import { FONT } from "./fonts";
import marksJson from "./marks.json";

const INK = "#1B2A1F", WHEAT = "#E8B931", LEAF = "#2F6B3A", RUST = "#B5471B";
const FIELD = "#EEF2EC", MUTED = "#55625A", PALE = "#C9D3CC", WHITE = "#FFFFFF";
const FPS = 30;
const s = (sec: number) => Math.round(sec * FPS);

// ---- Сахналар кестесі (кадр) ----
const RATE = 1.25; // экран жазбасы 1,25× жылдамдықпен
const MARKS = marksJson.marks as [number, string][];
const DEMO_LEN = Math.round((MARKS[MARKS.length - 1][0] / RATE) * FPS);
const SCENES = [
  ["intro", s(7)], ["problem", s(9)], ["analogs", s(5)], ["demo", DEMO_LEN],
  ["how", s(9)], ["results", s(8.5)], ["drone", s(28)], ["launch", s(6)], ["outro", s(7)],
] as const;
const START: Record<string, number> = {};
let acc = 0;
for (const [n, d] of SCENES) { START[n] = acc; acc += d; }
export const TOTAL = acc;
const LEN = Object.fromEntries(SCENES) as Record<string, number>;

// ---- Көмекшілер ----
const useSp = (delay = 0, damping = 200) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: f - delay, fps, config: { damping } });
};
const Up: React.FC<{ delay?: number; children: React.ReactNode; dist?: number; style?: React.CSSProperties }> = ({ delay = 0, children, dist = 50, style }) => {
  const p = useSp(delay);
  return <div style={{ transform: `translateY(${(1 - p) * dist}px)`, opacity: p, ...style }}>{children}</div>;
};
const fmt = (v: number, d = 1) => v.toFixed(d).replace(".", ",");
const Counter: React.FC<{ to: number; delay?: number; dur?: number; d?: number; suffix?: string }> = ({ to, delay = 0, dur = 40, d = 1, suffix = "" }) => {
  const f = useCurrentFrame();
  const v = interpolate(f - delay, [0, dur], [0, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return <>{fmt(v, d)}{suffix}</>;
};
const FadeScene: React.FC<{ len: number; children: React.ReactNode; bg?: string }> = ({ len, children, bg = WHITE }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 8, len - 8, len], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ background: bg, opacity: o, fontFamily: FONT, color: INK }}>{children}</AbsoluteFill>;
};
const Logo: React.FC<{ size: number }> = ({ size }) => <Img src={staticFile("img/logo.svg")} style={{ width: size, height: size }} />;
const Badge: React.FC<{ n: number | string; delay: number; color?: string; txt?: string; size?: number }> = ({ n, delay, color = WHEAT, txt = INK, size = 64 }) => {
  const p = useSp(delay, 12);
  return (
    <div style={{ width: size, height: size, borderRadius: size, background: color, border: `2px solid ${INK}`, display: "flex",
      alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: size * 0.45, color: txt, transform: `scale(${p})`, flexShrink: 0 }}>{n}</div>
  );
};

// ---- 1. Титул ----
const Intro: React.FC = () => {
  const f = useCurrentFrame();
  const panel = useSp(0);
  const zoom = interpolate(f, [0, LEN.intro], [1.18, 1.0]);
  const word = "EginAI".split("");
  return (
    <FadeScene len={LEN.intro} bg={INK}>
      <AbsoluteFill style={{ left: 820 }}>
        <Img src={staticFile("img/hero_field.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ width: 900, background: INK, transform: `translateX(${(panel - 1) * 900}px)` }} />
      <div style={{ position: "absolute", left: 120, top: 120 }}><Up delay={8}><Logo size={96} /></Up></div>
      <div style={{ position: "absolute", left: 120, top: 290, display: "flex", fontSize: 190, fontWeight: 700, color: WHITE, lineHeight: 1 }}>
        {word.map((c, i) => <Up key={i} delay={14 + i * 4} dist={80}>{c}</Up>)}
      </div>
      <div style={{ position: "absolute", left: 120, top: 520, width: 680 }}>
        <Up delay={44}><div style={{ fontSize: 52, fontWeight: 500, color: WHITE, lineHeight: 1.15 }}>Бидай ауруларын фото бойынша ерте анықтау</div></Up>
        <Up delay={60}><div style={{ fontSize: 30, color: PALE, marginTop: 36, lineHeight: 1.4 }}>Телефонмен түсір → диагноз → кеңес → аурулар картасы</div></Up>
      </div>
      <div style={{ position: "absolute", left: 120, top: 930 }}><Up delay={76}><div style={{ fontSize: 24, color: PALE }}>«AI autumn» 2026 · С. Сейфуллин атындағы ҚАТЗУ</div></Up></div>
    </FadeScene>
  );
};

// ---- 2. Мәселе ----
const Problem: React.FC = () => {
  const f = useCurrentFrame();
  const zoom = interpolate(f, [0, LEN.problem], [1.0, 1.12]);
  const pains = ["Шалғай ауылдарда агроном жетпейді", "Ауру кеш байқалады — өнім жоғалады", "Фунгицид «қалай болса да» шашылады"];
  return (
    <FadeScene len={LEN.problem}>
      <div style={{ position: "absolute", left: 120, top: 120, width: 640, height: 840, borderRadius: 28, overflow: "hidden", border: `2px solid ${INK}` }}>
        <Up delay={0} dist={60} style={{ width: "100%", height: "100%" }}>
          <Img src={staticFile("img/rust_hand.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} />
        </Up>
      </div>
      <div style={{ position: "absolute", left: 860, top: 130, width: 940 }}>
        <Up delay={10}><div style={{ fontSize: 34, fontWeight: 600, color: MUTED }}>Әлемдік егіннің</div></Up>
        <div style={{ fontSize: 220, fontWeight: 700, color: RUST, lineHeight: 1 }}><Counter to={40} d={0} delay={14} dur={45} suffix="%" /></div>
        <Up delay={30}><div style={{ fontSize: 36, color: INK, lineHeight: 1.3 }}>дейін зиянкестер мен аурулардан жоғалады (ФАО)</div></Up>
        <div style={{ marginTop: 70 }}>
          {pains.map((p, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 28, marginBottom: 34 }}>
              <Badge n={i + 1} delay={70 + i * 22} color={i === 2 ? RUST : WHEAT} txt={i === 2 ? WHITE : INK} />
              <Up delay={74 + i * 22} dist={30}><div style={{ fontSize: 38, fontWeight: 500 }}>{p}</div></Up>
            </div>
          ))}
        </div>
      </div>
    </FadeScene>
  );
};

// ---- 3. Аналогтар ----
const Analogs: React.FC = () => {
  const cols = ["Қазақ тілі", "Аурулар картасы", "Тегін, жарнамасыз"];
  const rows: [string, boolean[]][] = [["Plantix", [false, false, false]], ["Agrio", [false, false, false]], ["DoctorP", [false, false, true]], ["EginAI", [true, true, true]]];
  return (
    <FadeScene len={LEN.analogs} bg={INK}>
      <div style={{ position: "absolute", left: 120, top: 100 }}><Up><div style={{ fontSize: 64, fontWeight: 700, color: WHITE }}>Бар қолданбалар бізге жат</div></Up></div>
      <div style={{ position: "absolute", left: 120, top: 260, width: 1680 }}>
        <div style={{ display: "flex", fontSize: 30, color: PALE, paddingBottom: 18 }}>
          <div style={{ width: 600 }} />{cols.map((c) => <div key={c} style={{ width: 360, textAlign: "center" }}>{c}</div>)}
        </div>
        {rows.map(([name, v], ri) => {
          const me = name === "EginAI";
          return (
            <Up key={name} delay={8 + ri * 10} dist={30}>
              <div style={{ display: "flex", alignItems: "center", height: 120, borderRadius: 18, background: me ? WHEAT : "transparent",
                borderTop: me ? "none" : `1px solid #3a4a3f`, color: me ? INK : WHITE }}>
                <div style={{ width: 600, paddingLeft: 30, fontSize: 44, fontWeight: me ? 700 : 500 }}>{name}</div>
                {v.map((ok, ci) => (
                  <div key={ci} style={{ width: 360, textAlign: "center", fontSize: 54, fontWeight: 700, color: me ? INK : ok ? "#7FBF7F" : "#6B7A70" }}>
                    <Mark delay={20 + ri * 10 + ci * 6} ok={ok} />
                  </div>
                ))}
              </div>
            </Up>
          );
        })}
      </div>
    </FadeScene>
  );
};
const Mark: React.FC<{ delay: number; ok: boolean }> = ({ delay, ok }) => {
  const p = useSp(delay, 10);
  return <span style={{ display: "inline-block", transform: `scale(${p})` }}>{ok ? "✓" : "—"}</span>;
};

// ---- 4. Қосымша демосы ----
const CAPTIONS: Record<string, string> = {
  start: "Тіркелусіз: браузерде немесе Telegram-да ашылады",
  upload_rust: "Фермер ауру жапырақты суретке түсіреді",
  result_rust: "Бірнеше секундта: қоңыр тат, сенімділік, зақымданған аудан",
  cam_toggle: "«Белгілер аймағы»: модель қай жерге қарағанын көрсетеді",
  advice: "Не істеу керек: шаралар, мерзімі, алдын алу — қазақша",
  ask: "Еркін сұрақ — жауап білім базасынан",
  consent: "Келісіммен картаға белгілеу: фото сақталмайды",
  lang_ru: "Орыс тілі де бар — сары тат анықталды",
  not_plant: "Өсімдік емес фото → ойдан диагноз жоқ",
  map: "Аурулар ошақтарының картасы",
  about: "Модель сапасы мен деректер саясаты",
};
const Demo: React.FC = () => {
  const f = useCurrentFrame();
  const t = (f / FPS) * RATE; // видео уақыты
  const steps = [["start", 0] as [string, number], ...MARKS.filter(([, k]) => CAPTIONS[k] && k !== "result_stripe").map(([tt, k]) => [k, tt] as [string, number])];
  let cur = 0;
  steps.forEach(([, tt], i) => { if (t >= tt) cur = i; });
  const [key, t0] = steps[cur];
  const local = (t - t0) / RATE * FPS; // титр басталғаннан бергі кадр
  const capP = spring({ frame: local, fps: FPS, config: { damping: 200 } });
  const enter = useSp(0);
  const tMap = MARKS.find(([, k]) => k === "map")![0];
  const tAbout = MARKS.find(([, k]) => k === "about")![0];
  const mapO = interpolate(t, [tMap + 0.6, tMap + 1.2, tAbout - 0.2, tAbout], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const camZoom = key === "cam_toggle" || key === "result_rust" ? interpolate(local, [0, 20], [1, 1.06], { extrapolateRight: "clamp" }) : 1;
  return (
    <FadeScene len={LEN.demo} bg={FIELD}>
      <div style={{ position: "absolute", left: 300, top: 40, width: 500, height: 1000, borderRadius: 56, background: INK, padding: 18,
        transform: `translateY(${(1 - enter) * 1100}px) scale(${camZoom})`, transformOrigin: "50% 30%" }}>
        <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 40, overflow: "hidden", background: WHITE }}>
          <OffthreadVideo src={staticFile("clips/phone.mp4")} playbackRate={RATE} muted style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }} />
          <Img src={staticFile("img/map.png")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: "top", opacity: mapO }} />
        </div>
      </div>
      <div style={{ position: "absolute", left: 960, top: 110 }}>
        <Up delay={6}><div style={{ fontSize: 28, fontWeight: 600, color: MUTED }}>Нақты қосымша — экран жазбасы</div></Up>
      </div>
      <div style={{ position: "absolute", left: 960, top: 380, width: 840, opacity: capP, transform: `translateX(${(1 - capP) * 80}px)` }}>
        <div style={{ display: "flex", gap: 28, alignItems: "flex-start" }}>
          <div style={{ width: 96, height: 96, borderRadius: 96, background: WHEAT, border: `2px solid ${INK}`, display: "flex", alignItems: "center",
            justifyContent: "center", fontSize: 44, fontWeight: 700, flexShrink: 0 }}>{cur + 1}</div>
          <div style={{ fontSize: 58, fontWeight: 700, lineHeight: 1.15 }}>{CAPTIONS[key]}</div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 960, top: 880, display: "flex", gap: 14 }}>
        {steps.map((_, i) => <div key={i} style={{ width: i === cur ? 56 : 18, height: 18, borderRadius: 18, background: i <= cur ? INK : PALE }} />)}
      </div>
    </FadeScene>
  );
};

// ---- 5. Модель қалай жұмыс істейді ----
const How: React.FC = () => {
  const f = useCurrentFrame();
  const reveal = interpolate(f, [120, 170], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const bars: [string, number, string][] = [["Қоңыр тат", 82, RUST], ["Масақ фузариозы", 5, PALE], ["Ақ ұнтақ ауруы", 5, PALE]];
  return (
    <FadeScene len={LEN.how}>
      <div style={{ position: "absolute", left: 120, top: 90 }}><Up><div style={{ fontSize: 60, fontWeight: 700 }}>Модель қалай шешеді</div></Up></div>
      {/* фото */}
      <div style={{ position: "absolute", left: 120, top: 300, width: 560 }}>
        <Up delay={8}><Img src={staticFile("img/leaf_raw.jpg")} style={{ width: 560, borderRadius: 18, border: `2px solid ${INK}` }} /></Up>
        <Up delay={14}><div style={{ fontSize: 28, color: MUTED, marginTop: 16 }}>Фото</div></Up>
      </div>
      {/* нейрожелі қабаттары */}
      <div style={{ position: "absolute", left: 760, top: 280, width: 360, display: "flex", gap: 14, alignItems: "center", height: 300 }}>
        {[260, 220, 180, 140, 100].map((h, i) => {
          const on = interpolate(f, [30 + i * 14, 42 + i * 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return <div key={i} style={{ width: 52, height: h, borderRadius: 10, border: `2px solid ${INK}`, background: on > 0.5 ? (i === 4 ? WHEAT : LEAF) : FIELD, opacity: 0.4 + on * 0.6 }} />;
        })}
      </div>
      <div style={{ position: "absolute", left: 760, top: 610 }}><Up delay={30}><div style={{ fontSize: 28, color: MUTED }}>EfficientNet-B0 · 57 мс</div></Up></div>
      {/* жылу картасы */}
      <div style={{ position: "absolute", left: 1200, top: 300, width: 600 }}>
        <div style={{ position: "relative", width: 600 }}>
          <Img src={staticFile("img/leaf_raw.jpg")} style={{ width: 600, borderRadius: 18, border: `2px solid ${INK}`, display: "block", opacity: f > 100 ? 1 : 0 }} />
          <Img src={staticFile("img/leaf_cam.jpg")} style={{ position: "absolute", inset: 0, width: 600, borderRadius: 18, clipPath: `inset(0 ${100 - reveal}% 0 0)` }} />
        </div>
        <Up delay={110}><div style={{ fontSize: 28, color: MUTED, marginTop: 16 }}>Белгілер аймағы (CAM)</div></Up>
      </div>
      {/* ықтималдықтар */}
      <div style={{ position: "absolute", left: 1200, top: 640, width: 600 }}>
        {bars.map(([n, v, c], i) => {
          const w = interpolate(f, [180 + i * 8, 215 + i * 8], [0, v], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
          return (
            <div key={n} style={{ marginBottom: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 28, fontWeight: i === 0 ? 700 : 400 }}><span>{n}</span><span>{Math.round(w)}%</span></div>
              <div style={{ height: 20, background: FIELD, borderRadius: 10, marginTop: 6 }}><div style={{ width: `${w}%`, height: 20, background: c, borderRadius: 10 }} /></div>
            </div>
          );
        })}
      </div>
    </FadeScene>
  );
};

// ---- 6. Нәтижелер ----
const Results: React.FC = () => {
  const f = useCurrentFrame();
  const big: [number, string, string][] = [[97.1, "дәлдік", WHEAT], [96.7, "macro-F1", WHITE], [98.4, "сенімді жауаптарда", WHITE]];
  const f1: [string, number][] = [["Сары тат", 100], ["Масақ фузариозы", 99], ["Қоңыр тат", 97], ["Сау жапырақ", 97], ["Сау масақ", 96], ["Ақ ұнтақ ауруы", 96], ["Масақ септориозы", 92]];
  return (
    <FadeScene len={LEN.results} bg={INK}>
      <div style={{ position: "absolute", left: 120, top: 90 }}><Up><div style={{ fontSize: 60, fontWeight: 700, color: WHITE }}>Модель көрмеген 580 суретте</div></Up></div>
      {big.map(([v, l, c], i) => (
        <div key={l} style={{ position: "absolute", left: 120, top: 250 + i * 230 }}>
          <div style={{ fontSize: 130, fontWeight: 700, color: c, lineHeight: 1 }}><Counter to={v} delay={10 + i * 12} dur={45} suffix="%" /></div>
          <Up delay={20 + i * 12}><div style={{ fontSize: 30, color: PALE }}>{l}</div></Up>
        </div>
      ))}
      <div style={{ position: "absolute", left: 900, top: 260, width: 900 }}>
        <Up delay={20}><div style={{ fontSize: 30, color: PALE, marginBottom: 24 }}>Әр класс бойынша F1, %</div></Up>
        {f1.map(([n, v], i) => {
          const w = interpolate(f, [40 + i * 6, 80 + i * 6], [0, v], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
          return (
            <div key={n} style={{ display: "flex", alignItems: "center", height: 80 }}>
              <div style={{ width: 300, fontSize: 28, color: WHITE, textAlign: "right", paddingRight: 24 }}>{n}</div>
              <div style={{ width: 480, height: 44, background: "#2c3d31", borderRadius: 10 }}><div style={{ width: `${w}%`, height: 44, background: i === 6 ? WHEAT : "#5FA36A", borderRadius: 10 }} /></div>
              <div style={{ width: 80, fontSize: 30, fontWeight: 700, color: WHITE, paddingLeft: 18 }}>{Math.round(w)}</div>
            </div>
          );
        })}
      </div>
    </FadeScene>
  );
};

// ---- 7. Дрон ----
const Clip: React.FC<{ src: string; len: number; dim?: number }> = ({ src, len, dim = 0 }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 8, len - 8, len], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <OffthreadVideo src={staticFile(src)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      {dim > 0 && <AbsoluteFill style={{ background: INK, opacity: dim }} />}
    </AbsoluteFill>
  );
};
const Lower: React.FC<{ kicker?: string; text: string; delay?: number }> = ({ kicker, text, delay = 6 }) => {
  const p = useSp(delay);
  return (
    <div style={{ position: "absolute", left: 100, bottom: 90, background: INK, borderRadius: 20, padding: "28px 40px", maxWidth: 1300,
      transform: `translateX(${(1 - p) * -200}px)`, opacity: p, fontFamily: FONT }}>
      {kicker && <div style={{ fontSize: 28, fontWeight: 600, color: WHEAT, marginBottom: 8 }}>{kicker}</div>}
      <div style={{ fontSize: 52, fontWeight: 700, color: WHITE, lineHeight: 1.15 }}>{text}</div>
    </div>
  );
};
const HOTS = [[420, 300, 40], [1120, 260, 46], [760, 560, 34], [1300, 700, 44], [360, 820, 30]] as const;
const Survey: React.FC<{ len: number }> = ({ len }) => {
  const f = useCurrentFrame();
  const X0 = 140, X1 = 1500, Y0 = 120, Y1 = 960, FW = 210, FH = 160;
  const nL = 6;
  const lanes = Array.from({ length: nL }, (_, k) => Y0 + FH / 2 + ((Y1 - Y0 - FH) * k) / (nL - 1));
  const pts: [number, number][] = [];
  lanes.forEach((y, k) => { const a = X0 + FW / 2, b = X1 - FW / 2; pts.push(k % 2 ? [b, y] : [a, y], k % 2 ? [a, y] : [b, y]); });
  const segs = pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
  const total = segs.reduce((a, b) => a + b, 0);
  const prog = interpolate(f, [15, len - 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  let d = prog * total, x = pts[0][0], y = pts[0][1];
  for (let i = 0; i < segs.length; i++) {
    if (d <= segs[i]) { const r = d / segs[i]; x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * r; y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * r; break; }
    d -= segs[i]; x = pts[i + 1][0]; y = pts[i + 1][1];
  }
  const path = "M " + pts.map((p) => p.join(" ")).join(" L ");
  // ошақ табылды ма: дрон оның жолағынан өтті ме
  const seen = (hx: number, hy: number) => {
    const lane = lanes.findIndex((ly) => Math.abs(ly - hy) <= FH / 2 + 10);
    const passedLanes = Math.floor((prog * total) / ((X1 - X0 - FW) + (lanes[1] - lanes[0])));
    if (lane < passedLanes) return true;
    if (lane > passedLanes) return false;
    const forward = lane % 2 === 0;
    return forward ? x >= hx - FW / 2 : x <= hx + FW / 2;
  };
  const found = HOTS.filter(([hx, hy]) => seen(hx, hy)).length;
  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        <rect x={X0} y={Y0} width={X1 - X0} height={Y1 - Y0} fill="none" stroke={WHITE} strokeWidth={4} strokeDasharray="14 10" />
        <path d={path} fill="none" stroke={WHITE} strokeWidth={3} strokeOpacity={0.9} strokeDasharray={total} strokeDashoffset={total * (1 - prog)} />
        {HOTS.map(([hx, hy, r], i) => seen(hx, hy) && (
          <g key={i}>
            <circle cx={hx} cy={hy} r={r} fill={RUST} fillOpacity={0.75} />
            <rect x={hx - r - 12} y={hy - r - 12} width={2 * r + 24} height={2 * r + 24} fill="none" stroke={RUST} strokeWidth={5} />
          </g>
        ))}
        <rect x={x - FW / 2} y={y - FH / 2} width={FW} height={FH} fill={WHITE} fillOpacity={0.15} stroke={WHEAT} strokeWidth={5} />
        <g transform={`translate(${x} ${y})`}>
          {[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([dx, dy], i) => (
            <g key={i}>
              <line x1={0} y1={0} x2={dx * 30} y2={dy * 30} stroke={INK} strokeWidth={7} />
              <circle cx={dx * 30} cy={dy * 30} r={19} fill={PALE} stroke={INK} strokeWidth={3} />
              <line x1={dx * 30 - 16 * Math.cos(f)} y1={dy * 30 - 16 * Math.sin(f)} x2={dx * 30 + 16 * Math.cos(f)} y2={dy * 30 + 16 * Math.sin(f)} stroke={INK} strokeWidth={3} />
            </g>
          ))}
          <rect x={-18} y={-18} width={36} height={36} rx={8} fill={WHEAT} stroke={INK} strokeWidth={3} />
        </g>
      </svg>
      <div style={{ position: "absolute", right: 60, top: 120, width: 340, background: INK, borderRadius: 20, padding: 32, fontFamily: FONT, color: WHITE }}>
        <div style={{ fontSize: 30, fontWeight: 700 }}>Шолу ұшуы</div>
        <div style={{ fontSize: 24, color: PALE, marginTop: 10, lineHeight: 1.5 }}>Биіктік 100 м<br />Маршрут: ары-бері<br />Қабаттасу 70%</div>
        <div style={{ fontSize: 56, fontWeight: 700, color: WHITE, marginTop: 24 }}>{Math.round(prog * 100)}%</div>
        <div style={{ fontSize: 24, color: PALE }}>шолынды</div>
        <div style={{ fontSize: 56, fontWeight: 700, color: WHEAT, marginTop: 16 }}>{found}</div>
        <div style={{ fontSize: 24, color: PALE }}>ошақ табылды</div>
      </div>
    </AbsoluteFill>
  );
};
const DroneStats: React.FC = () => {
  const items: [React.ReactNode, string, string][] = [
    [<><Counter to={21.1} delay={10} />{" ц/га"}</>, "өнімділік болжамы (масақ санау)", WHITE],
    [<><Counter to={30} d={0} delay={20} />{" га"}</>, "ауру ошағы (алқаптың 6%)", WHEAT],
    [<><Counter to={9.5} delay={30} />{" т"}</>, "өңделмесе шығын ≈ 855 мың ₸", WHEAT],
    [<>−<Counter to={91} d={0} delay={40} />%</>, "фунгицид: тек 45 га шашыратылады", WHITE],
  ];
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 120, top: 100 }}><Up><div style={{ fontSize: 56, fontWeight: 700, color: WHITE }}>500 га алқап мысалы</div></Up></div>
      <div style={{ position: "absolute", left: 120, top: 260, display: "grid", gridTemplateColumns: "820px 820px", rowGap: 70 }}>
        {items.map(([n, l, c], i) => (
          <Up key={i} delay={8 + i * 10}>
            <div style={{ fontSize: 120, fontWeight: 700, color: c, lineHeight: 1 }}>{n}</div>
            <div style={{ fontSize: 30, color: PALE, marginTop: 10 }}>{l}</div>
          </Up>
        ))}
      </div>
      <div style={{ position: "absolute", left: 120, bottom: 60, fontSize: 20, color: PALE }}>Есеп: drone/calc.py. Болжам: бидай 90 000 ₸/т, өңдеу 10 000 ₸/га. Дрон кадрлары — көрсетілім үшін (DJI Mavic 3M, ашық видео).</div>
    </AbsoluteFill>
  );
};
const DRONE = [["wide", s(4)], ["scan", s(5)], ["survey", s(10)], ["layers", s(4)], ["stats", s(5)]] as const;
const Drone: React.FC = () => {
  let a = 0;
  const at: Record<string, [number, number]> = {};
  for (const [n, d] of DRONE) { at[n] = [a, d]; a += d; }
  return (
    <AbsoluteFill style={{ background: INK, fontFamily: FONT }}>
      <Sequence from={at.wide[0]} durationInFrames={at.wide[1]}><Clip src="clips/drone_wide.mp4" len={at.wide[1]} /><Lower kicker="2-кезең" text="Дрон ірі алқапты тексереді" /></Sequence>
      <Sequence from={at.scan[0]} durationInFrames={at.scan[1]}><Clip src="clips/drone_scan.mp4" len={at.scan[1]} /><Lower text="100 м биіктіктен бүкіл алқапты шолады" /></Sequence>
      <Sequence from={at.survey[0]} durationInFrames={at.survey[1]}><Clip src="clips/field_topdown.mp4" len={at.survey[1]} dim={0.15} /><Survey len={at.survey[1]} /></Sequence>
      <Sequence from={at.layers[0]} durationInFrames={at.layers[1]}><Clip src="clips/drone_layers.mp4" len={at.layers[1]} /><Lower text="Ошақтарды 25 м-ден нақтылайды, EginAI ауру түрін анықтайды" /></Sequence>
      <Sequence from={at.stats[0]} durationInFrames={at.stats[1]}><Clip src="clips/drone_ndvi.mp4" len={at.stats[1]} dim={0.9} /><DroneStats /></Sequence>
    </AbsoluteFill>
  );
};

// ---- 8. Іске қосу ----
const Launch: React.FC = () => {
  const f = useCurrentFrame();
  const cmd = "docker compose up";
  const typed = cmd.slice(0, Math.max(0, Math.floor((f - 12) / 2)));
  const lines: [string, string][] = [["✓ db", "healthy"], ["✓ api", "EginAI ready: 7 classes"], ["→", "http://localhost:8000"]];
  return (
    <FadeScene len={LEN.launch} bg={INK}>
      <div style={{ position: "absolute", left: 120, top: 100 }}><Up><div style={{ fontSize: 60, fontWeight: 700, color: WHITE }}>Жюри компьютерінде — бір команда</div></Up></div>
      <div style={{ position: "absolute", left: 120, top: 250, width: 1050, height: 520, background: "#0F1912", borderRadius: 24, border: `2px solid ${WHEAT}`, padding: 48, fontFamily: "monospace" }}>
        <div style={{ fontSize: 46, color: WHEAT }}>$ {typed}<span style={{ opacity: f % 30 < 15 ? 1 : 0 }}>▌</span></div>
        {lines.map(([a, b], i) => {
          const o = interpolate(f, [60 + i * 14, 66 + i * 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return <div key={i} style={{ fontSize: 38, color: i === 2 ? WHITE : "#7FBF7F", marginTop: 34, opacity: o }}>{a}  {b}</div>;
        })}
      </div>
      <div style={{ position: "absolute", left: 1260, top: 270, width: 560 }}>
        {["Фото сақталмайды", "Кілт қажет емес", "52 автотест", "Код ашық — MIT"].map((t, i) => (
          <div key={t} style={{ display: "flex", alignItems: "center", gap: 22, marginBottom: 44 }}>
            <Badge n="✓" delay={20 + i * 10} size={56} />
            <Up delay={22 + i * 10} dist={20}><div style={{ fontSize: 38, color: WHITE }}>{t}</div></Up>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 120, top: 840 }}><Up delay={90}><div style={{ fontSize: 40, fontWeight: 600, color: WHEAT }}>github.com/raissov01/eginai</div></Up></div>
    </FadeScene>
  );
};

// ---- 9. Команда ----
const Outro: React.FC = () => {
  const f = useCurrentFrame();
  const zoom = interpolate(f, [0, LEN.outro], [1.0, 1.1]);
  const team: [string, string][] = [["Әбдімүтәлі Бекназар", "капитан, архитектура"], ["Әбдіқадыр Ернұр", "модель және деректер"], ["Есен Арман", "сервер және бот"], ["Жақсығұл Рамазан", "интерфейс және карта"]];
  return (
    <FadeScene len={LEN.outro} bg={INK}>
      <AbsoluteFill><Img src={staticFile("img/field_wide.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} /></AbsoluteFill>
      <AbsoluteFill style={{ background: INK, opacity: 0.82 }} />
      <div style={{ position: "absolute", left: 120, top: 110, display: "flex", alignItems: "center", gap: 28 }}>
        <Up><Logo size={90} /></Up><Up delay={6}><div style={{ fontSize: 80, fontWeight: 700, color: WHITE }}>EginAI</div></Up>
      </div>
      <div style={{ position: "absolute", left: 120, top: 320, display: "grid", gridTemplateColumns: "820px 820px", rowGap: 60 }}>
        {team.map(([n, r], i) => (
          <Up key={n} delay={14 + i * 8}>
            <div style={{ fontSize: 50, fontWeight: 600, color: WHEAT }}>{n}</div>
            <div style={{ fontSize: 30, color: WHITE, marginTop: 6 }}>{r}</div>
          </Up>
        ))}
      </div>
      <div style={{ position: "absolute", left: 120, top: 830 }}><Up delay={60}><div style={{ fontSize: 30, color: PALE }}>Ғылыми жетекші: Таберхан Роман</div></Up></div>
      <div style={{ position: "absolute", right: 120, top: 880 }}><Up delay={70}><div style={{ fontSize: 60, fontWeight: 700, color: WHITE }}>Рақмет!</div></Up></div>
    </FadeScene>
  );
};

const COMP: Record<string, React.FC> = { intro: Intro, problem: Problem, analogs: Analogs, demo: Demo, how: How, results: Results, drone: Drone, launch: Launch, outro: Outro };

export const Video: React.FC = () => (
  <AbsoluteFill style={{ background: INK }}>
    {SCENES.map(([n, d]) => {
      const C = COMP[n];
      return <Sequence key={n} from={START[n]} durationInFrames={d} premountFor={30}><C /></Sequence>;
    })}
    <Audio src={staticFile("music.wav")} volume={(f) => interpolate(f, [0, 20, TOTAL - 45, TOTAL], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
  </AbsoluteFill>
);

export const SCENE_TIMES = { START, LEN };
