// Offline rendering of the actual Web Audio score; no microphone or device access.
const {app,BrowserWindow}=require('electron'),fs=require('node:fs'),path=require('node:path');
const out=path.resolve('build/audio-check');app.setPath('userData',path.join(out,'userdata'));
const source=fs.readFileSync(path.resolve(__dirname,'../game/tianjie/src/audio.mjs'),'utf8').replace('export const','const').replace('export class','class');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
app.whenReady().then(async()=>{
 fs.mkdirSync(out,{recursive:true});const win=new BrowserWindow({show:false,webPreferences:{sandbox:true,nodeIntegration:false,contextIsolation:true}});await win.loadURL('about:blank');
 const results=[];
 for(let scene=0;scene<4;scene++){
  const data=await win.webContents.executeJavaScript(`(async()=>{${source}
   const context=new OfflineAudioContext(2,44100*10,44100);window.AudioContext=function(){return context;};
   const score=new AudioDirector();score.enabled=false;await score.unlock();clearInterval(score.timer);score.enabled=true;score.setScene(${scene});score.mixAmbience();
   let t=.1,i=0;while(t<7)t+=score.phrase(i++%32,t,true);
   score.event('sword');score.event('guard');score.event('thunder');score.event('enemy-killed');
   const b=await context.startRendering(),channels=[Array.from(b.getChannelData(0)),Array.from(b.getChannelData(1))];
   let peak=0,sq=0;for(const c of channels)for(const x of c){peak=Math.max(peak,Math.abs(x));sq+=x*x;}
   return {peak,rms:Math.sqrt(sq/(b.length*2)),channels,name:SCENE_SCORES[${scene}].name};})()`);
  assert(Number.isFinite(data.peak)&&data.peak<1,'nonfinite/clipped audio scene '+scene);assert(data.rms>.005,'silent score scene '+scene);
  const n=data.channels[0].length,buffer=Buffer.alloc(44+n*4);buffer.write('RIFF');buffer.writeUInt32LE(36+n*4,4);buffer.write('WAVEfmt ',8);buffer.writeUInt32LE(16,16);buffer.writeUInt16LE(1,20);buffer.writeUInt16LE(2,22);buffer.writeUInt32LE(44100,24);buffer.writeUInt32LE(44100*4,28);buffer.writeUInt16LE(4,32);buffer.writeUInt16LE(16,34);buffer.write('data',36);buffer.writeUInt32LE(n*4,40);
  for(let i=0;i<n;i++)for(let ch=0;ch<2;ch++)buffer.writeInt16LE(Math.round(Math.max(-1,Math.min(1,data.channels[ch][i]))*32767),44+(i*2+ch)*2);
  fs.writeFileSync(path.join(out,'scene-'+scene+'.wav'),buffer);results.push({scene,name:data.name,peak:data.peak,rms:data.rms});
 }
 const outcome=[];
 for(const mode of ['outcome','silent']){
  const data=await win.webContents.executeJavaScript(`(async()=>{${source}
   const context=new OfflineAudioContext(2,44100*3,44100);window.AudioContext=function(){return context;};
   const score=new AudioDirector();score.enabled=false;await score.unlock();clearInterval(score.timer);score.enabled=true;
   score.event('finish');score.setMode('${mode}');
   const b=await context.startRendering(),d=b.getChannelData(0);let sq=0;for(let i=22050;i<66150;i++)sq+=d[i]*d[i];
   return {mode:'${mode}',tailRms:Math.sqrt(sq/44100)};})()`);outcome.push(data);
 }
 assert(outcome[0].tailRms>.001,'victory tail was truncated');
 assert(outcome[1].tailRms<outcome[0].tailRms*.02,'pause did not mute active sound');
 console.log('Outcome and pause audio:',outcome);
 fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(results,null,2));console.log('Four scene scores rendered without clipping:',results);app.exit(0);
}).catch(e=>{console.error(e);app.exit(1);});
