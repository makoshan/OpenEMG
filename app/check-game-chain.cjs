// 合成设备信号→真实MetaLive→真实Electron IPC→真实游戏，再将拒绝原因返回识别页。
const {app,BrowserWindow,ipcMain}=require('electron');
const fs=require('node:fs'),path=require('node:path');
app.setPath('userData',path.resolve('build/chain-check/userdata'));
app.whenReady().then(async()=>{
 fs.mkdirSync('build/chain-check',{recursive:true});
 const {registerGame}=require('./electron/game.cjs');
 const handlers={};
 registerGame({ipcMain:{handle:(name,fn)=>{handlers[name]=fn;ipcMain.handle(name,fn);}},guarded:fn=>async(_e,...a)=>{try{return {ok:true,value:await fn(...a)}}catch(e){return {ok:false,message:e.message}}}});
 await handlers['yuanli:game:open']({});
 const game=BrowserWindow.getAllWindows()[0];game.webContents.setBackgroundThrottling(false);
 const js=s=>game.webContents.executeJavaScript(s);const wait=ms=>new Promise(r=>setTimeout(r,ms));
 for(let i=0;i<100;i++){if(await js('window.TianjieGame?.diagnostics().ready').catch(()=>false))break;await wait(200);}
 game.hide();await wait(300);
 await js('document.getElementById("quickstart").click();{const b=document.getElementById("testmode");if(b.getAttribute("aria-pressed")!=="true")b.click()}');
 ipcMain.handle('test:pause',()=>js('window.dispatchEvent(new Event("blur"))'));
 const preload=path.resolve('build/chain-check/preload.cjs');
 fs.writeFileSync(preload,`const {contextBridge,ipcRenderer}=require('electron');contextBridge.exposeInMainWorld('testGame',{gesture:(g,c)=>ipcRenderer.invoke('yuanli:game:gesture',g,c)});contextBridge.exposeInMainWorld('testPause',()=>ipcRenderer.invoke('test:pause'));`);
 const live=new BrowserWindow({show:false,webPreferences:{preload,backgroundThrottling:false}});
 live.webContents.on('console-message',(_e,_level,message)=>console.log('识别页:',message));
 await live.loadFile('build/live-dist/build/live-check/index.html');
 for(let i=0;i<200;i++){await wait(100);const result=await live.webContents.executeJavaScript('window.checkResult');if(result){console.log(JSON.stringify(result));fs.writeFileSync('build/chain-check/result.json',JSON.stringify(result));fs.writeFileSync('build/chain-check/game.png',(await game.capturePage()).toPNG());app.exit(result.ok?0:1);return;}}
 throw Error('完整链路超时');
}).catch(e=>{console.error(e);app.exit(1)});
