import {specialEnemy} from './realms.mjs';
import * as T from 'three';
import {ENCOUNTERS} from './encounters.mjs';
const V=(x=0,y=0,z=0)=>new T.Vector3(x,y,z);
export class Actors {
 constructor(world){this.world=world;this.map=new Map();world.enemy.visible=false;
  for(const e of ENCOUNTERS.flatMap(a=>a.enemies)){
   const root=specialEnemy(world,e)||world.enemy.clone(true);root.visible=false;
   root.traverse(o=>{if(o.isMesh||o.isSprite){o.material=o.material.clone();if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}}});
   const scale=({keeper:1,shade:.8,wisp:.62,manta:.95,dragonfly:1.15,reflection:.9,mirror:1.15,golem:1.2,phoenix:1.05,thunderlord:1.15})[e.kind]||1;root.scale.setScalar(scale);
   const wings=[];
   if(['shade','wisp'].includes(e.kind)){
    const wingMat=new T.MeshPhysicalMaterial({color:e.kind==='shade'?0x12343d:0x2c3b36,emissive:e.kind==='shade'?0x153544:0x233829,emissiveIntensity:.6,roughness:.52,metalness:.35,side:T.DoubleSide,transparent:true,opacity:.87});
    for(const sign of [-1,1]){const wing=new T.Group();root.add(wing);wing.position.set(sign*.45,.7,-.1);for(let i=0;i<4;i++){
      const shape=new T.Shape();shape.moveTo(0,0);shape.quadraticCurveTo(sign*(2.1+i*.25),1.1-i*.13,sign*(3.1-i*.4),.7-i*.55);shape.quadraticCurveTo(sign*1.7,-.9-i*.28,0,-.3);const mesh=new T.Mesh(new T.ShapeGeometry(shape,14),wingMat);mesh.position.z=-i*.11;wing.add(mesh);
    }wings.push({wing,sign});}
   }
   const glow=new T.Sprite(new T.SpriteMaterial({map:world.glow,color:e.kind==='wisp'?0x80d7bd:e.kind==='shade'?0x83a5ee:0xe4a56f,transparent:true,opacity:.13,blending:T.AdditiveBlending,depthWrite:false}));glow.scale.set(7,7,1);glow.position.y=.7;root.add(glow);
   world.scene.add(root);this.map.set(e.id,{root,wings,scale,glow,kind:e.kind,born:-1,dead:-1,hit:0});
  }
 }
 position(id){return this.map.get(id)?.root.position.clone().add(V(0,.65,.3));}
 hit(id){const a=this.map.get(id);if(a)a.hit=1;}
 reset(){for(const a of this.map.values()){a.root.visible=false;a.born=-1;a.dead=-1;a.hit=0;}}
 update(dt,state,t){
  const live=new Map((state.enemies||[]).map(e=>[e.id,e]));
  for(const [id,a]of this.map){const e=live.get(id);if(!e||!e.visible){a.root.visible=false;continue;}
   if(a.born<0)a.born=t;
   if(!e.alive){if(a.dead<0)a.dead=t;const f=(t-a.dead)/.85;a.root.visible=f<1;a.root.scale.setScalar(a.scale*(1-.14*f)*Math.max(.01,1-Math.max(0,f-.65)/.35));a.root.position.y=e.y-Math.min(f,.65)*1.8;a.root.rotation.x=-f*.9;a.root.rotation.z=f*.55;continue;}
   a.root.visible=true;const f=Math.min(1,(t-a.born)/.5);a.root.scale.setScalar(a.scale*(.15+.85*f));a.root.position.set(e.x,e.y,e.z);
   a.root.rotation.set(Math.sin(t*2)*.03,Math.atan2(this.world.camera.position.x-e.x,this.world.camera.position.z-e.z),Math.sin(t*1.3)*.025);
   if(e.dodging)a.root.rotation.z+=Math.sin(t*18)*.3;
   if(e.kind==='dragonfly'){a.root.rotation.x=.3+Math.sin(t*3)*.08+(e.incoming?-.45:0);a.root.rotation.y+=.35+Math.sin(t*1.8)*.18;a.root.traverse(o=>{if(o.userData.dragonWing){const {side,pair}=o.userData.dragonWing;o.rotation.z=side*(.28+Math.sin(t*(e.incoming?72:43)+pair*.6)*.4);}if(o.userData.demonEye){o.material.emissive.set(e.incoming?0xff183b:0x53bc98);o.material.emissiveIntensity=e.incoming?3.5:.6;}});}
   for(const child of a.root.children){if(child.userData.flap)child.rotation.z=child.userData.flap*Math.sin(t*4)*.3;if(child.userData.segment!==undefined)child.position.x+=Math.sin(t*3+child.userData.segment*.5)*dt*.45;}a.hit=Math.max(0,a.hit-dt*5);a.glow.material.opacity=.1+a.hit*.35+(e.incoming?.12:0)+(e.shielded?.12:0);a.glow.material.color.set(e.shielded?0x8294ff:e.incoming?0xff7654:id===state.targetId?0xade8d0:0x789fbc);
   for(const {wing,sign}of a.wings){wing.rotation.y=sign*(.3+Math.sin(t*(e.kind==='shade'?8:4))*.45);wing.rotation.z=sign*Math.sin(t*3)*.15;}
  }
 }
 project(camera,w,h){const labels=[];for(const [id,a]of this.map){if(!a.root.visible||a.dead>=0)continue;const p=a.root.position.clone().add(V(0,a.scale*3.4,0)).project(camera);if(p.z<1&&p.z>0&&Math.abs(p.x)<1.15&&Math.abs(p.y)<1.15)labels.push({id,x:(p.x*.5+.5)*w,y:(-.5*p.y+.5)*h});}return labels;}
}
