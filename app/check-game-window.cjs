// Production sandbox, input bridge and renderer; synthetic gestures only, no device access.
const {app,BrowserWindow}=require('electron'),fs=require('node:fs'),path=require('node:path');
const root=process.env.YUANLI_GAME_ROOT||__dirname,proof=path.resolve('build/game-check');app.setPath('userData',path.join(proof,'userdata'));
const wait=ms=>new Promise(r=>setTimeout(r,ms)),check=(v,m)=>{if(!v)throw Error(m);};
app.whenReady().then(async()=>{
 const {bridgeCenterX,deckHeight,BRIDGE,LAKE_ENTRY}=await import(require('node:url').pathToFileURL(path.resolve(__dirname,'../game/tianjie/src/bridge-route.mjs')).href);
 fs.mkdirSync(proof,{recursive:true});const handlers={};const {registerGame}=require(path.join(root,'electron/game.cjs'));
 const gm=registerGame({ipcMain:{handle:(ch,f)=>handlers[ch]=f},guarded:fn=>async(_e,...a)=>{try{return {ok:true,value:await fn(...a)}}catch(e){return {ok:false,message:e.message,code:e.code}}}});
 const call=(ch,...a)=>handlers[ch]({},...a),send=(g,c=.95)=>call('yuanli:game:gesture',g,c).then(r=>r.value);
 check((await send('sword')).code==='closed','closed reason missing');check(!(await call('yuanli:game:gesture','alert(1)',.95)).ok,'invalid name passed');
 await call('yuanli:game:open');const win=BrowserWindow.getAllWindows()[0];win.webContents.setBackgroundThrottling(false);const js=s=>win.webContents.executeJavaScript(s),click=id=>js(`document.getElementById(${JSON.stringify(id)}).click()`),snap=()=>js('window.TianjieGame.snapshot()');
 for(let i=0;i<120;i++){if(await js('window.TianjieGame?.diagnostics().ready').catch(()=>false))break;await wait(200);}check(await js('window.TianjieGame?.diagnostics().ready'),'game load timeout');win.hide();await wait(200);await click('sound');
 const save=async name=>{fs.writeFileSync(path.join(proof,name+'.png'),(await win.capturePage()).toPNG());};
 const set=(id,on)=>js(`{const b=document.getElementById('${id}');if(b.getAttribute('aria-pressed')!=='${on}')b.click();}`);
 check((await send('sword')).code==='not-started','not-started reason missing');await click('quickstart');await set('godmode',true);await set('testmode',false);await wait(2300);
 await js('window.dispatchEvent(new Event("blur"))');check((await send('sword')).code==='paused','paused bypassed');await click('pause');
 for(const g of ['sword','guard','thunder']){check((await send(g)).accepted,`${g} rejected`);await wait(70);check((await js('window.TianjieGame.diagnostics().handAura'))===g,`${g} aura missing`);await save('aura-'+g);}
 check(!(await send('sword',.5)).accepted,'low confidence passed');check((await send('thunder')).code==='cooldown','cooldown bypassed');
 await wait(450);const live=await snap();check(live.enemies.some(e=>e.visible),'no visible enemy');await save('01-gate-combat');
 // band panel and wrist following remain the existing contract.
 const status={state:'live',text:'识别中 · 道指剑 0.95',pose:'sword',acc:[250,0,966],lanes:['ok','mask','ok','ok','ok','ok','ok','ok'],signal:'第 2 路已屏蔽',rec:'道指剑 0.95'};
 check((await call('yuanli:game:band',status)).value,'band rejected');check((await js('document.querySelectorAll("#device-lanes i").length'))===8,'eight channels missing');
 await wait(1700);check((await js('document.getElementById("device-state").dataset.state'))==='off','stale band not cleared');
 // Clear via normal input/cooldown and observe all four scenes. God mode only isolates survival in this path test.
 const sceneProof=new Set([0]),gateProof=new Set(),routeSamples=[],descentProof=new Set();let ended=false,deathSeen=false,dragonSeen=false;
 for(let i=0;i<1500;i++){
  const s=await snap();if(s.paused)await click('pause');
  if(s.phase==='travel'&&s.area===0){
   const d=await js('window.TianjieGame.diagnostics()');routeSamples.push(d.camera);
   check(await js('Number(document.getElementById("scene-curtain").style.opacity)===0'),'gate passage must stay visible');
   const z=d.camera[2],stage=z>-20?'approach':z>-28?'doorway':'cliff-reveal';
   if(!gateProof.has(stage)){gateProof.add(stage);await save('gate-travel-'+stage);
    if(stage==='doorway'){await click('pause');const frozen=await js('window.TianjieGame.diagnostics().camera');await wait(350);check(JSON.stringify(frozen)===JSON.stringify(await js('window.TianjieGame.diagnostics().camera')),'paused gate camera moved');await click('pause');}
   }
   if(z<-22&&z>-31){check(Math.abs(d.camera[0])<1,'camera crossed the gate outside the opening');check(d.gateAngles.every(a=>Math.abs(a)>1.4),'camera reached closed doors');}
  }
  if(s.phase==='travel'&&s.area===1){
   const d=await js('window.TianjieGame.diagnostics()'),p=d.journeyProgress;
   const stage=p<.48?'bridge':p<.73?'pavilion':'descent';
   if((stage==='bridge'&&p>.3||stage==='pavilion'&&p>.64||stage==='descent'&&p>.89)&&!descentProof.has(stage)){descentProof.add(stage);await save('journey-'+stage);if(stage==='pavilion'){await click('pause');const pos=await js('window.TianjieGame.diagnostics().camera');await wait(250);check(JSON.stringify(pos)===JSON.stringify(await js('window.TianjieGame.diagnostics().camera')),'pavilion pause moved');await click('pause');}}
   check(await js('Number(document.getElementById("scene-curtain").style.opacity)===0'),'bridge-to-lake must remain visible');
  }
  if(!deathSeen&&(await js('window.TianjieGame.diagnostics().deathBursts'))>0){deathSeen=true;await save('death-burst');}
  if(!dragonSeen&&s.area===1&&s.enemies.some(e=>e.kind==='dragonfly'&&e.visible&&e.alive)){
   dragonSeen=true;for(let j=0;j<3&&(await snap()).target?.id!=='bridge-keeper';j++)await js('document.body.dispatchEvent(new KeyboardEvent("keydown",{code:"Tab",bubbles:true}))');await wait(1300);await save('dragonfly-demon');
  }
  if(!sceneProof.has(s.area)){sceneProof.add(s.area);await wait(2000);await save(['gate','02-cloud-bridge','03-mirror-lake','04-thunder-court'][s.area]);
   if(s.area===2){const p=await js('window.TianjieGame.diagnostics().camera');check(Math.abs(p[0]-LAKE_ENTRY.x)<4&&Math.abs(p[1]-LAKE_ENTRY.y)<.15,'lake entry was not below pavilion');check((await js('window.TianjieGame.diagnostics().audio.scene'))===2,'water sound scene missing');}
   if(s.area===1){
    await js('document.body.dispatchEvent(new KeyboardEvent("keydown",{code:"KeyD",bubbles:true}))');await wait(700);await js('document.body.dispatchEvent(new KeyboardEvent("keyup",{code:"KeyD",bubbles:true}));document.body.dispatchEvent(new KeyboardEvent("keydown",{code:"Space",bubbles:true}));document.body.dispatchEvent(new KeyboardEvent("keyup",{code:"Space",bubbles:true}))');await wait(250);
    const bridge=await js('window.TianjieGame.diagnostics().camera');check(bridge[0]-bridgeCenterX(bridge[2])<=BRIDGE.safeX+.03&&bridge[0]-bridgeCenterX(bridge[2])>BRIDGE.safeX-.12,'movement/dash escaped narrow bridge bounds');
    const deck=deckHeight(bridge[2]);check(Math.abs(bridge[1]-deck-1.75)<.15,'camera does not follow suspended deck');
   }
  }
  if(s.phase==='victory'){ended=true;break;}
  if((s.incoming&&s.incoming.hit-s.time<.27)||(s.hazard&&s.hazard.hit-s.time<.3)||(s.area===2&&s.enemies.some(e=>e.visible&&e.alive&&e.shielded)))await send('guard');
  if((s.cooldowns.sword||0)<=s.time)await send('sword');
  if(((s.cooldowns.thunder||0)<=s.time&&s.qi>=35))await send('thunder');
  await wait(65);
 }
 check(ended,'normal input did not finish route');check(descentProof.size===3&&deathSeen&&dragonSeen,'journey/death/dragonfly proof missing');check(gateProof.size===3,'continuous gate journey checkpoints missing');const won=await snap();check(won.kills===12&&sceneProof.size===4,'route did not require twelve enemies and four scenes');check(await js('!document.getElementById("ascension").hidden'),'victory cinematic absent');await wait(650);await save('05-victory-impact');await click('ending-skip');await wait(250);check(await js('!document.getElementById("result").hidden'),'victory summary absent');await save('05-victory');
 // Explicit positive/negative control for surviving vs taking damage.
 await click('retry');await wait(100);check((await js('window.TianjieGame.diagnostics().gateAngles')).every(a=>a===0),'retry did not close the gate');await set('godmode',true);await wait(8000);const protectedSnap=await snap();check(protectedSnap.time>5&&protectedSnap.hp===100,'god-mode positive control invalid');await set('godmode',false);let damaged=await snap();for(let i=0;i<45&&damaged.hp===100;i++){await wait(200);damaged=await snap();}check(damaged.hp<100,'normal mode must take damage');for(let i=0;i<130&&(await snap()).phase!=='defeat';i++)await wait(200);check((await snap()).phase==='defeat','unopposed run must fail');await wait(2600);await save('06-defeat');
 check(!(await js('window.TianjieGame.inputResult({gesture:"dash",confidence:1})')).accepted,'hardware dash should be rejected');
 const diagnostics=await js('window.TianjieGame.diagnostics()');check(diagnostics.failedAssets.length===0,'assets failed');fs.writeFileSync(path.join(proof,'result.json'),JSON.stringify({ok:true,evidence:'synthetic-input-production-window',routeSamples,descentProof:[...descentProof],deathSeen,dragonSeen,won,diagnostics,blockedRequests:gm.blockedRequests()},null,2));
 console.log('Game window passed: twelve enemies, four scenes, normal cooldown, band/staleness, win and damage controls. Evidence:',proof);app.exit(0);
}).catch(e=>{console.error(e);app.exit(1);});
