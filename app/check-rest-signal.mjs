import assert from 'node:assert/strict';
import { BREAK_MS, lanePlan, RestSignalGate, SIGNAL_VALID_MS } from './src/emg8/rest-signal.ts';
import { askRestFor, calibrationHolds, canWaive, contactGate, doneActions, noiseFloor, pauseHistory, noiseVerdict, scoreVerdict, startCalibration, stopForRelaxationNoise, waiveCal, waiveNoise } from './src/emg8/calibration.ts';
const low = Array(8).fill(50), high = low.map((v, i) => i === 1 ? 400 : v);
function feed(g, from, to, values = low) { for (let t = from; t <= to; t += 100) g.observe(values, t, t); }
const g = new RestSignalGate(); g.reset(1000);
feed(g, 1000, 2700); assert.equal(g.status(2700).allowed, false, '短暂低值不能通过');
g.observe(low, 2800, 2800); assert.equal(g.status(2800).allowed, true);
feed(g, 2900, 8900, high); assert.equal(g.status(8900).allowed, true, '持续动作不判接触坏');
const hist = Array.from({ length: 41 }, (_, i) => ({ t: 4900 + i * 100, rms: high }));
assert.equal(noiseVerdict(noiseFloor(hist, 8900), 150).kind, 'bad', '旧算法反例必须触发，不能假通过');
feed(g, 9000, 2800 + SIGNAL_VALID_MS, high);
assert.equal(g.status(12800).allowed, false, '高幅动作不能永久续期');
feed(g, 12900, 18000, high); assert.equal(g.status(18000).allowed, false, '单路持续异常不能通过放松检查');
assert.match(g.status(18000).text, /^第 2 路电极没贴好/, '1–2 路连续过线满 3 秒说接触');
{ const t = new RestSignalGate(); t.reset(1000); feed(t, 1000, 2000, high); assert.match(t.status(2000).text, /^请放松：第 2 路偏高/, '刚过线不到 3 秒不说接触'); }
feed(g, 18100, 20000, Array(8).fill(400)); assert.equal(g.status(20000).allowed, false, '多路异常同样拦住');
assert.match(g.status(20000).text, /^手还在用力：完全松开 2 秒/, '≥3 路高说手在用力，不说电极');
{
  const q = new RestSignalGate(); q.reset(1000);
  q.observe(low, 1000, 1000);
  assert.match(q.status(1300).text, /再等 1\.5 秒/, '松开后先把剩余时间倒出来');
  for (let t = 1600; t <= 2000; t += 100) q.observe(low, t, t);
  assert.match(q.status(2000).text, /再保持 0\.8 秒/, '安静段要倒计时');
  assert.equal(q.status(2000).allowed, false, '倒计时没走完不能通过');
}
feed(g, 20100, 21300); assert.equal(g.status(21300).allowed, true, '连续正常后可恢复');
assert.equal(g.status(21300 + BREAK_MS).allowed, true, '短暂不连续（≤2 s）沿用通过：丢帧不重查');
assert.equal(g.status(21301 + BREAK_MS).allowed, false, '断开超过 2 s 不沿用旧通过状态');
for (const invalid of [[50], [...low.slice(0, 7), NaN], low.map(() => -1)]) {
  const x = new RestSignalGate(); x.reset(1000); feed(x, 1000, 2800);
  x.observe(invalid, 2900, 2900); assert.equal(x.status(2900).allowed, false);
}
{ // 没有 RMS（显示滤波稳定期）不是坏数值：不撤销已有放行，也不能当放松累积
  const x = new RestSignalGate(); x.reset(1000); feed(x, 1000, 2800);
  x.observe(null, 2900, 2900); assert.equal(x.status(2900).allowed, true, '空 RMS 不撤销放行');
  const z = new RestSignalGate(); z.reset(1000);
  for (let t = 1000; t <= 5000; t += 100) { z.heartbeat(t); z.observe(null, t, t); }
  assert.equal(z.status(5000).allowed, false, '空 RMS 不能当放松通过');
}
const x = new RestSignalGate(); x.reset(1000);
for (let t = 1000; t < 6000; t += 100) x.observe(low, 1000, t);
assert.equal(x.status(6000).allowed, false, '重复旧批次不能完成检查');
const y = new RestSignalGate(); y.reset(1000);
for (let t = 1000; t < 6000; t += 100) { const v = [...low]; v[Math.floor(t / 100) % 8] = 400; y.observe(v, t, t); }
assert.equal(y.status(6000).allowed, false, '各通道交替坏不能拼出虚假正常底噪');
console.log('放松信号门检查通过：动作反例、旧算法必失败、单/多路异常、恢复、过期、断流、无效与重复数据');

