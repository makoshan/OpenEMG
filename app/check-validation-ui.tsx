// 隔离媒体夹具：不请求真实摄像头、不连接采集器；真实MediaRecorder只编码合成画布。
import React from 'react';
import { createRoot } from 'react-dom/client';
import { ContinuousValidation } from './src/emg8/continuous-validation';
import './src/tokens.css';
import './src/app.css';
import './src/emg8/emg8.css';
import './src/emg8/thumb-capture.css';
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
const assert = (ok: unknown, why: string) => { if (!ok) throw Error(why); };
const NativeRecorder = window.MediaRecorder, nativeCapture = HTMLCanvasElement.prototype.captureStream;
let mode = '', callback = 0, frame = 0, permitDelay = 0, stoppedTracks = 0;
let requests: MediaStreamConstraints[] = [], tracks: ReturnType<typeof track>[] = [], denied = false, granted = false;
const cameras = [{kind:'videoinput', deviceId:'internal', label:'MacBook Air相机'}, {kind:'videoinput',deviceId:'action5',label:'OsmoAction5pro'}];
const timers = new Map<number, ReturnType<typeof setTimeout>>();
const track = (id = 'internal') => {
  const t = {readyState:'live', label:id === 'action5' ? 'OsmoAction5pro' : 'MacBook Air相机',
    getSettings: () => ({deviceId:id}), stop() { stoppedTracks++; t.readyState='ended'; }, onended:null as (() => void) | null};
  tracks.push(t); return t;
};
const stream = (id = 'internal') => { const t = track(id); return {getTracks: () => [t], getVideoTracks: () => [t]}; };
Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', {value: async () =>
  cameras.map(c => ({...c, label:mode === 'hidden-labels' && !granted ? '' : c.label}))});
Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {value: async (c: MediaStreamConstraints) => {
  requests.push(c); await sleep(permitDelay); if (denied) throw Error('权限拒绝'); granted = true;
  const id = ((c.video as MediaTrackConstraints)?.deviceId as ConstrainDOMStringParameters)?.exact as string;
  return stream(id || 'internal');
}});
Object.defineProperty(HTMLMediaElement.prototype, 'srcObject', {configurable:true, get() {return null;}, set(_value) {}});
HTMLMediaElement.prototype.play = async function () {};
HTMLCanvasElement.prototype.captureStream = () => stream() as unknown as MediaStream;
CanvasRenderingContext2D.prototype.drawImage = () => {};
HTMLVideoElement.prototype.requestVideoFrameCallback = function (fn) {
  const id = ++callback;
  timers.set(id, setTimeout(() => { timers.delete(id); fn(performance.now(), {mediaTime:++frame/30, presentedFrames:frame, expectedDisplayTime:performance.now()} as VideoFrameCallbackMetadata); }, 100));
  return id;
};
HTMLVideoElement.prototype.cancelVideoFrameCallback = id => { clearTimeout(timers.get(id)); timers.delete(id); };
class Recorder {
  static isTypeSupported() { return true; }
  state = 'inactive'; onstart: (() => void) | null = null; onstop: (() => void) | null = null;
  ondataavailable: ((e: {data: Blob}) => void) | null = null;
  start() { this.state='recording'; setTimeout(() => this.onstart?.(),10); }
  stop() { this.state='inactive'; if (mode === 'stop-timeout') return;
    this.ondataavailable?.({data:new Blob([new Uint8Array([0x1a,0x45,0xdf,0xa3])])}); this.onstop?.(); }
}
Object.defineProperty(window, 'MediaRecorder', {value:Recorder, configurable:true});
async function scenario(name: string) {
  mode=name; requests=[]; tracks=[]; denied=name==='denied'; granted=false;
  Object.defineProperty(window, 'MediaRecorder', {value:name==='native-recorder' ? NativeRecorder : Recorder, configurable:true});
  HTMLCanvasElement.prototype.captureStream = name==='native-recorder' ? nativeCapture : () => stream() as unknown as MediaStream;
  permitDelay = name==='slow-permission' ? 2100 : name==='cancel-preparing' ? 300 : 0;
  let busy=false, finalized=true, active=false, heldClock=false; const calls: Record<string, any>[]=[];
  const bridge = {validation: async (_: string,a: Record<string,any>) => {
    calls.push(a);
    if (name==='slow-clock-stop' && a.action==='clock' && !heldClock) {heldClock=true; await sleep(6000);}
    if (a.action==='start') {assert(finalized,'上次没有收尾'); active=true; finalized=false;}
    if (a.action==='stop') active=false;
    if (a.action==='finish') finalized=true;
    return {ok:true,value:{id:'fake',active,host_ms:performance.now(),path:'/tmp/test-only',complete:false}};
  }} as any;
  const host=document.createElement('div'); host.className='emg8'; document.body.append(host); const root=createRoot(host);
  const props={bridge,projectId:'fixture',ready:name!=='offline-preview',donning:1,labels:['rest','a','b','c'],onBusy:(v:boolean)=>{busy=v;},logger:{current:null}};
  root.render(<ContinuousValidation {...props} />);
  const button=(text:string) => [...host.querySelectorAll('button')].find(b=>b.textContent===text)!;
  for(let i=0;i<50 && (host.querySelectorAll('select option').length<3);i++) await sleep(20);
  assert(button('开始录制与倒计时').disabled,'未预览可录制');
  assert((host.querySelector('select') as HTMLSelectElement).value===(name==='hidden-labels'?'internal':'action5'),'首选摄像头错误：'+name+':'+host.innerHTML);
  button('开启预览').click();
  if (name==='cancel-preparing') {
    await sleep(50); button('关闭预览').click(); await sleep(500);
    assert(calls.length===0,'取消预览仍启动录制');
  } else if (name==='denied') {
    await sleep(150); assert(!busy && calls.length===0 && button('开始录制与倒计时').disabled,'拒绝权限仍可录制');
  } else {
    await sleep(permitDelay+300);
    assert(calls.length===0 && !active,'预览期间已开始原始录制');
    assert(!host.textContent?.includes('剩余约'),'预览期间倒计时');
    assert(button('开始录制与倒计时').disabled,'未确认入镜可录制');
    assert(((requests.at(-1)!.video as MediaTrackConstraints).deviceId as ConstrainDOMStringParameters).exact==='action5','未精确选择Action 5');
    assert(requests.every(r=>r.audio===false),'请求麦克风');
    if (name==='normal') { console.log('CAMERA_PREVIEW_SCREEN'); await sleep(250); }
    if (name==='switch-camera') {
      (host.querySelector('input[type=checkbox]') as HTMLInputElement).click(); await sleep(20);
      const select=host.querySelector('select')!; select.value='internal'; select.dispatchEvent(new Event('change',{bubbles:true})); await sleep(250);
      assert(tracks[0].readyState==='ended','旧摄像头未释放');
      assert(((requests.at(-1)!.video as MediaTrackConstraints).deviceId as ConstrainDOMStringParameters).exact==='internal','覆盖手动选择');
      assert(!(host.querySelector('input[type=checkbox]') as HTMLInputElement).checked,'切换镜头未清入镜确认');
    }
    if (name==='offline-preview' || name==='connection-lost-preview') {
      if (name==='connection-lost-preview') root.render(<ContinuousValidation {...props} ready={false} />);
      await sleep(50);
      assert(!busy && calls.length===0 && !button('关闭预览').disabled,'离线预览阻塞了识别启动或保存了数据');
      (host.querySelector('input[type=checkbox]') as HTMLInputElement).click(); await sleep(20);
      assert(button('开始录制与倒计时').disabled,'未连接也能录制');
      button('关闭预览').click(); await sleep(20);
    } else if (name==='unplug-preview') {
      if (name==='unplug-preview') {const t=tracks.at(-1)!; t.readyState='ended'; t.onended?.();}
      else root.render(<ContinuousValidation {...props} ready={false} />);
      await sleep(50); assert(button('开始录制与倒计时').disabled && calls.length===0 && !busy,'预览失联仍可录制');
    } else {
      (host.querySelector('input[type=checkbox]') as HTMLInputElement).click(); await sleep(30);
      const n=requests.length; button('开始录制与倒计时').click();
      await sleep(30); assert(host.querySelector('select')!.matches(':disabled'),'录制中可换镜头');
      assert(requests.length===n,'录制重新打开默认镜头');
      if (name==='slow-clock-stop') {
        await sleep(200); button('停止并保存已有部分').click(); await sleep(6500);
        assert(calls.filter(a=>a.action==='clock').length>=5,'等待时未保活');
        assert(calls.some(a=>a.action==='finish'),'在途同步结束后未收尾');
      } else {
        await sleep(600); assert(active && busy,'录制没有启动：'+host.textContent);
        if (name==='unplug-recording') {const t=tracks.find(t=>t.label==='OsmoAction5pro')!; t.readyState='ended'; t.onended?.();}
        else button('停止并保存已有部分').click();
        await sleep(name==='stop-timeout'?5300:name==='native-recorder'?1500:150);
        assert(calls.some(a=>a.action==='finish'),'未保存收尾');
        if (name==='stop-timeout' || name==='unplug-recording') assert(calls.find(a=>a.action==='finish')?.video_ok===false,'故障未标不完整');
        if (name==='stop-timeout') assert(calls.filter(a=>a.action==='clock').length>=7,'保存期间未心跳');
        assert(calls.at(-1)?.action==='finish','结束后仍写数据');
      }
    }
  }
  if (name==='native-recorder') {
    const blob=new Blob(calls.filter(a=>a.action==='video').map(a=>a.bytes),{type:'video/webm'});
    assert(blob.size>100,'真实录像无输出');
    const v=document.createElement('video'),url=URL.createObjectURL(blob);
    await new Promise<void>((resolve,reject)=>{v.onloadedmetadata=()=>resolve();v.onerror=()=>reject(Error('录像无法解码'));v.src=url;setTimeout(()=>reject(Error('解码超时')),3000);});
    assert(v.videoWidth===640 && v.videoHeight===480,'画幅错误');URL.revokeObjectURL(url);
  }
  assert(!busy && finalized,'页面或会话仍占用');
  root.unmount();host.remove();await sleep(50);
  assert(tracks.every(t=>t.readyState==='ended'),'摄像头未释放');
  console.log('PASS 连续验证页面 '+name);
}
try {
  for(const name of ['normal','offline-preview','hidden-labels','switch-camera','denied','unplug-preview','connection-lost-preview','unplug-recording','slow-permission','cancel-preparing','stop-timeout','native-recorder','slow-clock-stop']) await scenario(name);
  assert(stoppedTracks>=4,'媒体未释放');console.log('VALIDATION_UI_PASS');
} catch(e) {console.error('VALIDATION_UI_FAIL',String(e));}
