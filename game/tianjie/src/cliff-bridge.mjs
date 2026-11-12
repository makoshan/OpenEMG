import * as T from 'three';
import {BRIDGE,deckHeight,bridgePoint,bridgeYaw,PAVILION_ANCHOR} from './bridge-route.mjs';
export function buildCloudBridge(world){
 const M=world.materials,group=new T.Group();group.name='cliff-suspension-bridge';world.bridgeGroup=group;world.scene.add(group);
 // The gate's stone threshold ends here; no platform extends beneath the span.
 world.box(M.stone,0,.85,-33,5.8,1.4,5.4,group);
 for(const [x,z,w,d] of [[0,-23,18,10],[-19,-45,7,5],[20,-66,8,6]]){
  const cliff=world.mesh(new T.IcosahedronGeometry(1,2),M.stone,x,-29,z,w,31,d,group);cliff.rotation.y=.12;
  world.mesh(new T.IcosahedronGeometry(1,1),M.darkStone,x,-51,z,w*.7,20,d*.7,group);
 }
 // A small rock anchorage meets the painted cliff beneath the ORIGINAL pavilion.
 const end=PAVILION_ANCHOR;
 world.mesh(new T.IcosahedronGeometry(1,2),M.stone,end.x,end.y-4,end.z+1,3.5,4,4,group);
 const grain=document.createElement('canvas');grain.width=512;grain.height=128;const ctx=grain.getContext('2d');
 ctx.fillStyle='#78634b';ctx.fillRect(0,0,512,128);
 for(let i=0;i<180;i++){ctx.strokeStyle=i%3?'#322b2530':'#c0a17b38';ctx.lineWidth=i%4===0?2:.7;ctx.beginPath();for(let x=0;x<=512;x+=16){const y=(i*.73)%128+Math.sin(x*.023+i)*1.4;x?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();}
 const texture=new T.CanvasTexture(grain);texture.colorSpace=T.SRGBColorSpace;
 const wood=new T.MeshStandardMaterial({map:texture,color:0xa9a292,roughness:.95});
 const rope=new T.MeshStandardMaterial({color:0xa18c65,roughness:1});
 const count=Math.ceil((BRIDGE.start-BRIDGE.end)/.46)+1,boards=new T.InstancedMesh(new T.BoxGeometry(1,.14,.43),wood,count),dummy=new T.Object3D();
 for(let i=0;i<count;i++){
  const z=BRIDGE.start+(BRIDGE.end-BRIDGE.start)*i/(count-1);
  const p=bridgePoint(z,Math.sin(i*7.1)*.025,-.07);dummy.position.set(p.x,p.y,p.z);
  dummy.rotation.set(Math.atan((deckHeight(z-.05)-deckHeight(z+.05))/.1),bridgeYaw(z)+Math.sin(i*9)*.013,Math.sin(i*5)*.012);
  dummy.scale.set(BRIDGE.width+Math.sin(i*17)*.09,1,1);dummy.updateMatrix();boards.setMatrixAt(i,dummy.matrix);
  boards.setColorAt(i,new T.Color().setScalar(.76+(Math.sin(i*19)+1)*.12));
 }
 boards.castShadow=true;boards.receiveShadow=true;group.add(boards);
 for(const x of [-.79,.79]){
  for(const height of [-.19,.52,1.22])world.tube(Array.from({length:49},(_,i)=>{const z=BRIDGE.start+(BRIDGE.end-BRIDGE.start)*i/48;const p=bridgePoint(z,x,height);return [p.x,p.y,p.z];}),height===1.22?.055:.035,rope,group);
  const n=Math.ceil((BRIDGE.start-BRIDGE.end)/1.4)+1,hangers=new T.InstancedMesh(new T.CylinderGeometry(.025,.025,1.45,6),rope,n);
  for(let i=0;i<n;i++){const z=BRIDGE.start+(BRIDGE.end-BRIDGE.start)*i/(n-1),p=bridgePoint(z,x,.5);dummy.position.set(p.x,p.y,p.z);dummy.rotation.set(0,0,Math.sin(i*7)*.025);dummy.scale.set(1,1,1);dummy.updateMatrix();hangers.setMatrixAt(i,dummy.matrix);}group.add(hangers);
  for(const z of [BRIDGE.start+.3,BRIDGE.end-.3]){
   const p=bridgePoint(z,x);world.cylinder(M.woodLight,.13,.17,3,p.x,p.y+1,p.z,group);
   for(const y of [p.y+.35,p.y+1.2])world.cylinder(rope,.18,.18,.15,p.x,y,p.z,group);
   world.mesh(new T.SphereGeometry(.18,8,8),M.metal,p.x,p.y+2.5,p.z,1,1,1,group);
  }
 }
 for(const x of [-2.4,2.4])world.lantern(x,-32.5);
 // Distant needle peaks frame a deep, empty cleft rather than a flat floor.
 for(let i=0;i<12;i++){const side=i%2?1:-1;const x=side*(15+(i%4)*7),z=-42-i*4;
  world.mesh(new T.IcosahedronGeometry(1,1),i%2?M.stone:M.darkStone,x,-20-i%3*8,z,3+i%3,21+i%4*5,4,group);
 }
 const c=document.createElement('canvas');c.width=c.height=256;const g=c.getContext('2d');
 const gradient=g.createRadialGradient(128,128,0,128,128,128);gradient.addColorStop(0,'#c6dfdf50');gradient.addColorStop(1,'#c6dfdf00');g.fillStyle=gradient;g.fillRect(0,0,256,256);
 const cloudTexture=new T.CanvasTexture(c);world.clouds=[];
 for(let i=0;i<24;i++){const sprite=new T.Sprite(new T.SpriteMaterial({map:cloudTexture,color:0xb6d0d5,transparent:true,opacity:.58,depthWrite:false}));sprite.position.set((i%2?1:-1)*(4+i%5*5),-9-i%4*5,-35-i*2.5);sprite.scale.set(29,8,1);group.add(sprite);world.clouds.push(sprite);}
}
