// Real renderer, synthetic inputs only. No wristband access.
const {app,BrowserWindow}=require('electron'),fs=require('node:fs'),path=require('node:path');
const out=path.resolve(__dirname,'build/game-art');app.setPath('userData',path.join(out,'userdata'));
const wait=ms=>new Promise(r=>setTimeout(r,ms)),check=(v,m)=>{if(!v)throw Error(m)};
app.whenReady().then(async()=>{
 fs.mkdirSync(out,{recursive:true});const win=new BrowserWindow({width:1600,height:960,show:false,webPreferences:{sandbox:true,contextIsolation:true,backgroundThrottling:false}}),errors=[];
 win.webContents.on('console-message',(_e,...args)=>{const msg=args.find(x=>typeof x==='object'&&x.message)?.message||args[1];if(/ERROR|Error|shader.*error|VALIDATE_STATUS.*false/i.test(String(msg)))errors.push(String(msg));});
 await win.loadFile(path.join(__dirname,'game/tianjie/index.html'));
 const js=s=>win.webContents.executeJavaScript(s),click=id=>js(`document.getElementById('${id}').click()`),diag=()=>js('TianjieGame.diagnostics()'),snap=()=>js('TianjieGame.snapshot()'),save=async n=>fs.writeFileSync(path.join(out,n+'.png'),(await win.capturePage()).toPNG());
 for(let i=0;i<100&&!(await diag().catch(()=>({}))).ready;i++)await wait(100);
 check((await diag()).ready,'load timeout');await wait(400);check((await diag()).daylight===0,'cover must start at night');await save('01-cover');
 await click('begin');await click('story-skip');await click('wear-keyboard');await wait(500);await save('02-gesture-practice');
 check(await js('document.querySelectorAll(".seal-gallery [data-current=true]").length===1'),'active lesson missing');
 await click('journey-close');await click('quickstart');
 for(const id of ['godmode','testmode'])await js(`{const b=document.getElementById('${id}');if(b.getAttribute('aria-pressed')!=='true')b.click()}`);
 await wait(2300);
 for(const g of ['sword','guard','thunder']){
  if((await snap()).paused)await click('pause');const cast=await js(`TianjieGame.inputResult({gesture:'${g}',confidence:.95})`);check(cast.accepted,`cast rejected: ${JSON.stringify(cast)}`);for(let frame=0;frame<15;frame++){await wait(25);const curls=(await diag()).handCurls;if(g==='thunder'?curls?.[0]>1.25:g==='guard'?curls?.[1]<.1:curls?.[1]>1.1)break;}
  check(await js(`document.querySelector('[data-action="${g}"]').classList.contains('active')`),'active skill not highlighted');if(g==='thunder')check((await diag()).handCurls.every(c=>c>1.2),'thunder hand never formed fist');await click('pause');await save('03-'+g);await click('pause');await wait(1100);
 }
 check(await js('[...document.images].every(i=>i.complete&&i.naturalWidth>0)'),'broken UI image');
 let sawClear=false,pausedDawn=false;
 for(let i=0;i<350;i++){
  const s=await snap(),d=await diag();if(s.paused)await click('pause');
  if(s.phase==='travel'&&s.area===0){
   if(!sawClear){sawClear=true;check(await js('!document.getElementById("chapter-clear").hidden'),'clear title missing');await save('04-night-disperses');}
   if(!pausedDawn&&d.daylight>.2&&d.daylight<.8){await click('pause');const day=(await diag()).daylight;await wait(200);check((await diag()).daylight===day,'sunrise advanced while paused');await click('pause');pausedDawn=true;}
  }
  if(s.area===1){check(d.daylight===1,'bridge is not daylight');await wait(600);await save('05-daytime-bridge');break;}
  if(s.phase==='combat')await js("TianjieGame.input({gesture:'thunder',confidence:.95});TianjieGame.input({gesture:'sword',confidence:.95})");await wait(100);
 }
 check(sawClear&&pausedDawn&&(await snap()).area===1,'day transition not observed');
 await click('pause');win.setContentSize(390,844);await wait(400);await save('06-mobile');
 check(await js("[...document.querySelectorAll('.skill')].every(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight})"),'mobile skills overflow');
 await click('return');await wait(300);check((await diag()).daylight===0,'reset must restore night');
 check((await diag()).failedAssets.length===0,'failed world assets');check(errors.length===0,'renderer errors: '+errors.join('\n'));
 fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({ok:true,checks:['night cover','loaded medallions','practice highlight','active spells','chapter clear','pause freezes sunrise','day bridge','mobile HUD','reset to night','no renderer errors'],diagnostics:await diag()},null,2));
 console.log('Art flow passed; proof:',out);app.exit(0);
}).catch(e=>{console.error(e);app.exit(1)});
