import test from 'node:test';import assert from 'node:assert/strict';import {EndingClock,endingFrame,ENDING_DURATION} from '../src/ending-timeline.mjs';
test('finale progresses from stillness through skybreak to palace response and logo',()=>{
 const a=endingFrame(1),b=endingFrame(4),c=endingFrame(9.4),d=endingFrame(13.8);assert.equal(a.scene,false);assert.equal(b.scene,true);assert.equal(b.bloom,0);assert.equal(c.bloom,1);assert.equal(d.pull,1);assert.equal(d.title,1);assert.equal(d.darken,1);assert.equal(d.done,false);assert.equal(endingFrame(ENDING_DURATION).done,true);
});
test('pause, repeat, skip and reset cannot leak a cinematic into a new run',()=>{
 const clock=new EndingClock();clock.tick(1);assert.equal(clock.active,false);clock.start();assert.deepEqual(clock.takeCues(),[]);assert.deepEqual(clock.takeCues(),[]);for(let i=0;i<80;i++)clock.tick(.05);const at=clock.time;clock.tick(.05,true);assert.equal(clock.time,at);assert.deepEqual(clock.takeCues(),['heartbeat','fracture']);clock.skip();assert.equal(clock.frame.done,true);assert.deepEqual(clock.takeCues(),[]);clock.start();assert.equal(clock.time,0);assert.equal(clock.frame.done,false);clock.reset();assert.equal(clock.active,false);assert.equal(clock.time,0);
});
test('reduced motion shows the final composition without flash or camera travel',()=>{const clock=new EndingClock();clock.start(true);assert.equal(clock.frame.scene,true);for(const t of [0,1,3,5]){const f=endingFrame(t,{reduced:true});assert.equal(f.pull,1);assert.equal(f.flash,0);assert.equal(f.feathers,0);}clock.skip();assert.equal(clock.time,5);assert.equal(clock.frame.done,true);});

test('hand carries the scene transition and leaves only after the clouds open',()=>{assert.equal(endingFrame(3.39).hand,1);assert.equal(endingFrame(3.41).hand,1);assert.equal(endingFrame(5).hand,1);assert.ok(endingFrame(7).hand>0);assert.equal(endingFrame(8).hand,0);assert.equal(endingFrame(8).release,1);assert.equal(endingFrame(1,{reduced:true}).hand,0);});

test('the palm push opens the sky, the palace responds before the logo',()=>{assert.equal(endingFrame(.8).still,true);assert.equal(endingFrame(.8).crack,0);assert.equal(endingFrame(4.4).release,0);assert.ok(endingFrame(4.4).crack>.9);assert.ok(endingFrame(5.1).push===1);assert.ok(endingFrame(6.6).release>.7);assert.equal(endingFrame(9.9).release,1);assert.ok(endingFrame(10.4).beacon===1);assert.equal(endingFrame(10.4).suspense,1);assert.equal(endingFrame(10.4).title,0);assert.equal(endingFrame(13.8).suspense,0);});

test("reduced motion uses only the resolved logo phrase",()=>{const c=new EndingClock();c.start(true);for(let i=0;i<10;i++)c.tick(.05);assert.deepEqual(c.takeCues(),["heavens"]);for(let i=0;i<70;i++)c.tick(.05);assert.deepEqual(c.takeCues(),[]);});
