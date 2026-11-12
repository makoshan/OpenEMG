'use client';
// A2「仪器暖光」部件（design/emg-magic-v3/D4.md）：表盘、拍摄表、走纸、凹槽、滚轮、翻牌、指针表、阶段条。
// 规矩：动效只由真实状态驱动——没数据不亮、后端没收下不落珠、模型没判出不翻牌。
import { useEffect, useRef, type Ref, type RefObject } from 'react';
import './instrument.css';
import { magic, RGB } from './magic';

export type LedState = 'off' | 'on' | 'rec' | 'warn';
export const Led = ({ state }: { state: LedState }) => <i className={`ins-led ${state}`} aria-hidden />;

/** 第 i 路灯亮不亮：在线且这一路真有数值 */
export const channelLit = (online: boolean, values: number[] | null, i: number) => online && !!values && values[i] > 0;
/** 服务端一帧都没收到会停下这一批，先写停止句、再写一行「尝试 n 条」汇总（firmware/emg_web.py record()），所以看最后两行 */
export const zeroStopped = (st: { busy: string | null; log: string[] } | null) => !st?.busy && !!st?.log.slice(-2).some((l) => l.includes('没有收到任何数据，已停下这一批'));
/** 哪些类该落珠：只有正在录（或刚录完 3 s 内）的那一类，且计数正好 +1。切换数据集、工程未对上导致的计数跳变都不算 */
export const beadLabels = (before: Record<string, number> | null, now: Record<string, number>, recording: string | null) =>
  !before || !recording ? [] : Object.keys(now).filter((l) => l === recording && now[l] === (before[l] ?? 0) + 1);

/** 每路放松底噪上限，和服务端整体告警同一个数（firmware/wl8_ab.py「放松底噪 > 150 µV 偏高」） */
export const NOISE_LIMIT_UV = 150;
/** 这一路波形会顶格：RMS × 3 ≈ 峰值，超过量程就标「超量程」。空值 / NaN 不报 */
export const overRange = (rms: number | null | undefined, range: number) => Number.isFinite(rms as number) && (rms as number) * 3 > range;

const C = [260, 215] as const, RX = 158, RY = 124;
/** 第 i 路电极在腕截面上的位置；左手镜像，和 ring.tsx 一致 */
const at = (i: number, hand: 'left' | 'right', dr = 0) => {
  const a = (-90 + (hand === 'left' ? -1 : 1) * i * 45) * Math.PI / 180;
  return { x: C[0] + (RX + dr) * Math.cos(a), y: C[1] + (RY + dr * RY / RX) * Math.sin(a), a };
};

