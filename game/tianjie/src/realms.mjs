import {LAKE_OFFSET} from './bridge-route.mjs';
import * as T from 'three';
export function specialEnemy(world,e){
 const group=new T.Group(),bronze=new T.MeshStandardMaterial({color:0x937f57,metalness:.78,roughness:.4}),glass=new T.MeshPhysicalMaterial({color:0x86cbd1,metalness:.75,roughness:.15,transparent:true,opacity:.88,clearcoat:1}),fire=new T.MeshBasicMaterial({color:0xffaa54,toneMapped:false});
 const mesh=(g,m,x=0,y=0,z=0,s=1,sy=s,sz=s)=>{const o=new T.Mesh(g,m);o.position.set(x,y,z);o.scale.set(s,sy,sz);group.add(o);return o;};
 if(['reflection','mirror'].includes(e.kind)){
  mesh(new T.OctahedronGeometry(1,0),glass,0,.6,0,e.kind==='mirror'?1.2:.9,1.6,.48);
  for(let i=0;i<7;i++){const a=i*Math.PI*2/7;const shard=mesh(new T.OctahedronGeometry(.4,0),glass,Math.cos(a)*1.7,.6+Math.sin(a)*1.7,0,.6,1.8,.3);shard.rotation.z=a;}
  const ring=mesh(new T.TorusGeometry(1.9,.04,8,64),bronze,0,.6,-.1);ring.rotation.y=.3;
  mesh(new T.IcosahedronGeometry(.23,1),new T.MeshBasicMaterial({color:0xd0fff3}),0,.7,.6);
 }else if(e.kind==='manta'){
  const dark=new T.MeshStandardMaterial({color:0x236176,roughness:.4,metalness:.55,side:T.DoubleSide});
  mesh(new T.SphereGeometry(1,24,16),dark,0,.5,0,.7,.35,1.7);
  for(const sign of [-1,1]){const shape=new T.Shape();shape.moveTo(0,0);shape.quadraticCurveTo(sign*1.6,1.3,sign*3.3,.25);shape.quadraticCurveTo(sign*2.1,-.5,0,-.4);const wing=mesh(new T.ShapeGeometry(shape,24),dark,0,.5,0);wing.rotation.x=-Math.PI/2;wing.userData.flap=sign;}
  world.tube([[0,.4,-1],[0,.25,-2.3],[.5,.4,-3.4],[.9,.8,-4.6]],.05,bronze,group);
  for(const sign of [-1,1])mesh(new T.SphereGeometry(.08,12,8),fire,sign*.25,.72,1.05);
 }else if(e.kind==='dragonfly'){
  const shell=new T.MeshPhysicalMaterial({color:0x70c7b5,metalness:.58,roughness:.22,clearcoat:1,iridescence:.9,iridescenceIOR:1.35});
  const wingMat=new T.MeshPhysicalMaterial({color:0xc1e9df,roughness:.13,metalness:.18,transparent:true,opacity:.68,side:T.DoubleSide,iridescence:1,depthWrite:false});
  mesh(new T.SphereGeometry(1,24,16),shell,0,.7,0,.38,.4,.85);
  for(let i=0;i<9;i++){const part=mesh(new T.SphereGeometry(1,14,10),i%3===0?bronze:shell,0,.65-i*.035,-.7-i*.34,.22-i*.014,.2-i*.012,.28);part.userData.segment=i;}
  mesh(new T.SphereGeometry(.42,24,16),shell,0,.8,.85,1,.9,1);
  for(const side of [-1,1]){
   const eye=mesh(new T.IcosahedronGeometry(.23,2),new T.MeshStandardMaterial({color:0x9edfc3,emissive:0x53bc98,emissiveIntensity:.6,roughness:.24}),side*.3,.94,1.03);eye.userData.demonEye=true;
   for(let pair=0;pair<2;pair++){
    const pivot=new T.Group();pivot.position.set(side*.16,.86,.35-pair*.95);pivot.rotation.x=.23;pivot.userData.dragonWing={side,pair};group.add(pivot);
    const shape=new T.Shape();shape.moveTo(0,0);shape.bezierCurveTo(side*.9,.55,side*2.8,.65,side*3.3,.08);shape.bezierCurveTo(side*2.9,-.5,side*.8,-.45,0,0);
    const wing=new T.Mesh(new T.ShapeGeometry(shape,28),wingMat);wing.rotation.x=-Math.PI/2;pivot.add(wing);
    for(let j=0;j<7;j++){const f=(j+1)/8;world.tube([[0,0,0],[side*1.4,.015,(f-.5)*.54],[side*(2.4+f*.65),.02,(f-.5)*.25]],.009,bronze,pivot);}
   }
   for(let i=0;i<3;i++)world.tube([[side*.23,.45,.3-i*.4],[side*.55,-.05,.6-i*.45],[side*.8,-.25,.9-i*.5]],.025,bronze,group);
  }
 }else if(e.kind==='golem'){
  for(const [x,y,z,sx,sy,sz]of [[0,.6,0,1,1.25,.55],[0,2,0,.7,.6,.7],[-1.1,.7,0,.65,.8,.6],[1.1,.7,0,.65,.8,.6],[-.5,-.9,0,.45,.7,.5],[.5,-.9,0,.45,.7,.5]])mesh(new T.IcosahedronGeometry(1,1),world.materials.darkStone,x,y,z,sx,sy,sz);
  for(const sign of [-1,1])mesh(new T.BoxGeometry(.24,.08,.1),fire,sign*.25,2.12,.6);mesh(new T.OctahedronGeometry(.35),fire,0,.8,.58,1,1.4,1);
 }else if(e.kind==='phoenix'){
  const red=new T.MeshStandardMaterial({color:0x6f2d24,metalness:.5,roughness:.44,emissive:0x682b0e,emissiveIntensity:.5});
  mesh(new T.SphereGeometry(1,20,12),red,0,.7,0,.5,.7,.9);mesh(new T.ConeGeometry(.2,.65,6),bronze,0,1.4,.9).rotation.x=Math.PI/2;
  for(const sign of [-1,1])for(let i=0;i<7;i++){const feather=mesh(new T.ConeGeometry(.18,2.2-i*.1,6),i%2?red:bronze,sign*(.9+i*.23),.6-i*.11,0,.9,1,.4);feather.rotation.z=-sign*(.55+i*.08);}
  for(let i=0;i<4;i++)world.tube([[0,.1,-.5],[(i-1.5)*.35,-.7,-1.3],[(i-1.5)*.7,-1.5,-2.4]],.065,i%2?fire:bronze,group);
 }else if(e.kind==='thunderlord'){
  mesh(new T.ConeGeometry(1.35,3.5,8),bronze,0,.3,0);mesh(new T.IcosahedronGeometry(.6,1),bronze,0,2.5,.1);
  for(let i=0;i<5;i++){const a=i*Math.PI*2/5;const spoke=mesh(new T.ConeGeometry(.13,1.2,5),fire,Math.cos(a)*.65,3+Math.sin(a)*.5,-.2);spoke.rotation.z=-a;}
  for(const sign of [-1,1]){world.tube([[sign*.7,1.4,0],[sign*1.6,1.1,0],[sign*2.2,1.7,.4]],.14,bronze,group);mesh(new T.OctahedronGeometry(.45),new T.MeshBasicMaterial({color:0xb5a2ff}),sign*2.2,1.7,.4);}
  mesh(new T.TorusGeometry(2.3,.06,8,80),fire,0,1,-.8);
 }else return null;
 group.userData.special=true;return group;
}
export function buildRealms(world){
 const M=world.materials;world.realmGroups=[];
 // Mirror lake: a jade path over dark reflective water, hanging mirror disks and pale columns.
 const lake=new T.Group();lake.position.set(LAKE_OFFSET.x,LAKE_OFFSET.y,LAKE_OFFSET.z);lake.visible=false;world.scene.add(lake);world.realmGroups[2]=lake;
 const water=new T.Mesh(new T.PlaneGeometry(110,70),new T.MeshPhysicalMaterial({color:0x2a666d,roughness:.06,metalness:.65,clearcoat:1,transparent:true,opacity:.94}));water.rotation.x=-Math.PI/2;water.position.set(0,-.35,-122);lake.add(water);world.lakeWater=water;world.waterRipples=[];
 world.box(M.stone,0,-.45,-118,9,.8,37,lake);const white=new T.MeshStandardMaterial({color:0x9cbea9,map:M.stone.map,normalMap:M.stone.normalMap,roughness:.58});world.box(white,0,.005,-118,9,.06,37,lake);
 for(const x of [-9,9])for(let z=-105;z>=-136;z-=9){world.cylinder(white,.38,.52,7,x,3.1,z,lake,20);world.cylinder(M.metal,.65,.65,.14,x,6.7,z,lake,20);const disk=new T.Mesh(new T.TorusGeometry(1.5,.08,8,48),M.metal);disk.position.set(x,4.8,z);disk.rotation.y=x<0?.6:-.6;lake.add(disk);}
 for(let i=0;i<7;i++){const ring=new T.Mesh(new T.RingGeometry(2.5+i*1.1,2.52+i*1.1,64),new T.MeshBasicMaterial({color:0x90d2bf,transparent:true,opacity:.11,side:T.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.set((i%2?1:-1)*12,-.31,-113-i*3);lake.add(ring);world.waterRipples.push(ring);}
 // Thunder prison: broken basalt dais, lava fissures, chains and high lightning rods.
 const storm=new T.Group();storm.visible=false;world.scene.add(storm);world.realmGroups[3]=storm;
 world.cylinder(M.darkStone,15,17,3,0,-1.6,-170,storm,32);world.box(M.darkStone,0,-.15,-157,9,.5,22,storm);
 const lava=new T.MeshBasicMaterial({color:0xfa783e,toneMapped:false});for(let i=0;i<14;i++){const a=i*Math.PI*2/14,x=Math.cos(a)*18,z=-170+Math.sin(a)*18;const pillar=world.mesh(new T.IcosahedronGeometry(1,1),M.darkStone,x,3,z,1.2,4+i%4,1.2,storm);pillar.rotation.z=(i%3-1)*.12;world.box(M.metal,x,7+i%3,z,.12,3,.12,storm);}
 for(let i=0;i<6;i++){const a=i*Math.PI/3;world.tube([[Math.cos(a)*2,.02,-170+Math.sin(a)*2],[Math.cos(a)*7,.02,-170+Math.sin(a)*7],[Math.cos(a+.1)*13,.02,-170+Math.sin(a+.1)*13]],.045,lava,storm);}
 const rune=new T.Mesh(new T.PlaneGeometry(25,25),new T.MeshBasicMaterial({map:world.runes,color:0xab7cde,transparent:true,opacity:.3,blending:T.AdditiveBlending,depthWrite:false}));rune.rotation.x=-Math.PI/2;rune.position.set(0,.03,-170);storm.add(rune);
 world.realmRune=rune;
}
