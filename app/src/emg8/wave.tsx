'use client';
// N 路肌电滚动波形（默认 8 路；单通道工作室传 channels=1）（webgl-plot 的 WebglLineRoll，一个 canvas 画完 8 条细线）+ 3 轴陀螺小窗。
// 父组件通过 ref.push() 喂滤波后的帧；这里按 4:1 抽稀到 500 点/秒（每 4 个样本取绝对值最大的一个，尖峰不丢）。
import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef } from 'react';
import { ColorRGBA, WebglLineRoll, WebglPlot } from 'webgl-plot';
import { CH_COLORS } from './contract';

export type WaveHandle = { push: (frames: number[][]) => void; pushGyro: (rows: number[][]) => void };
const DECIM = 4, DISPLAY_HZ = 500, GYRO_HZ = 222;
const GYRO_COLORS = ['#EF4444', '#22C55E', '#3B82F6'];                  // 模块常量：每次渲染传新数组会让 WebGL 反复重建
// WebglLineRoll.setLineColor 把颜色写进 Uint8Array：分量要 0–255，不是 ColorRGBA 常见的 0–1（写 0–1 会全变黑）
const rgba = (hex: string) => new ColorRGBA(parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16), 255);

function useRoll(canvas: React.RefObject<HTMLCanvasElement | null>, lines: number, points: number, colors: string[]) {
  const roll = useRef<{ plot: WebglPlot; roll: WebglLineRoll } | null>(null);
  useEffect(() => {
    const c = canvas.current; if (!c) return;
    const make = () => {
      const dpr = window.devicePixelRatio || 1;
      c.width = Math.max(1, c.clientWidth * dpr); c.height = Math.max(1, c.clientHeight * dpr);
      // transparent / preserveDrawing 是 webgl-plot 1.1.2 实际支持但类型里没声明的选项：不开 transparent 画布是不透明黑底；
      // preserveDrawing 让截图和读像素能拿到画面（验收要用）
      const hidden = { transparent: true, preserveDrawing: true } as object;
      const plot = new WebglPlot(c, { antialias: true, backgroundColor: [0, 0, 0, 0], ...hidden });
      const r = new WebglLineRoll(plot.gl, points, lines);
      colors.forEach((col, i) => r.setLineColor(rgba(col), i));
      roll.current = { plot, roll: r };
    };
    make();
    let raf = 0;
    const draw = () => { const r = roll.current; if (r) { r.plot.clear(); r.roll.draw(); } raf = requestAnimationFrame(draw); };
    raf = requestAnimationFrame(draw);
    const ro = new ResizeObserver(() => make()); ro.observe(c);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); roll.current = null; };
  }, [canvas, lines, points, colors]);
  return roll;
}

export const Waveform = forwardRef<WaveHandle, { rangeUv: number; seconds?: number; rms?: number[]; showGyro?: boolean; channels?: number; fsHz?: number; unit?: string }>(
  function Waveform({ rangeUv, seconds = 4, rms, showGyro = true, channels: n = 8, fsHz = 2000, unit = 'µV' }, ref) {
    const emgCanvas = useRef<HTMLCanvasElement>(null), gyroCanvas = useRef<HTMLCanvasElement>(null);
    const colors = useMemo(() => Array.from({ length: n }, (_, i) => CH_COLORS[i % CH_COLORS.length]), [n]);   // 同一数组引用：每次渲染新数组会让 WebGL 反复重建
    const decim = Math.max(1, Math.round(fsHz / DISPLAY_HZ));
    const emg = useRoll(emgCanvas, n, seconds * DISPLAY_HZ, colors);
    const gyro = useRoll(gyroCanvas, 3, seconds * GYRO_HZ, GYRO_COLORS);
    const acc = useRef<{ n: number; best: number[] }>({ n: 0, best: Array.from({ length: n }, () => 0) });
    const range = useRef(rangeUv);
    useEffect(() => { range.current = rangeUv; }, [rangeUv]);
    useEffect(() => { acc.current = { n: 0, best: Array.from({ length: n }, () => 0) }; }, [n, decim]);

    useImperativeHandle(ref, () => ({
      push(frames) {
        const r = emg.current; if (!r) return;
        const out: number[][] = Array.from({ length: n }, () => []);
        const a = acc.current, lane = 2 / n;
        if (a.best.length !== n) { a.n = 0; a.best = Array.from({ length: n }, () => 0); }
        for (const f of frames) {
          for (let c = 0; c < n; c++) if (Math.abs(f[c]) > Math.abs(a.best[c])) a.best[c] = f[c];
          if (++a.n < decim) continue;
          for (let c = 0; c < n; c++) {
            const v = Math.max(-1, Math.min(1, a.best[c] / range.current));
            out[c].push(1 - lane * (c + 0.5) + v * lane * 0.45); a.best[c] = 0;
          }
          a.n = 0;
        }
        if (out[0].length) r.roll.addPoints(out);
      },
      pushGyro(rows) {
        const r = gyro.current; if (!r || !rows.length) return;
        const out: number[][] = [[], [], []];
        for (const row of rows) for (let k = 0; k < 3; k++) out[k].push(Math.max(-1, Math.min(1, (row[k] * 0.0012) / 2)) * 0.9);   // ±2 rad/s 满量程
        r.roll.addPoints(out);
      },
    }), [emg, gyro, n, decim]);

    return <div className="emg8-wave" data-channels={n}>
      <div className="emg8-wave-emg" data-channels={n} style={{ ['--ch-count' as string]: n }}>
        <canvas ref={emgCanvas} aria-label={`${n} 路肌电实时波形`} />
        <ol className="emg8-lanes">{colors.map((col, c) => <li key={c}><b style={{ color: col }}>CH{c + 1}</b><span>{rms && rms[c] != null ? `${rms[c].toFixed(0)} ${unit}` : '—'}</span></li>)}</ol>
      </div>
      {showGyro && <div className="emg8-wave-gyro"><canvas ref={gyroCanvas} aria-label="陀螺仪三轴" /><span>陀螺 ±2 rad/s</span></div>}
    </div>;
  });
