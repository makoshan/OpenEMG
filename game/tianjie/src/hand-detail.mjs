import * as T from 'three';
// Nails are shaded ON the skinned surface: no separate plates, offsets or detached joints.
export function skinMaterial(){
 const material=new T.MeshPhysicalMaterial({color:0xc89779,roughness:.65,metalness:0,clearcoat:.04,sheen:.24,sheenColor:0xe8bcaa,sheenRoughness:.8});
 material.onBeforeCompile=shader=>{
  shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vSkinP;\nvarying vec3 vSkinN;').replace('#include <begin_vertex>','#include <begin_vertex>\nvSkinP=position;vSkinN=normal;');
  shader.fragmentShader=shader.fragmentShader.replace('#include <common>',`#include <common>
   varying vec3 vSkinP;varying vec3 vSkinN;
   float skinNoise(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
   float nail(vec2 p,vec2 c,vec2 size){vec2 q=abs((p-c)/size);return 1.0-smoothstep(.8,1.0,pow(pow(q.x,4.0)+pow(q.y,4.0),.25));}
  `).replace('#include <color_fragment>',`#include <color_fragment>
   vec3 p=vSkinP;float pore=skinNoise(floor(p*7200.0)),mottling=skinNoise(floor(p*420.0));
   diffuseColor.rgb*=1.0+(pore-.5)*.035+(mottling-.5)*.025;
   float vein=exp(-pow(sin(p.z*150.0+p.y*45.0)*7.0,2.0))*(1.0-smoothstep(.0,.03,abs(p.y+.008)));
   diffuseColor.rgb=mix(diffuseColor.rgb,diffuseColor.rgb*vec3(.9,.96,.96),vein*.16);
   float nMask=nail(p.zy,vec2(-.011,-.108),vec2(.0046,.0055))+nail(p.zy,vec2(.015,-.116),vec2(.0048,.0055))+nail(p.zy,vec2(.043,-.102),vec2(.0045,.005))+nail(p.zy,vec2(.060,-.077),vec2(.0036,.0045));
   nMask=clamp(nMask,0.0,1.0)*smoothstep(.3,.75,vSkinN.x);
   // A thin pink nail bed follows the same skin weights as its fingertip.
   diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.60,.35,.27),nMask*.32);
   float warmth=exp(-pow((p.y+.075)*28.0,2.0));diffuseColor.rgb*=mix(vec3(1.0),vec3(1.045,.965,.94),warmth*.55);
   float knuckle=exp(-pow((p.y+.078)*1050.0,2.0))*exp(-pow((p.z+.013)*90.0,2.0))+exp(-pow((p.y+.083)*1050.0,2.0))*exp(-pow((p.z-.012)*100.0,2.0))+exp(-pow((p.y+.071)*1050.0,2.0))*exp(-pow((p.z-.036)*100.0,2.0))+exp(-pow((p.y+.052)*1050.0,2.0))*exp(-pow((p.z-.053)*100.0,2.0));
   diffuseColor.rgb*=1.0-knuckle*.10*smoothstep(.35,.8,vSkinN.x);

  `).replace('#include <roughnessmap_fragment>',`#include <roughnessmap_fragment>\nroughnessFactor=clamp(roughnessFactor+(skinNoise(floor(vSkinP*6200.0))-.5)*.065,.5,.8);roughnessFactor=mix(roughnessFactor,.38,nMask);`);
 };
 const originalCompile=material.onBeforeCompile;material.onBeforeCompile=shader=>{originalCompile(shader);shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>\n vec3 grain=vec3(sin(vSkinP.y*5200.0)*sin(vSkinP.z*4500.0),sin(vSkinP.x*4700.0)*sin(vSkinP.y*5800.0),sin(vSkinP.z*6100.0)*sin(vSkinP.x*4900.0));normal=normalize(normal+grain*.026*(1.0-nMask));`);};
 material.customProgramCacheKey=()=> 'yuanli-skin-moonlight-v4';return material;
}
// One Loop subdivision pass with explicit skin influence blending. Bone indices are categorical,
// so they must NEVER be interpolated as floating-point attributes.
export function refineHand(geometry){
 const p=geometry.attributes.position,si=geometry.attributes.skinIndex,sw=geometry.attributes.skinWeight;if(!si||!sw)return geometry;
 const pts=[],skins=[],lookup=new Map(),original=[];
 for(let i=0;i<p.count;i++){
  const ids=[0,1,2,3].map(j=>si.array[i*4+j]),ws=[0,1,2,3].map(j=>sw.array[i*4+j]);
  const key=[p.getX(i),p.getY(i),p.getZ(i)].map(n=>Math.round(n*1e6)).join(',')+'|'+ids.map((id,j)=>`${id}:${Math.round(ws[j]*1e4)}`).join(',');
  if(!lookup.has(key)){lookup.set(key,pts.length);pts.push(new T.Vector3(p.getX(i),p.getY(i),p.getZ(i)));skins.push(ids.map((id,j)=>[id,ws[j]]));}
  original.push(lookup.get(key));
 }
 const indices=geometry.index?Array.from(geometry.index.array):Array.from({length:p.count},(_,i)=>i),faces=[];for(let i=0;i<indices.length;i+=3)faces.push(indices.slice(i,i+3).map(i=>original[i]));
 const neighbors=pts.map(()=>new Set()),edges=new Map(),key=(a,b)=>a<b?`${a},${b}`:`${b},${a}`;
 for(const [a,b,c]of faces)for(const [u,v,o]of [[a,b,c],[b,c,a],[c,a,b]]){neighbors[u].add(v);neighbors[v].add(u);const k=key(u,v);if(!edges.has(k))edges.set(k,{a:u,b:v,opposite:[]});edges.get(k).opposite.push(o);}
 const blend=terms=>{const pos=new T.Vector3(),weights=new Map();for(const [id,w]of terms){pos.addScaledVector(pts[id],w);for(const [bone,weight]of skins[id])weights.set(bone,(weights.get(bone)||0)+weight*w);}const sorted=[...weights].sort((a,b)=>b[1]-a[1]).slice(0,4),total=sorted.reduce((n,s)=>n+s[1],0)||1;while(sorted.length<4)sorted.push([0,0]);return {pos,skin:sorted.map(([bone,w])=>[bone,w/total])};};
 const vertices=[];
 for(let i=0;i<pts.length;i++){const boundary=[...neighbors[i]].filter(j=>edges.get(key(i,j)).opposite.length===1);if(boundary.length===2)vertices.push(blend([[i,.75],[boundary[0],.125],[boundary[1],.125]]));else{const n=neighbors[i].size,beta=n===3?3/16:3/(8*Math.max(1,n));vertices.push(blend([[i,1-n*beta],...[...neighbors[i]].map(j=>[j,beta])]));}}
 for(const edge of edges.values()){edge.mid=vertices.length;vertices.push(blend(edge.opposite.length===2?[[edge.a,.375],[edge.b,.375],...[...edge.opposite].map(o=>[o,.125])]:[[edge.a,.5],[edge.b,.5]]));}
 const out=[];for(const [a,b,c]of faces){const ab=edges.get(key(a,b)).mid,bc=edges.get(key(b,c)).mid,ca=edges.get(key(c,a)).mid;out.push(a,ab,ca,b,bc,ab,c,ca,bc,ab,bc,ca);}
 const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(vertices.flatMap(v=>v.pos.toArray()),3));g.setAttribute('skinIndex',new T.Uint16BufferAttribute(vertices.flatMap(v=>v.skin.map(s=>s[0])),4));g.setAttribute('skinWeight',new T.Float32BufferAttribute(vertices.flatMap(v=>v.skin.map(s=>s[1])),4));g.setIndex(out);g.computeVertexNormals();g.computeBoundingSphere();return g;
}
export function createNails(world){world.nails=[];}
export function updateNails(){}
