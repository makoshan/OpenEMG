'use client';
// 鼠标八类「手势控制台」（design/emg-console-v4/magic.html，A 控制器 · 魔法手帐）。
// 识别、边沿触发、执行在 meta-live.tsx；这里只把真实事件演出来：一次触发 → 键帽 / 魔法阵 / 光迹 / 读数 / 光标，
// 实时肌电幅度 → 手的光晕，st.wl8.ai → AI 请求卡（召唤、倒计时、结果章）。没发生的事不演。
import { useEffect, useMemo, useRef, useState, type MutableRefObject } from 'react';
import type { AiRequest } from './contract';
import { mousePreset } from './gesture-actions';
import { magic, RGB } from './magic';
import { grayTitle } from './gray-title';
import { RealHand } from './meta-guide';
import POSES from './meta-hand-poses.json';
import './magic.css';

export type Fired = { id: number; label: string; ok: boolean; skipped?: string; latency?: number | null };
type Pose = Record<string, { pts: number[][]; depth: number }>;
const HAND = POSES as unknown as Record<'index' | 'middle', { open: Pose; contact: Pose }>;

const KEY: Record<string, { icon: string; name: string; rgb: string; color: string }> = {
  mouse_up: { icon: 'M12 19V5M6 11l6-6 6 6', name: '上滑', rgb: RGB.sky, color: 'var(--mg-sky)' },
  mouse_down: { icon: 'M12 5v14M6 13l6 6 6-6', name: '下滑', rgb: RGB.sky, color: 'var(--mg-sky)' },
  mouse_left: { icon: 'M19 12H5M11 6l-6 6 6 6', name: '左滑', rgb: RGB.sky, color: 'var(--mg-sky)' },
  mouse_right: { icon: 'M5 12h14M13 6l6 6-6 6', name: '右滑', rgb: RGB.sky, color: 'var(--mg-sky)' },
  mouse_index: { icon: 'M8 21v-6.5c0-1 .6-1.6 1.4-1.6.8 0 1.4.6 1.4 1.6V6.8c0-1 .6-1.6 1.4-1.6s1.4.6 1.4 1.6V13M17.5 3.8a2.2 2.2 0 1 1 0 4.4 2.2 2.2 0 0 1 0-4.4', name: '食指捏', rgb: RGB.mint, color: 'var(--mg-mint)' },
  mouse_middle: { icon: 'M7 21v-6c0-1 .6-1.6 1.4-1.6.8 0 1.4.6 1.4 1.6V5.6c0-1 .6-1.6 1.4-1.6s1.4.6 1.4 1.6V12M12.8 6.4c0-1 .6-1.6 1.4-1.6s1.4.6 1.4 1.6V13M19 5.8a2.2 2.2 0 1 1 0 4.4 2.2 2.2 0 0 1 0-4.4', name: '中指捏', rgb: RGB.sakura, color: 'var(--mg-sakura)' },
  mouse_side: { icon: 'M5 16c3-6 8-8 14-7M15 5c3 1.6 4.4 4 4 7', name: '侧点', rgb: RGB.lilac, color: 'var(--mg-lilac)' },
  mouse_rest: { icon: 'M12 4a8 8 0 1 1 0 16 8 8 0 0 1 0-16M8.5 14.5c2 2 5 2 7 0M9 10h.01M15 10h.01', name: '放松', rgb: RGB.gold, color: 'var(--mg-gold)' },
};

/** AI 卡显示什么：钩子的状态 + 本机时钟（秒）。超时 = 拒绝且原因里写着没等到 / 超时 */
export function aiView(ai: AiRequest | undefined, nowSec: number) {
  if (!ai || ai.state === 'idle') return { kind: 'idle' as const, left: 0 };
  if (ai.state === 'pending') return { kind: 'pending' as const, left: Math.max(0, (ai.deadline ?? nowSec) - nowSec), total: Math.max(1, (ai.deadline ?? 0) - (ai.started ?? 0)) };
  const timeout = ai.decision === 'deny' && /没等到|超时|没回报/.test(ai.reason ?? '');
  return { kind: timeout ? 'timeout' as const : ai.decision === 'allow' ? 'allow' as const : 'deny' as const, left: 0, ms: ai.ms ?? null };
}

