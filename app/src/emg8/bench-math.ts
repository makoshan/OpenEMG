// 指向基准的计算（ISO 9241-9 / MacKenzie 的有效吞吐）。口径（2026-10-03 评审定）：
// - T1 测的是「指向 + 选择」：从上一次点击到这一次点击的全部时间，捏合识别的等待也算在里面。
// - 每组连续试次算一个吞吐：TP = log2(Ae / We + 1) / mean(MT)，We = 4.133 × SD(dx)，dx 是点击位置沿本次移动轴的偏差。
// - 失败试次保留、照常计入 dx 和 MT；不按「每次 ID / 时间」平均，也不只留点中的。
export type Pt = { x: number; y: number };
export type Trial = { from: Pt; to: Pt; click: Pt; mt: number; hit: boolean; firstEnter: number | null; entries: number; mode?: string };
export type SeqResult = { d: number; w: number; trials: Trial[]; tp: number; ide: number; mt: number; err: number; ae: number; we: number };

const dist = (a: Pt, b: Pt) => Math.hypot(a.x - b.x, a.y - b.y);

/** 点击位置沿「起点 → 目标」这条轴超出（+）或不足（−）目标中心多少像素 */
export function dxAlongAxis(from: Pt, to: Pt, click: Pt): number {
  const a = dist(from, to), b = dist(to, click), c = dist(from, click);
  return a === 0 ? 0 : (c * c - b * b - a * a) / (2 * a);
}

export function sequenceResult(d: number, w: number, trials: Trial[]): SeqResult {
  const dx = trials.map((t) => dxAlongAxis(t.from, t.to, t.click));
  const n = dx.length, mean = dx.reduce((s, v) => s + v, 0) / Math.max(1, n);
  const sd = n > 1 ? Math.sqrt(dx.reduce((s, v) => s + (v - mean) ** 2, 0) / (n - 1)) : 0;
  const ae = trials.reduce((s, t, i) => s + dist(t.from, t.to) + dx[i], 0) / Math.max(1, n);
  const we = Math.max(4.133 * sd, 1);                       // 全点在同一处时 SD = 0：给 1 像素下限，免得吞吐变成无穷大
  const mt = trials.reduce((s, t) => s + t.mt, 0) / Math.max(1, n) / 1000;
  const ide = Math.log2(ae / we + 1);
  return { d, w, trials, tp: mt > 0 ? ide / mt : 0, ide, mt, err: trials.filter((t) => !t.hit).length / Math.max(1, n), ae, we };
}

/** 环形目标：n 个点均布在直径 d 的圆上；顺序每次跨到对面（n = 13 时步长 7） */
export function ringTargets(cx: number, cy: number, d: number, n = 13): Pt[] {
  return Array.from({ length: n }, (_, i) => { const a = -Math.PI / 2 + (i * 2 * Math.PI) / n; return { x: cx + (d / 2) * Math.cos(a), y: cy + (d / 2) * Math.sin(a) }; });
}
export const ringOrder = (n = 13) => Array.from({ length: n + 1 }, (_, k) => (k * Math.ceil(n / 2)) % n);

/** 固定种子的伪随机（各设备用同一批条件顺序和目标位置） */
export function rng(seed: number) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export function shuffled<T>(xs: T[], seed: number): T[] {
  const r = rng(seed), a = xs.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

/** 目标辅助（bubble cursor 的选择规则）：选离点击位置最近的那个目标。只看所有目标的几何，不知道哪个是正确目标。 */
export function nearestTarget(targets: Pt[], click: Pt): number {
  let best = 0;
  targets.forEach((t, i) => { if (dist(t, click) < dist(targets[best], click)) best = i; });
  return best;
}
