// 显示及放松门使用的滤波统计；不改录制原值和分类特征。
// 两条链（2026-10-15 Mako 定）：gate = 放松检查、戴好检查和 82.5 / 150 µV 两条线用的口径，20 Hz 四阶巴特沃斯高通 + 50 Hz 陷波（Q=5）+ 2、3 次谐波陷波（Q=30）；
//   基波 Q=30 → 5（2026-10-25 Mako 定，evidence/2026-10-25-gate-q5）：Q=30 建立约 190 ms，工频强度一变就漏 100–300 ms 被当成动作；谐波保持 Q=30，全改会挖掉 50–150 Hz 肌电、门读数低 12%。八通道 HTML 页仍是 Q=30；
// view = 只给波形和读数看的唯理式去噪，45 Hz 十四阶巴特沃斯高通 + 50 Hz 各次谐波到 900 Hz 的定宽 6 Hz 陷波（evidence/2026-10-15-weili-filter-loo I 节：放松过黄线 19→6，识别不用它）。
export const FS = 2000;

type Coef = [number, number, number, number, number];      // b0 b1 b2 a1 a2（a0 归一）

function highpass(f: number, q: number): Coef {
  const w = (2 * Math.PI * f) / FS, c = Math.cos(w), al = Math.sin(w) / (2 * q), a0 = 1 + al;
  return [(1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0, (-2 * c) / a0, (1 - al) / a0];
}
function notch(f: number, q: number): Coef {
  const w = (2 * Math.PI * f) / FS, c = Math.cos(w), al = Math.sin(w) / (2 * q), a0 = 1 + al;
  return [1 / a0, (-2 * c) / a0, 1 / a0, (-2 * c) / a0, (1 - al) / a0];
}

export type FilterChain = 'gate' | 'view';
/** 巴特沃斯高通拆成 order/2 个双二阶：第 k 节 Q = 1 / (2 sin((2k−1)π / 2·order))，和 scipy butter(order, f, 'highpass', output='sos') 同一组极点 */
function butterHighpass(f: number, order: number): Coef[] {
  return Array.from({ length: order / 2 }, (_, k) => highpass(f, 1 / (2 * Math.sin(((2 * k + 1) * Math.PI) / (2 * order)))));
}

/** 定宽陷波：α = tan(π·bw/FS)，每个谐波的 −3 dB 宽都是 bw Hz（和 scipy iirnotch(f, f/bw) 同一只滤波器）。
 *  上面 notch(f, q) 的 α = sin(ω0)/(2Q) 是模拟原型的 Q，数字带宽随频率收窄（复核：f/6 写法在 900 Hz 只剩 0.65 Hz）；gate 链沿用 notch 不改。 */
function notchBw(f: number, bw: number): Coef {
  const w = (2 * Math.PI * f) / FS, c = Math.cos(w), al = Math.tan((Math.PI * bw) / FS), a0 = 1 + al;
  return [1 / a0, (-2 * c) / a0, 1 / a0, (-2 * c) / a0, (1 - al) / a0];
}

/** 8 路独立的双二阶级联；process 原地返回滤波后的一帧 */
export class DisplayFilter {
  private coefs: Coef[];
  private z: Float64Array;                                 // 每级每路两个状态
  constructor(mains = 50, channels = 8, chain: FilterChain = 'gate') {
    if (chain === 'view') {
      // 陷波定宽 6 Hz，只陷到 900 Hz：50 Hz 市电的 950 Hz 已贴近 1000 Hz 奈奎斯特，60 Hz 市电的 1080 Hz 放不下，统一到 900 为止
      this.coefs = butterHighpass(45, 14);
      if (mains) for (let f = mains; f <= 900; f += mains) this.coefs.push(notchBw(f, 6));
    } else {
      this.coefs = [highpass(20, 0.5412), highpass(20, 1.3066)];
      if (mains) for (const k of [1, 2, 3]) this.coefs.push(notch(mains * k, k === 1 ? 5 : 30));
    }
    this.z = new Float64Array(this.coefs.length * channels * 2);
  }
  // 新段按首帧直流稳态初始化，避免电极直流偏置制造启动尖峰；系数不变。
  reset(frame: number[]) {
    this.z.fill(0);
    for (let c = 0; c < frame.length; c++) {
      let x = frame[c];
      for (let s = 0; s < this.coefs.length; s++) {
        const [b0, b1, b2, a1, a2] = this.coefs[s], i = (s * frame.length + c) * 2;
        const y = x * (b0 + b1 + b2) / (1 + a1 + a2);
        this.z[i] = y - b0 * x; this.z[i + 1] = b2 * x - a2 * y; x = y;
      }
    }
  }
  process(frame: number[]): number[] {
    const out: number[] = Array.from({ length: frame.length }, () => 0);
    for (let c = 0; c < frame.length; c++) {
      let x = frame[c];
      for (let s = 0; s < this.coefs.length; s++) {
        const [b0, b1, b2, a1, a2] = this.coefs[s], i = (s * frame.length + c) * 2;
        const y = b0 * x + this.z[i];
        this.z[i] = b1 * x - a1 * y + this.z[i + 1];
        this.z[i + 1] = b2 * x - a2 * y;
        x = y;
      }
      out[c] = x;
    }
    return out;
  }
}

/** 滑动均方根：最近 n 个样本 */
export class Rms {
  private sq: Float64Array; private sum: Float64Array; private buf: Float64Array; private i = 0; private filled = 0;
  constructor(private n = 1000, private ch = 8) { this.buf = new Float64Array(n * ch); this.sq = new Float64Array(ch); this.sum = this.sq; }
  push(frame: number[]) {
    for (let c = 0; c < this.ch; c++) {
      const v = frame[c] * frame[c], j = this.i * this.ch + c;
      this.sum[c] += v - this.buf[j]; this.buf[j] = v;
    }
    this.i = (this.i + 1) % this.n; this.filled = Math.min(this.filled + 1, this.n);
  }
  values(): number[] { return Array.from(this.sum, (s) => Math.sqrt(Math.max(0, s) / Math.max(1, this.filled))); }
}

// 先让陷波状态稳定，再收满半秒统计；准备期绝不以零幅度冒充放松。
export const FILTER_SETTLE_SAMPLES = FS;
export const RMS_SAMPLES = FS / 2;
export const STREAM_GAP_MS = 300;
export class SignalStream {
  private filter: DisplayFilter;
  private rms = new Rms(RMS_SAMPLES);
  private count = 0;
  private last: number | null = null;
  private index: number | null = null;
  private dropped: number | null = null;
  constructor(private chain: FilterChain = 'gate') { this.filter = new DisplayFilter(50, 8, chain); }
  reset() { this.filter = new DisplayFilter(50, 8, this.chain); this.rms = new Rms(RMS_SAMPLES); this.count = 0; this.last = this.index = this.dropped = null; }
  expire(now: number) { if (this.last !== null && (now < this.last || now - this.last > STREAM_GAP_MS)) { this.reset(); return true; } return false; }
  push(rows: number[][], now: number, end: number | null, dropped: number) {
    let boundary = this.expire(now);
    if (!rows.length) return { frames: [], boundary };
    if (rows.some(f => f.length !== 8 || f.some(x => !Number.isFinite(x)))) { this.reset(); return { frames: [], boundary: true }; }
    if ((this.index !== null && end !== null && end - rows.length !== this.index) || (this.dropped !== null && dropped !== this.dropped)) { this.reset(); boundary = true; }
    if (!this.count) this.filter.reset(rows[0]);
    const frames = rows.map(row => { const f = this.filter.process(row); if (++this.count > FILTER_SETTLE_SAMPLES) this.rms.push(f); return f; });
    this.last = now; this.index = end; this.dropped = dropped;
    return { frames, boundary };
  }
  values() { return this.count >= FILTER_SETTLE_SAMPLES + RMS_SAMPLES ? this.rms.values() : null; }
}
