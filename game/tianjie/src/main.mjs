import {GESTURES} from './gestures.mjs';
import {World} from './world.mjs';
import {Combat} from './combat.mjs';
import {ENCOUNTERS} from './encounters.mjs';
import {createOnboarding} from './onboarding-view.mjs';
import {AudioDirector} from './audio.mjs';
import {parseBand,tilt,STALE_MS} from './band.mjs';
const $=id=>document.getElementById(id),keys=new Set(),score=new AudioDirector();
let world,onboarding,ready=false,elapsed=0,resultAt=Infinity,cueUntil=0,high=true,lastInput=null,fps=0,frameCount=0,fpsAt=performance.now();
function cue(main,sub='',duration=1.5){$('cue').textContent=main;$('cue-small').textContent=sub;cueUntil=elapsed+duration;}
function unlock(){score.unlock().catch(()=>{});}
document.addEventListener('visibilitychange',()=>score.setHidden(document.hidden));score.setHidden(document.hidden);   // 最小化 / 隐藏 / 被挡住时静音
const game=new Combat(e=>{
 if(!ready)return;world.effect(e);if(e.type!=='finish')score.event(e.type);
 const m={sword:['道指剑','飞剑出鞘'],thunder:['五雷诀','符动雷落'],guard:['破邪印','结印护身'],parry:['完美反制','妖气逆转'],block:['护身成功','御印承伤'],empty:['灵力不足','飞剑不耗灵力'],hit:['妖气侵体','E 护身 · 空格闪身'],evade:['闪身避劫',''],spawn:['妖影乍现','留意侧翼 · Tab 切换目标'],travel:[e.area===1?'夜魔已除':e.area===2?'妖翼已碎':'此境已破',e.area===1?'长夜破晓 · 穿过山门，踏入悬桥':e.area===2?'踏过悬桥 · 穿亭入云 · 落向镜湖':ENCOUNTERS[e.area]?.name||'前往下一境'],expose:['镜障已破','趁此刻进攻 · 破邪印可再破镜障'],'armor-break':['雷甲崩裂','石傀已失去护甲'],interrupt:['妖翼失衡','连剑截断了它的扑击'],resist:['攻势受阻',e.reason==='mirror'?'先结破邪印，破除镜障':'用五雷诀击碎雷甲'],'hazard-warning':['脚下有雷！','移出雷圈，或临身时护身 / 闪身'], 'enemy-dodge':['掠影闪避','试试五雷诀的范围雷击']};
 if(m[e.type])cue(...m[e.type],e.type==='travel'?e.duration:.75);
 if(e.type==='hit'){$('damage-flash').style.opacity=.6;setTimeout(()=>$('damage-flash').style.opacity=0,160);}
 if(e.type==='finish'){resultAt=Infinity;$('hud').hidden=true;cueUntil=0;keys.clear();$('outcome-fx').hidden=true;setEndingUI(true);}
 if(e.type==='defeat'){resultAt=elapsed+2.4;$('hud').hidden=true;$('outcome-fx').hidden=false;$('outcome-fx').dataset.state='defeat';$('outcome-word').textContent='试炼失败';$('outcome-line').textContent='神锁反噬 · 气血耗尽';}
 window.dispatchEvent(new CustomEvent('tianjie:feedback',{detail:{version:3,type:e.type,simulated:true,color:GESTURES[e.type]?.color||(e.type==='hit'?'#b54435':'#82e6c5')}}));
});
function attempt(action,source='keyboard',confidence=1){
 if(onboarding?.active){lastInput=onboarding.input(action,source,confidence);return lastInput;}
 const rejected=ready?game.rejection(action,confidence):{code:'loading',message:'游戏正在加载，请稍候'};
 lastInput=rejected?{accepted:false,...rejected}:{accepted:game.act(action,source,confidence),code:'accepted',message:'已出招'};
 if(rejected&&rejected.code!=='travel'&&['gesture-adapter','touch'].includes(source))cue(rejected.message,'放松后再做一次',1.4);
 return lastInput;
}
const act=(action,source='keyboard',confidence=1)=>attempt(action,source,confidence).accepted;
function syncPause(){$('pause').textContent=game.paused?'继续 ▶':'暂停 Ⅱ';$('pause').setAttribute('aria-label',game.paused?'继续':'暂停');}
function setEndingUI(on){$('ascension').hidden=!on;document.body.dataset.ending=String(on);document.body.style.setProperty('--ending-dark','0');document.body.style.setProperty('--ending-logo','0');$('ending-pause').textContent='暂停 · P';}
function skipEnding(){if(game.phase!=='victory'||!world.ending.clock.active||world.ending.clock.frame.done)return;world.ending.skip();game.paused=false;}
function reset(start){
 setEndingUI(false);
 game.reset();$('outcome-fx').hidden=true;resultAt=Infinity;cueUntil=0;keys.clear();$('advance').textContent='自动前进 开';$('advance').setAttribute('aria-pressed','true');$('result').hidden=true;$('intro').hidden=start;$('hud').hidden=!start;
 if(start){unlock();game.start();cue('失序山门','Q 飞剑 · E 护身 · R 雷符 · Tab 换敌',3);}syncPause();
}
function pause(){if(!['combat','travel'].includes(game.phase)&&!(game.phase==='victory'&&world.ending.clock.active&&!world.ending.clock.frame.done))return;game.paused=!game.paused;keys.clear();syncPause();$('ending-pause').textContent=game.paused?'继续 · P':'暂停 · P';cue(game.paused?'暂歇片刻':'重返诸天',game.paused?'按 P 继续':'',game.paused?999:1);}
onboarding=createOnboarding({preview:(pose,cast=false)=>{if(!world)return;world.previewPose=pose;if(cast){world.effect({type:pose});score.event(pose);}},startCombat:()=>reset(true),onOpen:()=>{setEndingUI(false);unlock();score.event('story');game.reset();$('outcome-fx').hidden=true;resultAt=Infinity;cueUntil=0;keys.clear();$('intro').hidden=true;$('hud').hidden=true;$('result').hidden=true;},onClose:()=>{$('intro').hidden=false;$('begin').focus();}});
$('begin').onclick=()=>onboarding.open();$('quickstart').onclick=()=>reset(true);$('replay-onboarding').onclick=()=>{$('guide').close();onboarding.open();};$('retry').onclick=()=>reset(true);$('return').onclick=()=>reset(false);$('pause').onclick=pause;$('ending-pause').onclick=pause;$('ending-skip').onclick=skipEnding;$('ending-replay').onclick=()=>{if(game.phase!=='victory')return;game.paused=false;world.ending.start();$('result').hidden=true;setEndingUI(true);};
let priorPause=false;$('help').onclick=()=>{priorPause=game.paused;game.paused=true;keys.clear();$('guide').showModal();};$('close-help').onclick=()=>$('guide').close();$('guide').addEventListener('close',()=>{game.paused=onboarding.active?false:priorPause;syncPause();});
for(const [id,prop,store,label]of [['testmode','testMode','tianjie-test','测试'],['godmode','godMode','tianjie-god','无敌']]){
 const set=on=>{game[prop]=on;$(id).textContent=`${label} ${on?'开':'关'}`;$(id).setAttribute('aria-pressed',String(on));try{localStorage.setItem(store,on?'1':'0');}catch{}};
 let saved=true;try{saved=localStorage.getItem(store)!=='0';}catch{}set(saved);$(id).onclick=()=>set(!game[prop]);   // 没存过默认开（Mako 2026-10-17「默认打开测试和无敌模式」）；手动关过就记住关
}
$('sound').onclick=()=>{unlock();score.setEnabled(!score.enabled);$('sound').textContent=`音效 ${score.enabled?'开':'关'}`;$('sound').setAttribute('aria-label',score.enabled?'关闭音效':'开启音效');};
$('quality').onclick=()=>{high=!high;world?.quality(high);$('quality').textContent=`画质 ${high?'高':'流畅'}`;};
$('advance').onclick=()=>{game.autoAdvance=!game.autoAdvance;$('advance').textContent=game.autoAdvance?'自动前进 开':'自动前进 关';$('advance').setAttribute('aria-pressed',String(game.autoAdvance));};
$('fullscreen').onclick=()=>{(document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen())?.catch(()=>{});};
$('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({version:3,kind:'local-gameplay',rawEMG:false,snapshot:game.snapshot(),events:game.events},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='zhangtian-session.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('export-note').textContent='已导出，不含肌电信号。';};
document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>act(b.dataset.action,'touch'));
document.querySelectorAll('[data-move]').forEach(b=>{const key={forward:'KeyW',back:'KeyS',left:'KeyA',right:'KeyD'}[b.dataset.move];b.onpointerdown=e=>{keys.add(key);b.setPointerCapture(e.pointerId);};b.onpointerup=b.onpointercancel=()=>keys.delete(key);});
window.addEventListener('keydown',e=>{
 if(e.code==='Escape'&&!$('guide').open){skipEnding();return;}
 if($('guide').open||e.target.matches('input,textarea,select,summary'))return;
 if(e.code==='Tab'){if(!onboarding.active&&game.phase==='combat'){e.preventDefault();game.cycleTarget();}return;}
 if(['Space','KeyQ','KeyE','KeyR','KeyW','KeyA','KeyS','KeyD','KeyP'].includes(e.code))e.preventDefault();
 keys.add(e.code);if(e.repeat)return;const a={KeyQ:'sword',KeyE:'guard',KeyR:'thunder',Space:'dash'}[e.code];if(a)act(a);if(e.code==='KeyP'&&!onboarding.active)pause();
});
window.addEventListener('keyup',e=>keys.delete(e.code));window.addEventListener('blur',()=>{keys.clear();if((['combat','travel'].includes(game.phase)||(game.phase==='victory'&&!world.ending.clock.frame.done))&&!game.paused)pause();});
const scene=$('scene');scene.oncontextmenu=e=>e.preventDefault();let x=0,y=0;
scene.onpointerdown=e=>{if(!ready)return;if(e.button===2||e.pointerType==='touch'){world.dragging=true;x=e.clientX;y=e.clientY;scene.setPointerCapture(e.pointerId);}else act('sword','mouse');};
scene.onpointermove=e=>{if(!world?.dragging)return;world.yaw=Math.max(-2,Math.min(2,world.yaw+(e.clientX-x)*.004));world.pitch=Math.max(-.7,Math.min(.7,world.pitch-(e.clientY-y)*.004));x=e.clientX;y=e.clientY;};scene.onpointerup=scene.onpointercancel=()=>{if(world)world.dragging=false;};
function inputResult(i){return attempt(['sword','guard','thunder'].includes(i?.gesture)?i.gesture:'invalid','gesture-adapter',i?.confidence??NaN);}
const gesture=i=>inputResult(i).accepted;
const OFF={state:'off',text:'未收到识别页状态 · 请保持识别页开启',pose:'',acc:null};let bandNow=OFF,bandAt=-Infinity,neutral=null;
function showBand(b){
 $('device-state').textContent='● '+b.text;$('device-state').dataset.state=b.state;const p=$('device-panel'),on=(b.state==='live'||b.state==='paused')&&!!b.lanes;p.hidden=!on;if(!on)return;
 $('device-lanes').innerHTML=b.lanes.map((x,i)=>`<i data-lane="${x}" title="第 ${i+1} 路"></i>`).join('');$('device-signal').textContent=b.signal;$('device-signal').dataset.bad=String(b.lanes.includes('bad')||b.state==='paused');$('device-rec').textContent=b.rec||'—';
}
function band(raw){const b=parseBand(raw);if(!b)return false;if(b.state!=='live'||bandNow.state!=='live')neutral=null;bandNow=b;bandAt=performance.now();if(b.state==='live'&&b.acc){neutral||=b.acc;if(world)world.bandTilt=tilt(neutral,b.acc);}else if(world)world.bandTilt={pitch:0,roll:0};if(world)world.bandPose=b.state==='live'?b.pose:'';showBand(b);onboarding.band(b);return true;}
function bandStale(){if(bandNow!==OFF&&performance.now()-bandAt>STALE_MS){bandNow=OFF;neutral=null;if(world){world.bandPose='';world.bandTilt={pitch:0,roll:0};}showBand(OFF);}}
window.TianjieGame={input:gesture,inputResult,band,snapshot:()=>game.snapshot(),onboarding:()=>onboarding.snapshot(),diagnostics:()=>({ready,lastInput,fps,audio:{enabled:score.enabled,state:score.context?.state||'locked',scene:score.scene},...world?.diagnostics()})};window.addEventListener('tianjie:gesture',e=>gesture(e.detail));
const enemyButtons=new Map();
function renderEnemies(s){
 const projected=world.actors?.project(world.camera,innerWidth,innerHeight)||[],positions=new Map(projected.map(p=>[p.id,p]));
 for(const e of s.enemies){let b=enemyButtons.get(e.id);if(!b){b=document.createElement('button');b.className='enemy-tag';b.innerHTML='<span></span><i><b></b></i>';b.onclick=()=>game.select(e.id);$('enemy-labels').append(b);enemyButtons.set(e.id,b);}const p=positions.get(e.id);b.hidden=!p||!e.alive||!e.visible||s.phase!=='combat';if(p){b.style.transform=`translate(${p.x}px,${p.y}px) translate(-50%,-100%)`;b.dataset.target=String(e.id===s.targetId);b.dataset.attack=String(!!e.incoming);b.querySelector('span').textContent=e.name+(e.incoming?' · 蓄势':'');b.querySelector('b').style.width=e.hp/e.maxHp*100+'%';}}
 for(const [id,b]of enemyButtons)if(!s.enemies.some(e=>e.id===id))b.hidden=true;
}
function ui(){
 const s=game.snapshot();score.setScene(s.phase==='travel'&&s.area===1&&(world.journeyProgress||0)>.73?2:s.area);score.setMode(s.paused?'silent':['defeat','victory'].includes(s.phase)?'outcome':s.phase==='combat'?'combat':'explore');
 const ending=world.ending,ef=ending.clock.frame,cinematic=game.phase==='victory'&&ending.clock.active;score.setEndingMix(cinematic,ef.done);
 if(cinematic){
  document.body.style.setProperty('--ending-dark',String(ef.darken));document.body.style.setProperty('--ending-logo',String(ef.title));$('ending-flash').style.opacity=String(ef.flash);$('ending-caption').style.opacity=String(ef.suspense);$('ending-chapter').textContent=ef.chapter;
  $('ending-chapter').style.opacity=ef.time<10.7?'1':'0';$('ending-skip').hidden=ef.done;
  if(!game.paused)for(const cue of ending.clock.takeCues())score.endingCue(cue);
  if(ef.done&&$('result').hidden){resultAt=elapsed;setEndingUI(false);document.body.dataset.ending='complete';document.body.style.setProperty('--ending-dark','1');document.body.style.setProperty('--ending-logo','1');}
 }

 $('hp-value').textContent=`${Math.ceil(s.hp)}/100`;$('qi-value').textContent=`${Math.floor(s.qi)}/100`;$('hp-fill').style.width=s.hp+'%';$('qi-fill').style.width=s.qi+'%';
 $('enemy-hp').style.width=(s.target?s.target.hp/s.target.maxHp:0)*100+'%';$('enemy-title').textContent=s.target?.name||'妖影将至';$('boss-sub').textContent=`${s.areaName} · ${s.kills}/${s.totalEnemies} 镇伏`;
 $('quest').textContent=s.phase==='travel'?`此境已破 · 前往${ENCOUNTERS[s.area+1]?.name||'下一境'}`:ENCOUNTERS[s.area].subtitle;
 $('combo').textContent=s.combo>1?`COMBO ${s.combo}`:'';
 $('chapter-clear').hidden=!(s.phase==='travel'&&s.area===0&&!s.paused);
 document.body.dataset.daylight=String((world.daylight||0)>.5);
 if(elapsed>cueUntil){$('cue-small').textContent=s.incoming?(s.incoming.launched?'攻击临身 · E 护身 / 空格闪身':'妖气蓄势 · 留意红色目标'):'';$('cue').textContent=s.incoming?(s.incoming.launched?'结印护身':'侧翼来袭'):'';}
 document.querySelectorAll('[data-action]').forEach(b=>{b.classList.toggle('active',world.handMode===b.dataset.action&&world.handUntil>world.time);const duration=b.dataset.action==='sword'?.42:b.dataset.action==='guard'?1.45:GESTURES[b.dataset.action].cooldown;const left=Math.max(0,(s.cooldowns[b.dataset.action]||0)-s.time);b.querySelector('i').style.transform=`scaleX(${left/duration})`;b.disabled=s.paused||s.phase==='travel'||(!game.testMode&&left>0)||(!game.testMode&&s.phase==='combat'&&s.qi<GESTURES[b.dataset.action].cost);});
 renderEnemies(s);
 if(s.phase==='travel'&&s.area>1){$('scene-curtain').style.opacity=String(Math.sin(Math.min(1,(s.time-(game.travelUntil-game.travelDuration))/game.travelDuration)*Math.PI)*.92);}else $('scene-curtain').style.opacity='0';
 if(elapsed>=resultAt){resultAt=Infinity;$('hud').hidden=true;$('result').hidden=false;$('result-title').textContent=s.phase==='victory'?'诸天重明':game.outcome;$('ending-replay').hidden=s.phase!=='victory';$('outcome-fx').hidden=true;$('result').dataset.state=s.phase;$('result').setAttribute('aria-label',s.phase==='victory'?'试炼成功':'试炼失败');$('result-kicker').textContent=s.phase==='victory'?'终章 · 诸天重明':`${s.areaName} · 气血耗尽`;$('result-desc').textContent=s.phase==='victory'?'长夜已尽。你的故事，才刚刚开始。':'你倒下了，掌中的神性却仍在苏醒。看准妖气临身，以破邪印护住自己，再闯一次。';$('result-stats').textContent=`用时 ${s.time.toFixed(1)} 秒 · 击败 ${s.kills} 只 · 最高 ${s.bestCombo} 连击 · 成功格挡 ${s.parries} 次`;}
}
(async()=>{try{
 world=new World(scene,p=>{$('load-text').textContent=typeof p==='string'?p:'正在构筑道场…';});await world.init();ready=true;$('loading').hidden=true;$('intro').hidden=false;let last=performance.now();
 function frame(now){requestAnimationFrame(frame);const dt=Math.min(.05,(now-last)/1000);last=now;frameCount++;if(now-fpsAt>=1000){fps=Math.round(frameCount*1000/(now-fpsAt));frameCount=0;fpsAt=now;}if(!game.paused)elapsed+=dt;
  world.move.set(Number(keys.has('KeyD'))-Number(keys.has('KeyA')),0,Number(keys.has('KeyS'))-Number(keys.has('KeyW')));if(world.move.lengthSq()>1)world.move.normalize();
  bandStale();if(onboarding.active)onboarding.tick(document.hidden?0:dt);game.setPlayer(world.position);game.update(dt);world.update(game.paused?0:dt,game.snapshot());ui();
 }requestAnimationFrame(frame);
}catch(e){console.error(e);$('loading').hidden=true;$('fatal').hidden=false;$('fatal-message').textContent=e.message;}})();
