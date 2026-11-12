// Offline synthetic status -> production IPC -> real sandboxed game. Never opens a device.
const {app,BrowserWindow}=require('electron'),fs=require('node:fs'),path=require('node:path');
const proof=path.resolve('build/onboarding-check');app.setPath('userData',path.join(proof,'userdata'));
const wait=ms=>new Promise(r=>setTimeout(r,ms));const check=(v,m)=>{if(!v)throw Error(m);};
app.whenReady().then(async()=>{
 fs.mkdirSync(proof,{recursive:true});const handlers={};const {registerGame}=require('./electron/game.cjs');
 registerGame({ipcMain:{handle:(ch,f)=>handlers[ch]=f},guarded:fn=>async(_e,...a)=>{try{return {ok:true,value:await fn(...a)}}catch(e){return {ok:false,message:e.message}}}});
 const call=(ch,...a)=>handlers[ch]({},...a);await call('yuanli:game:open');const win=BrowserWindow.getAllWindows()[0];win.webContents.setBackgroundThrottling(false);
 const js=s=>win.webContents.executeJavaScript(s),snap=()=>js('window.TianjieGame.onboarding()'),click=id=>js(`document.getElementById(${JSON.stringify(id)}).click()`);
 for(let i=0;i<120;i++){if(await js('window.TianjieGame?.diagnostics().ready').catch(()=>false))break;await wait(200);}check(await js('window.TianjieGame?.diagnostics().ready'),'game not ready');win.hide();await wait(200);
 const save=async name=>{await wait(120);fs.writeFileSync(path.join(proof,name+'.png'),(await win.capturePage()).toPNG());};
 await save('00-title');await click('begin');check((await snap()).phase==='story','begin must open story');await save('01-story');await click('story-skip');
 await wait(2100);check(await js('document.getElementById("wear-continue").disabled'),'absent device passed');await save('02-no-device');
 await click('wear-keyboard');check((await snap()).mode==='keyboard','keyboard mode missing');
 for(const g of ['sword','guard','thunder']){await wait(450);await save('03-keyboard-'+g);check(!(await call('yuanli:game:gesture',g,.95)).value.accepted,'hardware counted as keyboard');await click('practice-key');await click('lesson-next');}
 check((await snap()).phase==='ready','keyboard practice incomplete');check((await js('document.getElementById("ready-mode").textContent')).includes('尚未检查'),'keyboard falsely claims hardware');
 await click('ready-hardware');await click('wear-confirm');
 const band=(text='识别中 · 放松 0.96')=>({state:'live',text,pose:'',acc:[0,0,1000],lanes:Array(8).fill('ok'),signal:'信号正常',rec:text});
 const send=b=>call('yuanli:game:band',b);let packet=null,busy=false;setInterval(()=>{if(packet&&!busy){busy=true;send(packet).finally(()=>busy=false);}},80);const stream=async(ms,b=band())=>{packet=b;await send(b);await wait(ms);};
 await stream(2200,band('识别中 · 数据过期'));check(!(await snap()).wearReady,'expired predictions passed');
 await stream(2300);check((await snap()).wearReady,'fresh signal not ready');await click('wear-continue');check((await snap()).phase==='practice','practice did not open: '+JSON.stringify(await snap()));
 await stream(800);const wrong=(await call('yuanli:game:gesture','guard',.95)).value;check(!wrong.accepted&&['practice-other','relax'].includes(wrong.code),'wrong gesture accepted: '+JSON.stringify(wrong));
 const practice=async()=>{for(const g of ['sword','guard','thunder']){await stream(800);const before=await js('window.TianjieGame.snapshot()');check(!(await call('yuanli:game:gesture',g,.5)).value.accepted,'confidence passed');const r=(await call('yuanli:game:gesture',g,.95)).value;check(r.accepted&&r.code==='practice','correct practice rejected: '+JSON.stringify(r));const after=await js('window.TianjieGame.snapshot()');check(after.hp===before.hp&&after.qi===before.qi&&after.boss===before.boss&&after.phase==='ready','practice changed combat');await click('lesson-next');}};
 await practice();check((await snap()).canFinish,'hardware practice incomplete');packet=null;await wait(1800);check((await snap()).phase==='wear','signal loss did not reset');check((await snap()).counts.every(n=>n===0),'old wearing retained');
 await click('wear-confirm');await stream(2300);await click('wear-continue');await practice();await click('enter-trial');check((await snap()).phase==='closed','tutorial not closed');check((await js('window.TianjieGame.snapshot().phase'))==='combat','not in combat');
 await wait(2100);check((await call('yuanli:game:gesture','sword',.95)).value.accepted,'hardware combat broken');
 fs.writeFileSync(path.join(proof,'result.json'),JSON.stringify({ok:true,evidence:'synthetic-status-and-production-ipc',checks:['story','missing-signal','explicit-keyboard','expired-predictions','fresh-wearing','wrong-gesture','confidence','three-lessons','no-combat-effects','disconnect-invalidates','reconnect','hardware-combat']},null,2));
 console.log('Onboarding UI/IPC passed:',proof);app.exit(0);
}).catch(e=>{console.error(e);app.exit(1)});
