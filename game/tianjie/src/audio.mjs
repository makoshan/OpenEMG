// Offline procedural score: pentatonic plucked strings, breathy bamboo flute and bronze percussion.
// No recorded samples, network calls or user audio recording.
export const SCENE_SCORES=[
 {name:'山门 · 钟鼓',bpm:116,root:50,notes:[62,69,74,76,81,79,76,74],ambience:'mountain'},
 {name:'悬桥 · 凌风',bpm:150,root:52,notes:[64,67,71,74,76,71,67,64],ambience:'wind'},
 {name:'镜湖 · 水吟',bpm:106,root:53,notes:[65,69,72,74,77,74,72,69],ambience:'water'},
 {name:'雷狱 · 战鼓',bpm:164,root:48,notes:[60,63,67,70,72,70,67,63],ambience:'storm'},
];
export class AudioDirector {
  constructor(){this.enabled=true;this.mode='explore';this.context=null;this.step=0;this.nextBeat=0;this.voices=0;this.scene=0;this.ambient=[];this.hidden=false;}
  /** 窗口最小化、隐藏或被完全挡住时挂起整个音频，回到前台且音效开着再恢复（Mako 2026-10-17「游戏关掉后，后台还有音乐」） */
  setHidden(hidden){this.hidden=hidden;if(!this.context)return;if(hidden)this.context.suspend().catch(()=>{});else if(this.enabled)this.context.resume().catch(()=>{});}
  async unlock(){
    if(!this.context){
      const Audio=window.AudioContext||window.webkitAudioContext;if(!Audio)return;
      const c=this.context=new Audio();this.master=c.createGain();this.master.gain.value=.52;
      const compressor=c.createDynamicsCompressor();compressor.threshold.value=-19;compressor.ratio.value=5;this.master.connect(compressor);compressor.connect(c.destination);
      this.space=c.createConvolver();const n=c.sampleRate*2.8,ir=c.createBuffer(2,n,c.sampleRate);
      for(let ch=0;ch<2;ch++){const d=ir.getChannelData(ch);for(let i=0;i<n;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/n,3)*.27;}
      this.space.buffer=ir;const wet=c.createGain();wet.gain.value=.3;this.space.connect(wet);wet.connect(this.master);
      this.regularBus=c.createGain();this.regularBus.connect(this.master);this.regularBus.connect(this.space);this.finaleBus=c.createGain();this.finaleBus.connect(this.master);this.finaleBus.connect(this.space);this.endingMix=null;this.buildAmbience();this.nextBeat=c.currentTime+.15;this.timer=setInterval(()=>this.schedule(),90);
    }
    if(this.hidden)await this.context.suspend().catch(()=>{});else if(this.enabled)await this.context.resume();
  }
  setEnabled(on){this.enabled=on;if(!this.context)return;this.master.gain.setTargetAtTime(on&&this.mode!=='silent'?.52:0,this.context.currentTime,.07);if(on&&!this.hidden)this.context.resume();this.mixAmbience();}
  setMode(mode){if(this.mode!==mode){this.mode=mode;if(this.context){this.nextBeat=Math.max(this.nextBeat,this.context.currentTime+.06);this.master.gain.setTargetAtTime(this.enabled&&mode!=='silent'?.52:0,this.context.currentTime,.1);this.mixAmbience();}}}
  setScene(scene){if(this.scene===scene)return;this.scene=Math.max(0,Math.min(3,scene));this.step=0;if(this.context){this.nextBeat=this.context.currentTime+.08;this.mixAmbience();}}
  buildAmbience(){
    const c=this.context,n=c.sampleRate*4,b=c.createBuffer(1,n,c.sampleRate),d=b.getChannelData(0);let brown=0;
    for(let i=0;i<n;i++){const white=Math.random()*2-1;brown=(brown+.018*white)/1.018;d[i]=brown*2.8+white*.08;}
    for(let i=0;i<4;i++){
      const source=c.createBufferSource();source.buffer=b;source.loop=true;const filter=c.createBiquadFilter();filter.type=i===2?'lowpass':'bandpass';filter.frequency.value=[650,1100,2300,180][i];filter.Q.value=.55;
      const gain=c.createGain();gain.gain.value=0;source.connect(filter);filter.connect(gain);gain.connect(this.master);source.start();this.ambient.push({source,filter,gain});
    }this.mixAmbience();
  }
  mixAmbience(){if(!this.context)return;for(const [i,a]of this.ambient.entries())a.gain.gain.setTargetAtTime(['silent','outcome'].includes(this.mode)||!this.enabled?0:i===this.scene?[.22,.48,.7,.42][i]:0,this.context.currentTime,.55);}
  strings(notes,at,length=2.2,gain=.025){
    const c=this.context;for(const [i,midi]of notes.entries()){
      const o=c.createOscillator(),o2=c.createOscillator(),env=c.createGain(),f=c.createBiquadFilter();o.type=o2.type='sawtooth';o.frequency.value=440*2**((midi-69)/12);o2.frequency.value=o.frequency.value;o.detune.value=-5;o2.detune.value=5;f.type='lowpass';f.frequency.value=850+i*150;f.Q.value=.6;
      env.gain.setValueAtTime(0,at);env.gain.linearRampToValueAtTime(gain,at+.3);env.gain.setTargetAtTime(.0001,at+length-.6,.18);o.connect(f);o2.connect(f);f.connect(env);this.bus(env,1,at,(i-1)*.25);o.start(at);o2.start(at);o.stop(at+length);o2.stop(at+length);o.onended=()=>{o.disconnect();o2.disconnect();f.disconnect();env.disconnect();};
    }
  }
  waterDrop(at,gain=.05,pan=0){const c=this.context,o=c.createOscillator(),env=c.createGain();o.frequency.setValueAtTime(1050,at);o.frequency.exponentialRampToValueAtTime(390,at+.13);env.gain.setValueAtTime(gain,at);env.gain.exponentialRampToValueAtTime(.0001,at+.32);o.connect(env);this.bus(env,1,at,pan);o.start(at);o.stop(at+.34);o.onended=()=>{o.disconnect();env.disconnect();};}

