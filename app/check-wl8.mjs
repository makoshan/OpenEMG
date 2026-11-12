// JS 解码（src/wl8.ts）与 Python 解码（host/wl8.py）对拍：同一段字节，两边逐帧结果必须完全一致。
// 用法：npm run check            （卖家 XCOM 实拍 6 帧 + 合成帧 + 坏帧/垃圾/截断尾）
//       npm run check -- <录音.npz>（再加一段真实录音重新封帧）
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { decode, dropped } from './src/wl8.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const PY = process.env.YUANLI_PY ?? (fs.existsSync(path.resolve(here, '..', '.venv', 'bin', 'python')) ? path.resolve(here, '..', '.venv', 'bin', 'python') : 'python3');
const py = String.raw`
import base64, json, sys, numpy as np, wl8
rng = np.random.default_rng(7)
s = bytes.fromhex(wl8.XCOM_ROWS.replace('\n', ' '))
for label in ('rest', 'fist', 'pinch'):
    frames, _ = wl8._synth_frames(label, rng, seconds=0.5)
    s += frames
bad = bytearray(wl8._frame(wl8.EMG, 7, bytes(range(24)))); bad[3] = 0xCC     # 类型字节坏：跳 1 字节重找
s += b'\x00\xd2\xd2' + bytes(bad) + b'\xd2\xd2\xd2\xaa' + wl8._frame(wl8.EMG, 8, bytes(24))
if len(sys.argv) > 1:                       # 真实录音重新封帧：EMG 每 10 帧插 1 帧 IMU，序号连续
    with np.load(sys.argv[1]) as z: emg, imu = z['emg_uv'], z['imu']
    n, k = 0, 0
    for r, row in enumerate(emg):
        s += wl8._frame(wl8.EMG, n & 0xFF, b''.join(int(v).to_bytes(3, 'big', signed=True) for v in row)); n += 1
        if r % 10 == 9 and k < len(imu):
            s += wl8._frame(wl8.IMU, n & 0xFF, bytes(2) + b''.join(int(v).to_bytes(2, 'big', signed=True) for v in imu[k]) + bytes(10)); n += 1; k += 1
s += wl8._frame(wl8.EMG, 9, bytes(24))[:17]                                # 没收完的半帧
emg, imu, seq, kinds, tail = wl8.decode(s, kinds=True)
print(json.dumps(dict(bytes=base64.b64encode(s).decode(), emg=emg.tolist(), imu=imu.tolist(), seq=seq.tolist(), kinds=kinds.tolist(), tail=base64.b64encode(tail).decode(), dropped=wl8.dropped(seq))))
`;
const ref = JSON.parse(execFileSync(PY, ['-c', py, ...process.argv.slice(2)], { cwd: path.join(here, '..', 'host'), maxBuffer: 1 << 28 }));
const bytes = Buffer.from(ref.bytes, 'base64');

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
let fail = 0;
const expect = (name, ok) => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}`); if (!ok) fail++; };

// 1. 一次性解
const whole = decode(new Uint8Array(bytes));
for (const k of ['emg', 'imu', 'seq', 'kinds']) expect(`整段 ${k}（${ref[k].length}）`, same(whole[k], ref[k]));
expect('整段 尾巴', Buffer.from(whole.tail).equals(Buffer.from(ref.tail, 'base64')));
expect(`整段 丢包 ${ref.dropped}`, dropped(whole.seq) === ref.dropped);

// 2. 像串口一样随机切块喂，带着尾巴拼下一块：结果必须和一次性解完全一样
let seed = 1; const rand = () => ((seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31);
for (let round = 0; round < 20; round++) {
  const acc = { emg: [], imu: [], seq: [], kinds: [] }; let tail = new Uint8Array(0), at = 0, lost = 0, prev = null;
  while (at < bytes.length) {
    const n = 1 + Math.floor(rand() * 300), chunk = bytes.subarray(at, at + n); at += n;
    const buf = new Uint8Array(tail.length + chunk.length); buf.set(tail); buf.set(chunk, tail.length);
    const d = decode(buf); tail = d.tail;
    for (const k of Object.keys(acc)) acc[k].push(...d[k]);
    lost += dropped(d.seq, prev); if (d.seq.length) prev = d.seq.at(-1);
  }
  if (!same(acc, { emg: ref.emg, imu: ref.imu, seq: ref.seq, kinds: ref.kinds }) || lost !== ref.dropped) { expect(`切块第 ${round} 轮`, false); break; }
  if (round === 19) expect('切块 20 轮全一致（每块 1–300 字节）', true);
}
if (fail) { console.error(`${fail} 项不一致`); process.exit(1); }
console.log('JS 与 Python 解码逐帧一致');