/** 表盘：腕截面 + 8 个金属电极。LED = 该路有数据；VU = 实时 RMS / max；checks 给出时显示阈值刻度与逐路结论 */
export function Dial({ values, max, online, hand, checks, limit, sweep, needle, big, small }: {
  values: number[] | null; max: number; online: boolean; hand: 'left' | 'right';
  checks?: ('ok' | 'bad')[] | null; limit?: number; sweep?: number | null; needle?: number | null; big: string; small: string;
}) {
  const ticks = Array.from({ length: 96 }, (_, k) => {
    const a = k * 3.75 * Math.PI / 180, r0 = k % 12 ? 242 : 236;
    return <line key={k} className={k % 12 ? 'tick' : 'tick major'} x1={C[0] + r0 * Math.cos(a)} y1={C[1] + r0 * .8 * Math.sin(a)} x2={C[0] + 250 * Math.cos(a)} y2={C[1] + 200 * Math.sin(a)} />;
  });
  const sweepPath = sweep == null ? '' : (() => {
    const a1 = (-90 + sweep * 360) * Math.PI / 180, a0 = a1 - Math.PI / 6, R = 250;
    return `M${C[0]} ${C[1]} L${C[0] + R * Math.cos(a0)} ${C[1] + R * .8 * Math.sin(a0)} A${R} ${R * .8} 0 0 1 ${C[0] + R * Math.cos(a1)} ${C[1] + R * .8 * Math.sin(a1)}Z`;
  })();
  return <svg className={`ins-dial ${checks || sweep != null ? 'check' : ''}`} viewBox="0 0 520 430" role="img" aria-label={`八路电极：${big} ${small}`}>
    <defs><linearGradient id="ins-metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#FBFAF7" /><stop offset=".55" stopColor="#DCD6CB" /><stop offset="1" stopColor="#C7C0B3" /></linearGradient></defs>
    {ticks}
    {sweepPath && <path className="sweep" d={sweepPath} />}
    <ellipse className="band" cx={C[0]} cy={C[1]} rx={RX} ry={RY} /><ellipse className="band2" cx={C[0]} cy={C[1]} rx={RX - 14} ry={RY - 14} />
    {Array.from({ length: 8 }, (_, i) => {
      const p = at(i, hand), v0 = at(i, hand, 22), v1 = at(i, hand, 62), t = at(i, hand, 84), l = at(i, hand, -24);
      const len = Math.hypot(v1.x - v0.x, v1.y - v0.y), v = values ? Math.max(0, Math.min(1, values[i] / max)) : 0;
      const lit = channelLit(online, values, i);
      const lim = limit != null ? Math.min(1, limit / max) : null, lx = v0.x + (v1.x - v0.x) * (lim ?? 0), ly = v0.y + (v1.y - v0.y) * (lim ?? 0);
      const state = checks?.[i];
      return <g key={i} className={`el ${lit ? 'on' : ''} ${state ?? ''}`} style={{ ['--i' as string]: i }}>
        <line className="vubg" x1={v0.x} y1={v0.y} x2={v1.x} y2={v1.y} />
        <line className="vu" x1={v0.x} y1={v0.y} x2={v1.x} y2={v1.y} strokeDasharray={`${(lit ? v : 0) * len} ${len}`} />
        {lim != null && <line className="thr" x1={lx - 5 * Math.sin(p.a)} y1={ly + 5 * Math.cos(p.a)} x2={lx + 5 * Math.sin(p.a)} y2={ly - 5 * Math.cos(p.a)} />}
        {/* 旋转放在外层 g：rect 上的 CSS transform-box 会把 SVG transform 属性的旋转中心算偏 */}
        <g transform={`rotate(${p.a * 180 / Math.PI + 90} ${p.x} ${p.y})`}><rect className="pad" x={p.x - 13} y={p.y - 8} width={26} height={16} rx={8} /></g>
        <circle className="ledc" cx={l.x} cy={l.y} r={3.2} />
        <text x={t.x} y={t.y + 4}>CH{i + 1}</text>
      </g>;
    })}
    {needle != null && <line className="needle" x1={C[0]} y1={C[1]} x2={C[0]} y2={C[1] - 100} transform={`rotate(${needle * 24} ${C[0]} ${C[1]})`} />}
    <text className="big" x={C[0]} y={C[1] + 2}>{big}</text><text className="small" x={C[0]} y={C[1] + 26}>{small}</text>
  </svg>;
}

/** 拍摄表：服务端 progress.phase 驱动——'3/2/1' 倒数、'准备录制' 等设备、'NOW' 录制 2 s（红弧走满） */
export function TakeDial({ phase, take, zero }: { phase?: string; take?: number; zero?: boolean }) {
  const n = zero ? '0' : phase === 'NOW' ? '做' : phase && /^[1-9]$/.test(phase) ? phase : '·';
  return <div className={`ins-take ${phase === 'NOW' ? 'rec' : ''} ${zero ? 'zero' : ''}`} aria-live="polite">
    <svg viewBox="0 0 170 170" aria-hidden>
      {Array.from({ length: 60 }, (_, k) => { const a = (k * 6 - 90) * Math.PI / 180, r0 = k % 5 ? 74 : 68; return <line key={k} className={k % 5 ? 'tk' : 'tk major'} x1={85 + r0 * Math.cos(a)} y1={85 + r0 * Math.sin(a)} x2={85 + 80 * Math.cos(a)} y2={85 + 80 * Math.sin(a)} />; })}
      <circle className="track" cx="85" cy="85" r="60" />
      {phase === 'NOW' && <circle key={take} className="arc" cx="85" cy="85" r="60" pathLength={100} transform="rotate(-90 85 85)" />}
    </svg>
    <b key={`${take}:${n}`}>{n}</b>
  </div>;
}

