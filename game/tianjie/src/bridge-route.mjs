// Shared geometry and travel timing keep the camera on the physical bridge.
// Foot of the existing pavilion at pixel (1270, 425) in the 1774 x 887 sky.
// Same spherical mapping and center as World.init; no duplicate pavilion is built.
const phi=1270/1774*Math.PI*2,theta=425/887*Math.PI;
export const PAVILION_ANCHOR={x:-288*Math.cos(phi)*Math.sin(theta),y:25+288*Math.cos(theta),z:288*Math.sin(phi)*Math.sin(theta)};
export const BRIDGE = {start:-35, end:PAVILION_ANCHOR.z, width:1.35, safeX:.38, height:1.55, sag:6};
export const travelDuration = fromArea => fromArea===0 ? 8.5 : fromArea===1 ? 18 : 3.2;
const clamp = n => Math.max(0,Math.min(1,n));
const smooth = n => {const t=clamp(n);return t*t*(3-2*t);};
export function deckHeight(z){
 const f=clamp((z-BRIDGE.start)/(BRIDGE.end-BRIDGE.start));
 return BRIDGE.height+(PAVILION_ANCHOR.y-BRIDGE.height)*smooth(f)-BRIDGE.sag*4*f*(1-f);
}
export function bridgeCenterX(z){return PAVILION_ANCHOR.x*smooth((z-BRIDGE.start)/(BRIDGE.end-BRIDGE.start));}
export function bridgeYaw(z){return Math.atan((bridgeCenterX(z+.05)-bridgeCenterX(z-.05))/.1);}
export function bridgePoint(z,lateral=0,height=0){const yaw=bridgeYaw(z);return {x:bridgeCenterX(z)+lateral*Math.cos(yaw),y:deckHeight(z)+height,z:z-lateral*Math.sin(yaw)};}
export function pathHeight(z){
 if(z>-23.6)return 1.55*clamp((-z-18)/5.6);
 return z>=BRIDGE.start?BRIDGE.height:deckHeight(z);
}
export function gateJourney(from, progress){
 const f=smooth((progress-.09)/.91);
 const z=from.z+(-43-from.z)*f;
 // Center before the staircase even if the player cleared the gate from a flank.
 const center=smooth(f/Math.max(.01,(-18-from.z)/(-43-from.z)));
 return {x:from.x*(1-center)+bridgeCenterX(z),y:1.75+pathHeight(z),z};
}

export const LAKE_OFFSET={x:PAVILION_ANCHOR.x,y:-24,z:PAVILION_ANCHOR.z-30+103};
export const LAKE_ENTRY={x:LAKE_OFFSET.x,y:LAKE_OFFSET.y+1.75,z:LAKE_OFFSET.z-103};
// Victory journey: run the remaining bridge, cross the pavilion floor, descend to water.
export function lakeJourney(from,progress){
 const f=clamp(progress),a=PAVILION_ANCHOR;
 if(f<=.58){const k=smooth(f/.58),z=from.z+(BRIDGE.end-from.z)*k;return {x:bridgeCenterX(z)+(from.x-bridgeCenterX(from.z))*(1-k),y:deckHeight(z)+1.75,z};}
 if(f<=.73){const k=smooth((f-.58)/.15);return {x:a.x,y:a.y+1.75,z:a.z-11*k};}
 const k=smooth((f-.73)/.27);
 return {x:a.x+Math.sin(k*Math.PI)*7,y:a.y+1.75+(LAKE_ENTRY.y-a.y-1.75)*k,z:a.z-11+(LAKE_ENTRY.z-a.z+11)*k};
}
