'use client';
// 电极环：8 个扇区绕手腕一圈，颜色按数值（实时 RMS 或每路准确率）。左手镜像。只是示意位置，不是测量出的电极坐标。
import { CH_COLORS } from './contract';

export function ElectrodeRing({ values, max, hand = 'left', size = 180, channels, label, format = (v: number) => v.toFixed(0), hot, onlyHot }:
  { values: number[] | null; max: number; hand?: 'left' | 'right'; size?: number; channels?: number; label?: string; format?: (v: number) => string; hot?: (v: number, i: number) => boolean; onlyHot?: boolean }) {   // onlyHot：小环上只给要动手的几片标数字，8 个数挤在一起读不出（2026-10-12）   // hot：这一片要用户动手（校准页标没贴紧的电极）
  const count = Math.max(1, values?.length ?? channels ?? 8);
  const step = (2 * Math.PI) / count, gap = Math.min(0.04, step * 0.12), span = Math.max(0.05, step - 2 * gap);
  const large = span > Math.PI ? 1 : 0;
  const r0 = size * 0.27, r1 = size * 0.44, cx = size / 2, cy = size / 2;
  const arc = (i: number) => {
    const k = hand === 'left' ? -1 : 1, a0 = -Math.PI / 2 + k * (i * step) - step / 2 + gap, a1 = a0 + span;
    const p = (r: number, a: number) => `${cx + r * Math.cos(a)} ${cy + r * Math.sin(a)}`;
    return `M ${p(r0, a0)} L ${p(r1, a0)} A ${r1} ${r1} 0 ${large} 1 ${p(r1, a1)} L ${p(r0, a1)} A ${r0} ${r0} 0 ${large} 0 ${p(r0, a0)} Z`;
  };
  const mid = (i: number, r: number) => { const k = hand === 'left' ? -1 : 1, a = -Math.PI / 2 + k * (i * step); return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
  return <figure className="emg8-ring" style={{ width: size }}>
    <svg viewBox={`0 0 ${size} ${size}`} aria-label={label ?? '电极环'}>
      {Array.from({ length: count }, (_, i) => {
        const rawV = values && values[i] != null ? values[i] : null;
        const col = CH_COLORS[i % CH_COLORS.length];
        const isHot = rawV !== null && !!hot?.(rawV, i);
        const v = rawV !== null ? Math.max(0, Math.min(1, rawV / max)) : 0;
        const [tx, ty] = mid(i, (r0 + r1) / 2), [lx, ly] = mid(i, r1 + 11);
        return <g key={i}>
          <path d={arc(i)} className="emg8-ring-seg" data-hot={isHot ? '1' : undefined} fill={isHot ? '#D0606A' : col} fillOpacity={isHot ? 0.95 : 0.12 + v * 0.85} stroke={isHot ? '#D0606A' : col} strokeWidth={isHot ? 2.4 : 1.2} style={{ transition: 'fill-opacity 180ms linear', color: col }} />
          <text x={tx} y={ty + 4} textAnchor="middle" className="emg8-ring-v">{rawV !== null && (!onlyHot || isHot) && count <= 12 ? format(rawV) : ''}</text>
          <text x={lx} y={ly + 4} textAnchor="middle" className="emg8-ring-l">{i + 1}</text>
        </g>;
      })}
      <text x={cx} y={cy - 2} textAnchor="middle" className="emg8-ring-c">{hand === 'left' ? '左手' : '右手'}</text>
      <text x={cx} y={cy + 14} textAnchor="middle" className="emg8-ring-s">{label ?? ''}</text>
    </svg>
  </figure>;
}