/** 走纸记录条：每帧读 envelope()（studio 里最近一批显示滤波帧的平均幅度，0–1）；rec 时录制窗口铺浅红。
 *  给了 noise（8 路最高 RMS µV + 红线）就改成底噪尺：绿区 ≤55% 红线、黄区到红线、红区在上；超线时曲线和读数变红（Mako 2026-10-08）。 */
export type NoiseTape = { uv: () => number; limit: number };
export function Tape({ envelope, rec, noise }: { envelope?: () => number; rec: boolean; noise?: NoiseTape }) {
  const ref = useRef<HTMLCanvasElement>(null), recRef = useRef(rec), readRef = useRef<HTMLSpanElement>(null);
  useEffect(() => { recRef.current = rec; }, [rec]);
  useEffect(() => {
    const cv = ref.current, ctx = cv?.getContext('2d'); if (!cv || !ctx || !envelope) return;
    const W = cv.width = 720, H = cv.height = 148, buf = new Array(240).fill(0);
    const top = noise ? noise.limit * 1.6 : 1;                       // 纵轴满量程：底噪尺 = 1.6 × 红线
    const yOf = (v: number) => H - 12 - Math.min(1, v / top) * (H - 30);
    let raf = 0;
    const draw = () => {
      const sample = noise ? noise.uv() : envelope(); buf.push(Number.isFinite(sample) ? sample : buf[buf.length - 1] ?? 0); buf.shift(); ctx.clearRect(0, 0, W, H);
      if (noise) {                                                   // 三色区间：从下往上 绿 / 黄 / 红
        ctx.fillStyle = 'rgba(32,119,104,.10)'; ctx.fillRect(0, yOf(noise.limit * .55), W, H - yOf(noise.limit * .55));
        ctx.fillStyle = 'rgba(233,185,73,.14)'; ctx.fillRect(0, yOf(noise.limit), W, yOf(noise.limit * .55) - yOf(noise.limit));
        ctx.fillStyle = 'rgba(208,96,106,.14)'; ctx.fillRect(0, 0, W, yOf(noise.limit));
        ctx.strokeStyle = 'rgba(208,96,106,.8)'; ctx.setLineDash([6, 5]); ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(0, yOf(noise.limit)); ctx.lineTo(W, yOf(noise.limit)); ctx.stroke(); ctx.setLineDash([]);
      }
      ctx.strokeStyle = 'rgba(36,53,47,.08)'; ctx.lineWidth = 1;
      for (let x = 0; x < W; x += 24) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
      if (recRef.current) { ctx.fillStyle = 'rgba(192,57,43,.07)'; ctx.fillRect(W * .55, 0, W * .45, H); }
      const cur = noise && !Number.isFinite(sample) ? NaN : buf[buf.length - 1], bad = !!noise && cur > noise.limit;
      ctx.strokeStyle = bad ? '#D0606A' : '#163F35'; ctx.lineWidth = 2.2; ctx.beginPath();
      buf.forEach((y, i) => { const X = i / (buf.length - 1) * W, Y = yOf(y); if (i) ctx.lineTo(X, Y); else ctx.moveTo(X, Y); });
      ctx.stroke();
      if (noise && readRef.current) { const ok = Number.isFinite(cur); readRef.current.textContent = ok ? `放松底噪 ${Math.round(cur)} µV · ${bad ? '太高' : cur >= noise.limit * .55 ? '偏高' : '正常'}` : '等信号'; readRef.current.dataset.state = !ok ? '' : bad ? 'bad' : cur >= noise.limit * .55 ? 'high' : 'ok'; }
      raf = requestAnimationFrame(draw);
    };
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [envelope, noise]);
  return <div className="ins-tape"><canvas ref={ref} aria-label={noise ? '底噪走纸' : '实时幅度走纸'} /><span className="ins-cap">{noise ? `放松底噪 · 红线 ${noise.limit} µV` : '实时幅度'}</span>{noise && envelope && <span ref={readRef} className="ins-tape-read" role="status" />}{!envelope && <em>没有实时数据</em>}</div>;
}

/** 样本凹槽：target 个，前 n 个有珠子；超过目标显示 +k */
export function Wells({ n, target, color }: { n: number; target: number; color: string }) {
  return <span className="ins-wells" style={{ ['--c' as string]: color }} aria-label={`${n} / ${target}`}>
    {Array.from({ length: target }, (_, i) => <span key={i} className={i < n ? 'well full' : 'well'} data-well={i} />)}
    {n > target && <small>+{n - target}</small>}
  </span>;
}

/** 手势颜色（#rrggbb）→ 'r,g,b'，认不出就用薰衣草紫 */
export const hexRgb = (c: string) => /^#[0-9a-f]{6}$/i.test(c) ? [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)).join(',') : RGB.lilac;
/** 收下一条：光迹从拍摄表飞进那一类的凹槽，凹槽弹一下。只在后端计数真的 +1 后调用（魔法手帐，magic.ts） */
export function flyBead(from: Element | null, to: Element | null, color: string) {
  if (!from || !to || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const a = from.getBoundingClientRect(), b = to.getBoundingClientRect(), rgb = hexRgb(color);
  magic.comet(a.left + a.width / 2, a.top + a.height / 2, b.left + b.width / 2, b.top + b.height / 2, rgb, 560);
  setTimeout(() => to.animate([{ transform: 'scale(2.2)' }, { transform: 'scale(.9)', offset: .6 }, { transform: 'none' }], { duration: 420, easing: 'cubic-bezier(.34,1.56,.64,1)' }), 560);
}

/** 滚轮计数器：每位一条 0–9 纸带滚到目标位；非数字字符原样 */
export function Odometer({ text }: { text: string }) {
  let k = 0;
  return <span className="ins-odo" aria-label={text}>{[...text].map((ch, i) => /\d/.test(ch)
    ? <span key={i} className="col"><span className="strip" style={{ transform: `translateY(-${Number(ch)}em)`, transitionDelay: `${(k++) * 90}ms` }}>{'0123456789'.split('').map((d) => <span key={d}>{d}</span>)}</span></span>
    : <span key={i}>{ch}</span>)}</span>;
}

/** 翻牌显示：字变了，那一格重新翻进来（key 带字），逐格错开 55 ms */
export function Flap({ text, dim }: { text: string; dim?: boolean }) {
  return <div className={`ins-flap ${dim ? 'dim' : ''}`} role="status" aria-label={text}>{[...text].map((ch, i) => <span key={`${i}:${ch}`} className="cell" style={{ animationDelay: `${i * 55}ms` }}>{ch}</span>)}</div>;
}

/** 置信指针表：0–1；给了 threshold 才画红色阈值线 */
export function Gauge({ value, threshold }: { value: number; threshold?: number }) {
  const ta = Math.PI * (1 - (threshold ?? 0));
  return <svg className="ins-gauge" viewBox="0 0 240 140" role="img" aria-label={`置信度 ${value.toFixed(2)}${threshold == null ? '' : `，阈值 ${threshold}`}`}>
    <path className="scale" d="M20 120 A100 100 0 0 1 220 120" />
    {Array.from({ length: 11 }, (_, k) => { const a = Math.PI * (1 - k / 10), r0 = k % 5 ? 84 : 78; return <line key={k} className={k % 5 ? 'tk' : 'tk major'} x1={120 + r0 * Math.cos(a)} y1={120 - r0 * Math.sin(a)} x2={120 + 92 * Math.cos(a)} y2={120 - 92 * Math.sin(a)} />; })}
    {threshold != null && <><line className="thr" x1={120 + 76 * Math.cos(ta)} y1={120 - 76 * Math.sin(ta)} x2={120 + 104 * Math.cos(ta)} y2={120 - 104 * Math.sin(ta)} />
    <text x={120 + 112 * Math.cos(ta)} y={120 - 112 * Math.sin(ta)}>{threshold.toFixed(2)}</text></>}
    <text x="20" y="136">0</text><text x="220" y="136">1</text>
    <line className="needle" x1="120" y1="120" x2="120" y2="36" style={{ transform: `rotate(${-90 + 180 * Math.max(0, Math.min(1, value))}deg)` }} />
    <circle cx="120" cy="120" r="7" className="hub" /><text className="val" x="120" y="100">{value.toFixed(2)}</text>
  </svg>;
}

/** 事件纸带：最新在右，旧的往左走 */
export function EventTape({ events }: { events: { id: number; t: string; text: string; ok: boolean }[] }) {
  return <div className="ins-evtape">{events.map((e) => <span key={e.id} className={e.ok ? 'ev' : 'ev dim'}><span className="num">{e.t}</span> {e.text}</span>)}</div>;
}

export type StepInfo = { t: string; s: string; done: boolean };
/** 五步阶段条：连线只连圆点；完成实心；下一步就绪时轻轻招手 */
export function Stepper({ steps, current, onPick }: { steps: StepInfo[]; current: number; onPick: (i: number) => void }) {
  const reach = steps.reduce((n, s, i) => (s.done && i === n ? n + 1 : n), 0);
  return <nav className="ins-steps" aria-label="使用步骤">
    <i className="fill" style={{ width: `${Math.min(reach, steps.length - 1) / (steps.length - 1) * 80}%` }} />
    {steps.map((s, i) => <button key={s.t} className={`step ${s.done ? 'done' : ''} ${i === current ? 'cur' : ''} ${!s.done && i === reach && i !== current ? 'ready' : ''}`} aria-current={i === current ? 'step' : undefined} onClick={() => onPick(i)}>
      <span className="dot">{s.done ? '✓' : i + 1}</span><b>{s.t}</b><small>{s.s}</small></button>)}
  </nav>;
}

/** 采集台右半边：REC 灯 + 拍摄表 + 走纸。zero = 服务端说这一批一帧都没收到、已停下 */
export function TakeDeck({ phase, take, count, recording, zero, envelope, deckRef, noise }: {
  phase?: string; take?: number; count?: number; recording: boolean; zero: boolean; envelope?: () => number; deckRef: Ref<HTMLDivElement>; noise?: NoiseTape;
}) {
  const led: LedState = zero ? 'warn' : recording && phase === 'NOW' ? 'rec' : envelope ? 'on' : 'off';
  return <div className="ins-deck" ref={deckRef}>
    <div className="ins-deck-head"><span className="ins-cap">{recording ? `第 ${take} / ${count} 条` : '拍摄表'}</span><span className="ins-cap"><Led state={led} /> {zero ? '已停下' : recording ? phase === 'NOW' ? 'REC' : '准备' : '待命'}</span></div>
    <TakeDial phase={recording ? phase : undefined} take={take} zero={zero} />
    {(envelope || recording) && <Tape envelope={envelope} rec={recording && phase === 'NOW'} noise={noise} />}
  </div>;
}

/** 后端计数从 n 变成 n+1（真的收下了一条）时，从拍摄表抛一颗珠子到那一类的第 n 个凹槽 */
export function useAcceptBead(counts: Record<string, number>, colorOf: (label: string) => string, deck: RefObject<HTMLDivElement | null>, recording: string | null) {
  const prev = useRef<Record<string, number> | null>(null);
  const last = useRef<{ label: string | null; until: number }>({ label: null, until: 0 });
  // 最后一条收下时服务端可能已经不忙了：录制结束后 3 s 内还认这一类
  if (recording) last.current = { label: recording, until: Infinity };
  else if (last.current.until === Infinity) last.current = { ...last.current, until: Date.now() + 3000 };
  useEffect(() => {
    const before = prev.current; prev.current = { ...counts };
    const active = Date.now() < last.current.until ? last.current.label : null;
    for (const label of beadLabels(before, counts, active)) flyBead(deck.current, document.querySelector(`[data-label="${CSS.escape(label)}"] [data-well="${counts[label] - 1}"]`), colorOf(label));
  }, [counts, colorOf, deck]);
}
