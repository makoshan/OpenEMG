// 合成信号驱动真实 MetaLive；只替换设备输入与游戏桥，不连接手环。
import './src/tokens.css';
import './src/app.css';
import './src/emg8/emg8.css';
import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { MetaLive } from './src/emg8/meta-live';
import { PROFILES } from './src/emg8/profiles';
const profile = Object.values(PROFILES).find(p => p.game === 'tianjie')!;
let listener: any, update: any;
const sent: string[] = [];
const realGame = (window as any).testGame;
const replies: any[] = [];
let reply = { accepted: true, code: 'accepted', message: '已出招' };
const bands: any[] = [];   // 识别页约 100 ms 推一次给游戏的手环状态
(window as any).pt = { game: { gesture: async (g: string) => { sent.push(g); const result = realGame ? await realGame.gesture(g, .99) : { ok: true, value: reply }; replies.push(result.value); return result; }, open: async () => ({ ok: true, value: true }), band: async (s: any) => { bands.push(s); return { ok: true, value: true }; } } };
// 每路缺了都还认得准（0.9）：第 2 路短时间偏高也有资格被屏蔽，用来证明「没持续够就不屏蔽」
const laneDrop = Array(8).fill(.9), liveCalls: any[] = [];
// 假服务端：tune 带的 mask 过 maskDelay 毫秒才生效，预测里回报当前生效的屏蔽
let serverMask: number[] = [], maskDelay = 0, dropped = 0;   // dropped：服务端累计丢帧数，加 1 = 下一批报丢帧
const bridge: any = { onEvent: (fn: any) => { listener = fn; return () => { listener = null; }; }, run: async () => ({ ok: true, value: { lane_drop: laneDrop, created: '2026-10-15T22:14:03' } }), live: async (_: string, a: any) => { liveCalls.push(a); if (a.mask) { const m = [...a.mask]; setTimeout(() => { serverMask = m; }, maskDelay); } return { ok: true, value: {} }; } };
// 模型 10-15 22:14 训的，手环 10-16 08:31 才重新出数据（跨佩戴用旧模型）：识别页要出横幅，游戏载荷 signal 带提醒
const st: any = { project: { id: 'test' }, rig: { streaming: true, link: 'streaming', link_since: Date.parse('2026-10-16T08:31:00') / 1000 }, wl8: { live: { run_id: 'test' } } };
const fail = (message: string) => { throw new Error(message); };
const assert = (value: any, message: string) => value || fail(message);
let mark = 0; const since = () => { const s = sent.slice(mark).join(); mark = sent.length; return s; };   // 结印游戏按住会再出同一印：后面的断言只看本步新增的出招
const wait = (ms: number) => new Promise(r => setTimeout(r, ms));
function Fixture() {
  const [data, set] = useState({ rms: Array(8).fill(50), at: Date.now() }); update = set;
  return <MetaLive profile={profile} projectId="test" bridge={bridge} st={st} runId="test" donning={1} onError={fail} rms={data.rms} rmsAt={data.at} />;
}
createRoot(document.getElementById('root')!).render(<Fixture />);
async function feed(ms: number, high = false, label = 'seal_rest', lane = 1) {
  for (let i = 0; i < ms / 100; i++) {
    update({ rms: Array.from({length: 8}, (_, i) => high && i === lane ? 400 : 50), at: Date.now() });
    await wait(30);
    listener?.({ type: 'batch', dropped, emg: [Array(8).fill(0)], imu: [], preds: [{ t: Date.now()/1000, mask: serverMask, top: label, probs: Object.fromEntries(profile.labels.map(l => [l, l === label ? .99 : .003])) }] });
    await wait(70);
  }
}
(async () => {
  await wait(300);
  // 跨佩戴用旧模型（design/rewear-hint-20261016，Mako 选 A）：横幅在页上、游戏载荷 signal 带同一句，只提醒不拦截（下面照常出招）
  assert(document.body.textContent?.includes('手环可能已重戴，请先在采集页重新校准再识别'), '识别页应显示重戴提醒横幅');
  assert(bands.some(b => b.signal === '手环可能已重戴，请先在采集页重新校准再识别'), '游戏载荷 signal 应带重戴提醒');
  if (realGame) {
    await feed(2300);
    for (const label of ['seal_daozhi','seal_poxie','seal_wulei']) { await feed(300); await feed(400,false,label); }
    assert(sent.join() === 'sword,guard,thunder' && replies.every(r=>r.accepted), '真实游戏必须接受三招');
    await (window as any).testPause();
    await feed(300); await feed(400,false,'seal_daozhi');   // 喂道指：破邪印 ~0.8 s 前刚出过，按印的限速还没过（复核二轮必须修）
    assert(replies.at(-1)?.code === 'paused' && document.body.textContent?.includes(replies.at(-1).message), '真实游戏暂停原因必须回到识别页');
    (window as any).checkResult = {ok:true,sent,replies}; return;
  }
  // 复核 P1 阳性对照：第 2 路偏高 2.5 秒（不到 LANE_HOLD_MS）不能被屏蔽换来通过；旧版这里会屏蔽第 2 路并送出道指
  await feed(1500, true); await feed(1000, true, 'seal_daozhi'); assert(sent.length === 0, '未检查通过不能送游戏');
  assert(!liveCalls.some(a => a.mask?.includes(2)), '短时间偏高不能屏蔽第 2 路');
  await feed(2200); await feed(400, true, 'seal_daozhi'); assert(sent.join() === 'sword', '检查通过应送道指');
  await feed(4400, true, 'seal_daozhi'); assert(!document.body.textContent?.includes('电极没贴好'), '持续手印不能报接触故障');
  // 结印游戏识别到就出：按住 4.4 秒会按剑的冷却（600 ms）再出几次剑，上限防退化成每帧重发；之后照常送破邪印（直接换印不经放松的情形在 check-seal-game.mjs 里测）
  await feed(300, true); await feed(400, true, 'seal_poxie'); { const swords = sent.filter(x => x === 'sword').length; assert(swords >= 6 && swords <= 10 && sent.at(-1) === 'guard' && sent.indexOf('guard') === sent.length - 1, `长动作后仍可送破邪印（实际 ${sent.join()}）`); }
  // 结印会话（session 策略，PR #78）：放行后整局有效，持续高值超过旧的 10 秒定时也不重查
  since(); await feed(5500, true); await feed(400, true, 'seal_wulei'); assert(since() === 'thunder', '放行后持续高值超过 10 秒不能重查');
  // 丢帧、短暂断流（< BREAK_MS 2 秒）只取消当次动作，沿用放行（PR #85）
  dropped++; await feed(500, true); await feed(400, true, 'seal_daozhi'); assert(since() === 'sword', '丢帧后应沿用放行');
  await wait(1000); await feed(300, true); await feed(400, true, 'seal_poxie'); assert(since() === 'guard', '短暂断流后应沿用放行');
  // 断流超过 BREAK_MS 撤销放行：之后持续高值必须拦，重新放松才恢复
  await wait(2500); await feed(1000, true); await feed(400, true, 'seal_wulei'); assert(since() === '', '断流超过 2 秒后持续高值必须拦');
  await feed(2200); await feed(400, false, 'seal_wulei'); assert(since() === 'thunder', '重新放松后恢复');
  // 断流前是放松也一样撤销；断流后先喂放松预测（结印游戏不需要上膛，这里纯测放松门）
  await feed(300, false, 'seal_rest'); await wait(2500); await feed(300, true); await feed(400, true, 'seal_daozhi'); assert(since() === '', '断流后不能沿用凭证');
  // 第 8 路持续没贴好：屏蔽它，放松检查通过后继续出招，并要求服务端屏蔽第 8 路
  // 服务端 4 秒后才换上屏蔽：这期间前端放松检查已过，但预测仍是全 8 路，不能出招
  maskDelay = 4000;
  await feed(5000, true, 'seal_rest', 7); await feed(400, true, 'seal_poxie', 7);
  assert(since() === '', '服务端还没屏蔽第 8 路时不能出招：' + sent.join());
  assert(document.body.textContent?.includes('正在同步屏蔽的路'), '页面应提示正在同步屏蔽');
  await feed(2500, true, 'seal_rest', 7); await feed(400, true, 'seal_poxie', 7);
  assert(since() === 'guard', '屏蔽第 8 路后应继续认：' + sent.join());
  assert(liveCalls.some(a => a.action === 'tune' && a.mask?.join() === '8'), '应让服务端屏蔽第 8 路');
  assert(document.body.textContent?.includes('已屏蔽第 8 路'), '页面应提示已屏蔽第 8 路');
  reply = { accepted: false, code: 'paused', message: '游戏已暂停，回到游戏点「继续」或按 P' };
  await feed(300, true, 'seal_rest', 7); await feed(400, true, 'seal_wulei', 7);   // 用五雷诀：上一次破邪印刚出过，按印的冷却（1.5 s）限速还没过
  assert(document.body.textContent?.includes(reply.message), '识别页必须显示游戏实际拒绝原因');
  // 用手势页手动屏蔽（2026-10-16）：第 1 路先被自动屏蔽，随后第 2 路也偏高、第 3 路在 80/120 µV 之间跳，自动判不出。
  // 连续卡满 5 秒才给按钮；按钮要连已屏蔽的第 1 路一起屏蔽，只给第 2 路会把第 1 路放开、点完又卡住（复核 #102 P1）
  maskDelay = 0;
  const jitter = (t: number) => t % 1000 < 500 ? 120 : 80;
  const offer = (lanes = '1、2') => [...document.querySelectorAll('button')].find(b => b.textContent === `松手后仍偏高 · 屏蔽第 ${lanes} 路`);
  async function feedRms(ms: number, rms: () => number[], label = 'seal_rest', until?: () => boolean) {
    for (let i = 0; i < ms / 100 && !until?.(); i++) {
      update({ rms: rms(), at: Date.now() }); await wait(30);
      listener?.({ type: 'batch', dropped, emg: [Array(8).fill(0)], imu: [], preds: [{ t: Date.now()/1000, mask: serverMask, top: label, probs: Object.fromEntries(profile.labels.map(l => [l, l === label ? .99 : .003])) }] });
      await wait(70);
    }
  }
  const one = () => [300, 60, 60, 60, 60, 60, 60, 60], both = () => [300, 300, jitter(Date.now()), 60, 60, 60, 60, 60];
  await wait(2500);   // 断流超过 BREAK_MS：撤销整局放行，重新做放松检查
  await feedRms(2000, one);
  assert(document.body.textContent?.includes('请放松：第 1 路偏高') && !offer('1'), '卡 2 秒不给屏蔽按钮');
  await feedRms(6000, one, 'seal_rest', () => !!document.body.textContent?.includes('已屏蔽第 1 路（没贴好）'));
  assert(document.body.textContent?.includes('已屏蔽第 1 路（没贴好）'), '只有第 1 路高、其余安静：应自动屏蔽第 1 路');
  await feedRms(6000, both);   // 卡住计时从第 1 路偏高就开始；换路时若有一拍没卡、重新计时，6 秒也够
  assert(document.body.textContent?.includes('请放松：第 2 路偏高'), '第 1 路已屏蔽后应只拦第 2 路');
  assert(!offer('2'), '按钮不能只屏蔽第 2 路（会把已屏蔽的第 1 路放开）');
  assert(offer(), '卡满 5 秒应给「松手后仍偏高 · 屏蔽第 1、2 路」');
  assert(!liveCalls.some(a => a.mask?.join() === '1,2'), '没点按钮不能屏蔽第 1、2 路');
  offer()!.click();
  await feedRms(2500, both);
  assert(liveCalls.some(a => a.action === 'tune' && a.mask?.join() === '1,2'), '点了应让服务端屏蔽第 1、2 路');
  assert(document.body.textContent?.includes('已屏蔽第 1、2 路（手动）'), '页面应提示手动屏蔽');
  assert(document.body.textContent?.includes('放松检查通过'), '屏蔽后其余路 ≤150 µV 应放行');
  assert(!offer(), '屏蔽后按钮收起');
  const before = sent.length; await feedRms(300, both); await feedRms(400, both, 'seal_poxie');
  assert(sent.length === before + 1 && sent.at(-1) === 'guard', '手动屏蔽后应能出招：' + sent.join());
  (window as any).checkResult = { ok: true, sent, text: document.body.textContent };
})().catch(e => { (window as any).checkResult = { ok: false, error: String(e) }; });
