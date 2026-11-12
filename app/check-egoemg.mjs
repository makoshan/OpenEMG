// EgoEMG 六手势（穿插录制）自检：动作组定义、每轮随机顺序、示范图素材。由 check-seal-game.mjs 带进 CI。
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { calibrationPlan, cellIndex, startCalibration } from './src/emg8/calibration.ts';

const profiles = JSON.parse(readFileSync(new URL('./electron/emg8-profiles.json', import.meta.url)));
const ego = profiles['egoemg-six'];
assert.ok(ego, '缺 egoemg-six 动作组');
assert.equal(ego.protocol, 'select');
assert.deepEqual(ego.calibrate, { rounds: 10, minRatio: 2.5, minTrain: 3, shuffle: true });
assert.equal(ego.labels.length, 6);
assert.equal(ego.labels[0], 'ego_rest', '第一类必须是放松（识别页把第一类当放松）');
for (const l of ego.labels) {
  const g = ego.gestures[l];
  assert.ok(g?.name && g.icon && g.color && g.cue && g.voice, `${l} 缺字段`);
  assert.ok(['rest', 'hold', 'cont'].includes(g.kind), `${l} 种类 ${g.kind}`);
}
assert.deepEqual(ego.labels.filter((l) => ego.gestures[l].kind === 'cont'), ['ego_thumb_slide', 'ego_index_bow']);
// 其它组不受 shuffle 影响
for (const [id, p] of Object.entries(profiles)) if (id !== 'egoemg-six') assert.ok(!p.calibrate?.shuffle, `${id} 不该开 shuffle`);

// 轮序：不给随机源与改动前逐字相同
const L = ego.labels;
assert.deepEqual(calibrationPlan(L, 3), [...L, ...L, ...L]);
assert.deepEqual(calibrationPlan(['ego_rest'], 1), ['ego_rest']);
// 给随机源：每轮都是六类的一个排列；全程相邻两条不同类；轮与轮的顺序确实在变
const lcg = (seed) => () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
const firsts = new Set();
let collisionsAvoided = 0;
for (let seed = 1; seed <= 300; seed++) {
  const plan = calibrationPlan(L, 10, lcg(seed));
  assert.equal(plan.length, 60);
  for (let r = 0; r < 10; r++) assert.deepEqual([...plan.slice(r * 6, r * 6 + 6)].sort(), [...L].sort(), `seed ${seed} 第 ${r + 1} 轮不是排列`);
  for (let i = 1; i < plan.length; i++) assert.notEqual(plan[i], plan[i - 1], `seed ${seed} 第 ${i} 条和前一条同类`);
  firsts.add(plan[0]);
  // 不做交界处理时会撞的次数（证明交界规则真的被用到）
  const raw = []; const rnd = lcg(seed);
  for (let r = 0; r < 10; r++) { const x = [...L]; for (let i = x.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [x[i], x[j]] = [x[j], x[i]]; } if (raw.length && x[0] === raw.at(-1)) collisionsAvoided++; raw.push(...x); }
}
assert.equal(firsts.size, 6, '每一类都应该有机会排第一');
assert.ok(collisionsAvoided > 50, `交界规则应被触发多次，实际 ${collisionsAvoided}`);
// 进度格：打乱后按计划找格子，每一格都对应它列头的手势（r*n+c 会错位）
{ const plan = calibrationPlan(L, 10, lcg(11)); let misplaced = 0;
  for (let r = 0; r < 10; r++) L.forEach((l, c) => { const k = cellIndex(plan, r, 6, l); assert.equal(plan[k], l, `第 ${r + 1} 轮 ${l} 格错位`); if (plan[r * 6 + c] !== l) misplaced++; });
  assert.ok(misplaced > 0, '用 r*n+c 应当会错位，否则这条测不到');
  const part = plan.slice(0, 9);   // 第 2 轮只排了 3 条
  assert.equal(cellIndex(part, 1, 6, plan.slice(6, 12).find((l) => !part.slice(6).includes(l))), -1, '这一轮还没排到的手势返回 -1'); }
// 补一轮：新计划第一条不和上一计划最后一条同类
for (let seed = 1; seed <= 200; seed++) for (const after of L) assert.notEqual(calibrationPlan(L, 1, lcg(seed), after)[0], after);
const cal = startCalibration(L, 10, lcg(7));
assert.equal(cal.plan.length, 60); assert.equal(cal.marks.length, 60); assert.equal(cal.i, 0);

// 示范图：fist-guide.tsx 里每个 ego_* 都有素材表项，且对应的首帧图片存在
const guide = readFileSync(new URL('./src/emg8/fist-guide.tsx', import.meta.url), 'utf8');
for (const l of L) {
  const m = guide.match(new RegExp(`${l}: \\{ file: '([a-z_0-9]+)'`));
  assert.ok(m, `fist-guide 缺 ${l} 素材表项`);
  assert.ok(existsSync(new URL(`./public/images/emg8-meta/${m[1]}-first.png`, import.meta.url)), `缺图片 ${m[1]}-first.png`);
}
console.log('check-egoemg ok', { collisionsAvoided });
