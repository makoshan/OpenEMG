import * as T from 'three';
const V=(x,y,z)=>new T.Vector3(x,y,z);
export function disposeEffect(root){root.traverse(o=>{if(o.isInstancedMesh)o.dispose();o.geometry?.dispose();if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();}});}
export function swordMesh(){
 const g=new T.Group(),blade=new T.Shape();blade.moveTo(0,1.3);blade.lineTo(.095,.94);blade.lineTo(.075,-.38);blade.lineTo(-.075,-.38);blade.lineTo(-.095,.94);blade.closePath();
 const mat=new T.MeshStandardMaterial({color:0xd9fff3,metalness:.85,roughness:.18,emissive:0x338dff,emissiveIntensity:2.3});
 const m=new T.Mesh(new T.ExtrudeGeometry(blade,{depth:.035,bevelEnabled:true,bevelSize:.018,bevelThickness:.012,bevelSegments:1,steps:1}),mat);g.add(m);
 const gold=new T.MeshStandardMaterial({color:0xd4b478,metalness:.8,roughness:.28});
 const guard=new T.Mesh(new T.BoxGeometry(.43,.065,.08),gold);guard.position.y=-.4;g.add(guard);
 const handle=new T.Mesh(new T.CylinderGeometry(.042,.042,.35,8),new T.MeshStandardMaterial({color:0x193c39}));handle.position.y=-.6;g.add(handle);
 return g;
}
export function lightning(world,from,to){
 const points=[];for(let j=0;j<=18;j++){const t=j/18,p=from.clone().lerp(to,t);if(j&&j<18)p.add(V((Math.random()-.5)*.65,(Math.random()-.5)*.28,(Math.random()-.5)*.5));points.push(p);}
 const group=new T.Group();
 for(const [radius,color,opacity] of [[.055,0xff8c24,.5],[.018,0xfff1cd,1]]){const geo=new T.TubeGeometry(new T.CatmullRomCurve3(points, false,'catmullrom',0),50,radius,5,false);group.add(new T.Mesh(geo,new T.MeshBasicMaterial({color,transparent:true,opacity,depthWrite:false,blending:T.AdditiveBlending,toneMapped:false})));}
 world.scene.add(group);world.spellEffects.push({root:group,age:0,life:.65,kind:'bolt'});
}
export function thunder(world,target){
 const from=world.camera.position.clone().add(V(.45,-.12,-2.2).applyQuaternion(world.camera.quaternion));
 const group=new T.Group();const paper=new T.Mesh(new T.PlaneGeometry(.20,.42),new T.MeshBasicMaterial({map:world.thunderPaper,side:T.DoubleSide,color:0xffdeb1,toneMapped:false}));group.add(paper);
 const light=new T.PointLight(0xffa32c,15,8);group.add(light);group.position.copy(from);group.quaternion.copy(world.camera.quaternion);world.scene.add(group);
 world.spellEffects.push({root:group,age:0,life:1.2,kind:'talisman',from,to:target.clone()});
 for(let i=0;i<5;i++){const a=i*Math.PI*2/5;lightning(world,target.clone().add(V(Math.cos(a)*2.4,8+Math.random()*2,Math.sin(a)*2.4)),target);}
 lightning(world,from,target);world.emitParticles(target,0xffbe54,140,8);world.ring(target,0xffad35,6);
}
export function updateSpells(world,dt){world.spellEffects=world.spellEffects.filter(e=>{e.age+=dt;const f=e.age/e.life;if(e.kind==='talisman'){e.root.position.lerpVectors(e.from,e.to,Math.min(1,f*1.5));e.root.rotateZ(dt*.8);}else e.root.children.forEach((o,i)=>o.material.opacity=e.kind==='wake'?(1-f)*.8:(i===0?.5:1)*(.65+.35*Math.abs(Math.sin(e.age*75))));if(f>=1){world.scene.remove(e.root);disposeEffect(e.root);return false;}return true;});}

export function swordWake(world,from,to){
 const root=new T.Group(),dir=to.clone().sub(from),side=new T.Vector3().crossVectors(dir.clone().normalize(),V(0,1,0));
 for(let i=0;i<3;i++){
  const points=[];for(let j=0;j<=24;j++){const f=j/24,p=from.clone().lerp(to,f),radius=Math.sin(f*Math.PI)*(.16+i*.07),a=f*22+i*2.1;p.addScaledVector(side,Math.cos(a)*radius);p.y+=Math.sin(a)*radius;points.push(p);}
  root.add(new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3(points),64,i===0?.014:.006,5,false),new T.MeshBasicMaterial({color:i===0?0x82c8ff:0x2878ff,transparent:true,opacity:.75,blending:T.AdditiveBlending,depthWrite:false,toneMapped:false})));
 }
 world.scene.add(root);world.spellEffects.push({root,age:0,life:.35,kind:'wake'});
}
