'use client';
import { useEffect, useId, useState } from 'react';
import type { Hand } from './contract';
import { grayTitle } from './gray-title';

export type GuideMode = 'preview' | 'paused' | 'prepare' | 'record';
const ease = (v: number) => v * v * (3 - 2 * v);
// 方向按使用者视角；回程先抬起，避免动画教成来回摩擦。
export function thumbPose(label: string, hand: Hand, seconds: number, mode: GuideMode) {
  let u = 0, lift = 0, step = 0;
  if (label !== 'thumb_rest' && (mode === 'preview' || mode === 'record')) {
    const w = mode === 'preview' ? seconds % 3.6 : Math.min(2, seconds);
    if (mode === 'preview') {
      if (w >= .7 && w < 1.8) { u = ease((w - .7) / 1.1); step = 1; }
      else if (w >= 1.8 && w < 2.4) { u = 1; lift = (w - 1.8) / .6; step = 2; }
      else if (w >= 2.4 && w < 3.3) { lift = 1; u = 1 - ease((w - 2.4) / .9); step = 2; }
      else if (w >= 3.3) { lift = 1 - (w - 3.3) / .3; }
    } else if (w < .85) { u = ease(w / .85); step = 1; }
    else if (w < 1.3) { u = 1; lift = (w - .85) / .45; step = 2; }
    else { lift = 1; u = 1 - ease((w - 1.3) / .7); step = 2; }
  }
  const sign = hand === 'right' ? -1 : 1;
  const dx = (label === 'thumb_left' ? -19 : label === 'thumb_right' ? 19 : 0) * u * sign;
  const dy = (label === 'thumb_up' ? -34 : label === 'thumb_down' ? 34 : 0) * u;
  return { x: 185 + dx + 38 * lift, y: 157 + dy - 7 * lift, lift, step };
}

export function ThumbGuide({ label, name, icon, cue, hand, mode, takeKey, onPreview }: {
  label: string; name: string; icon: string; cue: string; hand: Hand; mode: GuideMode; takeKey: string; onPreview: () => void;
}) {
  const marker = useId().replaceAll(':', '');
  const [pose, setPose] = useState(() => thumbPose(label, hand, 0, mode));
  useEffect(() => {
    if (mode === 'paused') return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let raf = 0; const start = performance.now();
    const tick = () => {
      setPose(thumbPose(label, hand, reduced ? 0 : (performance.now() - start) / 1000, mode));
      if (!reduced && (mode === 'preview' || mode === 'record') && label !== 'thumb_rest') raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [label, hand, mode, takeKey]);
  const { x, y, lift } = pose, sign = hand === 'right' ? -1 : 1;
  const arrow = label === 'thumb_up' ? 'M133 148V113' : label === 'thumb_down' ? 'M133 148V185'
    : label === 'thumb_left' ? `M${185 - 15 * sign} 116H${185 - 40 * sign}` : label === 'thumb_right' ? `M${185 - 15 * sign} 116H${185 + 10 * sign}` : '';
  return <div className="emg8-demo-body">
    <figure className="emg8-thumb-picture">
      <small>手背朝上 · 指尖朝前 · 局部放大示意</small>
      <svg viewBox="0 0 360 320" role="img" aria-label={`${hand === 'left' ? '左手' : '右手'}${name}动作示范：食指固定，拇指滑一次后抬起复位`}>
        <defs><marker id={marker} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M1 1L7 4L1 7" className="thumb-arrow" /></marker></defs>
        <g transform={hand === 'right' ? 'translate(360 0) scale(-1 1)' : undefined}>
          <path className="thumb-finger" d="M109 293L102 250Q88 225 96 207Q100 194 112 196L139 217L147 200L150 65Q150 41 173 41Q196 41 196 65L197 206Q215 201 237 224L249 270L226 298Z" />
          <path className="thumb-finger" d="M137 220L124 183Q117 167 104 174Q91 181 99 196L115 224ZM112 231L91 203Q79 188 69 196Q59 205 72 219L95 243ZM97 248L77 231Q63 219 56 229Q49 238 65 250L93 269Z" />
          <path className="thumb-anatomy" d="M153 92Q174 99 193 92M153 134Q174 139 194 134M146 223Q161 229 171 237M116 271Q142 264 168 277" />
          <g opacity={1 - .27 * lift}>
            <path className="thumb-pad" d={`M230 282Q273 258 257 223Q246 199 ${x + 14} ${y + 14}L${x + 22} ${y - 6}Q272 203 276 237Q271 268 249 288Z`} />
            <ellipse className="thumb-pad" cx={x} cy={y} rx="29" ry="15" transform={`rotate(-28 ${x} ${y})`} />
          </g>
          <ellipse className="thumb-contact" cx="178" cy="157" rx="12" ry="7" opacity={lift > .1 ? 0 : 1} />
          <path className="thumb-arrow" d={arrow} markerEnd={`url(#${marker})`} />
        </g>
        <text className="thumb-label" x="28" y="62">食指固定</text><text className="thumb-label" x="28" y="79">朝指尖 ↑</text>
      </svg>
      <figcaption>{label === 'thumb_rest' ? '拇指轻贴食指，保持放松' : '虚线为接触位置；回程先抬起'}</figcaption>
    </figure>
    <div className="emg8-thumb-instructions">
      <h3>{icon} {name.replace('拇指', '')}</h3><p>{cue}</p><small>前臂有支撑，手腕和食指保持不动。</small>
      <ol className="emg8-thumb-sequence">{['轻贴食指，保持放松', label === 'thumb_rest' ? '保持静止，不施力' : '看到“做！”后滑一次', label === 'thumb_rest' ? '继续放松' : '抬起拇指，再回到起点'].map((text, i) => <li key={i} className={pose.step === i ? 'current' : ''}><b>{i + 1}</b>{text}</li>)}</ol>
      <div className="emg8-preview-controls"><button onClick={onPreview} disabled={mode === 'prepare' || mode === 'record'} title={grayTitle((mode === 'prepare' || mode === 'record') && '正在录，示范跟着口令走')}>{mode === 'paused' ? '播放示范' : '暂停示范'}</button><small>{mode === 'record' || mode === 'prepare' ? '跟随真实录制口令' : label === 'thumb_rest' ? '静止示范 · 不施力' : mode === 'paused' ? '示范已暂停' : ['轻贴食指', '滑动一次', '抬起复位'][pose.step] + ' · 未录制'}</small></div>
    </div>
  </div>;
}
