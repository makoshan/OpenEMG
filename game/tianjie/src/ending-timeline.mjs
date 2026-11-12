// One paused game clock owns the hand, sky, camera, text and cue boundaries.
export const ENDING_DURATION=15;
const smooth=(x,a,b)=>{const u=Math.max(0,Math.min(1,(x-a)/(b-a)));return u*u*(3-2*u);};
export function endingFrame(time,{reduced=false}={}){
 const t=Math.max(0,Number.isFinite(time)?time:0),duration=reduced?5:ENDING_DURATION;
 if(reduced)return {time:t,duration,done:t>=duration,chapter:'新境',scene:true,hand:0,release:1,lift:1,bloom:1,darken:1,reveal:1,pull:1,flash:0,title:smooth(t,.4,1.3),feathers:0,still:false,crack:1,push:1,beacon:1,suspense:0};
 return {time:t,duration,done:t>=duration,chapter:t<1.5?'万籁俱寂':t<4.6?'掌起 · 天裂':t<8.5?'一掌开天':t<11.8?'诸天之外':'掌天诀',scene:t>=1.5,still:t<1.5,
  hand:1-smooth(t,6.3,7.8),lift:smooth(t,1.5,4.2),crack:smooth(t,2.1,4.5),push:smooth(t,4.6,5.05),release:smooth(t,4.6,7.4),reveal:smooth(t,1.5,2.1),pull:smooth(t,5,9.2),bloom:smooth(t,4.6,6),
  darken:smooth(t,11.4,12.9),flash:.42*smooth(t,4.6,4.75)*(1-smooth(t,4.75,5.12)),title:smooth(t,12.3,13.6),feathers:smooth(t,2.2,4.2)*(1-smooth(t,8.3,10)),beacon:smooth(t,9.2,9.8),suspense:smooth(t,9.7,10.3)*(1-smooth(t,11.8,12.4))};
}
export class EndingClock{
 constructor(){this.reset();}
 reset(){this.active=false;this.time=0;this.reduced=false;this.cues=new Set();}
 start(reduced=false){this.reset();this.active=true;this.reduced=reduced;}
 tick(dt,paused=false){if(this.active&&!paused)this.time=Math.min(this.reduced?5:ENDING_DURATION,this.time+Math.max(0,Math.min(.05,Number.isFinite(dt)?dt:0)));return this.frame;}
 skip(){if(this.active)this.time=this.reduced?5:ENDING_DURATION;}
 get frame(){return endingFrame(this.time,{reduced:this.reduced});}
 takeCues(){if(!this.active)return [];const due=[];for(const [name,at]of (this.reduced?[['heavens',.4]]:[['heartbeat',.25],['fracture',2.1],['skybreak',4.6],['soar',7.2],['beacon',9.4],['heavens',12.3]])){if(this.time>=at&&!this.cues.has(name)){this.cues.add(name);if(!this.frame.done)due.push(name);}}return due;}
}
