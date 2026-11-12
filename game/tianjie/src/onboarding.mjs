import { STALE_MS } from './band.mjs';
export const LESSONS = [
  { gesture:'sword', name:'道指剑', mark:'剑', key:'Q', line:'让第一缕剑意，听从你的意志。', pose:'掌心朝上，伸出食指与小指，中指、无名指弯下，拇指压在它们的指甲上。', effect:'飞剑出鞘 · 持续进攻', hint:'放松，再结印。' },
  { gesture:'guard', name:'破邪印', mark:'印', key:'E', line:'这只手，也可以选择守护。', pose:'手背朝上，食指、中指并拢伸直，无名指、小指弯下，拇指从侧面压住弯下的两指。', effect:'结阵护身 · 迎击反制', hint:'不要用力绷紧。认出手印后，先回到放松。' },
  { gesture:'thunder', name:'五雷诀', mark:'雷', key:'R', line:'雷从掌起，却不由天命。', pose:'手背朝上，四指握紧，拇指在拳外横扣在食指、中指上，与本次校准一致。', effect:'雷符落下 · 重击镇邪', hint:'动作清楚即可，不必握得更紧。' },
];
export const STORY_SECONDS = 4;
export const REQUIRED_RESPONSES = 1;
export const STORY = [
  { kicker:'五手定天', title:'天有五手。执掌诸天。', text:'五只巨手，曾维系世界的秩序。', visual:'order' },
  { kicker:'诸天失序', title:'诸天崩塌。一手入你。', text:'你的右手正在神化。腕上的环，是最后一道锁。', visual:'fall' },
  { kicker:'掌心之问', title:'神锁将裂。谁在掌谁？', text:'来者未必为杀你。先让这只手，听你的。', visual:'wake' },
];
export class Onboarding {
  constructor(){ this.close(); }
  close(){ this.phase='closed'; this.mode='hardware'; this.chapter=0; this.storyTime=0; this.worn=false; this.stableSince=null; this.bandAt=-Infinity; this.band=null; this.counts=[0,0,0]; this.lesson=0; this.armed=false; this.restSince=null; this.lastKey=-Infinity; this.message=''; }
  start(){ this.close(); this.phase='story'; }
  nextStory(){ if(this.phase!=='story')return; if(this.chapter<STORY.length-1){this.chapter++;this.storyTime=0;}else this.toWear(); }
  toWear(){ this.phase='wear';this.storyTime=0;this.message=''; }
  useKeyboard(){ this.mode='keyboard';this.beginPractice(); }
  chooseHardware(){ this.mode='hardware';this.worn=false;this.counts=[0,0,0];this.lesson=0;this.toWear(); }
  setWorn(value){ this.worn=!!value; }
  updateBand(b,now){
    if(now-this.bandAt>STALE_MS){this.stableSince=null;this.restSince=null;this.armed=false;}
    this.band=b;this.bandAt=now;
    if(!this.healthy(now)){this.stableSince=null;this.restSince=null;this.armed=false;}else{
      this.stableSince??=now;
      // The existing bridge has no structured rest label. Its canonical rest text is "识别中 · 放松".
      if(!b.pose && /放松|rest/i.test(b.text)){this.restSince??=now;if(now-this.restSince>=300)this.armed=true;}else this.restSince=null;
    }
    this.checkConnection(now);
  }
  healthy(now){return !!this.band && now-this.bandAt<=STALE_MS && this.band.state==='live' && !/数据过期|数据中断|信号不连续|同步屏蔽/.test(this.band.text) && Array.isArray(this.band.lanes) && this.band.lanes.length===8 && this.band.lanes.includes('ok') && this.band.lanes.every(x=>x==='ok'||x==='mask');}
  wearReady(now){return this.worn&&this.healthy(now)&&this.stableSince!==null&&now-this.stableSince>=2000;}
  beginPractice(now){if(this.mode==='hardware'&&!this.wearReady(now))return false;this.phase='practice';this.counts=[0,0,0];this.lesson=0;this.armed=false;this.restSince=null;this.message=this.mode==='hardware'?'先放松手指，等画面提示后再结印。':'键盘练习：按提示按键，每个手印试一次。';return true;}
  checkConnection(now){
    if(this.mode==='hardware'&&['practice','ready'].includes(this.phase)&&!this.healthy(now)){
      this.phase='wear';this.counts=[0,0,0];this.lesson=0;this.worn=false;this.stableSince=null;this.armed=false;this.restSince=null;this.message='信号中断或检查未通过。请回到识别页检查，再重新开始。';
    }
  }
  tick(dt,now,reduced=false){
    if(this.phase==='story'&&!reduced){this.storyTime+=dt;if(this.storyTime>=STORY_SECONDS)this.nextStory();}
    if(!this.healthy(now)){this.stableSince=null;this.restSince=null;this.armed=false;}
    this.checkConnection(now);
  }
  input(action,source,confidence,now){
    if(this.phase!=='practice')return {accepted:false,code:'onboarding',message:'请先完成当前引导'};
    if(!LESSONS.some(x=>x.gesture===action)||!Number.isFinite(confidence)||confidence<.8||confidence>1)return {accepted:false,code:'confidence',message:'手印尚不确定，放松后重试'};
    this.checkConnection(now);
    if(this.phase!=='practice')return {accepted:false,code:'band-offline',message:this.message};
    if(this.counts[this.lesson]>=REQUIRED_RESPONSES)return {accepted:false,code:'practice-complete',message:'这一印已完成，请选择下一印'};
    const hardware=source==='gesture-adapter';
    if((this.mode==='hardware')!==hardware)return {accepted:false,code:'input-mode',message:this.mode==='hardware'?'当前为手环检查，请用真实手印':'当前为键盘练习，手环检查尚未完成'};
    if(hardware&&!this.armed)return {accepted:false,code:'relax',message:'先放松至少片刻，再做一次手印'};
    if(!hardware&&now-this.lastKey<300)return {accepted:false,code:'practice-wait',message:'松开按键，再试一次'};
    if(hardware){this.armed=false;this.restSince=null;}else this.lastKey=now;
    const expected=LESSONS[this.lesson].gesture;
    if(action!==expected){this.message=`这次是${LESSONS.find(x=>x.gesture===action).name}，请试${LESSONS[this.lesson].name}。`;return {accepted:false,code:'practice-other',message:this.message};}
    this.counts[this.lesson]++;this.message='这一印已响应。';
    return {accepted:true,code:'practice',message:`${LESSONS[this.lesson].name}练习已响应`,practice:true};
  }
  nextLesson(){if(this.phase!=='practice'||this.counts[this.lesson]<REQUIRED_RESPONSES)return false;this.armed=false;this.restSince=null;this.lastKey=-Infinity;if(this.lesson<2){this.lesson++;this.message=this.mode==='hardware'?'先放松，再试这一印。':'按提示按键，各试一印。';}else this.phase='ready';return true;}
  canFinish(now){return this.phase==='ready'&&this.counts.every(n=>n>=REQUIRED_RESPONSES)&&(this.mode==='keyboard'||this.wearReady(now));}
  snapshot(now){return {phase:this.phase,mode:this.mode,chapter:this.chapter,storyTime:this.storyTime,lesson:this.lesson,counts:[...this.counts],armed:this.armed,worn:this.worn,healthy:this.healthy(now),stableMs:this.stableSince===null?0:Math.max(0,now-this.stableSince),wearReady:this.wearReady(now),canFinish:this.canFinish(now),message:this.message};}
}
