import * as T from 'three';
import {disposeEffect} from './spells.mjs';
const palette={sword:0x5caaff,guard:0xffbf55,thunder:0xff9e2c};
const glowMat=(color,opacity=1)=>new T.MeshBasicMaterial({color,transparent:true,opacity,depthWrite:false,side:T.DoubleSide,blending:T.AdditiveBlending,toneMapped:false});
export function initCombatFX(world){
 world.deathBursts=[];world.handAuras={};
 for(const mode of Object.keys(palette)){
  const root=new T.Group();root.visible=false;root.position.set(-.025,mode==='thunder'?.16:.27,.045);world.handRig.add(root);
  const color=palette[mode];
  if(mode==='guard'){
   const seal=new T.Mesh(new T.PlaneGeometry(.38,.38),new T.MeshBasicMaterial({map:world.runes,color,transparent:true,opacity:.9,blending:T.AdditiveBlending,depthWrite:false,side:T.DoubleSide,toneMapped:false}));seal.position.z=-.055;seal.userData.spin=true;root.add(seal);
   for(let i=0;i<5;i++){
    const paper=new T.Mesh(new T.PlaneGeometry(.046,.115),new T.MeshBasicMaterial({map:world.guardPaper,color:0xffd883,transparent:true,side:T.DoubleSide,depthWrite:false,toneMapped:false}));
    paper.userData.orbit=i*Math.PI*2/5;root.add(paper);
    const border=new T.LineSegments(new T.EdgesGeometry(paper.geometry),new T.LineBasicMaterial({color:0xffc462,transparent:true,blending:T.AdditiveBlending,depthWrite:false,toneMapped:false}));paper.add(border);
   }
  }else{
   const arcCount=mode==='sword'?5:12;
   for(let i=0;i<arcCount;i++){
    const pts=[];for(let j=0;j<18;j++){
     const a=i*Math.PI*2/arcCount+j*.16,r=.10+(j%3)*.012;
     pts.push(new T.Vector3(Math.cos(a)*r,-.14+j*.017,Math.sin(a)*r+.035));
    }
    const arc=new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts),36,.0007,4,false),glowMat(color,.85));root.add(arc);
   }
  }
  // Fine embers instead of opaque rings covering the hand.
  const positions=[];for(let i=0;i<65;i++){const a=i*2.399;positions.push(Math.cos(a)*(.09+i%7*.014),-.17+i/65*.4,Math.sin(a)*.08+.06);}
  const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(positions,3));root.add(new T.Points(geo,new T.PointsMaterial({map:world.glow,color,size:.012,transparent:true,opacity:.8,blending:T.AdditiveBlending,depthWrite:false,toneMapped:false})));
  root.traverse(o=>{if(o.material)o.userData.baseOpacity=o.material.opacity;});world.handAuras[mode]=root;
 }
}
export function handCast(world,mode){world.auraCast={mode,start:world.time,life:{sword:.8,guard:1.15,thunder:1.25}[mode]};}
export function deathBurst(world,pos,kind){
 const color=['reflection','mirror'].includes(kind)?0x91eeec:kind==='dragonfly'?0xcfb0ff:0xffc082;
 const root=new T.Group();root.position.copy(pos);world.scene.add(root);
 const flash=new T.Mesh(new T.SphereGeometry(.7,12,8),glowMat(0xfff1d5));root.add(flash);
 const rings=[];for(let i=0;i<2;i++){const ring=new T.Mesh(new T.TorusGeometry(1,.045,6,48),glowMat(color));ring.quaternion.copy(world.camera.quaternion);ring.rotateX(i*.7);root.add(ring);rings.push(ring);}
 const shards=new T.InstancedMesh(new T.OctahedronGeometry(.16),glowMat(color),36),vel=[];root.add(shards);
 for(let i=0;i<36;i++)vel.push(new T.Vector3(Math.sin(i*2.4),Math.cos(i*1.7),Math.sin(i*4.1)).normalize().multiplyScalar(4+i%7));
 world.deathBursts.push({root,flash,rings,shards,vel,age:0,life:1.2});world.emitParticles(pos,color,260,12);
}
export function updateCombatFX(world,dt){
 const cast=world.auraCast,f=cast?(world.time-cast.start)/cast.life:2;
 for(const [mode,root]of Object.entries(world.handAuras||{})){
  root.visible=mode===cast?.mode&&f<1;
  if(!root.visible)continue;
  const strength=Math.min(1,f*12)*Math.min(1,(1-f)*5);root.scale.setScalar(mode==='guard'?.8+Math.sin(Math.min(1,f)*Math.PI)*.15:.64+Math.sin(Math.min(1,f)*Math.PI)*.12);root.rotation.z=mode==='guard'?0:Math.sin(world.time*25)*.035;for(const o of root.children){if(o.userData.spin)o.rotation.z=-world.time*.4;if(o.userData.orbit!==undefined){const a=o.userData.orbit+world.time*.45;o.position.set(Math.cos(a)*.24,Math.sin(a)*.18,-.03);o.rotation.z=-Math.cos(a)*.2;}}
  root.traverse(o=>{if(o.material)o.material.opacity=o.userData.baseOpacity*strength*(mode==='thunder'?.72+.28*Math.sin(world.time*53)**2:1);});
 }
 const dummy=new T.Object3D();
 world.deathBursts=(world.deathBursts||[]).filter(e=>{
  e.age+=dt;const f=e.age/e.life;e.flash.scale.setScalar(1+f*7);e.flash.material.opacity=Math.max(0,1-f*6);
  for(const [i,r]of e.rings.entries()){r.scale.setScalar(.2+f*(5+i*2));r.material.opacity=Math.max(0,1-f*1.4);}
  for(let i=0;i<e.vel.length;i++){dummy.position.copy(e.vel[i]).multiplyScalar(e.age);dummy.position.y-=e.age*e.age*2;dummy.rotation.set(e.age*(i%4+2),e.age*3,i);dummy.scale.setScalar(Math.max(.01,1-f));dummy.updateMatrix();e.shards.setMatrixAt(i,dummy.matrix);}e.shards.instanceMatrix.needsUpdate=true;e.shards.material.opacity=Math.max(0,1-f);
  if(f>=1){e.root.removeFromParent();disposeEffect(e.root);return false;}return true;
 });
}
export function clearCombatFX(world){for(const e of world.deathBursts||[]){e.root.removeFromParent();disposeEffect(e.root);}world.deathBursts=[];world.auraCast=null;for(const r of Object.values(world.handAuras||{}))r.visible=false;}