/** 拇指尖在屏幕上的位置：viewBox 60 20 260 290、meet 居中 */
function tipOnScreen(svg: SVGSVGElement | null, finger: 'index' | 'middle', amount: number) {
  if (!svg) return null;
  const b = svg.getBoundingClientRect(), s = Math.min(b.width / 260, b.height / 290), ox = b.left + (b.width - 260 * s) / 2, oy = b.top + (b.height - 290 * s) / 2;
  const o = HAND[finger].open.thumb.pts.at(-1)!, c = HAND[finger].contact.thumb.pts.at(-1)!;
  return [ox + (o[0] + (c[0] - o[0]) * amount - 60) * s, oy + (o[1] + (c[1] - o[1]) * amount - 20) * s] as const;
}
const center = (el: Element | null) => { if (!el) return null; const b = el.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2] as const; };

function Key({ label, text, dim, refs }: { label: string; text?: string; dim?: boolean; refs: MutableRefObject<Record<string, HTMLDivElement | null>> }) {
  const k = KEY[label];
  return <div ref={(el) => { refs.current[label] = el; }} className={`mg-key ${dim ? 'dim' : ''}`} style={{ ['--c' as string]: k.color }} data-k={label}>
    <svg viewBox="0 0 24 24" aria-hidden><path d={k.icon} /></svg><b>{k.name}</b><small>{text}</small></div>;
}
function glowKey(el: HTMLDivElement | null, rgb: string) {
  if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  el.animate([{ transform: 'scale(1)' }, { transform: 'scale(.93)', offset: .18 }, { transform: 'scale(1.07)', offset: .5 }, { transform: 'scale(1)' }], { duration: 560, easing: 'cubic-bezier(.34,1.56,.64,1)' });
  el.animate([{ boxShadow: `0 0 0 0 rgba(${rgb},0)` }, { boxShadow: `0 0 0 6px rgba(${rgb},.25),0 0 30px 6px rgba(${rgb},.6)`, offset: .3 }, { boxShadow: `0 0 0 16px rgba(${rgb},0)` }], { duration: 900, easing: 'ease-out', composite: 'add' });
  el.classList.remove('shine'); void el.offsetWidth; el.classList.add('shine');
}

