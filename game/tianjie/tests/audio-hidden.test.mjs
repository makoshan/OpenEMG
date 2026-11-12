import test from 'node:test';
import assert from 'node:assert/strict';
import { AudioDirector } from '../src/audio.mjs';
// 假 AudioContext：只记 suspend / resume 调用，验证隐藏时挂起、可见且音效开时恢复
function fake(){const calls=[];const gain={setTargetAtTime(){}};return {calls,ctx:{state:'running',currentTime:0,suspend(){calls.push('suspend');this.state='suspended';return Promise.resolve();},resume(){calls.push('resume');this.state='running';return Promise.resolve();}},master:{gain}};}
test('hidden window suspends audio; visible again resumes only when sound is on',()=>{
  const a=new AudioDirector();const f=fake();a.context=f.ctx;a.master=f.master;a.ambient=[];
  a.setHidden(true);assert.equal(f.ctx.state,'suspended');
  a.setEnabled(true);assert.equal(f.ctx.state,'suspended','隐藏期间打开音效也不能出声');
  a.setHidden(false);assert.equal(f.ctx.state,'running');
  a.setEnabled(false);a.setHidden(true);a.setHidden(false);assert.equal(f.ctx.state,'suspended','音效关着时回到前台不恢复');
});
test('setHidden before unlock is safe',()=>{const a=new AudioDirector();a.setHidden(true);a.setHidden(false);assert.equal(a.context,null);});
test('hidden window: sound events are dropped, not queued for a burst on return',()=>{
  const a=new AudioDirector();const f=fake();a.context=f.ctx;a.master=f.master;a.ambient=[];let touched=0;
  Object.defineProperty(f.ctx,'currentTime',{get(){touched++;return 0;}});
  a.setHidden(true);touched=0;a.event('thunder');a.endingCue('gate');assert.equal(touched,0,'隐藏时不排任何音效');
});
test('first unlock while hidden ends suspended',async()=>{
  const a=new AudioDirector();const calls=[];a.hidden=true;
  globalThis.window={AudioContext:class{constructor(){this.state='running';this.currentTime=0;this.sampleRate=8000;this.destination={};}
    createGain(){return {gain:{value:0,setTargetAtTime(){}},connect(){}};}createDynamicsCompressor(){return {threshold:{},ratio:{},connect(){}};}
    createConvolver(){return {connect(){}};}createBuffer(ch,n){return {getChannelData:()=>new Float32Array(n)};}
    createBufferSource(){return {connect(){},start(){}};}createBiquadFilter(){return {frequency:{},Q:{},connect(){}};}
    suspend(){calls.push('suspend');this.state='suspended';return Promise.resolve();}resume(){calls.push('resume');this.state='running';return Promise.resolve();}}};
  await a.unlock();clearInterval(a.timer);delete globalThis.window;
  assert.equal(a.context.state,'suspended','隐藏时首次解锁不能出声');assert.ok(!calls.includes('resume'));
});
