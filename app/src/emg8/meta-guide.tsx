'use client';
import { useEffect, useState } from 'react';
import type { GuideMode } from './thumb-guide';
import type { Hand } from './contract';
import POSES from './meta-hand-poses.json';
import { grayTitle } from './gray-title';

type Pose = Record<string, { pts: number[][]; depth: number }>;
const FINGER_ORDER = ['thumb', 'index', 'middle', 'ring', 'little'];

/** 0 = 张开手型，1 = 贴上手型。时间表和组件里的 contact 一致；贴上用 0.18 s、松开用 0.3 s。 */
export function contactAmount(kind: string, mode: GuideMode, s: number, delay: number): number {
  if (!['preview', 'record'].includes(mode) || kind === 'rest' || kind === 'other') return 0;
  const p = s - delay; if (p < 0) return 0;
  const spans = kind === 'tap' ? [[0, .3]] : kind === 'double' ? [[0, .2], [.4, .6]] : kind === 'long' ? [[0, 1.2]] : kind === 'hold' && mode === 'record' ? [[0, Infinity]] : [[0, 1.65]];
  const IN = .18, OUT = .3;
  return Math.max(...spans.map(([a, b]) => p < b ? Math.min(1, (p - a) / IN) : Math.max(0, Math.min(1, (b - a) / IN) - (p - b) / OUT)));
}

/** 真人动捕手型：张开 / 贴上两帧按 amount 插值，按深度排绘制顺序（近的后画）。使用内置参数化几何手骨坐标插值绘制。 */
export function RealHand({ open, contact, amount, active, hot: hotColor = '#207768', rest: restColor = '#8A8F98' }: { open: Pose; contact: Pose; amount: number; active: string; hot?: string; rest?: string }) {
  const lerp = (a: number[], b: number[]) => [a[0] + (b[0] - a[0]) * amount, a[1] + (b[1] - a[1]) * amount];
  const f = FINGER_ORDER.map((id) => ({ id, pts: open[id].pts.map((p, i) => lerp(p, contact[id].pts[i])), depth: open[id].depth + (contact[id].depth - open[id].depth) * amount }));
  const [wx, wy] = f[0].pts[0];                                                                // 腕点；掌形 = 四个指根 + 腕两侧，圆角描边
  const palm = [...f.slice(1).map((x) => x.pts[1]), [wx - 34, wy], [wx + 30, wy - 6], f[0].pts[1]].map((p) => p.join(',')).join(' ');
  const line = (pts: number[][]) => pts.map((p) => p.join(',')).join(' ');
  return <>
    <polygon points={palm} fill="#F0E4D6" stroke="#F0E4D6" strokeWidth="14" strokeLinejoin="round" />
    {[...f].sort((a, b) => a.depth - b.depth).map((x) => { const hot = x.id === 'thumb' || x.id === active; return <g key={x.id}>
      <polyline points={line(x.pts.slice(1))} fill="none" stroke={hot ? hotColor : restColor} strokeWidth="22" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={line(x.pts.slice(1))} fill="none" stroke={x.id === 'thumb' ? '#E8CFB7' : '#F0E4D6'} strokeWidth="18.5" strokeLinecap="round" strokeLinejoin="round" /></g>; })}
    {amount > .9 && <circle cx={f[0].pts[f[0].pts.length - 1][0]} cy={f[0].pts[f[0].pts.length - 1][1]} r="11" fill="none" stroke={hotColor} strokeWidth="3" strokeDasharray="3 3" />}
  </>;
}

