'use client';
// 演示用的动效：只负责"把真实数据演得好看"，不产生任何数据。系统"减少动态效果"打开时全部退化成静态。
// 思路参考 Magic UI（number-ticker / confetti / particles / border-beam），用 motion 自己实现，不加依赖。
import { animate, motion, useMotionValue, useReducedMotion, useTransform } from 'motion/react';
import { useEffect, useMemo, useState } from 'react';

/** 数字滚动：从上一个值滚到新值 */
export function NumberTicker({ value, format = (v: number) => `${Math.round(v)}`, duration = 0.8 }: { value: number; format?: (v: number) => string; duration?: number }) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(value);
  const text = useTransform(mv, format);
  useEffect(() => { if (reduce) { mv.set(value); return; } const c = animate(mv, value, { duration, ease: [0.16, 1, 0.3, 1] }); return () => c.stop(); }, [mv, value, duration, reduce]);
  return <motion.span style={{ fontVariantNumeric: 'tabular-nums' }}>{text}</motion.span>;
}

/** 礼花：fire 变化一次就从中间炸一次（只在结果真的过门槛时触发） */
export function Confetti({ fire, colors = ['#22D3EE', '#A855F7', '#22C55E', '#F59E0B', '#F43F5E'] }: { fire: number; colors?: string[] }) {
  const reduce = useReducedMotion();
  const bits = useMemo(() => Array.from({ length: 70 }, (_, i) => ({
    id: `${fire}-${i}`, x: (Math.random() - 0.5) * 520, y: -120 - Math.random() * 220, r: Math.random() * 720 - 360,
    c: colors[i % colors.length], w: 6 + Math.random() * 6, delay: Math.random() * 0.15,
  })), [fire]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!fire || reduce) return null;
  return <div className="emg8-fx-layer" aria-hidden>{bits.map((b) => <motion.i key={b.id} className="emg8-confetti" style={{ background: b.c, width: b.w, height: b.w * 0.45 }}
    initial={{ x: 0, y: 0, opacity: 1, rotate: 0 }} animate={{ x: b.x, y: [0, b.y, b.y + 420], opacity: [1, 1, 0], rotate: b.r }}
    transition={{ duration: 2.2, delay: b.delay, ease: 'easeOut', times: [0, 0.35, 1] }} />)}</div>;
}

/** 粒子爆开：key 变化一次爆一圈（识别结果换了一类时用） */
export function Burst({ burstKey, color }: { burstKey: string; color: string }) {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState<string | null>(null);
  useEffect(() => { if (!burstKey || reduce) return; setShown(burstKey); const t = setTimeout(() => setShown(null), 900); return () => clearTimeout(t); }, [burstKey, reduce]);
  // 不用 AnimatePresence：退场要等动画帧，窗口在后台时帧暂停，粒子会卡在屏上；这里只靠定时器摘掉
  return <div className="emg8-fx-layer" aria-hidden>{shown && Array.from({ length: 18 }, (_, i) => {
    const a = (i / 18) * Math.PI * 2, d = 90 + (i % 3) * 30;
    return <motion.i key={`${shown}-${i}`} className="emg8-particle" style={{ background: color, boxShadow: `0 0 10px ${color}` }}
      initial={{ x: 0, y: 0, scale: 1, opacity: 1 }} animate={{ x: Math.cos(a) * d, y: Math.sin(a) * d, scale: 0, opacity: 0 }} transition={{ duration: 0.8, ease: 'easeOut' }} />;
  })}</div>;
}

/** 置信度圆环：0–1 */
export function ConfidenceRing({ value, color, size = 170 }: { value: number; color: string; size?: number }) {
  const r = size / 2 - 8, c = 2 * Math.PI * r;
  return <svg className="emg8-confring" width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
    <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--emg8-line)" strokeWidth={8} />
    <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={8} strokeLinecap="round" strokeDasharray={c}
      animate={{ strokeDashoffset: c * (1 - Math.max(0, Math.min(1, value))) }} transition={{ type: 'spring', stiffness: 120, damping: 20 }}
      style={{ rotate: -90, transformOrigin: '50% 50%', filter: `drop-shadow(0 0 8px ${color})` }} />
  </svg>;
}
