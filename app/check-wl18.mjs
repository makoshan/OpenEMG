// JS 解码（src/wl18.ts）与 Python 解码（host/wl18.py）对拍：同一段字节，两边逐帧结果必须完全一致。
// 字节：说明书截图 3 帧 + 41/59 两种帧长各一段（中途切换）+ 载荷里藏伪帧头 + 坏类型字节 + 半帧尾巴。
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { decode18 } from './src/wl18.ts';
import { dropped } from './src/wl8.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const PY = process.env.YUANLI_PY ?? (fs.existsSync(path.resolve(here, '..', '.venv', 'bin', 'python')) ? path.resolve(here, '..', '.venv', 'bin', 'python') : 'python3');
const py = String.raw`
import base64, json, numpy as np, wl18
rng = np.random.default_rng(7)
s = bytearray(bytes.fromhex(wl18.MANUAL_41.replace('\n', ' ')))
n = 0x5C
for size, hi in ((41, 1 << 15), (59, 1 << 23), (41, 1 << 15)):
    for k in range(300):
        s += wl18.emg_frame(n & 0xFF, rng.integers(-hi, hi, wl18.N_CH), size); n += 1
        if k % 10 == 0: s += wl18.imu_frame(n & 0xFF, tuple(int(v) for v in rng.integers(-3000, 3000, 6)), size); n += 1
fake = bytearray(wl18.emg_frame(n & 0xFF, np.zeros(wl18.N_CH, int))); fake[10:14] = b'\xd2\xd2\xd2\xaa'; n += 1
s += b'\x00\xd2' + fake[6:]                                                   # 从伪帧头前面开始：不该被认
bad = bytearray(wl18.emg_frame(n & 0xFF, np.ones(wl18.N_CH, int))); bad[3] = 0xCC; n += 1
s += bad
for k in range(5): s += wl18.emg_frame(n & 0xFF, rng.integers(-99, 99, wl18.N_CH)); n += 1
s += wl18.emg_frame(n & 0xFF, np.zeros(wl18.N_CH, int))[:17]                  # 没收完的半帧
s = bytes(s)
emg, imu, seq, kinds, sizes, tail = wl18.decode(s, kinds=True, sizes=True)
print(json.dumps(dict(bytes=base64.b64encode(s).decode(), emg=emg.tolist(), imu=imu.tolist(), seq=seq.tolist(), kinds=kinds.tolist(), sizes=sizes.tolist(), tail=base64.b64encode(tail).decode(), dropped=int(((np.diff(seq.astype(np.int16)) - 1) % 256).sum()))))
`;
const ref = JSON.parse(execFileSync(PY, ['-c', py], { cwd: path.join(here, '..', 'host'), maxBuffer: 1 << 28 }));
const bytes = Buffer.from(ref.bytes, 'base64');

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
let fail = 0;
const expect = (name, ok) => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}`); if (!ok) fail++; };

const whole = decode18(new Uint8Array(bytes));
for (const k of ['emg', 'imu', 'seq', 'kinds', 'sizes']) expect(`18ch 整段 ${k}（${ref[k].length}）`, same(whole[k], ref[k]));
expect('18ch 整段 尾巴', Buffer.from(whole.tail).equals(Buffer.from(ref.tail, 'base64')));
expect(`18ch 整段 丢包 ${ref.dropped}`, dropped(whole.seq) === ref.dropped);
expect('18ch 两种帧长都出现', new Set(ref.sizes).size === 2);

// 像串口一样随机切块喂，带着尾巴拼下一块：结果必须和一次性解完全一样
let seed = 3; const rand = () => ((seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31);
for (let round = 0; round < 20; round++) {
  const acc = { emg: [], imu: [], seq: [], kinds: [], sizes: [] }; let tail = new Uint8Array(0), at = 0;
  while (at < bytes.length) {
    const n = 1 + Math.floor(rand() * 300), chunk = bytes.subarray(at, at + n); at += n;
    const buf = new Uint8Array(tail.length + chunk.length); buf.set(tail); buf.set(chunk, tail.length);
    const d = decode18(buf); tail = d.tail;
    for (const k of Object.keys(acc)) acc[k].push(...d[k]);
  }
  if (!same(acc, { emg: ref.emg, imu: ref.imu, seq: ref.seq, kinds: ref.kinds, sizes: ref.sizes })) { expect(`18ch 切块第 ${round} 轮`, false); break; }
  if (round === 19) expect('18ch 切块 20 轮全一致（每块 1–300 字节）', true);
}
if (fail) { console.error(`${fail} 项不一致`); process.exit(1); }
console.log('18 通道 JS 与 Python 解码逐帧一致');