  bus(node,gain,at,pan=0){const c=this.context,g=c.createGain(),p=c.createStereoPanner();g.gain.value=gain;p.pan.value=pan;node.connect(g);g.connect(p);p.connect(this.cinematicVoice?this.finaleBus:this.regularBus);setTimeout(()=>{g.disconnect();p.disconnect();},4000);return g;}
  pluck(midi,at,gain=.12,pan=0,length=1.4){
    const c=this.context,f=440*Math.pow(2,(midi-69)/12),period=Math.max(2,Math.round(c.sampleRate/f)),n=Math.ceil(c.sampleRate*length),b=c.createBuffer(1,n,c.sampleRate),d=b.getChannelData(0);
    for(let i=0;i<period;i++)d[i]=(Math.random()*2-1)*.8;
    for(let i=period;i<n;i++)d[i]=(d[i-period]+d[i-period+1])*.496;
    const source=c.createBufferSource();source.buffer=b;const filter=c.createBiquadFilter();filter.type='lowpass';filter.frequency.value=4200;source.connect(filter);this.bus(filter,gain,at,pan);source.start(at);source.onended=()=>{source.disconnect();filter.disconnect();};
  }
  flute(midi,at,length=1,gain=.05){
    const c=this.context,f=440*Math.pow(2,(midi-69)/12),carrier=c.createOscillator(),harm=c.createOscillator(),breath=c.createBufferSource(),env=c.createGain(),vib=c.createOscillator(),vg=c.createGain();
    carrier.type='sine';carrier.frequency.value=f;harm.type='sine';harm.frequency.value=f*2;const hg=c.createGain();hg.gain.value=.12;harm.connect(hg);hg.connect(env);carrier.connect(env);
    vib.frequency.value=4.7;vg.gain.value=2.2;vib.connect(vg);vg.connect(carrier.frequency);
    const b=c.createBuffer(1,Math.ceil(c.sampleRate*length),c.sampleRate),data=b.getChannelData(0);for(let i=0;i<data.length;i++)data[i]=(Math.random()*2-1)*.12;
    breath.buffer=b;const bp=c.createBiquadFilter();bp.type='bandpass';bp.frequency.value=f*2;bp.Q.value=1.4;breath.connect(bp);bp.connect(env);
    env.gain.setValueAtTime(0,at);env.gain.linearRampToValueAtTime(gain,at+.09);env.gain.setTargetAtTime(gain*.75,at+.14,.25);env.gain.setTargetAtTime(0,at+length-.15,.06);this.bus(env,1,at,Math.sin(midi)*.3);
    carrier.start(at);harm.start(at);breath.start(at);vib.start(at);carrier.stop(at+length+.1);harm.stop(at+length+.1);vib.stop(at+length+.1);breath.onended=()=>{carrier.disconnect();harm.disconnect();breath.disconnect();bp.disconnect();env.disconnect();vib.disconnect();vg.disconnect();hg.disconnect();};
  }
  gong(at,gain=.12,base=110){const c=this.context;for(const [i,ratio]of [1,1.48,2.07,2.91,4.16].entries()){const o=c.createOscillator(),g=c.createGain();o.frequency.value=base*ratio;g.gain.setValueAtTime(gain/(i+1),at);g.gain.exponentialRampToValueAtTime(.0001,at+1.6-i*.2);o.connect(g);this.bus(g,1,at);o.start(at);o.stop(at+1.7);o.onended=()=>{o.disconnect();g.disconnect();};}}
  air(at,length=.25,gain=.08,f=1600){const c=this.context,b=c.createBuffer(1,c.sampleRate*length,c.sampleRate),d=b.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/d.length,1.7);const s=c.createBufferSource();s.buffer=b;const bp=c.createBiquadFilter();bp.type='bandpass';bp.frequency.setValueAtTime(f,at);bp.frequency.exponentialRampToValueAtTime(Math.max(100,f*.3),at+length);bp.Q.value=.7;s.connect(bp);this.bus(bp,gain,at);s.start(at);s.onended=()=>{s.disconnect();bp.disconnect();};}
  drum(at,gain=.18){const c=this.context,o=c.createOscillator(),g=c.createGain();o.frequency.setValueAtTime(125,at);o.frequency.exponentialRampToValueAtTime(45,at+.19);g.gain.setValueAtTime(gain,at);g.gain.exponentialRampToValueAtTime(.0001,at+.35);o.connect(g);this.bus(g,1,at);o.start(at);o.stop(at+.36);o.onended=()=>{o.disconnect();g.disconnect();};}
  phrase(i,t,combat=true){
    const p=SCENE_SCORES[this.scene],beat=60/(combat?p.bpm:p.bpm*.73)/2,note=p.notes[i%8];
    this.pluck(note,t,combat?.095:.075,i%2?.5:-.5,1.7);
    if(i%2===0)this.pluck(p.notes[(i+3)%8]-12,t+beat*.5,.065,i%2?-.65:.65,1.8);
    if(i%8===0){this.strings([p.root-12,p.root,p.root+7,p.root+12],t,Math.min(3.6,beat*9),combat?.026:.02);this.flute(note+12,t+.09,Math.min(2.4,beat*5),.05);}
    if(i%4===0){this.pluck(p.root-12,t,.15,-.15,2.2);if(combat)this.drum(t,this.scene===3?.23:.15);}
    if(combat&&(i%8===6||this.scene===3&&i%2===1)){this.drum(t,.075);this.air(t,.1,.04,1900);}
    if(i%16===0)this.gong(t,this.scene===3?.075:.04,p.root===48?65.4:98);
    if(this.scene===1&&i%8===5){this.air(t,.9,.08,1400);this.flute(p.notes[(i+2)%8]+12,t+.1,.7,.035);}
    if(this.scene===2){if(i%3===0)this.waterDrop(t,.08,Math.sin(i)*.75);if(i%8===2)this.air(t,1.1,.055,2400);}
    if(this.scene===3&&i%16===12){this.air(t,1.8,.12,220);this.drum(t+.2,.16);}
    return beat;
  }
  schedule(){if(!this.context||!this.enabled||this.context.state!=='running'||['silent','outcome'].includes(this.mode))return;
    const c=this.context;if(this.nextBeat<c.currentTime-.2)this.nextBeat=c.currentTime+.05;
    while(this.nextBeat<c.currentTime+.25){this.nextBeat+=this.phrase(this.step++%32,this.nextBeat,this.mode==='combat');}
  }

  event(type){if(!this.context||!this.enabled||this.hidden)return;const t=this.context.currentTime+.008;
    if(type==='sword'){[81,86,93,98].forEach((m,i)=>this.pluck(m,t+i*.026,.15,(i-1.5)*.35,.9));this.air(t,.12,.13,4200);this.air(t+.12,.25,.1,2100);this.gong(t+.17,.035,330);this.drum(t+.19,.07);}
    else if(type==='guard'){this.air(t,.35,.11,700);this.gong(t+.04,.13,146.83);[62,69,74,81].forEach((m,i)=>this.pluck(m,t+.06+i*.045,.14,(i-1.5)*.3,1.6));this.strings([50,57,62],t+.08,1.2,.035);}
    else if(type==='thunder'){[62,69,74,81,86].forEach((m,i)=>this.pluck(m,t+i*.025,.14,(i-2)*.2));this.drum(t+.06,.32);this.air(t+.08,.65,.22,850);this.gong(t+.08,.14,73.4);this.air(t+.02,.1,.17,5000);this.drum(t+.27,.21);this.air(t+.32,1.2,.15,220);this.flute(86,t+.38,.6,.045);}
    else if(type==='parry'){this.gong(t,.15,220);[86,93,98].forEach((m,i)=>this.pluck(m,t+i*.035,.2));}
    else if(type==='enemy-killed'){this.drum(t,.24);this.air(t,.12,.19,4000);this.air(t+.08,.7,.14,750);[74,81,86,93].forEach((m,i)=>this.pluck(m,t+.07+i*.04,.1,(i-1.5)*.4,.8));this.gong(t+.09,.065,196);}
    else if(type==='enemy-hit'){this.air(t,.09,.055,2200);this.pluck(62,t,.07,0,.25);}
    else if(type==='enemy-dodge'||type==='dash'||type==='evade'){this.air(t,.28,.12,2500);this.flute(86,t,.27,.045);}
    else if(type==='hit'){this.drum(t,.25);this.air(t,.25,.16,420);}
    else if(type==='block'){this.gong(t,.08,180);this.air(t,.13,.09,1600);}
    else if(type==='enemy-cast'){this.pluck(57,t,.13);this.air(t,.3,.09,1200);}
    else if(type==='expose'||type==='armor-break'||type==='interrupt'){this.gong(t,.12,220);[81,86,93].forEach((m,i)=>this.pluck(m,t+i*.045,.13));}
    else if(type==='resist'){this.pluck(50,t,.05,0,.2);}
    else if(type==='hazard-warning'){this.gong(t,.08,82.4);this.flute(57,t,.65,.07);}
    else if(type==='hazard-strike'){this.drum(t,.3);this.air(t,.6,.19,700);}
    else if(type==='warning'){this.flute(57,t,.55,.07);}
    else if(type==='spawn'){this.air(t,.55,.12,600);this.pluck(50,t,.1);}
    else if(type==='travel'||type==='stage'||type==='seal'){this.gong(t,.14,110);this.flute(81,t,.9,.07);}
    else if(type==='finish'){[62,69,74,81,86,93].forEach((m,i)=>this.pluck(m,t+i*.11,.17,(i-2)*.15,2));this.gong(t,.2,146.8);}
    else if(type==='defeat'){this.gong(t,.15,55);this.flute(62,t,1.5,.07);}
    else if(type==='story'){this.gong(t,.11,73.4);this.flute(74,t+.2,1.6,.05);}
    else if(type==='empty')this.pluck(50,t,.08,0,.3);
  }
  // Short, stage-triggered phrases follow the cinematic clock; no fifteen-second
  // wall-clock score can continue playing after skip/retry or a paused tab.
  setEndingMix(active,done){
    if(!this.context)return;const state=active?(done?'done':'playing'):'off';if(this.endingMix===state)return;
    this.endingMix=state;const t=this.context.currentTime;
    this.regularBus.gain.setTargetAtTime(active?0:1,t,.08);
    // Retire the old finale bus on replay/reset so its scheduled notes never resume.
    if(state==='playing'){
      const old=this.finaleBus;old.gain.setTargetAtTime(0,t,.03);setTimeout(()=>old.disconnect(),4000);
      this.finaleBus=this.context.createGain();this.finaleBus.connect(this.master);this.finaleBus.connect(this.space);
    }else this.finaleBus.gain.setTargetAtTime(0,t,.15);
  }
  endingCue(cue){if(!this.context||!this.enabled||this.hidden||this.mode==='silent')return;const t=this.context.currentTime+.015;
    this.cinematicVoice=true;
    try{
      if(cue==='heartbeat'){this.drum(t,.19);this.drum(t+.25,.10);}
      if(cue==='fracture'){this.air(t,1.3,.08,2600);[62,69,74,81,86].forEach((m,i)=>this.pluck(m,t+i*.28,.10,(i-2)*.3,1.7));this.strings([38,50,57],t,2.2,.022);}
      if(cue==='skybreak'){this.drum(t,.34);this.drum(t+.15,.22);this.gong(t,.22,65.4);this.air(t,.15,.23,3800);this.air(t+.07,2,.22,400);this.strings([38,50,57,62,69],t,3.5,.04);[62,69,74,81,86,93].forEach((m,i)=>this.pluck(m,t+.1+i*.09,.17,(i-2.5)*.3,2));this.flute(86,t+.4,2.2,.075);}
      if(cue==='soar'){this.strings([50,57,62,74],t,3.2,.035);[81,86,93].forEach((m,i)=>this.flute(m,t+i*.65,1.4,.065));this.air(t,2,.055,1700);}
      if(cue==='beacon'){this.gong(t,.10,293.6);this.pluck(98,t+.12,.16,0,2.4);}
      if(cue==='heavens'){this.drum(t,.17);this.gong(t,.16,146.8);[74,81,86].forEach((m,i)=>this.pluck(m,t+i*.2,.15,(i-1)*.3,2.3));this.strings([50,57,62,74],t,2.5,.035);this.flute(86,t+.3,1.8,.065);}
    }finally{this.cinematicVoice=false;}
  }
  dispose(){clearInterval(this.timer);for(const a of this.ambient){a.source.stop();a.source.disconnect();a.filter.disconnect();a.gain.disconnect();}this.ambient=[];this.context?.close();}
}
