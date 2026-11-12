import './check-filter-ipc.mjs';
import './check-filter-stream.mjs';
import './check-pack-source.mjs';
// 结印 → 掌中天劫的映射与门槛（src/emg8/gesture-actions.ts）；游戏只收置信度 0.8–1。用法：npm run check:seal-game
import assert from 'node:assert/strict';
import './check-egoemg.mjs';
import './check-rest-signal.mjs';
import './check-session-rest.mjs';
import { readFileSync } from 'node:fs';
import { contactPause, WIDE_LOOSE_MS } from './src/emg8/calibration.ts';
import { examPlan, examScore, GestureTrigger, sealToGame, SEAL_TO_GAME } from './src/emg8/gesture-actions.ts';

// 三个结印各对应游戏一个手印，且游戏页确实认这三个名字
assert.deepEqual(sealToGame('seal_daozhi', .9), { gesture: 'sword', confidence: .9 });
assert.deepEqual(sealToGame('seal_poxie', 1), { gesture: 'guard', confidence: 1 });
assert.deepEqual(sealToGame('seal_wulei', .8), { gesture: 'thunder', confidence: .8 });
const game = readFileSync(new URL('./game/tianjie/game.js', import.meta.url), 'utf8');
for (const g of Object.values(SEAL_TO_GAME)) assert.ok(game.includes(`"${g}"`) || game.includes(`'${g}'`) || game.includes(`${g}:`), `游戏里找不到手印 ${g}`);
// 校准口令和游戏「结印要领」写的是同一种手型（design/seal-hands-20261016 照片：破邪印拇指压住、道指掌心朝上压指甲、五雷诀拇指在拳外）；哪边文案漂了这里红
{
  const { LESSONS } = await import('../game/tianjie/src/onboarding.mjs');
  const seals = JSON.parse(readFileSync(new URL('./electron/emg8-profiles.json', import.meta.url), 'utf8'))['ghost-seals'].gestures;
  const guide = readFileSync(new URL('../game/tianjie/src/index.html', import.meta.url), 'utf8');   // 「初入山门」说明弹窗，第三处写手型的地方
  const KEY = { seal_poxie: { cue: ['手背朝上', '拇指', '压住'], voice: '压住' }, seal_daozhi: { cue: ['掌心朝上', '指甲'], voice: '掌心朝上' }, seal_wulei: { cue: ['手背朝上', '拳外', '食指、中指'], voice: '在外' } };
  for (const [seal, { cue: words, voice }] of Object.entries(KEY)) {
    const lesson = LESSONS.find(x => x.gesture === SEAL_TO_GAME[seal]);
    const tip = guide.match(new RegExp(`<b>[QER] · ${lesson.name}</b><p>([^<]*)</p>`))?.[1] ?? '';
    for (const w of words) { assert.ok(seals[seal].cue.includes(w), `${seal} 校准口令少了「${w}」`); assert.ok(lesson.pose.includes(w), `${SEAL_TO_GAME[seal]} 游戏要领少了「${w}」`); assert.ok(tip.includes(w), `${lesson.name} 初入山门弹窗少了「${w}」`); }
    assert.ok(seals[seal].voice.includes(voice), `${seal} 语音口令没提「${voice}」`);   // 语音只念最容易错的一点
  }
}
// 低于 0.8、放松类、别的组的类名都不送
assert.ok('skip' in sealToGame('seal_daozhi', .79));
assert.ok('skip' in sealToGame('seal_rest', .99));
assert.ok('skip' in sealToGame('ai_up', .99));
assert.ok('skip' in sealToGame('seal_wulei', NaN));
// 和识别页一起用：先放松两次才上膛，同一结印连续 3 次、≥0.65 才触发一次
const t = new GestureTrigger('seal_rest');
const seq = [['seal_rest', .9], ['seal_rest', .9], ['seal_daozhi', .85], ['seal_daozhi', .86], ['seal_daozhi', .88], ['seal_daozhi', .9]];
const fired = seq.map(([l, c]) => t.push(l, c)).filter(Boolean);
assert.deepEqual(fired, ['seal_daozhi'], '按住不放只触发一次');
// 放松检查还没过时只 watch：先放松再稳住的印，放行后下一帧就出；没放松过的印不能补出
const held = new GestureTrigger('seal_rest');
held.watch('seal_rest', .9); held.watch('seal_rest', .9);
held.watch('seal_daozhi', .9); held.watch('seal_daozhi', .9); held.watch('seal_daozhi', .9);
assert.equal(held.primed(), true, '等待期间的放松要上膛');
assert.equal(held.push('seal_daozhi', .9), 'seal_daozhi', '检查期间已上膛并稳住的印，放行后下一帧就出');
assert.equal(held.push('seal_daozhi', .9), null, '出过一次再按住不连发');
const cold = new GestureTrigger('seal_rest');
cold.watch('seal_daozhi', .9); cold.watch('seal_daozhi', .9); cold.watch('seal_daozhi', .9);
assert.equal(cold.push('seal_daozhi', .9), null, '没先放松不能在放行时补出');
// 结印游戏（continuous）：识别到就出招，不等放松；按住按各印冷却（墙钟）再出；换印连续 3 次就出（Mako 2026-10-16「只要识别到就可以攻击」）
{
  const { REPEAT_MS } = await import('./src/emg8/gesture-actions.ts');
  const g = new GestureTrigger('seal_rest', true); const T = 1_000_000;
  assert.equal(g.primed(), true, '结印游戏不需要先放松上膛');
  const first = [1, 2, 3].map(() => g.push('seal_daozhi', .9, T));
  assert.deepEqual(first, [null, null, 'seal_daozhi'], '没放松过也要在第 3 次稳住时出招');
  const hold = Array.from({ length: 11 }, (_, i) => g.push('seal_daozhi', .9, T + 50 * (i + 1)));
  assert.deepEqual(hold, Array(11).fill(null), '按住 550 ms 内不连发');
  assert.equal(g.push('seal_daozhi', .9, T + REPEAT_MS.seal_daozhi), 'seal_daozhi', '按住到剑的冷却间隔再出一次');
  const sw = [1, 2, 3].map(() => g.push('seal_poxie', .9, T + 650));
  assert.deepEqual(sw, [null, null, 'seal_poxie'], '直接换印、不经放松，稳住 3 次就出');
  assert.equal(g.push('seal_wulei', .5, T + 700), null, '不确定不出');
  assert.deepEqual([1, 2, 3].map(() => g.push('seal_wulei', .9, T + 750)), [null, null, 'seal_wulei'], '不确定打断计数，重新稳住 3 次才出');
  assert.equal(g.push('seal_rest', .9, T + 800), null, '放松不出招');
  assert.deepEqual([1, 2, 3].map(() => g.push('seal_daozhi', .9, T + 900)), [null, null, null], '放松后再摆同一印，离上次出招不到剑的冷却不出（抖动绕不过限速）');
  assert.deepEqual([1, 2, 3].map(() => g.push('seal_daozhi', .9, T + 1300)), ['seal_daozhi', null, null], '手一直稳着，过了冷却间隔的第一帧就出，之后不重复');
  g.reset();
  assert.deepEqual([1, 2, 3].map(() => g.push('seal_daozhi', .9, T + 1400)), [null, null, null], '丢帧重置不清限速：刚出过的印 100 ms 内不重出');
  assert.deepEqual([1, 2, 3].map(() => g.push('seal_daozhi', .9, T + 2000)), ['seal_daozhi', null, null], '重置后手仍稳着，过了冷却间隔照常出');
  const w = new GestureTrigger('seal_rest', true);
  [1, 2, 3].forEach(() => w.watch('seal_poxie', .9));
  assert.equal(w.push('seal_poxie', .9, T), 'seal_poxie', '等待期间已稳住的印，放行后下一帧就出');
  assert.equal(w.push('seal_poxie', .9, T + 100), null, '随后在冷却间隔内不重复');
  const low = new GestureTrigger('seal_rest', true);
  assert.deepEqual([1, 2, 3].map(() => low.push('seal_daozhi', .7, T)), [null, null, null], '置信 0.65–0.8 只计数不出招，不占这次出招');
  assert.equal(low.push('seal_daozhi', .9, T + 50), 'seal_daozhi', '置信爬到 0.8 立刻出，不用再等');
  const sw2 = new GestureTrigger('seal_rest', true);
  assert.equal([1, 2, 3].map(() => sw2.push('seal_poxie', .9, T)).at(-1), 'seal_poxie');
  sw2.continuous = false;   // 认对测试期间识别页这样关掉连发
  assert.equal(Array.from({ length: 100 }, (_, i) => sw2.push('seal_poxie', .9, T + 50 * (i + 1))).filter(Boolean).length, 0, '连发关掉后按住 5 秒不再出（要先放松）');
  const back = new GestureTrigger('seal_rest', true);
  assert.equal([1, 2, 3].map(() => back.push('seal_poxie', .9, T)).at(-1), 'seal_poxie');
  assert.deepEqual([1, 2, 3].map(() => back.push('seal_poxie', .9, T - 3_600_000)), ['seal_poxie', null, null], '系统时钟往回拨时限速当作已过（随后照常限速）');
  const mouse = new GestureTrigger('seal_rest');
  assert.equal([['seal_daozhi', .9], ['seal_daozhi', .9], ['seal_daozhi', .9]].map(([l, c]) => mouse.push(l, c)).at(-1), null, '鼠标组照旧：没先放松不出');
}
// 认对测试：每类题数相同、只是打乱；暂停过的题不计分；没触发算漏认、认成别类记进 wrong
const plan = examPlan(['a', 'b', 'c'], 7, () => .3);
assert.equal(plan.length, 21);
assert.notDeepEqual(examPlan(['a', 'b', 'c'], 2, () => .3), ['a', 'a', 'b', 'b', 'c', 'c'], '题目要打乱');
for (const l of ['a', 'b', 'c']) assert.equal(plan.filter((x) => x === l).length, 7);
const sc = examScore([
  { target: 'a', got: 'a', restFires: 0, paused: false },
  { target: 'a', got: 'b', restFires: 1, paused: false },
  { target: 'b', got: null, restFires: 0, paused: false },
  { target: 'b', got: 'b', restFires: 0, paused: true },
]);
assert.deepEqual([sc.n, sc.ok, sc.paused, sc.restFires], [3, 1, 1, 1]);
assert.equal(examScore([{ target: 'a', got: null, restFires: 2, paused: true }]).restFires, 0, '暂停题的误出招不计');
assert.deepEqual(sc.per.a, { n: 2, ok: 1, miss: 0, wrong: { b: 1 } });
assert.deepEqual(sc.per.b, { n: 1, ok: 0, miss: 1, wrong: {} });
// 贴合暂停：1–2 路过线立刻停；≥3 路要持续 10 s；没过线不停
const nv = (bad) => ({ kind: bad.length ? 'bad' : 'ok', bad, high: [] });
assert.equal(contactPause(nv([2]), 0, 1000), true);
assert.equal(contactPause(nv([1, 2]), 0, 1000), true, '2 路过线也立刻停');
assert.equal(contactPause(nv([1, 2, 4]), 1000, 1000 + WIDE_LOOSE_MS - 1), false, '用力的几秒不停');
assert.equal(contactPause(nv([1, 2, 4]), 1000, 1000 + WIDE_LOOSE_MS), true, '整条松了 10 s 要停');
assert.equal(contactPause(nv([1, 2, 4]), 0, 99999), false);
assert.equal(contactPause(nv([]), 1, 99999), false);
console.log('结印 → 游戏映射检查通过');

