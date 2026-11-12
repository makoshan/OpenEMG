import test from 'node:test';
import assert from 'node:assert/strict';
import {gateJourney,deckHeight,bridgeCenterX,bridgePoint,PAVILION_ANCHOR,BRIDGE,lakeJourney,LAKE_ENTRY} from '../src/bridge-route.mjs';
test('a cleared gate is approached through its center from either courtyard flank',()=>{
 for(const x of [-11.5,0,11.5])for(const z of [17,0,-18]){
  let previous=z;
  for(let i=0;i<=1000;i++){
   const p=gateJourney({x,z},i/1000);
   assert.ok(p.z<=previous+1e-9);previous=p.z;
   if(p.z<-22&&p.z>-31)assert.ok(Math.abs(p.x)<.01,'route must enter the real doorway');
  }
  const end=gateJourney({x,z},1);assert.ok(Math.abs(end.x-bridgeCenterX(end.z))<1e-9);assert.equal(end.z,-43);assert.equal(end.y,deckHeight(end.z)+1.75);
 }
});

test('the bridge ends beneath the existing painted pavilion, with finite continuous decking',()=>{
 const end=bridgePoint(BRIDGE.end);
 for(const key of ['x','y','z'])assert.ok(Math.abs(end[key]-PAVILION_ANCHOR[key])<1e-8);
 let prev=bridgePoint(BRIDGE.start);
 for(let z=BRIDGE.start;z>=BRIDGE.end;z-=.1){const p=bridgePoint(z);assert.ok(Object.values(p).every(Number.isFinite));assert.ok(Math.hypot(p.x-prev.x,p.y-prev.y,p.z-prev.z)<.2);prev=p;}
});

test('bridge victory journey crosses the pavilion before descending to the lake, without jumps',()=>{
 const from={x:bridgeCenterX(-58),y:deckHeight(-58)+1.75,z:-58};
 assert.deepEqual(lakeJourney(from,0),from);
 const arrival=lakeJourney(from,.58),exit=lakeJourney(from,.73);
 assert.ok(Math.abs(arrival.z-PAVILION_ANCHOR.z)<1e-8);assert.ok(exit.z<arrival.z-10);assert.ok(Math.abs(exit.y-arrival.y)<1e-8);
 const end=lakeJourney(from,1);for(const key of ['x','y','z'])assert.ok(Math.abs(end[key]-LAKE_ENTRY[key])<1e-8);
 let prev=from;for(let i=1;i<=10000;i++){const p=lakeJourney(from,i/10000);assert.ok(Math.hypot(p.x-prev.x,p.y-prev.y,p.z-prev.z)<.1);prev=p;}
});

// The physical floor spans A.z-10 through A.z+1; descend only after clearing it.
test('pavilion descent never intersects the floor volume',()=>{
 const a=PAVILION_ANCHOR,from={x:bridgeCenterX(-58),y:deckHeight(-58)+1.75,z:-58};
 for(let i=5800;i<=10000;i++){const p=lakeJourney(from,i/10000);
  if(Math.abs(p.x-a.x)<=3.5&&p.z>=a.z-10&&p.z<=a.z+1)assert.ok(p.y>=a.y+1.7,'camera descended inside pavilion floor');
 }
});