// 屏蔽坏路：第 2 路持续过线 → 屏蔽它后放松检查能通过，over 仍报第 2 路；取消屏蔽又拦住
{
  const m = new RestSignalGate(); m.reset(1000); feed(m, 1000, 3000, high);
  assert.equal(m.status(3000).allowed, false); assert.deepEqual(m.status(3000).over, [2]);
  assert.deepEqual(m.status(3000).stuck, [], '过线不到 LANE_HOLD_MS 不算坏路');
  feed(m, 3100, 4000, high); assert.deepEqual(m.status(4000).stuck, [2], '连续过线满 3 秒才算坏路');
  m.setIgnore([2]); feed(m, 4100, 5500, high);
  assert.equal(m.status(5500).allowed, true, '屏蔽后放松检查通过'); assert.deepEqual(m.status(5500).over, [2]);
  feed(m, 5600, 6000 + SIGNAL_VALID_MS, high); assert.deepEqual(m.status(6000 + SIGNAL_VALID_MS).stuck, [2], '有效期到期重检时坏路仍算坏路，不闪断');
  const k = new RestSignalGate(); k.reset(1000); feed(k, 1000, 2900, high); feed(k, 3000, 3000); feed(k, 3100, 4500, high);
  assert.deepEqual(k.status(4500).stuck, [], '中间回落过一次就重新计时');
  const j = new RestSignalGate(); j.reset(1000); feed(j, 1000, 2900, high); feed(j, 3500, 4500, high);
  assert.deepEqual(j.status(4500).stuck, [], '数据断过就重新计时');
  // 复核 #55 P1：页面在断流时先调 reset（last 清零），恢复后第一帧仍过线，也不能把断流时间算进连续
  const r = new RestSignalGate(); r.reset(1000); feed(r, 1000, 1200, high); r.reset(1300); r.observe(high, 4700, 4700);
  assert.deepEqual(r.status(4700).stuck, [], '外部 reset 后断流也要重新计时');
  // 复核 #55 P2：已屏蔽的第 2 路回落一帧又回来，重新计时期间不能靠旧屏蔽通过放松检查
  const q = new RestSignalGate(); q.reset(1000); feed(q, 1000, 4100, high); q.setIgnore([2]); q.observe(low, 4200, 4200); feed(q, 4300, 6000, high);
  assert.equal(q.status(6000).allowed, false, '回落后重新起算的路不能被旧屏蔽放过');
  // 复核 #55 P3：有效期到期时 status 先于 observe 调用，stuck 不能空一拍
  const o = new RestSignalGate(); o.reset(1000); feed(o, 1000, 4100, high); o.setIgnore([2]); feed(o, 4200, 5400, high);
  assert.equal(o.status(5400).allowed, true); feed(o, 5500, 15300, high);
  assert.deepEqual(o.status(15450).stuck, [2], '到期那一拍 stuck 不闪断');
  const n = new RestSignalGate(); n.reset(1000); n.setIgnore([3]); feed(n, 1000, 3000, high);
  assert.equal(n.status(3000).allowed, false, '屏蔽别的路不放过第 2 路');
}
const drop = [.9, .7, .9, .9, .9, .9, .5, .9];
assert.deepEqual(lanePlan([2], drop), { mask: [2], estimate: .7 });
assert.deepEqual(lanePlan([2, 7], drop), { mask: [], estimate: .5 }, '缺了认不准就不屏蔽');
assert.deepEqual(lanePlan([1, 2, 3], drop).mask, [], '≥3 路不屏蔽');
assert.deepEqual(lanePlan([], drop).mask, []);
assert.deepEqual(lanePlan([7], null), { mask: [7], estimate: null }, '旧模型没有估计也屏蔽');
console.log('屏蔽坏路检查通过');

