import * as T from 'three';
// Presentation only. The combat clock owns the sunrise, so pause/retry are deterministic.
export function daylightFor(state, time, travelStart, travelDuration) {
 if (state.area > 0) return 1;
 if (state.phase !== 'travel') return 0;
 return T.MathUtils.smoothstep((time-travelStart)/travelDuration,.12,.82);
}
export async function buildArt(world) {
 const night=await world.texture('sky-night.jpg');
 if(night){
  night.wrapT=T.ClampToEdgeWrapping;
  // Artwork is a sky panorama: redistribute upper hemisphere UVs so the moon
  // sits above the temple, and its tree horizon stays at the world horizon.
  const domeGeo=new T.SphereGeometry(285,64,48),uv=domeGeo.attributes.uv;
  for(let i=0;i<uv.count;i++){uv.setX(i,.5+.5*Math.tanh((uv.getX(i)-.5)*6)/Math.tanh(3));uv.setY(i,Math.min(1,.16+1.1*Math.tanh(Math.max(0,uv.getY(i)-.5)*4)));}
  uv.needsUpdate=true;
  const mat=new T.MeshBasicMaterial({color:0x8db0d8,map:night,side:T.BackSide,fog:false,toneMapped:false,transparent:true,depthWrite:false});
  world.nightDome=new T.Mesh(domeGeo,mat);
  world.nightDome.rotation.y=1.85;world.nightDome.position.y=25;world.nightDome.renderOrder=-999;world.scene.add(world.nightDome);
 }
 world.courtLights=[];
 for(const [x,y,z,intensity,distance] of [[-8,3,-18,65,26],[8,3,-18,65,26],[0,4,-23,65,22]]){
  const l=new T.PointLight(0xff962f,intensity,distance,2);l.position.set(x,y,z);world.scene.add(l);world.courtLights.push(l);
 }
 // Warm reflected pools on the wet paving; the actual lanterns also cast point illumination.
 world.reflections=new T.Group();world.scene.add(world.reflections);
 for(const x of [-12,12])for(const z of [-19,-7,5,17]){
  const m=new T.Mesh(new T.PlaneGeometry(2.8,9),new T.MeshBasicMaterial({map:world.glow,color:0xff9b36,opacity:.13,transparent:true,blending:T.AdditiveBlending,depthWrite:false}));
  m.rotation.x=-Math.PI/2;m.position.set(x,-.025,z+1);world.reflections.add(m);
 }
 world.daylight=0;
}
export function updateArt(world,state){
 const day=daylightFor(state,world.time,world.travelStart,world.travelDuration);world.daylight=day;
 if(world.nightDome){world.nightDome.visible=day<1;world.nightDome.material.opacity=1-day;}
 if(world.skyMaterial&&state.area===0)world.skyMaterial.opacity=day;
 const night=new T.Color(0x07152d),dayFog=new T.Color(0x41555d);
 if(state.area===0)world.scene.fog.color.copy(night).lerp(dayFog,day);
 world.hemi.color.set(0x7dacf8).lerp(new T.Color(0xb5d4e7),day);world.hemi.intensity=.75+day*1.35;
 world.sun.color.set(0x9bbcff).lerp(new T.Color(0xffd8a2),day);world.sun.intensity=1.35+day*2.15;
 world.fill.intensity=.48+day*.52;
 world.scene.environmentIntensity=.14+day*.21;
 for(const l of world.courtLights)l.intensity=(1-day)*65+day*8;
 world.reflections.visible=state.area===0;world.reflections.children.forEach(o=>o.material.opacity=.16*(1-day));
 world.materials.floor.roughness=.32+day*.23;
 world.handKey.color.set(0xffddba).lerp(new T.Color(0xffddbc),day);world.handKey.intensity=2.7+day*.2;
 world.handFill.intensity=.9+day*.3;
}
