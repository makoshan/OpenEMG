// 唯理 8 通道腕带串口帧解码，逐行照抄 host/wl8.py 的 decode()（协议说明见那里）。
// 两边必须逐帧一致：改这里先跑 `npm run check`（check-wl8.mjs 拿 Python 解出的结果对拍）。
export const FRAME = 29, EMG = 0xaa, IMU = 0xbb, BAUD = 921600, EMG_HZ = 2000;
// 接收芯片：CP2102（0x10C4 任意 pid）或 CH343（0x1A86:0x55D3），和 wl8.RECEIVERS 一致
export const RECEIVERS = [{ usbVendorId: 0x10c4 }, { usbVendorId: 0x1a86, usbProductId: 0x55d3 }];

export type Decoded = { emg: number[][]; imu: number[][]; seq: number[]; kinds: number[]; tail: Uint8Array };

function findSync(buf: Uint8Array, from: number): number {
  for (let j = from; j + 2 < buf.length; j++) if (buf[j] === 0xd2 && buf[j + 1] === 0xd2 && buf[j + 2] === 0xd2) return j;
  return -1;
}

const int24 = (b: Uint8Array, k: number) => ((b[k] << 16) | (b[k + 1] << 8) | b[k + 2]) << 8 >> 8;   // 有符号 24 bit 大端
const int16 = (b: Uint8Array, k: number) => ((b[k] << 8) | b[k + 1]) << 16 >> 16;

/** 字节 → EMG（µV，n×8）、IMU（原始 int16，m×6）、到达顺序的共用包序号、帧类型、没拼完的尾巴。
 *  按 3 字节帧头重新同步；类型字节不对就跳 1 字节再找。 */
export function decode(buf: Uint8Array): Decoded {
  const emg: number[][] = [], imu: number[][] = [], seq: number[] = [], kinds: number[] = [];
  let i = 0, j = -1;
  for (;;) {
    j = findSync(buf, i);
    if (j < 0 || j + FRAME > buf.length) break;
    const kind = buf[j + 3], p = j + 5;
    if (kind === EMG) emg.push(Array.from({ length: 8 }, (_, c) => int24(buf, p + c * 3)));
    else if (kind === IMU) imu.push(Array.from({ length: 6 }, (_, c) => int16(buf, p + 2 + c * 2)));
    else { i = j + 1; continue; }
    seq.push(buf[j + 4]); kinds.push(kind);
    i = j + FRAME;
  }
  j = findSync(buf, i);
  return { emg, imu, seq, kinds, tail: buf.slice(j < 0 ? i : j) };
}

/** 按 uint8 循环包序号算丢了几包；prev 是上一批最后一个序号（没有就 null） */
export function dropped(seq: number[], prev: number | null = null): number {
  let n = 0, last = prev;
  for (const s of seq) { if (last !== null) n += (s - last - 1 + 256) % 256; last = s; }
  return n;
}