// 「仍然开始」：1–2 路过线可以放过，≥3 路不行；放过的路不再拦，新过线的路照旧拦，累计不能超过 2 路
{
  const at = (lanes, v = 400) => low.map((x, i) => lanes.includes(i + 1) ? v : x);
  const two = noiseVerdict(at([1, 2]), 150), three = noiseVerdict(at([1, 2, 5]), 150), yellow = noiseVerdict(at([3], 100), 150);
  assert.equal(canWaive(two, null), true, '2 路过线可以仍然开始');
  assert.equal(canWaive(three, null), false, '3 路过线照旧拦');
  assert.equal(canWaive(yellow, null), false, '只有黄色偏高本来就不拦，不出仍然开始');
  assert.equal(calibrationHolds(yellow), false, '黄线只提醒，校准照常录（Mako 2026-10-15）');
  assert.equal(calibrationHolds(two), true, '过红线才停');
  assert.equal(calibrationHolds(noiseVerdict(at([1, 2, 3, 4, 5, 6, 7, 8], 140), 150)), false, '8 路都在 140 µV 也只是黄线，不停');
  assert.equal(calibrationHolds(noiseVerdict([50, 50, 50, 50, 50, 50, 50, 151], 150)), true, '一路刚过 150 µV 就停');
  assert.equal(canWaive(noiseVerdict(low, 150), null), false, '正常时不出按钮');
  assert.equal(waiveNoise(two, [1, 2]).kind, 'ok', '放过后不再拦');
  assert.equal(waiveNoise(yellow, []).kind, 'ok', '放过后黄色偏高不拦');
  assert.equal(waiveNoise(two, null).kind, 'bad', '没放过照旧拦');
  const moved = noiseVerdict(at([1, 5]), 150);
  assert.deepEqual(waiveNoise(moved, [1, 2]).bad, [5], '放过的以外又有一路过线，照旧拦');
  assert.equal(canWaive(moved, [1, 2]), false, '放过的加新过线超过 2 路，不能再放');
  assert.equal(canWaive(noiseVerdict(at([2]), 150), [1]), true, '累计 2 路以内可以再放');
  // 2026-10-16 截图：校准完认对 100%，之后第 1、2 路 259/252 µV、其余 62–85 µV，完成页只剩灰按钮。放过后 restDue 清掉，按分数走
  const done = noiseVerdict([259, 252, 85, 64, 62, 69, 65, 65], 150);
  assert.equal(canWaive(done, undefined), true, '完成页 1–2 路过线要有放过按钮');
  const doneCal = { ...startCalibration(['rest', 'fist'], 1), phase: 'done', restDue: true };
  assert.equal(doneActions(scoreVerdict(1, 4).kind, askRestFor(doneCal, calibrationHolds(waiveNoise(done, doneCal.waived)))), 'rest', '没放过：只给重录放松');
  const w = waiveCal(doneCal, done.bad), ask = askRestFor(w, calibrationHolds(waiveNoise(done, w.waived)));
  assert.equal(doneActions(scoreVerdict(1, 4).kind, ask), 'look', '放过后 restDue 清掉，100% 直接给「看认到哪一类」');
  assert.equal(doneActions(scoreVerdict(.3, 4).kind, ask), 'retry', '放过后分数低照旧先补一轮');
  assert.deepEqual(waiveCal({ ...doneCal, waived: [2] }, [1, 2]).waived, [1, 2], '放过累计去重');
  const relax = Array.from({ length: 21 }, (_, i) => ({ t: 1000 + i * 100, rms: at([1, 2]) }));
  assert.equal(stopForRelaxationNoise(relax, 3000, '2', 150), true, '放松倒数里过线照旧停');
  assert.equal(stopForRelaxationNoise(relax, 3000, '2', 150, [1, 2]), false, '放过的路在放松倒数里不再停');
  assert.equal(stopForRelaxationNoise(relax.map((h) => ({ ...h, rms: at([1, 2, 5]) })), 3000, '2', 150, [1, 2]), true, '放过之外的路过线照旧停');
  console.log('仍然开始检查通过：2 路可放、3 路拦、累计上限、放过后新坏路照旧停');
}

// 握印不能把最强的路当成没贴好（2026-10-15：第 1、2 路校准时放松 45 µV、动作 1000+ µV，识别时被屏蔽）
{
  const seal = [1000, 800, 120, 110, 100, 100, 90, 90];          // 第 1、2 路过线，其余路被带起来但没过线
  const allUp = [1000, 800, 400, 400, 400, 300, 300, 300];       // 整条一起发力
  const bad2 = low.map((v, i) => i === 1 ? 400 : v);              // 真没贴好：只有第 2 路高，其余安静
  const a = new RestSignalGate(); a.reset(1000); feed(a, 1000, 6000, seal);
  assert.deepEqual(a.status(6000).stuck, [], '握印 5 秒（其余路 90–120 µV）不算坏路');
  assert.match(a.status(6000).text, /^请放松：第 1、2 路偏高/, '握印时说请放松，不说电极没贴好');
  const b = new RestSignalGate(); b.reset(1000); feed(b, 1000, 6000, allUp);
  assert.deepEqual(b.status(6000).stuck, [], '整条发力 5 秒不算坏路');
  const c = new RestSignalGate(); c.reset(1000); feed(c, 1000, 1500, [1000, 800, ...low.slice(2)]); feed(c, 1600, 6000, seal);
  assert.deepEqual(c.status(6000).stuck, [], '起印瞬间只有两路过线，随后别的路跟上：计时作废');
  const d = new RestSignalGate(); d.reset(1000); feed(d, 1000, 4500, bad2);
  assert.deepEqual(d.status(4500).stuck, [2], '只有一路高、其余安静满 3 秒：仍判坏路');
  feed(d, 4600, 6500, allUp.map((v, i) => i === 1 ? 400 : v));
  assert.deepEqual(d.status(6500).stuck, [2], '已判坏的路做动作时保持屏蔽，不闪断');
  assert.deepEqual(lanePlan(a.status(6000).stuck, drop).mask, [], '握印不会触发屏蔽');
  console.log('握印不误判坏路检查通过：其余路带起、整条发力、起印瞬间、真坏路保持');
}