export function MouseConsole({ fired, output, onOutput, ready, conf, step, onStep, latency, ai, envelope, events }: {
  fired: Fired | null; output: boolean; onOutput: (on: boolean) => void; ready: boolean; conf: number; step: number; onStep: (n: number) => void;
  latency: number | null; ai?: AiRequest; envelope?: () => number; events: { id: number; t: string; text: string; ok: boolean }[];
}) {
  const preset = useMemo(() => mousePreset(step), [step]);
  const keys = useRef<Record<string, HTMLDivElement | null>>({});
  const aiKeys = useRef<Record<string, HTMLDivElement | null>>({});
  const handRef = useRef<SVGSVGElement>(null), auraRef = useRef<HTMLDivElement>(null), wordRef = useRef<HTMLDivElement>(null);
  const screenRef = useRef<HTMLDivElement>(null), cursorRef = useRef<SVGSVGElement>(null), trailRef = useRef<HTMLCanvasElement>(null), cardRef = useRef<HTMLDivElement>(null), sealRef = useRef<HTMLDivElement>(null);
  const [hand, setHand] = useState<{ finger: 'index' | 'middle'; amount: number }>({ finger: 'index', amount: 0 });
  const [word, setWord] = useState({ main: '放松', why: '等你做动作' });
  const [now, setNow] = useState(() => Date.now() / 1000);

  useEffect(() => { const off = magic.mount(); return off; }, []);
  useEffect(() => { magic.setAmbient(ready); return () => magic.setAmbient(false); }, [ready]);

  // 手的光晕 = 实时肌电幅度（studio 最近一批显示滤波帧的平均幅度），每帧读一次
  useEffect(() => {
    if (!envelope) return; let raf = 0, smooth = 0;
    const tick = () => { smooth += (Math.min(1, envelope() * 1.6) - smooth) * .15; auraRef.current?.style.setProperty('--aura', smooth.toFixed(3)); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [envelope]);

  // 指针表：真弹簧（k=170、阻尼 13，一次过冲），目标 = 当前置信度
  const needle = useRef({ x: 0, v: 0, raf: 0 });
  const gaugeRef = useRef<SVGGElement>(null), arcRef = useRef<SVGPathElement>(null);
  useEffect(() => {
    const n = needle.current; cancelAnimationFrame(n.raf); let last = performance.now();
    const step = (t: number) => { const dt = Math.min(.032, (t - last) / 1000); last = t; n.v += (-170 * (n.x - conf) - 13 * n.v) * dt; n.x += n.v * dt;
      const x = Math.max(-.02, Math.min(1.02, n.x)); gaugeRef.current?.setAttribute('transform', `rotate(${-90 + 180 * x} 115 118)`); arcRef.current?.setAttribute('stroke-dasharray', `${Math.max(0, x) * 100} 100`);
      if (Math.abs(n.v) + Math.abs(n.x - conf) > .002) n.raf = requestAnimationFrame(step); };
    n.raf = requestAnimationFrame(step); return () => cancelAnimationFrame(n.raf);
  }, [conf]);

  // 光标小屏：弹簧移动 + 紫色彗尾；只在服务端回执成功后动
  const cur = useRef({ x: .5, y: .5, tx: .5, ty: .5, vx: 0, vy: 0, trail: [] as [number, number, number][], raf: 0 });
  const moveCursor = (dx: number, dy: number) => {
    const c = cur.current; c.tx = Math.max(.06, Math.min(.92, c.tx + dx / 600)); c.ty = Math.max(.12, Math.min(.86, c.ty + dy / 420)); cancelAnimationFrame(c.raf); let last = performance.now();
    const step = (t: number) => { const dt = Math.min(.032, (t - last) / 1000); last = t;
      c.vx += (-140 * (c.x - c.tx) - 17 * c.vx) * dt; c.x += c.vx * dt; c.vy += (-140 * (c.y - c.ty) - 17 * c.vy) * dt; c.y += c.vy * dt;
      if (cursorRef.current) { cursorRef.current.style.left = `${c.x * 100}%`; cursorRef.current.style.top = `${c.y * 100}%`; }
      c.trail.push([c.x, c.y, t]); c.trail = c.trail.filter((p) => t - p[2] < 900);
      const cv = trailRef.current, g = cv?.getContext('2d');
      if (cv && g) { const W = cv.clientWidth, H = cv.clientHeight; if (cv.width !== W * 2) { cv.width = W * 2; cv.height = H * 2; } g.setTransform(2, 0, 0, 2, 0, 0); g.clearRect(0, 0, W, H); g.lineCap = 'round';
        for (let k = 1; k < c.trail.length; k++) { const a = 1 - (t - c.trail[k][2]) / 900; g.strokeStyle = `rgba(${RGB.lilac},${a * .75})`; g.lineWidth = 1 + a * 5; g.beginPath(); g.moveTo(c.trail[k - 1][0] * W, c.trail[k - 1][1] * H); g.lineTo(c.trail[k][0] * W, c.trail[k][1] * H); g.stroke(); }
        if (Math.random() < .25) { const b = cv.getBoundingClientRect(); magic.spark(b.left + c.x * b.width, b.top + c.y * b.height, RGB.lilac, 1, .8); } }
      if (Math.abs(c.vx) + Math.abs(c.vy) + Math.abs(c.x - c.tx) + Math.abs(c.y - c.ty) > .001 || c.trail.length) c.raf = requestAnimationFrame(step); };
    c.raf = requestAnimationFrame(step);
  };
  const clickCursor = (right: boolean) => {
    const s = screenRef.current; if (!s) return; const c = cur.current, rgb = right ? RGB.sakura : RGB.mint;
    for (const d of [0, 130]) { const r = document.createElement('i'); r.className = 'mg-ring'; r.style.cssText = `left:${c.x * 100}%;top:${c.y * 100}%;border-color:rgba(${rgb},.9);box-shadow:0 0 12px rgba(${rgb},.7)`; s.appendChild(r);
      r.animate([{ transform: 'scale(.2)', opacity: 1 }, { transform: 'scale(2.8)', opacity: 0 }], { duration: 640, delay: d, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'both' }).onfinish = () => r.remove(); }
    const b = s.getBoundingClientRect(); magic.spark(b.left + c.x * b.width, b.top + c.y * b.height, rgb, 10, 2);
  };

  // 一次触发：手做动作 → 指尖魔法阵 → 光迹飞向键帽 → 键帽发光 → 读数切换 → （执行成功）光标动
  useEffect(() => {
    if (!fired) return; const k = KEY[fired.label], act = preset[fired.label]; if (!k || !act) return;
    const finger = fired.label === 'mouse_middle' ? 'middle' : 'index';
    if (fired.label === 'mouse_index' || fired.label === 'mouse_middle') {
      const t0 = performance.now(); let raf = 0; const IN = 180, HOLD = 120, OUT = 300;
      const step = (t: number) => { const e = t - t0; setHand({ finger, amount: e < IN ? e / IN : e < IN + HOLD ? 1 : Math.max(0, 1 - (e - IN - HOLD) / OUT) }); if (e < IN + HOLD + OUT) raf = requestAnimationFrame(step); };
      raf = requestAnimationFrame(step); setTimeout(() => cancelAnimationFrame(raf), 1200);
    }
    const tip = tipOnScreen(handRef.current, finger, 1), to = center(keys.current[fired.label]);
    if (tip) magic.sigil(tip[0], tip[1], k.rgb, 30, 800);
    if (tip && to && !fired.skipped) magic.comet(tip[0], tip[1], to[0], to[1], k.rgb);
    setTimeout(() => glowKey(keys.current[fired.label], fired.skipped ? RGB.gold : k.rgb), fired.skipped ? 0 : 420);
    // 光迹打中键帽的一刻（460ms）= 识别成功：键帽和读数各亮一团光晕，读数柔和浮现
    const HIT = fired.skipped ? 0 : 460, w = wordRef.current;
    w?.animate([{ filter: 'blur(0)', opacity: 1, transform: 'none' }, { filter: 'blur(8px)', opacity: 0, transform: 'translateY(-10px) scale(.96)' }], { duration: 160, delay: Math.max(0, HIT - 160), easing: 'ease-in', fill: 'forwards' }).finished.then(() => {
      setWord({ main: k.name, why: fired.skipped ? `没执行：${fired.skipped}` : output && fired.ok ? act.text : '演练，没动鼠标' });
      w.animate(fired.skipped ? [{ filter: 'blur(10px)', opacity: 0, transform: 'translateY(12px)' }, { filter: 'blur(0)', opacity: 1, transform: 'none' }]
        : [{ filter: 'blur(10px)', opacity: 0, transform: 'scale(1.08)' }, { filter: 'blur(0)', opacity: 1, transform: 'none' }],
        { duration: 420, easing: 'cubic-bezier(.22,1,.36,1)' });
      if (fired.skipped) return;
      const wc = center(w); if (wc) magic.burst(wc[0], wc[1], k.rgb, .7);
      if (to) magic.burst(to[0], to[1], k.rgb, 1);
    }).catch(() => {});
    if (output && fired.ok && !fired.skipped) setTimeout(() => (act.kind === 'move' ? moveCursor(act.dx ?? 0, act.dy ?? 0) : act.kind !== 'none' && clickCursor(act.kind === 'right_click')), 480);
  }, [fired?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // AI 请求：召唤（魔法阵 + 光点聚拢 + 卡片从光里浮现）→ 倒计时 → 结果章
  const view = aiView(ai, now);
  useEffect(() => { if (view.kind !== 'pending') return; let raf = 0; const tick = () => { setNow(Date.now() / 1000); raf = requestAnimationFrame(tick); }; raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf); }, [view.kind, ai?.seq]);
  const seenSeq = useRef<string>('');
  useEffect(() => {
    if (!ai || ai.state === 'idle') return; const tag = `${ai.seq}:${ai.state}`; if (seenSeq.current === tag) return; seenSeq.current = tag;
    const c = center(cardRef.current);
    if (ai.state === 'pending') {
      if (c) { magic.sigil(c[0], c[1] - 30, RGB.lilac, 70, 1100); magic.implode(c[0], c[1] - 30, RGB.lilac, 30, 180); }
      cardRef.current?.animate([{ opacity: .3, filter: 'blur(10px)', transform: 'scale(.94) translateY(10px)' }, { opacity: 1, filter: 'blur(0)', transform: 'none' }], { duration: 700, delay: 250, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'backwards' });
      return;
    }
    const v = aiView(ai, Date.now() / 1000), sealC = center(sealRef.current);
    const pressed = v.kind === 'allow' ? aiKeys.current.mouse_index : v.kind === 'deny' ? aiKeys.current.mouse_middle : null;
    const tip = tipOnScreen(handRef.current, v.kind === 'deny' ? 'middle' : 'index', 1), to = center(pressed);
    if (tip && to) magic.comet(tip[0], tip[1], to[0], to[1], v.kind === 'allow' ? RGB.mint : RGB.sakura);
    setTimeout(() => {
      glowKey(pressed, v.kind === 'allow' ? RGB.mint : RGB.sakura);
      sealRef.current?.animate([{ transform: 'scale(2) rotate(-30deg)', opacity: 0, filter: 'blur(6px)' }, { transform: 'scale(.92) rotate(4deg)', opacity: 1, filter: 'blur(0)', offset: .6 }, { transform: 'none', opacity: 1 }], { duration: 620, easing: 'cubic-bezier(.2,.8,.2,1)', fill: 'both' });
      cardRef.current?.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.015)' }, { transform: 'scale(1)' }], { duration: 320, delay: 360 });
      setTimeout(() => { if (!sealC) return; if (v.kind === 'allow') { magic.burst(sealC[0], sealC[1], RGB.mint, 1.3); magic.rise(sealC[0], sealC[1], RGB.gold, 28); magic.wave(sealC[0], sealC[1], RGB.gold, 140); magic.spark(sealC[0], sealC[1], RGB.mint, 20, 3.4); }
        else { if (v.kind === 'deny') magic.burst(sealC[0], sealC[1], RGB.sakura, .8); magic.spark(sealC[0], sealC[1], v.kind === 'deny' ? RGB.sakura : RGB.grey, 22, 4.2); magic.wave(sealC[0], sealC[1], v.kind === 'deny' ? RGB.sakura : RGB.grey, 90); } }, 360);
    }, 460);
  }, [ai?.seq, ai?.state]); // eslint-disable-line react-hooks/exhaustive-deps

  const pad = ['', 'mouse_up', '', 'mouse_left', 'mouse_rest', 'mouse_right', '', 'mouse_down', ''];
  const live = output && ready;
  return <div className="mg-console">
    <section className="mg-card mg-keys">
      <div className="mg-cap">十字键 · 拇指滑</div>
      <div className="mg-pad">{pad.map((l, i) => l ? <Key key={l} label={l} refs={keys} text={l === 'mouse_rest' ? '上膛' : preset[l]?.text.replace('光标', '')} /> : <span key={i} />)}</div>
      <div className="mg-cap">按键 · 捏合</div>
      <div className="mg-btns">{['mouse_index', 'mouse_middle', 'mouse_side'].map((l) => <Key key={l} label={l} refs={keys} dim={preset[l]?.kind === 'none'} text={preset[l]?.kind === 'none' ? '未绑定' : preset[l]?.text.replace('单击', '')} />)}</div>
    </section>

    <section className="mg-card mg-main">
      <header className="mg-row">
        <button className={`mg-switch ${live ? 'on' : ''}`} disabled={!ready} title={grayTitle(!ready && '识别没在线，开不了')} aria-pressed={live} onClick={() => { const on = !output; onOutput(on); const b = center(document.querySelector('.mg-switch .rail')); if (on && b) magic.spark(b[0] + 12, b[1], RGB.mint, 12, 2.2); }}>
          <span className="rail"><span className="knob" /></span><span><b>{live ? '正在控制真鼠标' : '演练'}</b><small>{!ready ? '识别没在线，开不了' : live ? '识别到的动作会真的点 / 挪鼠标' : '只看识别结果，鼠标不动'}</small></span></button>
        <label className="mg-step">每次挪<select value={step} onChange={(e) => onStep(Number(e.target.value))}>{[60, 120, 240].map((v) => <option key={v} value={v}>{v} 像素</option>)}</select></label>
        <div className="mg-lat"><small>识别到执行</small><b>{latency ?? '—'}</b><small>ms</small></div>
      </header>
      {fired?.skipped && <div className="mg-banner warn" key={fired.id}>{KEY[fired.label]?.name}：{fired.skipped}，这次没执行</div>}
      <div className="mg-stage">
        <div className="mg-aura" ref={auraRef}><svg ref={handRef} className="mg-hand" viewBox="60 20 260 290" aria-label="手势示意">
          <RealHand open={HAND[hand.finger].open} contact={HAND[hand.finger].contact} amount={hand.amount} active={hand.finger} hot="#8B78D8" rest="rgba(47,58,54,.14)" /></svg></div>
        <div className="mg-readout"><div className="mg-word" ref={wordRef}>{ready ? word.main : '没在识别'}</div><div className="mg-why">{ready ? word.why : '先点「开始识别」'}</div>
          <svg className="mg-gauge" viewBox="0 0 230 128" aria-label={`把握 ${conf.toFixed(2)}`}>
            <defs><linearGradient id="mg-gg" x1="0" x2="1"><stop offset="0" stopColor="#8EC5F0" /><stop offset=".6" stopColor="#B9A6EC" /><stop offset="1" stopColor="#7FD3B0" /></linearGradient></defs>
            <path d="M23 118 A92 92 0 0 1 207 118" fill="none" stroke="rgba(47,58,54,.08)" strokeWidth="12" strokeLinecap="round" />
            <path ref={arcRef} d="M23 118 A92 92 0 0 1 207 118" fill="none" stroke="url(#mg-gg)" strokeWidth="12" strokeLinecap="round" pathLength={100} strokeDasharray="0 100" />
            <path d={`M${115 + 84 * Math.cos(Math.PI * .35)} ${118 - 84 * Math.sin(Math.PI * .35)} L${115 + 100 * Math.cos(Math.PI * .35)} ${118 - 100 * Math.sin(Math.PI * .35)}`} stroke="#E46A73" strokeWidth="3" strokeLinecap="round" />
            <g ref={gaugeRef}><line x1="115" y1="118" x2="115" y2="38" stroke="#2F3A36" strokeWidth="2.6" strokeLinecap="round" /><circle cx="115" cy="38" r="6" className="mg-tip" /><circle cx="115" cy="38" r="2.6" fill="#fff" /></g>
            <circle cx="115" cy="118" r="6" fill="#2F3A36" /></svg>
          <div className="mg-fine">把握 · 红线 0.65 · 连续 3 次才算一次</div></div>
      </div>
      <div className="mg-screen" ref={screenRef}><canvas ref={trailRef} /><span className="mg-cap">真鼠标 · 光标去了哪</span>
        <svg ref={cursorRef} className="mg-cursor" viewBox="0 0 18 24" aria-hidden><path d="M2 2 L2 19 L6.5 14.5 L10 22 L12.8 20.8 L9.4 13.6 L15.5 13.6 Z" /></svg>
        {!live && <div className="mg-off">{ready ? '演练中 · 鼠标不动' : '没在识别'}</div>}</div>
      <div className="mg-feed">{events.slice(-4).reverse().map((e) => <span key={e.id} className={e.ok ? '' : 'dim'}><i>{e.t}</i>{e.text}</span>)}</div>
    </section>

    <section className={`mg-card mg-ai ${view.kind === 'pending' ? 'pending' : ''}`} ref={cardRef}>
      <div className="mg-cap">✦ AI 授权 · Claude Code</div>
      {view.kind === 'idle' ? <><h3>还没有请求</h3><p className="mg-why">Claude Code 要跑低风险命令时，这张卡会被召唤出来，耳机同时念出来。危险命令照旧弹窗，不走手环。</p></> : <>
        <div className="mg-row" style={{ justifyContent: 'flex-start', gap: 14 }}>
          <svg width="78" height="78" viewBox="0 0 78 78"><defs><linearGradient id="mg-rg" x1="0" x2="1"><stop offset="0" stopColor="#B9A6EC" /><stop offset="1" stopColor="#8EC5F0" /></linearGradient></defs>
            <circle cx="39" cy="39" r="32" fill="none" stroke="rgba(47,58,54,.08)" strokeWidth="7" />
            <circle cx="39" cy="39" r="32" fill="none" stroke="url(#mg-rg)" strokeWidth="7" strokeLinecap="round" pathLength={100} strokeDasharray={`${view.kind === 'pending' ? (view.left / view.total) * 100 : 0} 100`} transform="rotate(-90 39 39)" />
            <text x="39" y="46" textAnchor="middle" className="mg-sec">{view.kind === 'pending' ? Math.ceil(view.left) : '·'}</text></svg>
          <div><h3>想运行这条命令</h3><div className="mg-why">{view.kind === 'pending' ? '食指捏住半秒 = 同意 · 中指捏 = 拒绝' : ai?.reason}</div></div></div>
        <div className="mg-cmd">{ai?.cmd}</div>
        <div className="mg-two"><Key label="mouse_index" refs={aiKeys} text="同意 · 放行" dim={view.kind === 'deny' || view.kind === 'timeout'} /><Key label="mouse_middle" refs={aiKeys} text="拒绝" dim={view.kind === 'allow'} /></div>
        <p className="mg-fine">{view.kind === 'pending' ? '⏸ 手势鼠标先暂停：食指同意不会顺带点左键' : '▶ 手势鼠标已恢复'}</p>
        {view.kind !== 'pending' && <div className={`mg-seal ${view.kind}`} ref={sealRef} key={ai?.seq}><b>{view.kind === 'allow' ? '已同意' : view.kind === 'deny' ? '已拒绝' : '超时'}</b><small>{view.ms != null ? `${(view.ms / 1000).toFixed(2)} s` : '—'}</small></div>}
      </>}
    </section>
  </div>;
}
