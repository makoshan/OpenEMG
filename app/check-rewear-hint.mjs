// 跨佩戴用旧模型的提醒：模型 created 早于手环最近一次重新出数据（link_since）才提醒，缺任一边不误报；游戏载荷把提醒写进 signal。
import assert from 'node:assert/strict';
import { guardRecord, REASK_MS, REWEAR_HINT, rewearHint, shouldAskRewear, withRewearHint } from './src/emg8/gesture-actions.ts';
const created = '2026-10-15T22:14:03';                               // run.json 的 created：本机本地时间，没时区
const epoch = (s) => new Date(s).getTime() / 1000;                   // link_since：采集服务 time.time()，epoch 秒（同一台电脑同一时钟）
// 2026-10-16 那局：前一晚 22:14 的模型，手环 08:31 才重新出数据 → 提醒，并说清两个时刻
const hit = rewearHint(created, epoch('2026-10-16T08:31:00'));
assert.equal(hit?.short, REWEAR_HINT);
assert.match(hit.detail, /10-15 22:14/); assert.match(hit.detail, /10-16 08:31/);
// 先连上、后训练（同一次佩戴）→ 不提醒；同一秒不算「早于」
assert.equal(rewearHint(created, epoch('2026-10-15T22:00:00')), null);
assert.equal(rewearHint(created, epoch('2026-10-15T22:14:03')), null);
// 缺任一边（旧服务没有 link_since / 还没选模型 / created 不是日期）→ 不提醒，不误报
const at = epoch('2026-10-16T08:31:00');
for (const [c, s] of [[created, undefined], [created, null], [created, 0], [null, at], ['', at], ['not-a-date', at]]) assert.equal(rewearHint(c, s), null, `${c} / ${s}`);
// 游戏载荷：有提醒就写进 signal（未开始识别时也发，「戴上神锁」页那一行显示它）；没有就原样不动
const idle = { state: 'link', text: '手环已连接 · 未开始识别', pose: '', acc: null };
assert.deepEqual(withRewearHint(idle, REWEAR_HINT), { ...idle, signal: REWEAR_HINT });
assert.equal(withRewearHint(idle, ''), idle);
const live = { state: 'live', text: '识别中 · 道指 0.91', pose: 'sword', acc: null, lanes: Array(8).fill('ok'), signal: '信号正常', rec: '道指 0.91' };
assert.equal(withRewearHint(live, REWEAR_HINT).signal, REWEAR_HINT, '识别中提醒顶掉「信号正常」（Mako 选 A）');
assert.equal(withRewearHint(live, REWEAR_HINT).rec, '道指 0.91', '其它字段不动');
assert.ok([...REWEAR_HINT].length <= 40, 'electron/game.cjs 对 signal 截 40 字');
// 录制前问不问「重新戴了吗」：旧数据第 4 次 10-14 23:58 → 10-15 10:41 空了 10.7 h，这种要问
const t0 = new Date('2026-10-14T23:58:00').getTime(), last = { donning: 4, at: t0 };
assert.equal(shouldAskRewear(last, 4, new Date('2026-10-15T10:41:00').getTime(), null, true), true, '隔 10.7 h 要问');
assert.equal(shouldAskRewear(last, 4, t0 + REASK_MS - 1, null, true), false, '29 分 59 秒内、没断流、本次运行已录过：不问');
assert.equal(shouldAskRewear(last, 4, t0 + REASK_MS, null, true), true, '满 30 分钟要问');
assert.equal(shouldAskRewear(last, 4, t0 + 60_000, t0 / 1000 + 30, true), true, '上一条之后手环重新出过数据（断流/拔插/服务重启）要问');
assert.equal(shouldAskRewear(last, 4, t0 + 60_000, t0 / 1000 - 30, true), false, '断流发生在上一条之前：不问');
assert.equal(shouldAskRewear(last, 4, t0 + 60_000, null, false), true, 'App 重启后第一次录要问');
assert.equal(shouldAskRewear(last, 5, t0 + 11 * 3600_000, t0 / 1000 + 99, false), false, '编号已被重戴按钮/校准 +1 改过：不再问');
assert.equal(shouldAskRewear(null, 1, t0, t0 / 1000 + 99, false), false, '没有上一条（新工程）：不问');
// 包装层：App 重启后批量录 4 条（enrollSequence 开头定了第 4 次），第 1 条弹窗选「重新戴了」→ 4 条都记第 5 次，只问一次（复核 P1）
{
  let clock = t0 + 3 * 3600_000, asks = 0; const sent = [], changed = [], saved = [];
  const rec = guardRecord(async (id, a) => { sent.push([a.donning, a.cable_dir, a.ch0_site]); return { ok: true }; }, {
    last, now: () => clock, ask: async (l) => { asks++; return l.donning + 1; }, changed: (n) => changed.push(n), saved: (l) => saved.push(l.donning),
    extra: () => ({ cable_dir: 'elbow', ch0_site: undefined, linkSince: null }) });
  for (let i = 0; i < 4; i++) { await rec('p', { donning: 4 }); clock += 5000; }
  assert.deepEqual(sent, Array(4).fill([5, 'elbow', undefined])); assert.equal(asks, 1); assert.deepEqual(changed, [5]); assert.deepEqual(saved, [5, 5, 5, 5]);
  // 界面跟上第 5 次后，用户发现点错、手动改回 4：照 4 发，不再被换成 5
  await rec('p', { donning: 5 }); await rec('p', { donning: 4 });
  assert.deepEqual(sent.slice(-2).map((x) => x[0]), [5, 4]);
  // 两条同时到：共用一个弹窗，两条都拿到同一个答案（复核 P2）
  let release; const asked = []; const rec2 = guardRecord(async (id, a) => ({ ok: true, d: a.donning }), {
    last, now: () => clock, ask: (l) => { asked.push(l); return new Promise((r) => { release = r; }); }, changed() {}, saved() {}, extra: () => ({}) });
  const both = [rec2('p', { donning: 4 }), rec2('p', { donning: 4 })]; await new Promise((r) => setTimeout(r, 0)); release(5);
  assert.deepEqual((await Promise.all(both)).map((r) => r.d), [5, 5]); assert.equal(asked.length, 1);
  // 录失败不更新「上一条」
  const failSaved = []; const rec3 = guardRecord(async () => ({ ok: false }), { last: null, ask: async () => 9, changed() {}, saved: (l) => failSaved.push(l), extra: () => ({}) });
  await rec3('p', { donning: 1 }); assert.deepEqual(failSaved, []);
}
console.log('check-rewear-hint ok');
