import {travelDuration} from './bridge-route.mjs';
import {GESTURES} from './gestures.mjs';
import {ENCOUNTERS,TOTAL_ENEMIES} from './encounters.mjs';
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export class Combat {
 constructor(emit=()=>{}){this.emit=emit;this.testMode=false;this.godMode=false;this.reset();}
 reset(){
  Object.assign(this,{phase:'ready',time:0,hp:100,qi:100,area:0,stage:1,boss:0,maxBoss:0,shield:0,guardStart:-99,paused:false,kills:0,casts:0,swords:0,thunders:0,parries:0,dodges:0,invulnerable:0,outcome:null,targetId:null,travelUntil:0,areaStart:0,combo:0,bestCombo:0,lastHit:-99,autoAdvance:true});
  this.hazard=null;this.nextHazard=0;this.cooldowns={};this.events=[];this.enemies=[];this.pending=[];this.player={x:0,z:13};this.emit({type:'reset'});
 }
 start(){if(this.phase!=='ready')return false;this.phase='combat';this.loadArea(0);this.emit({type:'start'});return true;}
 loadArea(index){this.area=index;this.stage=index+1;this.areaStart=this.time;this.enemies=ENCOUNTERS[index].enemies.map(e=>({...e,maxHp:e.hp,alive:true,visible:false,spawnAt:this.time+e.delay,attackAt:this.time+e.delay+1.8+(['keeper','dragonfly','thunderlord'].includes(e.kind)?.8:0),incoming:null,dodgeUntil:0,dodgeReady:0,revealUntil:0,armored:e.kind==='golem',hits:0,x:e.x,y:['keeper','dragonfly','mirror','thunderlord'].includes(e.kind)?2.8:2.4,z:e.z}));this.targetId=this.enemies[0].id;this.maxBoss=this.enemies.reduce((n,e)=>n+e.maxHp,0);this.refreshHealth();this.hazard=null;this.nextHazard=this.time+3;this.emit({type:'area',area:index});}
 log(e){this.events.push({t:+this.time.toFixed(3),...e});if(this.events.length>500)this.events.shift();}
 refreshHealth(){this.boss=this.enemies.reduce((n,e)=>n+Math.max(0,e.hp),0);}
 setPlayer(p){if(p&&Number.isFinite(p.x)&&Number.isFinite(p.z))this.player={x:p.x,z:p.z};}
 target(){return this.enemies.find(e=>e.id===this.targetId&&e.alive&&e.visible)||this.enemies.find(e=>e.alive&&e.visible);}
 select(id){if(this.enemies.some(e=>e.id===id&&e.alive&&e.visible)){this.targetId=id;return true;}return false;}
 cycleTarget(){const pool=this.enemies.filter(e=>e.alive&&e.visible);if(!pool.length)return false;const i=pool.findIndex(e=>e.id===this.targetId);return this.select(pool[(i+1)%pool.length].id);}
 rejection(action,confidence=1){
  if(!['sword','guard','thunder','dash'].includes(action))return {code:'gesture',message:'未知手印'};
  if(!Number.isFinite(confidence)||confidence<.8||confidence>1)return {code:'confidence',message:'手印尚不确定，放松后重试'};
  if(this.phase==='ready')return {code:'not-started',message:'请先入场'};
  if(this.paused)return {code:'paused',message:'游戏已暂停，请继续后出招'};
  if(this.phase==='travel')return {code:'travel',message:'本关已通过，正在前往下一关'};
  if(this.phase!=='combat')return {code:'ended',message:'试炼已结束，请重试'};
  if(!this.testMode&&(this.cooldowns[action]||0)>this.time)return {code:'cooldown',message:'这一印尚在冷却'};
  if(!this.testMode&&GESTURES[action]&&this.qi<GESTURES[action].cost)return {code:'mana',message:'灵力不足，用飞剑等待回复'};
  if(['sword','thunder'].includes(action)&&!this.target())return {code:'approaching',message:'留意四周，妖影将至'};
  return null;
 }
 act(action,source='keyboard',confidence=1){
  if(this.rejection(action,confidence))return false;
  const spell=GESTURES[action];this.cooldowns[action]=this.time+(action==='sword'?.42:action==='guard'?1.45:spell?.cooldown??1.2);
  if(action==='guard'){this.shield=this.time+1.05;this.guardStart=this.time;if(this.area===2){for(const e of this.enemies)e.revealUntil=this.time+3.5;this.emit({type:'expose'});}}
  if(action==='dash'){this.invulnerable=this.time+.5;this.dodges++;}
  const target=this.target();
  this.log({type:'input',action,source});this.emit({type:action,enemyId:target?.id});
  if(action==='sword'||action==='thunder'){
   if(!this.testMode)this.qi-=spell.cost;this.casts++;if(action==='sword')this.swords++;else{this.thunders++;for(const e of this.enemies)if(e.visible&&e.armored){e.armored=false;this.emit({type:'armor-break',enemyId:e.id});}}
   if(action==='sword'&&target.kind==='shade'&&target.dodgeReady<=this.time&&target.hits%3===2){target.dodgeUntil=this.time+.6;target.dodgeReady=this.time+3;target.attackAt=Math.max(target.attackAt,this.time+.8);this.combo=0;this.emit({type:'enemy-dodge',enemyId:target.id});return true;}
   const targets=action==='thunder'?this.enemies.filter(e=>e.alive&&e.visible):[target];
   for(const e of targets)this.pending.push({enemyId:e.id,amount:action==='thunder'?(e.id===target.id?spell.damage:Math.round(spell.damage*.5)):spell.damage,at:this.time+(action==='thunder'?.28:.2),stagger:action==='thunder'?1.15:.12});
  }
  return true;
 }
 damage(amount,enemyId=this.target()?.id,stagger=0){
  const e=this.enemies.find(e=>e.id===enemyId);if(!e?.alive||this.phase!=='combat')return;
  const mirror=['mirror','reflection'].includes(e.kind)&&e.revealUntil<=this.time;const shielded=mirror||e.armored;if(shielded){amount=Math.max(1,Math.round(amount*.2));this.emit({type:'resist',enemyId:e.id,reason:mirror?'mirror':'armor'});}
  e.hp=Math.max(0,e.hp-amount);e.hits++;if(this.area===1&&e.kind==='dragonfly'&&e.hits%3===0){e.incoming=null;e.attackAt=this.time+1.2;this.emit({type:'interrupt',enemyId:e.id});}this.combo=this.time-this.lastHit<2.4?this.combo+1:1;this.lastHit=this.time;this.bestCombo=Math.max(this.bestCombo,this.combo);
  if(stagger>0){e.attackAt=Math.max(e.attackAt,this.time+stagger);if(stagger>.5)e.incoming=null;}
  this.emit({type:'enemy-hit',enemyId:e.id,amount});
  if(e.hp===0){e.alive=false;e.incoming=null;this.kills++;this.qi=clamp(this.qi+10,0,100);this.emit({type:'enemy-killed',enemyId:e.id});this.log({type:'kill',enemyId:e.id});if(e.id===this.targetId)this.targetId=this.enemies.find(x=>x.alive&&x.visible)?.id||null;}
  this.refreshHealth();
  if(this.enemies.every(x=>!x.alive)){
   this.pending=[];
   if(this.area<ENCOUNTERS.length-1){this.phase='travel';this.travelDuration=travelDuration(this.area);this.travelUntil=this.time+this.travelDuration;this.emit({type:'travel',area:this.area+1,duration:this.travelDuration});}
   else{this.phase='victory';this.outcome='试炼成功';this.hazard=null;this.emit({type:'finish',enemyId:e.id});this.log({type:'finish',source:'last-enemy'});}
  }
 }
 update(dt){
  if(this.paused||!['combat','travel'].includes(this.phase))return;
  dt=clamp(Number.isFinite(dt)?dt:0,0,.1);this.time+=dt;this.qi=Math.min(100,this.qi+dt*8);
  if(this.phase==='travel'){if(this.time>=this.travelUntil){this.hp=Math.min(100,this.hp+25);this.qi=Math.min(100,this.qi+25);this.phase='combat';this.player={...ENCOUNTERS[this.area+1].camera};this.loadArea(this.area+1);}return;}
  if(this.phase!=='combat')return;
  const due=this.pending.filter(p=>p.at<=this.time);this.pending=this.pending.filter(p=>p.at>this.time);for(const p of due){this.damage(p.amount,p.enemyId,p.stagger);if(this.phase!=='combat')return;}
  for(const [i,e]of this.enemies.entries()){
   if(!e.alive)continue;if(!e.visible){if(this.time<e.spawnAt)continue;e.visible=true;this.emit({type:'spawn',enemyId:e.id,kind:e.kind});if(!this.target())this.targetId=e.id;}
   const age=this.time-e.spawnAt,base=ENCOUNTERS[this.area].enemies[i],dodging=e.dodgeUntil>this.time;
   e.x=base.x+Math.sin(age*(e.kind==='shade'?1.9:.65)+i)* (['keeper','thunderlord','golem'].includes(e.kind)?1.4:2.7)+(dodging?Math.sin((.6-e.dodgeUntil+this.time)/.6*Math.PI)*3.2:0);
   e.y=(ENCOUNTERS[this.area].camera.y?ENCOUNTERS[this.area].camera.y-1.75:0)+(['keeper','dragonfly','mirror','thunderlord'].includes(e.kind)?2.8:2.1)+Math.sin(age*(['wisp','manta','phoenix'].includes(e.kind)?2.4:1.1)+i)*(['wisp','manta','phoenix'].includes(e.kind)?1.1:.42);
   if(e.kind==='dragonfly'){e.x+=Math.sin(age*3.8)*2;e.y+=Math.sin(age*4)*.45;}
   e.z=base.z+Math.sin(age*.7+i)*(['wisp','manta','phoenix'].includes(e.kind)?2.2:1.1);
   if(!e.incoming&&this.time>=e.attackAt){e.incoming={start:this.time,release:this.time+.7,hit:this.time+1.35,launched:false};this.emit({type:'warning',enemyId:e.id});}
   if(e.incoming&&!e.incoming.launched&&this.time>=e.incoming.release){e.incoming.launched=true;this.emit({type:'enemy-cast',enemyId:e.id});}
   if(e.incoming&&this.time>=e.incoming.hit){e.incoming=null;e.attackAt=this.time+(['keeper','dragonfly','thunderlord'].includes(e.kind)?3:3.9)+i*.2;
    if(this.invulnerable>this.time){this.emit({type:'evade',enemyId:e.id});continue;}
    if(this.shield>this.time){const perfect=this.time-this.guardStart<=.32;this.parries++;this.qi=Math.min(100,this.qi+8);this.emit({type:perfect?'parry':'block',enemyId:e.id});if(perfect)this.damage(48,e.id,.9);}
    else{if(!this.godMode)this.hp=Math.max(0,this.hp-(['keeper','dragonfly','thunderlord'].includes(e.kind)?19:12));this.combo=0;this.emit({type:'hit',enemyId:e.id});if(!this.hp){this.phase='defeat';this.outcome='试炼失败';this.pending=[];this.emit({type:'defeat'});this.log({type:'defeat'});return;}}
    if(this.phase!=='combat')return;
   }
  }
  this.updateHazard();
 }
 updateHazard(){
  if(this.area!==3||this.phase!=='combat')return;
  if(!this.hazard&&this.time>=this.nextHazard){this.hazard={x:this.player.x,z:this.player.z,hit:this.time+1.5,radius:2.5};this.emit({type:'hazard-warning',position:{...this.hazard}});}
  if(this.hazard&&this.time>=this.hazard.hit){const h=this.hazard;this.hazard=null;this.nextHazard=this.time+4.5;this.emit({type:'hazard-strike',position:h});
   if(Math.hypot(this.player.x-h.x,this.player.z-h.z)>h.radius||this.invulnerable>this.time){this.emit({type:'evade'});return;}
   if(this.shield>this.time){this.parries++;this.emit({type:'block'});return;}
   if(!this.godMode)this.hp=Math.max(0,this.hp-17);this.emit({type:'hit'});if(!this.hp){this.phase='defeat';this.outcome='试炼失败';this.pending=[];this.emit({type:'defeat'});}
  }
 }
 snapshot(){const t=this.target();return {phase:this.phase,time:this.time,hp:this.hp,qi:this.qi,boss:this.boss,maxBoss:this.maxBoss,stage:this.stage,area:this.area,areaName:ENCOUNTERS[this.area].name,paused:this.paused,shield:this.shield,incoming:this.enemies.filter(e=>e.incoming).map(e=>({...e.incoming,enemyId:e.id})).sort((a,b)=>a.hit-b.hit)[0]||null,casts:this.casts,swords:this.swords,thunders:this.thunders,parries:this.parries,dodges:this.dodges,kills:this.kills,totalEnemies:TOTAL_ENEMIES,hazard:this.hazard?{...this.hazard}:null,combo:this.combo,bestCombo:this.bestCombo,targetId:t?.id||null,target:t?{id:t.id,name:t.name,hp:t.hp,maxHp:t.maxHp}:null,enemies:this.enemies.map(e=>({id:e.id,kind:e.kind,name:e.name,hp:e.hp,maxHp:e.maxHp,alive:e.alive,visible:e.visible,x:e.x,y:e.y,z:e.z,dodging:e.dodgeUntil>this.time,shielded:(['mirror','reflection'].includes(e.kind)&&e.revealUntil<=this.time)||e.armored,incoming:e.incoming?{...e.incoming}:null})),cooldowns:{...this.cooldowns},autoAdvance:this.autoAdvance};}
}
