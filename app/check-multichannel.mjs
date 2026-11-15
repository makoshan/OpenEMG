// 2 / 8 / 16 通道前端核心逻辑回归门禁：信号滤波链、放松门、校准底噪与放过、游戏面板映射。
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SignalStream } from './src/emg8/signal.ts';
import { lanePlan, RestSignalGate } from './src/emg8/rest-signal.ts';
import { canWaive, noiseAdvice, noiseFloor, noiseVerdict } from './src/emg8/calibration.ts';
import { bandSignal } from './src/emg8/gesture-actions.ts';

// 1. SignalStream 2 / 8 / 16 通道与 1000 / 2000 Hz 滤波稳态核查
for (const [nCh, fs] of [[2, 1000], [8, 2000], [8, 1000], [16, 1000]]) {
  for (const mode of ['gate', 'view']) {
    const s = new SignalStream(mode, nCh, fs);
    const total = Math.round(fs * 1.6);
    const frames = Array.from({ length: total }, (_, k) =>
      Array.from({ length: nCh }, (_, c) => 45 * Math.sin((2 * Math.PI * 95 * k) / fs + c * 0.3))
    );
    const r = s.push(frames, 1000, 0, 0);
    assert.equal(r.boundary, false);
    assert.equal(r.frames.length, total);
    assert.equal(r.frames[0].length, nCh);
    const vals = s.values();
    assert.ok(Array.isArray(vals) && vals.length === nCh, `${mode} ${nCh}ch@${fs}Hz values`);
    assert.ok(vals.every((v) => Number.isFinite(v) && v > 15 && v < 60), `unexpected RMS: ${vals}`);
  }
}

// 切换通道规格必须自动重置
{
  const s = new SignalStream('gate', 8, 2000);
  s.push(Array.from({ length: 3200 }, () => Array(8).fill(30)), 1000, 0, 0);
  assert.equal(s.values()?.length, 8);
  assert.equal(s.setSpec(16, 1000), true);
  assert.equal(s.values(), null);
}

// 2. RestSignalGate 2 / 8 / 16 通道通过与坏路屏蔽核查
for (const nCh of [2, 8, 16]) {
  const g = new RestSignalGate(150, 'session');
  const low = Array(nCh).fill(35);
  for (let t = 100; t <= 2200; t += 100) g.observe(low, t, t);
  assert.equal(g.status(2200).allowed, true, `RestSignalGate should pass for ${nCh}ch`);
}
// 2 通道不能同时屏蔽全部 2 路；两路全高判发力而非单路接触
{
  const g2 = new RestSignalGate(150, 'periodic');
  for (let t = 100; t <= 3600; t += 100) g2.observe([240, 260], t, t);
  const st = g2.status(3600);
  assert.equal(st.allowed, false);
  assert.deepEqual(st.stuck, []);
  assert.match(st.text, /手还在用力/);
  assert.deepEqual(lanePlan([1, 2], [0.85, 0.82]).mask, []);
  assert.deepEqual(lanePlan([1], [0.85, 0.82]).mask, [1]);
}
// 16 通道单路或双路接触差可屏蔽
{
  const drop16 = Array(16).fill(0.91);
  const p16 = lanePlan([3, 14], drop16);
  assert.deepEqual(p16.mask, [3, 14]);
  assert.equal(p16.estimate, 0.91);
}

// 3. 校准底噪、放过上限与建议文案
for (const nCh of [2, 8, 16]) {
  const hist = [
    { t: 1000, rms: Array(nCh).fill(42) },
    { t: 2500, rms: Array.from({ length: nCh }, (_, i) => (i === nCh - 1 ? 210 : 38)) },
  ];
  const fl = noiseFloor(hist, 2600);
  assert.equal(fl?.length, nCh);
  assert.equal(fl[nCh - 1], 42);
  const badVec = Array.from({ length: nCh }, (_, i) => (i === 0 ? 220 : 40));
  const v = noiseVerdict(badVec, 150);
  assert.equal(v.kind, 'bad');
  assert.deepEqual(v.bad, [1]);
  assert.equal(canWaive(v, null, nCh), true);
  assert.match(noiseAdvice(v, 150, nCh), new RegExp(`其余 ${nCh - 1} 路正常`));
}
// 2 通道两路全红禁止放过
assert.equal(canWaive(noiseVerdict([220, 210], 150), null, 2), false);
// 16 通道两路红允许放过，三路红禁止放过
assert.equal(canWaive(noiseVerdict([220, 210, ...Array(14).fill(35)], 150), null, 16), true);
assert.equal(canWaive(noiseVerdict([220, 210, 195, ...Array(13).fill(35)], 150), null, 16), false);

// 4. 掌中天劫游戏面板 2 / 8 / 16 路状态映射
const okCheck = { allowed: true, high: [], over: [], text: '放松检查通过' };
const b16 = bandSignal(okCheck, [15], true, 16);
assert.equal(b16.lanes.length, 8);
assert.equal(b16.lanes[7], 'mask');
assert.equal(b16.signal, '第 15 路接触差 · 已屏蔽，用 15 路识别');
const b2 = bandSignal(okCheck, [1], true, 2);
assert.equal(b2.lanes.length, 8);
assert.equal(b2.signal, '第 1 路接触差 · 已屏蔽，用 1 路识别');

// 5. 5 档设备入口与多通道样式契约检查
const mainSrc = readFileSync(new URL('./src/main.tsx', import.meta.url), 'utf8');
for (const tier of ['c08b-16ch', 'wl8', 'c08b-8ch', 'c08b-2ch', 'emg']) {
  assert.ok(mainSrc.includes(`id: '${tier}'`), `missing device tier ${tier} in main.tsx`);
}
const cssSrc = readFileSync(new URL('./src/emg8/emg8.css', import.meta.url), 'utf8');
for (const n of [2, 8, 16]) {
  assert.ok(cssSrc.includes(`data-channels="${n}"`), `missing CSS rule for data-channels="${n}"`);
}

console.log('check-multichannel OK (2 / 8 / 16 channels verified)');