// 用手势页手动屏蔽（2026-10-16）：第 1、2 路放松就偏高，其余路在 75–150 µV 之间跳，自动判坏路要等几分钟（evidence/2026-10-16-contact-quiet-replay）
{
  const shot = [259, 252, 85, 64, 62, 69, 65, 65];                                  // 截图数值
  const a = new RestSignalGate(); a.reset(1000); feed(a, 1000, 4500, shot);
  assert.deepEqual(a.status(4500).stuck, [1, 2], '截图数值（第 3 路 85 µV）在 .7 下满 3 秒判坏路');
  const jitter = (t) => [259, 252, t % 1000 < 500 ? 120 : 80, 64, 62, 69, 65, 65];   // 第 3 路在 80/120 之间跳
  const b = new RestSignalGate(); b.reset(1000); for (let t = 1000; t <= 20000; t += 100) b.observe(jitter(t), t, t);
  assert.equal(b.status(20000).allowed, false, '其余路跳过安静线：自动判不出，一直拦');
  assert.deepEqual(b.status(20000).stuck, []);
  b.force([1, 2]); for (let t = 20100; t <= 21500; t += 100) b.observe(jitter(t), t, t);
  assert.equal(b.status(21500).allowed, true, '手动屏蔽第 1、2 路后，其余路 ≤150 µV 满 1.2 秒就放行');
  const c = new RestSignalGate(); c.reset(1000); c.force([1]); feed(c, 1000, 3000, shot);
  assert.match(c.status(3000).text, /^请放松：第 2 路偏高/, '只屏蔽第 1 路，第 2 路照旧拦');
  assert.deepEqual(lanePlan([1, 2], [.9, .4, .9, .9, .9, .9, .9, .9], 0), { mask: [1, 2], estimate: .4 }, '手动屏蔽不看留一分数');
  console.log('手动屏蔽检查通过：截图数值自动判、其余路跳时手动放行、只屏蔽一路另一路照拦');
}

// 放松倒数里停录后，留下的样本必须和停录判定同一个时间基准（2026-10-15：多留一条旧的好样本，红线停下 1.5 s 就自动恢复）
{
  const h = Array.from({ length: 21 }, (_, i) => ({ t: 1000 + i * 100, rms: low.map((v, j) => j === 1 && i > 0 ? 300 : v) }));   // t=1000 时第 2 路还是 40，之后 300
  const now = 3010;
  assert.equal(stopForRelaxationNoise(h, now, '2', 150), true, '最近 2 s 第 2 路都过线：停');
  const kept = pauseHistory(h, now);
  assert.equal(kept.some((x) => x.t === 1000), false, '停录前那条好样本不能留下');
  assert.equal(noiseVerdict(noiseFloor(kept, kept.at(-1).t), 150).kind, 'bad', '停下后底噪仍判过线，不会自动恢复');
  console.log('停录样本口径检查通过：留下的样本与停录判定同一时间基准');
}

// 等贴合恢复只看最近 0.5 s：一条好样本不能把后面的过线盖住（复核 #76）
{
  const bad = low.map((v, j) => j === 1 ? 300 : v);
  const h = Array.from({ length: 21 }, (_, i) => ({ t: 500 + i * 100, rms: i === 0 ? low : bad }));   // 只有 t=500 那条好，其余第 2 路 300
  assert.equal(noiseVerdict(noiseFloor(h, 2500), 150).kind, 'ok', '旧口径（4 s 最低值）被一条好样本盖住');
  for (const now of [1100, 1500, 2500]) assert.equal(contactGate(h, now, 150).kind, 'bad', `t=${now} 最近 0.5 s 都过线：不恢复`);
  const good = Array.from({ length: 10 }, (_, i) => ({ t: 3000 + i * 100, rms: low }));
  assert.equal(contactGate([...h, ...good], 3900, 150).kind, 'ok', '压好后最近 0.5 s 都正常：可以恢复');
  assert.equal(contactGate(h, 9000, 150).kind, 'unknown', '断流（0.5 s 内没样本）不恢复');
  assert.equal(contactGate(h, 2500, 150, [2]).kind, 'ok', '已放过的路不拦恢复');
  console.log('等贴合恢复检查通过：只看最近 0.5 s，一条好样本盖不住过线');
}
