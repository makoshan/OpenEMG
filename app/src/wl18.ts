// 唯理 18 通道腕带串口帧解码，逐行照抄 host/wl18.py 的 decode()（协议说明见那里）。
// 两边必须逐帧一致：改这里先跑 `npm run check`（check-wl18.mjs 拿 Python 解出的结果对拍）。
const EMG = 0xaa, IMU = 0xbb;                                   // 和 wl8.ts 同一套帧类型

export const N_CH = 18, BAUD = 2_000_000, EMG_HZ = 2000;
const BYTES_PER_CH: Record<number, number> = { 41: 2, 59: 3 };   // 帧长 → 每路字节数（内置滤波开 / 关）
const UV_PER_COUNT: Record<number, number> = { 41: 1 / 7.5, 59: 1 / 60 };

export type Decoded18 = { emg: number[][]; imu: number[][]; seq: number[]; kinds: number[]; sizes: number[]; tail: Uint8Array };

function findSync(buf: Uint8Array, from: number): number {
  for (let j = from; j + 2 < buf.length; j++) if (buf[j] === 0xd2 && buf[j + 1] === 0xd2 && buf[j + 2] === 0xd2) return j;
  return -1;
}

const head = (b: Uint8Array, k: number) => k + 3 < b.length && b[k] === 0xd2 && b[k + 1] === 0xd2 && b[k + 2] === 0xd2 && (b[k + 3] === EMG || b[k + 3] === IMU);
const signed = (b: Uint8Array, k: number, w: number) => {
  let v = 0;
  for (let i = 0; i < w; i++) v = v * 256 + b[k + i];
  return v >= 2 ** (8 * w - 1) ? v - 2 ** (8 * w) : v;
};
const int16 = (b: Uint8Array, k: number) => ((b[k] << 8) | b[k + 1]) << 16 >> 16;

/** 字节 → EMG（µV，float32 精度，n×18）、IMU（原始 int16，m×6）、共用包序号、帧类型、帧长、没拼完的尾巴。
 *  当前位置和往后 41 或 59 字节处都是帧头才认一帧；看不到下一帧头就留到下一块。 */
export function decode18(buf: Uint8Array): Decoded18 {
  const emg: number[][] = [], imu: number[][] = [], seq: number[] = [], kinds: number[] = [], sizes: number[] = [];
  let i = 0, j = -1;
  for (;;) {
    j = findSync(buf, i);
    if (j < 0 || j + 4 > buf.length) break;
    if (buf[j + 3] !== EMG && buf[j + 3] !== IMU) { i = j + 1; continue; }
    if (j + 45 > buf.length) break;
    let size: number;
    if (head(buf, j + 41)) size = 41;
    else if (j + 63 > buf.length) break;
    else if (head(buf, j + 59)) size = 59;
    else { i = j + 1; continue; }
    const kind = buf[j + 3], p = j + 5, w = BYTES_PER_CH[size];
    if (kind === EMG) emg.push(Array.from({ length: N_CH }, (_, c) => Math.fround(signed(buf, p + c * w, w) * UV_PER_COUNT[size])));
    else imu.push(Array.from({ length: 6 }, (_, c) => int16(buf, p + 2 + c * 2)));
    seq.push(buf[j + 4]); kinds.push(kind); sizes.push(size);
    i = j + size;
  }
  j = findSync(buf, i);
  return { emg, imu, seq, kinds, sizes, tail: buf.slice(j < 0 ? i : j) };
}
