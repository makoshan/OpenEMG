'use client';
// 电极环：8 个扇区绕手腕一圈，颜色按数值（实时 RMS 或每路准确率）。左手镜像。只是示意位置，不是测量出的电极坐标。
import { CH_COLORS } from './contract';

export function ElectrodeRing({ values, max, hand = 'left', size = 180, channels, label, format = (v: number) => v.toFixed(0), hot, onlyHot }:
  { values: number[] | null; max: number; hand?: 'left' | 'right'; size?: number; channels?: number; label?: string; format?: (v: number) => string; hot?: (v: number, i: number) => boolean; onlyHot?: boolean }) {   // onlyHot：小环上只给要动手的几片标数字，8 个数挤在一起读不出（2026-10-12）   // hot：这一片要用户动手（校准页标没贴紧的电极）
  const count = Math.max(1, values?.length ?? channels ?? 8);
  const step = (2 * Math.PI) / count, gap = Math.min(0.036, step * 0.11), span = Math.max(0.04, step - 2 * gap);
  const large = span > Math.PI ? 1 : 0;
  const r0 = size * (count > 12 ? 0.28 : 0.27), r1 = size * 0.44, cx = size / 2, cy = size / 2;
  const arc = (i: number) => {
    const k = hand === 'left' ? -1 : 1, a0 = -Math.PI / 2 + k * (i * step) - step / 2 + gap, a1 = a0 + span;
    const p = (r: number, a: number) => `${cx + r * Math.cos(a)} ${cy + r * Math.sin(a)}`;
    return `M ${p(r0, a0)} L ${p(r1, a0)} A ${r1} ${r1} 0 ${large} 1 ${p(r1, a1)} L ${p(r0, a1)} A ${r0} ${r0} 0 ${large} 0 ${p(r0, a0)} Z`;
  };
  const mid = (i: number, r: number) => { const k = hand === 'left' ? -1 : 1, a = -Math.PI / 2 + k * (i * step); return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
  const showVal = count <= 8 || (size >= 176 && count <= 16);
  return <figure className="emg8-ring" data-channels={count} style={{ width: size }}>
    <svg viewBox={`0 0 ${size} ${size}`} aria-label={label ?? '电极环'}>
      <circle cx={cx} cy={cy} r={r0 - 4} fill="none" stroke="var(--emg8-line)" strokeWidth="1" strokeDasharray="2 3" opacity="0.7" />
      {Array.from({ length: count }, (_, i) => {
        const rawV = values && values[i] != null ? values[i] : null;
        const col = CH_COLORS[i % CH_COLORS.length];
        const isHot = rawV !== null && !!hot?.(rawV, i);
        const v = rawV !== null ? Math.max(0, Math.min(1, rawV / max)) : 0;
        const [tx, ty] = mid(i, (r0 + r1) / 2), [lx, ly] = mid(i, r1 + (count > 12 ? 9.5 : 11));
        return <g key={i}>
          <path d={arc(i)} className="emg8-ring-seg" data-hot={isHot ? '1' : undefined} fill={isHot ? '#D0606A' : col} fillOpacity={isHot ? 0.95 : 0.14 + v * 0.84} stroke={isHot ? '#D0606A' : col} strokeWidth={isHot ? 2.2 : count > 12 ? 1.0 : 1.25} style={{ transition: 'fill-opacity 180ms linear', color: col }} />
          <text x={tx} y={ty + 3} textAnchor="middle" className="emg8-ring-v" style={count > 12 ? { fontSize: 7.5 } : undefined}>{rawV !== null && (!onlyHot || isHot) && showVal ? format(rawV) : ''}</text>
          <text x={lx} y={ly + 3.5} textAnchor="middle" className="emg8-ring-l" style={count > 12 ? { fontSize: 8 } : undefined}>{i + 1}</text>
        </g>;
      })}
      <text x={cx} y={cy - 2} textAnchor="middle" className="emg8-ring-c">{hand === 'left' ? '左手' : '右手'}</text>
      <text x={cx} y={cy + 13} textAnchor="middle" className="emg8-ring-s">{label ?? ''}</text>
    </svg>
  </figure>;
}