// 手环状态推给游戏：只在置信够时摆印，放松不摆；没数据是 off，有数据没识别是 link
{
  const { bandIdle, bandLive, bandSignal, gatedWatch } = await import('./src/emg8/gesture-actions.ts');
  // 游戏面板肌电一栏：正常 / 屏蔽一路 / 暂停；没数据时不亮绿
  const pass = { allowed: true, high: [], over: [], text: '放松检查通过' };
  assert.equal(bandSignal(pass, [], true).signal, '信号正常'); assert.deepEqual(bandSignal(pass, [], true).lanes, Array(8).fill('ok'));
  const m = bandSignal({ allowed: true, high: [], over: [2], text: '' }, [2], true);
  assert.equal(m.lanes[1], 'mask'); assert.equal(m.signal, '第 2 路接触差 · 已屏蔽，用 7 路识别');
  const bad = bandSignal({ allowed: false, high: [1, 2, 3], over: [1, 2, 3], text: '请放松：第 1、2、3 路信号偏高，暂不出招' }, [], true);
  assert.deepEqual(bad.lanes.slice(0, 4), ['bad', 'bad', 'bad', 'ok']); assert.ok(bad.signal.includes('暂不出招'));
  assert.deepEqual(bandSignal(pass, [], false).lanes, Array(8).fill('')); assert.equal(bandSignal(pass, [], false).signal, '没收到肌电数据');
  assert.equal(bandLive('seal_wulei', .9, '五雷诀', [0, 0, 1]).pose, 'thunder');
  assert.equal(bandLive('seal_wulei', .5, '五雷诀', null).pose, '');
  assert.equal(bandLive('seal_rest', .99, '放松', null).pose, '');
  const held = gatedWatch('seal_daozhi', .91, '道指', [1, 0, 0], false);
  assert.equal(held.band.state, 'live'); assert.equal(held.band.pose, 'sword'); assert.match(held.live, /等放松后再出招/);
  assert.equal(gatedWatch('seal_daozhi', .91, '道指', null, true).band.pose, '', '幅度不够不摆印');
  assert.equal(bandIdle(false, false, false, '').state, 'off');
  assert.equal(bandIdle(true, false, false, '').text, '手环已连接 · 未开始识别');
  assert.equal(bandIdle(true, true, true, '').state, 'link');
  // 游戏页确实有接手环状态的口
  assert.ok(game.includes('band:') || game.includes('band,'), '游戏里找不到 TianjieGame.band');
  console.log('手环状态 → 游戏：通过');
}
