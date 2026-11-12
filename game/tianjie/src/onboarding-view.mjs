import { Onboarding, LESSONS, STORY, STORY_SECONDS, REQUIRED_RESPONSES } from './onboarding.mjs';
const $=id=>document.getElementById(id);
export function createOnboarding({ preview, startCombat, onOpen, onClose }) {
  const flow=new Onboarding();let lastStage='',lastChapter=-1,lastLesson=-1,noticeUntil=0,completedAt=null;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  function paint(now=performance.now()){
    const s=flow.snapshot(now),active=s.phase!=='closed';$('journey').hidden=!active;
    if(!active){preview('');return;}
    $('journey').dataset.phase=s.phase;
    document.querySelectorAll('[data-journey-step]').forEach(b=>{const steps=['story','wear','practice','ready'];b.dataset.current=String(b.dataset.journeyStep===s.phase);b.dataset.done=String(steps.indexOf(b.dataset.journeyStep)<steps.indexOf(s.phase));});
    for(const phase of ['story','wear','practice','ready'])$(`j-${phase}`).hidden=s.phase!==phase;
    if(s.phase==='story'){
      const chapter=STORY[s.chapter];$('story-kicker').textContent=chapter.kicker;$('story-title').textContent=chapter.title;$('story-copy').textContent=chapter.text;
      $('story-art').dataset.visual=chapter.visual;$('story-number').textContent=`0${s.chapter+1} / 03`;$('story-progress').style.width=`${Math.min(100,s.storyTime/STORY_SECONDS*100)}%`;
      $('story-next').textContent=s.chapter===2?'检查神锁 →':'继续 →';
      if(lastChapter!==s.chapter){$('j-story').classList.remove('enter');void $('j-story').offsetWidth;$('j-story').classList.add('enter');lastChapter=s.chapter;}
    }
    if(s.phase==='wear'){
      $('wear-confirm').checked=s.worn;$('wear-continue').disabled=!s.wearReady;
      $('wear-bar').style.width=`${Math.min(100,s.stableMs/2000*100)}%`;
      const b=flow.band;$('wear-status').textContent=s.wearReady?'神锁已回应 · 可开始试印':s.healthy?(s.worn?'保持放松，正在观察信号…':'信号已到达，请确认佩戴位置'):b?.state==='link'?'手环已连接 · 请在 App 开始结印识别':b?.state==='paused'?'信号检查暂停 · 请查看识别页':'等待 OpenEMG App 的实时信号';
      $('wear-signal').textContent=s.healthy?(b.signal||'正在接收八路状态'):s.message||(b?.signal||'在 OpenEMG App 完成「连上 → 戴好 → 校准」，选择「结印三招」并保持识别页开启。');
      $('wear-lanes').replaceChildren(...Array.from({length:8},(_,i)=>{const dot=document.createElement('span');dot.dataset.lane=now-flow.bandAt<=1500?(b?.lanes?.[i]||''):'';dot.textContent=String(i+1);return dot;}));
    }
    if(s.phase==='practice'){
      const lesson=LESSONS[s.lesson];document.querySelectorAll('[data-seal]').forEach(el=>{el.dataset.current=String(el.dataset.seal===lesson.gesture);});$('lesson-number').textContent=`0${s.lesson+1} / 03`;$('lesson-name').textContent=lesson.name;$('lesson-line').textContent=lesson.line;$('lesson-pose').textContent=lesson.pose;$('lesson-effect').textContent=lesson.effect;$('lesson-hint').textContent=lesson.hint;
      $('lesson-mode').textContent=s.mode==='hardware'?'真实手环 · 识别响应检查':'键盘练习 · 不计为手环识别通过';
      $('lesson-key').textContent=lesson.key;$('practice-key').textContent=`按 ${lesson.key} · ${lesson.name}`;$('practice-key').hidden=s.mode!=='keyboard';
      $('lesson-next').disabled=s.counts[s.lesson]<REQUIRED_RESPONSES;$('lesson-next').textContent=s.lesson===2?'完成三印 →':'下一印 →';
      $('lesson-counter').textContent=`${s.counts[s.lesson]} / ${REQUIRED_RESPONSES}`;
      document.querySelectorAll('[data-lesson-dot]').forEach((d,i)=>d.dataset.done=String(s.counts[s.lesson]>i));
      const b=flow.band;$('lesson-live').textContent=s.mode==='hardware'?(b?.rec||b?.text||'等待识别'):'请按提示按键，或点击练习按钮';
      if(now>=noticeUntil)$('lesson-status').textContent=s.message||'先放松，再结印。';
      $('lesson-relax').textContent=s.counts[s.lesson]>=REQUIRED_RESPONSES?'这一印已完成':s.mode==='hardware'?(s.armed?'可以结印了':'先放松手指'):'按提示完成这一印';
      if(lastLesson!==s.lesson||lastStage!==s.phase){lastLesson=s.lesson;preview(lesson.gesture);}
    }else preview('');
    if(s.phase==='ready'){
      $('ready-mode').textContent=s.mode==='hardware'?'神锁信号与三印响应已检查':'键盘练习完成 · 手环尚未检查';
      $('ready-description').textContent=s.mode==='hardware'?'三印已应。以剑进攻，以印护身，以雷镇邪。':'Q 剑 · E 印 · R 雷。键盘练习已完成，手环尚未检查。';
      $('enter-trial').disabled=!s.canFinish;
      $('ready-hardware').hidden=s.mode==='hardware';
    }
    lastStage=s.phase;
  }
  function open(){onOpen();flow.start();lastStage='';lastChapter=-1;lastLesson=-1;noticeUntil=0;completedAt=null;paint();$('journey-close').focus();}
  function close(){flow.close();preview('');paint();onClose();}
  $('journey-close').onclick=close;$('story-next').onclick=()=>{flow.nextStory();paint();};$('story-skip').onclick=()=>{flow.toWear();paint();};
  $('wear-confirm').onchange=e=>{flow.setWorn(e.target.checked);paint();};
  $('wear-continue').onclick=()=>{flow.beginPractice(performance.now());paint();};
  $('wear-keyboard').onclick=()=>{flow.useKeyboard();paint();};
  $('practice-key').onclick=()=>input(LESSONS[flow.lesson].gesture,'touch',1);
  $('lesson-next').onclick=()=>{flow.nextLesson();completedAt=null;paint();};
  $('lesson-back').onclick=()=>{flow.chooseHardware();paint();};
  $('ready-hardware').onclick=()=>{flow.chooseHardware();paint();};
  $('enter-trial').onclick=()=>{if(flow.canFinish(performance.now())){const mode=flow.mode;flow.close();preview('');paint();startCombat(mode);}};
  function input(action,source,confidence){
    const r=flow.input(action,source,confidence,performance.now());
    if(r.accepted){completedAt=performance.now();preview(action,true);$('lesson-status').textContent=flow.message;noticeUntil=0;}
    else if(flow.phase==='practice'){$('lesson-status').textContent=r.message;noticeUntil=performance.now()+1800;}
    paint();return r;
  }
  return {open,close,input,band(b){flow.updateBand(b,performance.now());paint();},tick(dt){const now=performance.now();flow.tick(dt,now,reduced);if(flow.phase==='practice'&&completedAt!==null&&now-completedAt>=1100){flow.nextLesson();completedAt=null;}paint();},get active(){return flow.phase!=='closed';},get phase(){return flow.phase;},snapshot:()=>flow.snapshot(performance.now())};
}
