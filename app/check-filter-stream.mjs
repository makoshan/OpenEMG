import assert from 'node:assert/strict';
import { SignalStream, DisplayFilter, FILTER_SETTLE_SAMPLES, RMS_SAMPLES } from './src/emg8/signal.ts';
import { RestSignalGate } from './src/emg8/rest-signal.ts';
import { stopForRelaxationNoise } from './src/emg8/calibration.ts';
const row = x => Array(8).fill(x);
const samples = (n, offset = 50000, amplitude = 0, start = 0) => Array.from({length:n}, (_,i) => row(offset + amplitude * Math.sin(2*Math.PI*80*(start+i)/2000)));
const n = FILTER_SETTLE_SAMPLES + RMS_SAMPLES;
// 同样的连续样本不因批次大小改变；准备期没有半窗或零值读数。
const a = new SignalStream(), b = new SignalStream(), data = samples(n,50000,30), original = structuredClone(data);
a.push(data,1000,n,0);
for (let i=0;i<n;i+=100) { b.push(data.slice(i,i+100),1000+i/2,i+100,0); if(i+100<n) assert.equal(b.values(),null); }
assert.deepEqual(a.values(),b.values()); assert.deepEqual(data,original);
assert(a.values().every(x => x>10 && x<30));
// 大直流阶跃重连后不制造假噪声；首帧稳态初始化保留原始参数。
const raw = new DisplayFilter(); assert(Math.abs(raw.process(row(50000))[0])>10000,'旧零状态反例必须有尖峰');
const f = new DisplayFilter(); f.reset(row(50000)); assert(Math.abs(f.process(row(50000))[0])<1e-6);
for (const mode of ['reset','timeout','index','dropped','invalid']) {
 const s = new SignalStream();s.push(samples(n),1000,n,0);assert(s.values().every(x=>x<1e-5));
 if(mode==='reset')s.reset();
 if(mode==='timeout')assert(s.expire(1301));
 if(mode==='invalid')s.push([row(NaN)],1050,n+1,0);
 s.push(samples(100,-70000),mode==='timeout'?1400:1100,mode==='index'?n+200:n+100,mode==='dropped'?1:0);
 assert.equal(s.values(),null,mode+' 必须重进准备期');
}
// 准备期不能当放松；真正高幅在准备后仍被拒绝；低幅能恢复。数据仍在流时重进准备期不撤销已有放行，断流超过 2 s 才撤销（Mako 2026-10-15 P0）。
for(const amplitude of [0,500]) {
 const s=new SignalStream(),g=new RestSignalGate(150,'session');let history=[];
 for(let k=0;k<100;k++) {
  const at=1000+k*50;s.push(samples(100,50000,amplitude,k*100),at,(k+1)*100,0);
  const v=s.values();g.observe(v,v?at:0,at);
  if(v)history.push({t:at,rms:v});else history=[];
  if(k<29) {assert.equal(g.status(at).allowed,false);assert.equal(stopForRelaxationNoise(history,at,'3',150),false);}
 }
 assert.equal(g.status(5950).allowed,amplitude===0);
 assert.equal(stopForRelaxationNoise(history,5950,'3',150),amplitude!==0);
 s.reset();g.heartbeat(6000);g.observe(s.values(),0,6000);assert.equal(g.status(6000).allowed,amplitude===0,'丢帧后重进准备期只取消动作，不撤销放行');
 assert.equal(g.status(8001).allowed,false,'断流超过 2 s 撤销放行');
}
// 两条链：view 只给画面（45 Hz 高通 + 谐波陷波到 900 Hz）；gate 口径（基波 Q=5、谐波 Q=30）必须不变且仍是默认，否则放松检查门会被偷偷改掉
const gain = (chain, hz, mains = 50) => { const f = new DisplayFilter(mains, 8, chain); let s = 0; for (let i = 0; i < 16000; i++) { const y = f.process(row(Math.sin(2*Math.PI*hz*i/2000)))[0]; if (i >= 12000) s += y*y; } return 10*Math.log10(s/4000*2 + 1e-30); };
const view = Object.fromEntries([20,30,45,50,75,100,120,150,200,225,475,800,925].map(hz => [hz, +gain('view', hz).toFixed(1)]));
assert(view[20] < -80 && view[30] < -40 && view[45] > -4.5 && view[45] < -2, 'view 高通形状不对 ' + JSON.stringify(view));
assert([75,120,225,475,925].every(hz => view[hz] > -1.5), 'view 通带被削 ' + JSON.stringify(view));
assert([50,100,150,200,800].every(hz => view[hz] < -30), 'view 谐波没陷住 ' + JSON.stringify(view));
const gate = Object.fromEntries([30,50,75,120,200].map(hz => [hz, +gain('gate', hz).toFixed(1)]));
assert(gate[30] > -1 && gate[75] > -1 && gate[200] > -1 && gate[50] < -20, 'gate 链变了 ' + JSON.stringify(gate));
// 谐波保持 Q=30：三个都改 Q=5 时 120 Hz 掉 1.9 dB、放松门读数整体低 12%（evidence/2026-10-25-gate-q5）
assert(gate[120] > -0.5, 'gate 谐波陷波被放宽了 ' + JSON.stringify(gate));
// 基波 Q=5：50 Hz 突然出现后 50–150 ms 只剩约 11%（Q=30 时 63%），工频强度变化不再漏 100–300 ms 当成动作
const burst = (() => { const f = new DisplayFilter(); let s = 0; for (let i = 0; i < 1100; i++) { const y = f.process(row(i >= 800 ? Math.sin(2*Math.PI*50*i/2000) : 0))[0]; if (i >= 900) s += y*y; } return Math.sqrt(s / 200 * 2); })();
assert(burst < 0.2, 'gate 50 Hz 陷波建立太慢 ' + burst.toFixed(3));
assert.deepEqual(new DisplayFilter().process(row(1)), new DisplayFilter(50, 8, 'gate').process(row(1)), '默认必须还是 gate 链');
assert(Math.abs(new DisplayFilter().process(row(1))[0] - 0.8955600699717047) < 1e-12, 'gate 链系数变了（指纹：50 Hz Q=5、100/150 Hz Q=30 的首样本；Q=30 全部时是 0.9072044153940412）');
// 陷波要定宽 6 Hz：偏中心 2 Hz 也得压住；模拟原型 Q 写法在 900 Hz 只剩 0.65 Hz 宽，898/902 Hz 只有 −0.1 dB
assert(gain('view', 898) < -4 && gain('view', 902) < -4 && gain('view', 52) < -4, 'view 陷波带宽不是定宽 6 Hz');
// SignalStream 的默认也必须是 gate：studio 的门流就是 new SignalStream()，30 Hz 要过（gate −0.2 dB），view 链会压到 −50 dB
const stream30 = (chain) => { const s = chain ? new SignalStream(chain) : new SignalStream(); s.push(Array.from({ length: n }, (_, i) => row(100 * Math.sin(2 * Math.PI * 30 * i / 2000))), 1000, n, 0); return s.values()[0]; };
assert(stream30() > 60 && stream30() < 75 && stream30('view') < 2, 'SignalStream 默认必须是 gate 链');
assert(gain('view', 60, 60) < -30 && gain('view', 920, 60) > -1.5 && Number.isFinite(gain('view', 990, 60)), '60 Hz 市电下 view 链不对');
console.log('两条链检查通过：view', JSON.stringify(view), 'gate', JSON.stringify(gate));
console.log('滤波边界检查通过：连续分块、原值不变、稳态初始化、重连/超时/缺样/丢包/非法数据、准备期不放行不误判噪声、高幅拒绝、低幅恢复');
