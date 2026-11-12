import test from 'node:test';import assert from 'node:assert/strict';import {parseBand,tilt} from '../src/band.mjs';
test('band status rejects bad input',()=>{assert.equal(parseBand(null),null);assert.equal(parseBand({state:'hack',text:'x'}),null);assert.equal(parseBand({state:'live',text:'x',pose:'alert'}),null);assert.equal(parseBand({state:'live',text:1}),null);const b=parseBand({state:'live',text:'识别中',pose:'sword',acc:[0,0,NaN]});assert.equal(b.pose,'sword');assert.equal(b.acc,null);assert.equal(parseBand({state:'live',text:'x'.repeat(99)}).text.length,40);});
test('tilt is zero at neutral, signed, and clamped',()=>{const n=[0,0,1000];const z=tilt(n,[0,0,2000]);assert.ok(Math.abs(z.pitch)<1e-9&&Math.abs(z.roll)<1e-9);const a=Math.PI/12;const r=tilt(n,[Math.sin(a)*1000,0,Math.cos(a)*1000]);const p=tilt(n,[-Math.sin(a)*1000,0,Math.cos(a)*1000]);assert.ok(Math.abs(Math.abs(r.pitch)-a)<1e-6,'15° 倾斜读回 15°');assert.equal(Math.sign(r.pitch),-Math.sign(p.pitch),'反向倾斜符号相反');const big=tilt(n,[1000,0,0]);assert.ok(Math.abs(big.pitch)<=.7);const s=tilt(n,[0,Math.sin(a)*1000,Math.cos(a)*1000]);assert.ok(Math.abs(Math.abs(s.roll)-a)<1e-6&&Math.abs(s.pitch)<1e-9,'另一轴只动 roll');});
test('band panel fields: lanes must be 8 known states, texts clipped, bad ones dropped',()=>{
  const ok=parseBand({state:'live',text:'识别中',pose:'',acc:null,lanes:['ok','ok','mask','bad','ok','ok','ok',''],signal:'第 3 路接触差 · 已屏蔽'.repeat(5),rec:'道指 0.91 → 出招'});
  assert.deepEqual(ok.lanes,['ok','ok','mask','bad','ok','ok','ok','']); assert.equal(ok.signal.length,40); assert.equal(ok.rec,'道指 0.91 → 出招');
  assert.equal(parseBand({state:'live',text:'x',pose:'',lanes:['ok','hack','ok','ok','ok','ok','ok','ok']}).lanes,null);
  assert.equal(parseBand({state:'live',text:'x',pose:'',lanes:['ok']}).lanes,null);
  assert.equal(parseBand({state:'live',text:'x',pose:'',rec:{}}).rec,'');
});
