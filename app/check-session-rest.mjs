import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { BREAK_MS, RestSignalGate } from './src/emg8/rest-signal.ts';
const low = Array(8).fill(50), high = Array(8).fill(500);
function started(policy = 'session') {
  const gate = new RestSignalGate(150, policy);
  gate.reset(1000);
  for (let t = 1000; t <= 2800; t += 100) gate.observe(low, t, t);
  assert.equal(gate.status(2800).allowed, true);
  return gate;
}
const initial = new RestSignalGate(150, 'session');
for (let t = 1000; t <= 5000; t += 100) initial.observe(high, t, t);
assert.equal(initial.status(5000).allowed, false, '起始高幅不能跳过放松');
for (const policy of ['session', 'periodic']) {
  const gate = started(policy);
  for (let t = 2900; t <= 40000; t += 100) {
    gate.observe(high, t, t);
    if (policy === 'session') assert.equal(gate.status(t).allowed, true, '结印持续动作不应被10秒定时打断');
  }
  assert.equal(gate.status(40000).allowed, policy === 'session', '默认策略仍定时重检');
}
// 丢帧、渲染卡顿这类短暂不连续：这一批不计，通过状态保留（2026-10-15 一局丢帧 33 次，每次整套重查，打着游戏中位要等 66 s）
for (const [name, glitch, checkAt = 2900] of [
  ['短断流 0.4 s', g => g.observe(high, 3200, 3200), 3200],
  ['乱序批次', g => g.observe(high, 2700, 2900)],
  ['过期批次', g => g.observe(low, 1000, 2900)],
  ['未来批次', g => g.observe(low, 3000, 2900)],
  ['重复批次 0.4 s', g => { for (let t = 2900; t <= 3200; t += 100) g.observe(low, 2800, t); }, 3200],
  ['卡顿 2 s 没数据', () => {}, 2800 + BREAK_MS],
  ['空 RMS', g => g.observe(null, 2900, 2900)],
  ['丢帧后滤波稳定 1.5 s（数据在流）', g => { for (let t = 2900; t <= 4300; t += 100) { g.heartbeat(t); g.observe(null, 0, t); } g.observe(low, 4400, 4400); }, 4400],
  ['数据在流、RMS 空 3 s 后恢复', g => { for (let t = 2900; t <= 5800; t += 100) { g.heartbeat(t); g.observe(null, 0, t); } g.observe(low, 5900, 5900); }, 5900],
]) {
  const gate = started(); glitch(gate);
  assert.equal(gate.status(checkAt).allowed, true, `${name}只取消当次动作，不撤销放松检查`);
}
// 断开超过 2 s、坏数值、主动重置：撤销，重新放松可恢复
for (const [name, breakData, checkAt = 2900] of [
  ['断开 2.1 s', g => g.observe(high, 2901 + BREAK_MS, 2901 + BREAK_MS), 2901 + BREAK_MS],
  ['卡顿超过 2 s', () => {}, 2801 + BREAK_MS],
  ['重复批次超过 2 s', g => { for (let t = 2900; t <= 2900 + BREAK_MS; t += 100) g.observe(low, 2800, t); }, 2900 + BREAK_MS],
  ['心跳和 RMS 都断 2.1 s', g => { g.heartbeat(2800); g.observe(null, 0, 4901); }, 4901],
  ['断 5 s 期间没查 status，恢复时心跳先到', g => { g.heartbeat(7800); g.observe(low, 7800, 7800); }, 7800],
  ['NaN', g => g.observe([NaN, ...low.slice(1)], 2900, 2900)],
  ['负数', g => g.observe([-1, ...low.slice(1)], 2900, 2900)],
  ['主动重置', g => g.reset(2900)],
]) {
  const gate = started(); breakData(gate);
  assert.equal(gate.status(checkAt).allowed, false, `${name}必须撤销通过状态`);
  for (let t = checkAt + 100; t <= checkAt + 2500; t += 100) gate.observe(low, t, t);
  assert.equal(gate.status(checkAt + 2500).allowed, true, `${name}后重新放松可恢复`);
}
// 已屏蔽的坏路通过后遇到短暂中断：坏路计时保持，屏蔽不能被放开（复核 #85 P1）
{
  const bad2 = low.map((v, i) => i === 1 ? 400 : v);
  for (const [name, glitch, at] of [
    ['断 0.4 s', g => g.observe(bad2, 5900, 5900), 5900],
    ['滤波稳定 1.5 s', g => { for (let t = 5600; t <= 7000; t += 100) { g.heartbeat(t); g.observe(null, 0, t); } g.observe(bad2, 7100, 7100); }, 7100],
  ]) {
    const gate = new RestSignalGate(150, 'session'); gate.reset(1000);
    for (let t = 1000; t <= 4100; t += 100) gate.observe(bad2, t, t);
    gate.setIgnore([2]);
    for (let t = 4200; t <= 5500; t += 100) gate.observe(bad2, t, t);
    assert.equal(gate.status(5500).allowed, true); assert.deepEqual(gate.status(5500).stuck, [2]);
    glitch(gate);
    assert.equal(gate.status(at).allowed, true, `${name}后沿用放行`);
    assert.deepEqual(gate.status(at).stuck, [2], `${name}后第 2 路仍算坏路，屏蔽不放开`);
  }
}
// 还没通过时，短暂中断不能把前后两截安静拼成连续 1.2 s
{
  const gate = new RestSignalGate(150, 'session'); gate.reset(1000);
  for (let t = 1000; t <= 2300; t += 100) gate.observe(low, t, t);
  for (let t = 2700; t <= 3200; t += 100) gate.observe(low, t, t);
  assert.equal(gate.status(3200).allowed, false, '中断前后的安静不能拼接');
  for (let t = 3300; t <= 3900; t += 100) gate.observe(low, t, t);
  assert.equal(gate.status(3900).allowed, true, '中断后连续安静满 1.2 s 通过');
}
const source = readFileSync(new URL('./src/emg8/meta-live.tsx', import.meta.url), 'utf8');
assert.match(source, /new RestSignalGate\(NOISE_LIMIT_UV, profile\.game === 'tianjie' \? 'session' : 'periodic'\)/);
assert.match(source, /\[projectId, runId, st\?\.wl8\?\.live\?\.run_id, donning, ready, profile\.game\]/);
// 页面只在认对测试的放松题显式重查；丢帧、预测对不上、数据过期、流报错不许再调 reset（旧代码有 5 处）
assert.equal(source.match(/signalGate\.reset\(/g)?.length, 1, '识别循环里不能因为短暂不连续重做放松检查');
assert.match(source, /exam\?\.phase === 'rest'\) signalGate\.reset\(/);
assert.ok(!source.includes('数据中断，请重新放松'), '流报错只取消动作，不要求重新放松');
// 门不再兜底以后，这几处是防陈旧出招的唯一保障：每条取消路径都要清动作序列（复核 #85 第 3 条）
// 同一句提示可能出现在几处（boundary 和预测时间对不上都说「信号不连续」），每一处都要查（复核 #85 第二轮：find 只查到第一处）
const clears = (l) => l.includes('sequence.current.reset(); trigger.current.reset(); lastPred = 0;');
for (const msg of ['丢帧，动作已取消', '信号不连续，动作已取消', '数据过期，动作已取消', '数据中断，动作已取消']) {
  const lines = source.split('\n').filter((l) => l.includes(msg));
  assert.ok(lines.length && lines.every(clears), `「${msg}」的每条路径都要清动作序列`);
}
assert.ok(clears(source.split('\n').find((l) => l.includes('p.t * 1000) > 300'))), '预测时间对不上那条路径要清动作序列');
assert.match(source, /const now = Date\.now\(\);\n\s*if \(e\.emg\.length\) signalGate\.heartbeat\(now\);/, '带肌电的批次要给放松门心跳');
console.log('结印持续动作、短暂不连续沿用通过、断开超过 2 s 重检：通过');