export function MetaGuide({ label, name, icon, cue, hand, mode, takeKey, onPreview, kind = 'hold' }: { label: string; name: string; icon: string; cue: string; hand: Hand; mode: GuideMode; takeKey: string; onPreview: () => void; kind?: string }) {
  const [t, setT] = useState(0);
  useEffect(() => {
    if (mode === 'paused') return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const start = performance.now(); let raf = 0;
    const tick = () => { setT(reduced ? 0 : (performance.now() - start) / 1000); if (!reduced && ['preview', 'record'].includes(mode)) raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [label, mode, takeKey]);
  const s = mode === 'preview' ? t % 4 : Math.min(2, t);
  const active = ['preview', 'record'].includes(mode);
  const practice = ['tap', 'double', 'long'].includes(kind);
  const delay = mode === 'preview' ? .6 : practice ? .35 : 0;
  const phase = Math.max(0, s - delay);
  const contact = active && s >= delay && kind !== 'rest' && kind !== 'other' && (kind === 'tap' ? phase < .3 : kind === 'double' ? phase < .2 || (phase >= .4 && phase < .6) : kind === 'long' ? phase < 1.2 : kind === 'hold' && mode === 'record' ? true : phase < 1.65);
  const amount = active && contact ? Math.min(1, Math.max(0, phase - .25) / .8) : 0;
  const angle = kind === 'rotate' ? (label === 'motion_cw' ? 22 : -22) * amount : 0;
  const dx = kind === 'move' ? (label === 'motion_left' ? -32 : label === 'motion_right' ? 32 : 0) * amount : 0;
  const dy = kind === 'move' ? (label === 'motion_up' ? -26 : label === 'motion_down' ? 26 : 0) * amount : 0;
  const finger = label.includes('middle') ? '中指' : '食指';
  // 手背视角、左手、指尖朝上：四指 + 拇指分开画。接触时只让做动作的那根手指弯向拇指尖（长度缩短 = 弯曲），其余手指自然放着；
  // 侧面接触是拇指尖碰食指侧边。旧图只有一根竖起的手指，中指动作看起来像竖中指（Mako 2026-10-05 反馈）。
  const target = label.includes('side') ? 'side' : label.includes('middle') ? 'middle' : 'index';
  const P = target === 'middle' ? [240, 112] : target === 'side' ? [232, 118] : [262, 120];          // 接触点
  const aim = (bx: number, by: number, len: number, rest: number, on: boolean) => {          // 指根 → 角度（顺时针为正）、长度比例
    if (!on) return { a: rest, k: 1 };
    const dx = P[0] - bx, dy = by - P[1]; return { a: Math.atan2(dx, dy) * 180 / Math.PI, k: Math.min(1.1, Math.hypot(dx, dy) / len) };
  };
  const fingers = [{ id: 'index', x: 213, w: 24, len: 95, rest: 6 }, { id: 'middle', x: 185, w: 24, len: 105, rest: 0 }, { id: 'ring', x: 157, w: 22, len: 95, rest: -5 }, { id: 'little', x: 129, w: 20, len: 75, rest: -12 }];
  const acting = kind !== 'rest' && kind !== 'other';                                          // 放松 / 日常动作：不标任何手指
  const isActive = (id: string) => acting && (id === target || (target === 'side' && id === 'index'));
  const bend = (id: string) => contact && isActive(id);
  const pose = (f: typeof fingers[number]) => target === 'side' && f.id === 'index' && contact ? { a: 10, k: .85 } : aim(f.x, 155, f.len, f.rest, bend(f.id));
  const thumb = aim(228, 205, 85, 45, contact);
  const real = acting && target !== 'side' ? (POSES as unknown as Record<'index' | 'middle', { open: Pose; contact: Pose }>)[target] : null;   // 食指 / 中指用动捕真手型；侧面接触动捕里没有，仍用示意图
  return <div className="emg8-demo-body">
    <figure className="emg8-thumb-picture"><small>{hand === 'left' ? '左手' : '右手'} · 指尖朝前 · {real ? '手部接触几何示意' : '接触位置示意'}</small>
      <svg viewBox="0 0 360 300" role="img" aria-label={`${name}动画示范：${cue}`}>
        <g transform={`translate(${dx} ${dy}) rotate(${angle} 180 225)`}>
          <g transform={hand === 'right' ? 'translate(360 0) scale(-1 1)' : undefined}>
            {real ? <RealHand open={real.open} contact={real.contact} amount={contactAmount(kind, mode, s, delay)} active={target} /> : <>
            <rect className="thumb-finger" x="110" y="145" width="125" height="130" rx="30" />
            <g transform={`translate(228 205) rotate(${thumb.a})`}><rect className="thumb-pad" x="-13" y={-85 * thumb.k} width="26" height={85 * thumb.k} rx="13" /></g>
            {[...fingers].sort((a, b) => Number(isActive(b.id)) - Number(isActive(a.id))).map((f) => { const p = pose(f);   /* 弯曲的手指先画：手背视角下它在其他手指下面 */ return <g key={f.id} transform={`translate(${f.x} 155) rotate(${p.a})`}>
              <rect className="thumb-finger" x={-f.w / 2} y={-f.len * p.k} width={f.w} height={f.len * p.k} rx={f.w / 2} style={isActive(f.id) ? { stroke: '#207768', strokeWidth: 2.4 } : undefined} />
              <path className="thumb-anatomy" d={`M${-f.w / 2 + 3} ${-f.len * p.k * .55}h${f.w - 6}`} /></g>; })}
            {contact && <circle cx={P[0]} cy={P[1]} r="10" fill="none" stroke="#207768" strokeWidth="3" strokeDasharray="3 3" />}</>}
          </g>
        </g>
        <text className="thumb-label" x="24" y="45">{acting ? `${finger}${label.includes('side') ? '侧面' : '指腹'}` : '手指放松'}</text>
        <text className="thumb-label" x="262" y="232">拇指</text>
        <text x="268" y="54" fontSize="32" fill="#256A60">{kind === 'rotate' || kind === 'move' ? icon : contact ? '接触' : '分开'}</text>
      </svg>
      <figcaption>{kind === 'rotate' || kind === 'move' ? '捏住 → 单向运动 → 松开 → 复位' : kind === 'double' ? '先放松 0.35 秒 → 点两次，每次分开' : kind === 'tap' ? '先放松 0.35 秒，轻碰一次，立即分开' : kind === 'rest' || kind === 'other' ? '手指分开，不触发指令' : '轻捏，保持；不要用力夹紧'}</figcaption>
    </figure>
    <div className="emg8-thumb-instructions"><h3>{icon} {name}</h3><p>{cue}</p><small>{kind === 'move' ? '以肘部为支点摆动；不测量直线位移。' : '前臂有支撑；左右、顺逆时针按你的视角。'}</small>
      <ol className="emg8-thumb-sequence"><li><b>1</b>先放松，看清接触位置</li><li className={contact ? 'current' : ''}><b>2</b>看到“做！”后完成当前动作</li><li><b>3</b>下一条前松开并复位</li></ol>
      <div className="emg8-preview-controls"><button onClick={onPreview} disabled={mode === 'prepare' || mode === 'record'} title={grayTitle((mode === 'prepare' || mode === 'record') && '正在录，示范跟着口令走')}>{mode === 'paused' ? '播放示范' : '暂停示范'}</button><small>{mode === 'prepare' || mode === 'record' ? '跟随真实录制口令' : '动作示范 · 未录制'}</small></div>
    </div>
  </div>;
}
