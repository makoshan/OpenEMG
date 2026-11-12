// node firmware/check_emg_studio.js — no hardware or real project writes.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const html = fs.readFileSync(__dirname + '/emg_pulse.html', 'utf8');
const script = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
async function main() {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {hidden:false, attrs:{}, setAttribute(k,v){this.attrs[k]=v;}, getAttribute(k){return k === 'src' ? this.src : this.attrs[k];}, removeAttribute(k){delete this[k];}});
    return elements.get(id);
  };
  const buttons = ['pulse','capture','train'].map(page => Object.assign(element(page), {dataset:{page}}));
  let state = {project:{id:'project-a', name:'测试工程'},rig:{kind:'emg',streaming:false}}, poll;
  const sandbox = {URLSearchParams, console, location:{search:'?view=studio&project=project-a'},
    document:{body:{classList:{add(){}}},getElementById:element,querySelectorAll:()=>buttons,querySelector:element},
    setInterval(fn){poll=fn;},fetch:async()=>({ok:true,json:async()=>state})};
  vm.createContext(sandbox); vm.runInContext(script,sandbox);
  await new Promise(resolve=>setImmediate(resolve));
  const frame = element('workspace');
  assert.equal(frame.src,'/pulse?project=project-a&embed=1&kind=emg');
  frame.contentWindow={hasUnsavedCapture:()=>true}; buttons[2].onclick();
  assert.equal(frame.src,'/pulse?project=project-a&embed=1&kind=emg','unsaved waveform must not be discarded');
  frame.contentWindow.hasUnsavedCapture=()=>false;
  buttons[2].onclick(); assert.equal(frame.src,'/guide?project=project-a&embed=1&view=train');
  assert.equal(buttons[2].attrs['aria-current'],'page');
  state.busy='录制中'; await poll(); const unchanged=frame.src;
  buttons[0].onclick(); assert.equal(frame.src,unchanged); assert.ok(buttons.every(b=>b.disabled));
  state.busy=null; state.rig.kind='wl8'; await poll();
  assert.equal(frame.src,'/?project=project-a&embed=1&view=train');
  buttons[1].onclick(); assert.equal(frame.src,'/?project=project-a&embed=1&view=capture');
  assert.match(element('studioNote').textContent,/CH1/);
  state.project.id='wrong-project'; await poll();
  assert.equal(frame.src,undefined); assert.equal(frame.hidden,true); assert.ok(buttons.every(b=>b.disabled));
  state.project.id='project-a'; await poll(); assert.equal(frame.hidden,false);
  sandbox.fetch=async()=>{throw Error('offline');}; await poll();
  assert.equal(frame.src,undefined); assert.ok(buttons.every(b=>b.disabled));
  sandbox.location.search='?view=studio&kind=wl8&section=capture&project=project-a';
  state.rig.kind='emg'; sandbox.fetch=async()=>({ok:true,json:async()=>state});
  vm.runInNewContext(script,{...sandbox});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(frame.src,undefined,'8ch entry must never fall back to 1ch UI');
  assert.match(element('studioStatus').textContent,/设备不匹配/);
  state.rig.kind='wl8'; await poll();
  assert.equal(frame.src,'/?project=project-a&embed=1&view=capture');
  assert.equal(buttons[1].textContent,'八通道波形与录制');
  state.rig.kind='emg'; await poll(); assert.equal(frame.src,undefined);
  console.log('PASS: three views, project propagation, recording lock, WL8 routing, mismatch/offline refusal and recovery');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
