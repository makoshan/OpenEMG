import {AscensionEnding} from './ending.mjs';
import {buildArt,updateArt} from './art-direction.mjs';
import {initCombatFX,handCast,deathBurst,updateCombatFX,clearCombatFX} from './combat-fx.mjs';
import {buildPavilionPassage} from './pavilion-passage.mjs';
import {buildRealms} from './realms.mjs';
import {ENCOUNTERS} from './encounters.mjs';
import {lightning} from './spells.mjs';
import {Actors} from './actors.mjs';
import {buildCloudBridge} from './cliff-bridge.mjs';
import {BRIDGE,deckHeight,bridgeCenterX,gateJourney,lakeJourney,LAKE_OFFSET} from './bridge-route.mjs';
import {skinMaterial,refineHand,createNails,updateNails} from './hand-detail.mjs';
import {GESTURES} from './gestures.mjs';
import {swordMesh,swordWake,thunder,updateSpells,disposeEffect} from './spells.mjs';
import * as T from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const TAU=Math.PI*2, jade=0x63b7ff, gold=0xf6bd72;
const rng=(seed=>()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;})(71827);
const v3=(x=0,y=0,z=0)=>new T.Vector3(x,y,z);
function canvasTexture(size, draw){const c=document.createElement('canvas');c.width=c.height=size;draw(c.getContext('2d'),size);const t=new T.CanvasTexture(c);t.colorSpace=T.SRGBColorSpace;return t;}
function glowTexture(){return canvasTexture(128,(c,s)=>{const g=c.createRadialGradient(s/2,s/2,0,s/2,s/2,s/2);g.addColorStop(0,'#fff');g.addColorStop(.1,'#ffffffdd');g.addColorStop(.4,'#ffffff44');g.addColorStop(1,'#ffffff00');c.fillStyle=g;c.fillRect(0,0,s,s);});}
function runeTexture(){return canvasTexture(1024,(c,s)=>{c.translate(s/2,s/2);c.strokeStyle='#b1efd5';c.fillStyle='#b1efd5';c.lineWidth=2.5;
 for(const r of [476,458,389,370,237]){c.beginPath();c.arc(0,0,r,0,TAU);c.stroke();}
 for(let i=0;i<96;i++){const a=i*TAU/96;c.save();c.rotate(a);c.fillRect(-1,422,2,i%4?14:29);c.restore();}
 const chars=['乾','坤','震','巽','坎','离','艮','兑'];c.font='38px serif';c.textAlign='center';c.textBaseline='middle';
 for(let i=0;i<8;i++){c.save();c.rotate(i*Math.PI/4);c.fillText(chars[i],0,-327);for(let j=0;j<3;j++){if((i>>j)&1){c.fillRect(-35,-290+j*12,26,5);c.fillRect(9,-290+j*12,26,5);}else c.fillRect(-35,-290+j*12,70,5);}c.restore();}
 for(let r=0;r<2;r++){c.save();c.rotate(r*Math.PI/4);c.strokeRect(-164,-164,328,328);c.restore();}
 c.lineWidth=4;c.beginPath();c.moveTo(0,-185);c.lineTo(75,-75);c.lineTo(0,0);c.lineTo(-75,75);c.lineTo(0,185);c.stroke();c.beginPath();c.arc(0,0,190,0,TAU);c.stroke();
 });}
export class World {
  constructor(container,onProgress=()=>{}){
    this.container=container;this.onProgress=onProgress;this.scene=new T.Scene();this.scene.background=new T.Color(0x526674);this.scene.fog=new T.Fog(0x41555d,38,140);
    this.camera=new T.PerspectiveCamera(58,innerWidth/innerHeight,.06,600);this.camera.position.set(1.5,2.6,16);
    this.renderer=new T.WebGLRenderer({antialias:true,powerPreference:'high-performance'});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));this.renderer.setSize(innerWidth,innerHeight);
    this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=T.PCFShadowMap;this.renderer.toneMapping=T.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.12;this.renderer.outputColorSpace=T.SRGBColorSpace;
    container.appendChild(this.renderer.domElement);this.renderer.domElement.setAttribute('aria-label','实时三维山门场景');
    this.composer=new EffectComposer(this.renderer);this.composer.addPass(new RenderPass(this.scene,this.camera));this.bloom=new UnrealBloomPass(new T.Vector2(innerWidth,innerHeight),.48,.6,1.05);this.composer.addPass(this.bloom);this.composer.addPass(new OutputPass());
    this.loader=new T.TextureLoader();this.geo={box:new T.BoxGeometry(1,1,1),sphere:new T.SphereGeometry(1,24,16),rock:new T.IcosahedronGeometry(1,1)};
    this.thunderPaper=canvasTexture(512,(c,s)=>{c.fillStyle='#d8aa58';c.fillRect(0,0,s,s);c.strokeStyle='#713321';c.lineWidth=10;c.strokeRect(24,16,464,480);c.fillStyle='#57243a';c.font='bold 86px serif';c.textAlign='center';[...'五雷敕令'].forEach((ch,i)=>c.fillText(ch,256,110+i*108));});this.guardPaper=canvasTexture(512,(c,s)=>{c.fillStyle='#e7b35d';c.fillRect(0,0,s,s);c.strokeStyle='#a2491d';c.lineWidth=8;c.strokeRect(22,16,468,480);c.fillStyle='#8c3618';c.font='bold 84px serif';c.textAlign='center';[...'护身敕令'].forEach((ch,i)=>c.fillText(ch,256,110+i*108));});this.glow=glowTexture();this.runes=runeTexture();this.emitters=[];this.ribbons=[];this.lanterns=[];this.particles=[];this.projectiles=[];this.ripples=[];this.spellEffects=[];
    this.move=v3();this.position=v3(0,1.75,13);this.yaw=0;this.pitch=0;this.dragging=false;this.shake=0;this.recoil=0;this.handMode='idle';this.handUntil=0;this.bandPose='';this.bandTilt={pitch:0,roll:0};this.time=0;this.startBlend=0;this.failedAssets=[];
    this.viewScene=new T.Scene();this.viewCamera=new T.PerspectiveCamera(53,innerWidth/innerHeight,.01,8);this.viewScene.add(this.viewCamera);
    this.handFill=new T.HemisphereLight(0x98baff,0x302019,1.1);this.viewScene.add(this.handFill);this.handKey=new T.DirectionalLight(0xffbc83,2.2);this.handKey.position.set(-2,3,2);this.viewScene.add(this.handKey);const rim=new T.DirectionalLight(0x74bcff,.9);rim.position.set(2,1,-3);this.viewScene.add(rim);
    this.handRig=new T.Group();this.handRig.scale.setScalar(.82);this.viewCamera.add(this.handRig);this.handRig.position.set(.29,-.35,-.67);
    this.handLight=new T.PointLight(jade,0,2);this.handLight.position.set(.1,.15,-.1);this.handRig.add(this.handLight);
    window.addEventListener('resize',()=>this.resize());
  }
  async texture(name,repeat=1){try{const t=await this.loader.loadAsync('./assets/'+name);t.wrapS=t.wrapT=T.RepeatWrapping;t.repeat.set(repeat,repeat);t.anisotropy=Math.min(8,this.renderer.capabilities.getMaxAnisotropy());if(name.includes('color')||name.includes('sky'))t.colorSpace=T.SRGBColorSpace;return t;}catch(e){this.failedAssets.push(name);return null;}}
  async init(){
    this.onProgress('正在铺设石庭与远山…');
    const [floor,floorN,floorR,rock,rockN,rockR,sky]=await Promise.all([this.texture('floor-color.jpg',12),this.texture('floor-normal.jpg',12),this.texture('floor-rough.jpg',12),this.texture('rock-color.jpg',2),this.texture('rock-normal.jpg',2),this.texture('rock-rough.jpg',2),this.texture('sky-mountains.png')]);
    this.materials={
      stone:new T.MeshStandardMaterial({color:0x8a9691,map:rock,normalMap:rockN,roughnessMap:rockR,roughness:.85,normalScale:new T.Vector2(.6,.6)}),
      floor:new T.MeshPhysicalMaterial({color:0x9caeaa,map:floor,normalMap:floorN,roughnessMap:floorR,roughness:.55,metalness:.08,clearcoat:.8,clearcoatRoughness:.22,normalScale:new T.Vector2(.8,.8)}),
      darkStone:new T.MeshStandardMaterial({color:0x374944,map:rock,normalMap:rockN,roughness:.8}),
      wood:new T.MeshStandardMaterial({color:0x532c23,roughness:.7}),woodLight:new T.MeshStandardMaterial({color:0x86503a,roughness:.7}),
      metal:new T.MeshStandardMaterial({color:0x9d8051,metalness:.7,roughness:.4}), roof:new T.MeshStandardMaterial({color:0x2e4b4f,roughness:.66,metalness:.15}),
      light:new T.MeshStandardMaterial({color:0xffc98c,emissive:0xffa84d,emissiveIntensity:2.3,roughness:.5}),
      cloth:new T.MeshStandardMaterial({color:0x152d31,roughness:.8,side:T.DoubleSide}),
      energy:new T.MeshBasicMaterial({color:jade,toneMapped:false}), fire:new T.MeshBasicMaterial({color:gold,toneMapped:false})
    };
    if(sky){const bg=new T.Mesh(new T.SphereGeometry(290,48,32),new T.MeshBasicMaterial({map:sky,fog:false,toneMapped:false,side:T.BackSide}));bg.position.y=25;this.scene.add(bg);this.skyMaterial=bg.material;this.skyDome=bg;bg.material.transparent=true;bg.material.depthWrite=false;bg.renderOrder=-1000;
      const env=sky.clone();env.mapping=T.EquirectangularReflectionMapping;env.needsUpdate=true;this.scene.environment=env;this.scene.environmentIntensity=.35;
    }
    this.lighting();this.courtyard();this.temple(0,-27,1.15,true);this.temple(-26,-30,.58);this.temple(27,-35,.62);this.gate();this.landscape();this.buildGateDoors();this.buildEnemy();this.actors=new Actors(this);buildCloudBridge(this);buildRealms(this);buildPavilionPassage(this);this.buildAmbient();
    this.onProgress('正在唤醒剑诀与护身印…');await this.buildHand();await buildArt(this);this.ending=new AscensionEnding(this);await this.ending.init();this.onProgress('山门已开');this.resize();
  }
  mesh(geo,mat,x=0,y=0,z=0,sx=1,sy=sx,sz=sx,parent=this.scene){const m=new T.Mesh(geo,mat);m.position.set(x,y,z);m.scale.set(sx,sy,sz);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;}
  box(mat,x,y,z,sx,sy,sz,parent){return this.mesh(this.geo.box,mat,x,y,z,sx,sy,sz,parent);}
  cylinder(mat,rt,rb,height,x,y,z,parent=this.scene,segments=12){return this.mesh(new T.CylinderGeometry(rt,rb,height,segments),mat,x,y,z,1,1,1,parent);}
  tube(points,r,mat,parent=this.scene){const c=new T.CatmullRomCurve3(points.map(p=>Array.isArray(p)?v3(...p):p));return this.mesh(new T.TubeGeometry(c,Math.max(12,points.length*6),r,6,false),mat,0,0,0,1,1,1,parent);}
  lighting(){
    this.hemi=new T.HemisphereLight(0xb5d4e7,0x202c40,2.1);this.scene.add(this.hemi);
    const sun=this.sun=new T.DirectionalLight(0xffd8a2,3.5);sun.position.set(22,35,-16);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-30,right:30,top:32,bottom:-28,near:1,far:100});sun.shadow.normalBias=.05;sun.shadow.bias=-.0002;this.scene.add(sun);sun.target.position.set(0,0,-10);this.scene.add(sun.target);
    const fill=this.fill=new T.DirectionalLight(0x8bb9d1,1);fill.position.set(-20,12,15);this.scene.add(fill);
    this.enemyLight=new T.PointLight(0xe6a062,22,18,2);this.enemyLight.position.set(0,4,-8);this.scene.add(this.enemyLight);
  }
  courtyard(){
    const M=this.materials;
    this.box(M.stone,0,-1.25,-4,36,2.4,55);this.box(M.darkStone,0,-.17,-4,36.7,.22,55.7);
    const floor=this.mesh(new T.PlaneGeometry(35.8,55,1,1),M.floor,0,-.04,-4);floor.rotation.x=-Math.PI/2;
    const trim=new T.MeshStandardMaterial({color:0x6c786a,metalness:.25,roughness:.6});
    for(const x of [-17,17]){
      this.box(M.stone,x,.12,-4,.9,.3,54);
      for(let z=-29;z<=21;z+=3.4){this.box(M.stone,x,1,z,.42,1.8,.42);this.box(trim,x,1.95,z,.68,.18,.68);this.mesh(new T.SphereGeometry(.24,8,6),M.stone,x,2.15,z);}
      for(const y of [.5,1.4])this.box(M.stone,x,y,-4,.19,.17,52);
    }
    for(let z=-24;z<18;z+=4){for(const x of [-13.3,13.3]){this.box(M.darkStone,x,.01,z,2,.12,2.5);this.box(M.stone,x,.08,z,1.65,.12,2.15);}}
    for(let i=0;i<8;i++)this.box(M.stone,0,i*.2,-18-i*.7,14-i*.25,.28,.8);
    const sealMat=new T.MeshBasicMaterial({map:this.runes,transparent:true,opacity:.55,depthWrite:false,blending:T.AdditiveBlending,color:0x92c5a9,toneMapped:false});
    this.groundSeal=new T.Mesh(new T.PlaneGeometry(14,14),sealMat);this.groundSeal.rotation.x=-Math.PI/2;this.groundSeal.position.set(0,.012,-6);this.scene.add(this.groundSeal);
    const puddleMat=new T.MeshPhysicalMaterial({color:0x6a8790,roughness:.04,metalness:.45,transparent:true,opacity:.24,clearcoat:1,depthWrite:false});
    for(let i=0;i<20;i++){const p=this.mesh(new T.CircleGeometry(1,24),puddleMat,(rng()-.5)*27,.008,(rng()-.5)*36-3,1+rng()*2,1,1);p.rotation.x=-Math.PI/2;p.scale.y=.3+rng()*.6;p.castShadow=false;}
    for(const x of [-10.7,10.7])for(const z of [-17,-7,5,16])this.lantern(x,z);
    for(let i=0;i<35;i++){const x=(rng()<.5?-1:1)*(12+rng()*4),z=rng()*48-28;this.mesh(this.geo.rock,M.darkStone,x,.02,z,.2+rng()*.5,.1+rng()*.3,.3+rng()*.4).rotation.y=rng()*TAU;}
  }
  roof(parent,y,width,depth,height){
    const sx=40,sz=18,pos=[],uv=[],idx=[];
    const roofY=(u,v)=>height*(1-Math.abs(v))*.9-height*.4*Math.max(0,(Math.abs(u)-.62)/.38)+Math.pow(Math.abs(u),6)*.55+Math.pow(Math.abs(v),8)*.45;
    for(let i=0;i<=sz;i++)for(let j=0;j<=sx;j++){const u=j/sx*2-1,v=i/sz*2-1;pos.push(u*width/2,roofY(u,v)+y,v*depth/2);uv.push(j/sx*8,i/sz*4);}
    for(let i=0;i<sz;i++)for(let j=0;j<sx;j++){const a=i*(sx+1)+j;idx.push(a,a+1,a+sx+1,a+1,a+sx+2,a+sx+1);}
    const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(pos,3));g.setAttribute('uv',new T.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();
    const m=this.mesh(g,this.materials.roof,0,0,0,1,1,1,parent);m.material.side=T.DoubleSide;
    for(const v of [-1,1])this.tube(Array.from({length:17},(_,i)=>{const u=i/8-1;return[u*width/2,y+roofY(u,v),v*depth/2];}),.065,this.materials.metal,parent);
    this.tube([[-width*.48,y+height*.75,0],[-width*.28,y+height*.94,0],[0,y+height*.9,0],[width*.28,y+height*.94,0],[width*.48,y+height*.75,0]],.12,this.materials.roof,parent);
    // Rows of dimensional roof tiles catch the grazing sunset.
    const tileGeo=new T.CylinderGeometry(.075,.075,depth/2*.95,5,1,true);const tiles=new T.InstancedMesh(tileGeo,this.materials.roof,Math.floor(width/.22)*2);const dummy=new T.Object3D();let count=0;
    for(let x=-width/2+.12;x<width/2-.1;x+=.22)for(const sign of [-1,1]){const u=x/(width/2);dummy.position.set(x,y+roofY(u,.5),sign*depth*.25);dummy.rotation.set(sign*(Math.PI/2+Math.atan(height*.9/(depth/2))),0,0);dummy.updateMatrix();if(count<tiles.count)tiles.setMatrixAt(count++,dummy.matrix);}
    tiles.count=count;tiles.castShadow=true;parent.add(tiles);
  }
  temple(x,z,scale,passage=false){
    const g=new T.Group();g.position.set(x,1.5,z);g.rotation.y=Math.PI;g.scale.setScalar(scale);this.scene.add(g);const M=this.materials;
    this.box(M.stone,0,passage?-.25:0,0,18,passage?.5:.8,10,g);
    if(passage){for(const side of [-1,1])this.box(M.wood,side*4.85,3,1,5.3,5.5,7,g);this.box(M.wood,0,5.35,1,4.4,.8,7,g);}
    else this.box(M.wood,0,3,1,15,5.5,7,g);
    for(const xx of (passage?[-7,-3.5,3.5,7]:[-7,-3.5,0,3.5,7])){
      this.cylinder(M.woodLight,.2,.26,5.8,xx,3.1,-3.6,g);this.cylinder(M.metal,.3,.32,.2,xx,.55,-3.6,g);this.cylinder(M.metal,.25,.25,.12,xx,5.4,-3.6,g);
      for(let j=0;j<3;j++)this.box(M.woodLight,xx,5.4+j*.17,-3.6,.9+j*.4,.13,.4,g);
    }
    for(const xx of (passage?[-5.3,5.3]:[-5.3,-1.8,1.8,5.3])){
      this.box(new T.MeshStandardMaterial({color:0x8b6946,emissive:0xffb36b,emissiveIntensity:.18,roughness:.9}),xx,3,-2.55,2.6,3.7,.05,g);
      for(let a=-1;a<=1;a+=.33)this.box(M.wood,xx+a,3,-2.6,.055,3.8,.12,g);
      for(let yy=1.2;yy<5;yy+=.42)this.box(M.wood,xx,yy,-2.65,2.7,.06,.12,g);
    }
    this.roof(g,6,20,12,2.6);this.box(M.wood,0,8,0,10,2.4,5.5,g);this.roof(g,9.4,14,8.2,1.9);
    for(const xx of [-4.7,0,4.7])this.cylinder(M.woodLight,.15,.15,2.2,xx,8.1,-2.9,g);
    const sign=canvasTexture(512,(c,s)=>{c.fillStyle='#18302d';c.fillRect(0,0,s,s);c.strokeStyle='#ae8651';c.lineWidth=9;c.strokeRect(20,150,s-40,210);c.font='85px serif';c.textAlign='center';c.fillStyle='#d1b478';c.fillText('太 玄 观',s/2,290);});
    this.box(new T.MeshStandardMaterial({map:sign,roughness:.65}),0,5,-3.8,4.6,1.3,.14,g);
  }
  gate(){
    const g=new T.Group();g.position.set(0,0,20.8);this.scene.add(g);const M=this.materials;
    for(const x of [-12,12]){this.box(M.stone,x,1.5,0,1.8,3,1.8,g);this.cylinder(M.wood,.43,.55,8,x,6.6,0,g);this.cylinder(M.metal,.58,.58,.2,x,3.1,0,g);}
    this.box(M.wood,0,10.1,0,27,.7,.9,g);this.roof(g,10.5,29,4.4,1.9);
  }
  lantern(x,z){
    const M=this.materials;this.box(M.stone,x,.3,z,.95,.6,.95);this.cylinder(M.darkStone,.15,.22,1.7,x,1.35,z);this.box(M.metal,x,2.3,z,.7,.12,.7);
    const body=this.mesh(new T.CylinderGeometry(.34,.28,.7,8),M.light,x,2.7,z);this.lanterns.push(body);
    for(let i=0;i<8;i++){const a=i*TAU/8;this.box(M.wood,x+Math.cos(a)*.32,2.7,z+Math.sin(a)*.32,.045,.75,.045);}
    this.cylinder(M.roof,.04,.52,.3,x,3.2,z);this.cylinder(M.metal,.08,.08,.13,x,3.42,z);
    const glow=new T.Sprite(new T.SpriteMaterial({map:this.glow,color:0xffa34b,transparent:true,opacity:.26,blending:T.AdditiveBlending,depthWrite:false}));glow.position.set(x,2.7,z);glow.scale.set(2.8,2.8,1);this.scene.add(glow);
    if(z===-7||z===5){const light=new T.PointLight(0xffad42,65,15,2);light.position.set(x,2.8,z);this.scene.add(light);}
  }
  tree(x,z,scale=1){
    const g=new T.Group();g.position.set(x,-1,z);g.scale.setScalar(scale);this.scene.add(g);
    const bark=new T.MeshStandardMaterial({color:0x343c2c,map:this.materials.stone.map,roughness:1});
    this.tube([[0,0,0],[.2,2,0],[-.3,4,.3],[.7,6,0],[.3,8,0]],.24,bark,g);
    const leaves=new T.MeshStandardMaterial({color:0xaf7f35,roughness:.95,side:T.DoubleSide});const leafGeo=new T.SphereGeometry(1,5,3);const inst=new T.InstancedMesh(leafGeo,leaves,2600);const o=new T.Object3D();
    for(let i=0;i<5;i++){const a=i*2.4;this.tube([[0,3+i*.7,0],[Math.cos(a)*1.8,4+i*.7,Math.sin(a)*1.8],[Math.cos(a)*3,4.8+i*.7,Math.sin(a)*2.6]],.12,bark,g);}
    for(let i=0;i<2600;i++){const a=rng()*TAU,r=Math.sqrt(rng())*3.4;o.position.set(Math.cos(a)*r,5+rng()*3,Math.sin(a)*r*.8);o.scale.set(.06+rng()*.12,.012+rng()*.015,.08+rng()*.14);o.rotation.set(rng(),rng()*TAU,rng());o.updateMatrix();inst.setMatrixAt(i,o.matrix);inst.setColorAt(i,new T.Color().setHSL(.09+rng()*.06,.42,.25+rng()*.18));}inst.castShadow=true;g.add(inst);
  }
  landscape(){
    const M=this.materials;
    for(let i=0;i<35;i++){const sign=i%2?1:-1;const rawX=sign*(23+rng()*70),z=-25-rng()*100,sy=8+rng()*28,x=z<-35&&Math.abs(rawX-bridgeCenterX(z))<18?bridgeCenterX(z)+sign*24:rawX;const m=this.mesh(new T.IcosahedronGeometry(1,2),M.stone,x,-10,z,4+rng()*10,sy,4+rng()*9);m.rotation.y=rng()*TAU;}
    for(const p of [[-20,6,1.2],[22,-3,1.45],[-24,-18,1.6],[25,14,1.15],[-29,-36,2]])this.tree(...p);
    const grassMat=new T.MeshStandardMaterial({color:0x657049,side:T.DoubleSide,roughness:1});const blades=new T.InstancedMesh(new T.PlaneGeometry(.08,.65),grassMat,500);const o=new T.Object3D();
    for(let i=0;i<500;i++){o.position.set((i%2?1:-1)*(15+rng()*1.5),.25,rng()*50-29);o.rotation.set(.1,rng()*TAU,rng()*.5-.25);o.scale.setScalar(.3+rng());o.updateMatrix();blades.setMatrixAt(i,o.matrix);}this.scene.add(blades);
  }
  buildGateDoors(){
    this.gateDoors=[];this.gateOpenAt=Infinity;
    for(const sign of [-1,1]){const g=new T.Group();g.position.set(sign*2.4,1.35,-22.1);this.scene.add(g);const center=-sign*1.2;this.box(this.materials.wood,center,2.25,0,2.4,4.5,.24,g);this.box(this.materials.metal,center,4.25,.14,2.35,.06,.04,g);this.box(this.materials.metal,center,.28,.14,2.35,.06,.04,g);
      for(let y=.65;y<4;y+=.6)for(let x=-.8;x<=.8;x+=.55)this.mesh(new T.SphereGeometry(.045,6,5),this.materials.metal,center+x,y,.16,1,1,1,g);
      this.gateDoors.push({g,sign});
    }
  }
  buildEnemy(){
    const g=new T.Group();g.position.set(0,2.8,-9);this.enemy=g;this.scene.add(g);const M=this.materials;
    const dark=new T.MeshStandardMaterial({color:0x182226,metalness:.38,roughness:.48});const armor=new T.MeshStandardMaterial({color:0x242933,metalness:.7,roughness:.32,map:M.stone.map});
    this.enemyMaterials=[dark,armor];
    const robeGeo=new T.CylinderGeometry(.48,1.05,2.45,32,12,true);const a=robeGeo.attributes.position;
    for(let i=0;i<a.count;i++){const x=a.getX(i),z=a.getZ(i),y=a.getY(i),angle=Math.atan2(z,x);const r=1+Math.sin(angle*11)*.085;a.setXYZ(i,x*r,y+(y<-.9?Math.sin(angle*5)*.2:0),z*r);}robeGeo.computeVertexNormals();
    this.mesh(robeGeo,M.cloth,0,-.5,0,1,1,1,g);
    this.mesh(new T.SphereGeometry(1,24,16),dark,0,.9,0,.62,.72,.38,g);
    this.mesh(new T.IcosahedronGeometry(1,1),armor,0,1.74,.06,.40,.59,.29,g);
    const face=new T.Group();face.position.set(0,1.8,.3);g.add(face);
    for(const sign of [-1,1]){
      this.tube([[sign*.15,.42,0],[sign*.43,.68,-.03],[sign*.5,1.03,-.15],[sign*.38,1.37,-.2]],.065,armor,face);
      const eye=this.box(M.fire,sign*.19,.08,.1,.2,.045,.04,face);eye.rotation.z=sign*.2;
      this.tube([[sign*.07,.18,.07],[sign*.22,.29,.02],[sign*.37,.14,-.01],[sign*.28,-.1,.04],[sign*.13,-.36,.01]],.024,M.metal,face);
      for(let i=0;i<3;i++){const shoulder=this.mesh(new T.IcosahedronGeometry(1,0),armor,sign*(.70+i*.14),1.07-i*.13,.03,.40-i*.045,.22,.43-i*.05,g);shoulder.rotation.z=sign*(-.22-i*.14);}
      const arm=this.tube([[sign*.7,.75,0],[sign*1.12,.25,.03],[sign*1.4,-.1,.22]],.14,dark,g);this.ribbons.push({obj:arm,base:arm.rotation.z,sign});
      this.mesh(new T.SphereGeometry(.17,12,8),armor,sign*1.4,-.12,.24,1,1,1,g);
      this.tube([[sign*.53,.52,.23],[sign*.78,-.2,.38],[sign*.62,-1.25,.32],[sign*1.1,-1.9,.1]],.055,M.metal,g);
    }
    this.tube([[0,2.3,.32],[0,1.9,.35],[-.06,1.72,.36],[.06,1.72,.36],[0,1.56,.32]],.022,M.metal,g);
    for(const sign of [-1,1])for(let i=0;i<4;i++){
      const plate=this.mesh(new T.IcosahedronGeometry(1,0),armor,sign*(.33+i*.1),.65-i*.54,.27,.35,.44,.18,g);plate.rotation.z=sign*(.13+i*.08);
    }
    for(const y of [.72,-.02]){const ring=new T.Mesh(new T.TorusGeometry(y>0?.23:.14,.025,8,32),M.fire);ring.position.set(0,y,.46);g.add(ring);}
    this.core=this.mesh(new T.OctahedronGeometry(.18),M.fire,0,.65,.42,1,1.4,1,g);
    this.halo=new T.Mesh(new T.PlaneGeometry(5,5),new T.MeshBasicMaterial({map:this.runes,transparent:true,opacity:.33,blending:T.AdditiveBlending,color:0xf5bd7c,depthWrite:false,side:T.DoubleSide,toneMapped:false}));this.halo.position.set(0,.6,-.5);g.add(this.halo);
    const paperTex=canvasTexture(256,(c,s)=>{c.fillStyle='#b79a5a';c.fillRect(0,0,s,s);c.strokeStyle='#593f27';c.lineWidth=8;c.strokeRect(15,12,s-30,s-24);c.font='55px serif';c.textAlign='center';c.fillStyle='#38291e';for(const [i,ch] of [...'镇山敕令'].entries())c.fillText(ch,128,65+i*54);});
    this.talismans=[];for(let i=0;i<8;i++){const p=new T.Mesh(new T.PlaneGeometry(.3,.75),new T.MeshStandardMaterial({map:paperTex,side:T.DoubleSide,color:0xdfc190,emissive:0x2c1f08,roughness:.8}));g.add(p);this.talismans.push(p);}
    this.aura=new T.Sprite(new T.SpriteMaterial({map:this.glow,color:0xefaa63,transparent:true,opacity:.13,blending:T.AdditiveBlending,depthWrite:false}));this.aura.scale.set(7,7,1);this.aura.position.y=.5;g.add(this.aura);
  }
  buildAmbient(){
    const N=240,geo=new T.BufferGeometry(),pos=new Float32Array(N*3),color=new Float32Array(N*3);this.ambientBase=[];
    for(let i=0;i<N;i++){const p=[(rng()-.5)*35,rng()*14,rng()*45-25];pos.set(p,i*3);this.ambientBase.push(p);const c=new T.Color(i%3?0xd6bb7a:0x94ddc7);color.set([c.r,c.g,c.b],i*3);}
    geo.setAttribute('position',new T.BufferAttribute(pos,3));geo.setAttribute('color',new T.BufferAttribute(color,3));this.ambient=new T.Points(geo,new T.PointsMaterial({map:this.glow,size:.1,transparent:true,opacity:.45,vertexColors:true,blending:T.AdditiveBlending,depthWrite:false}));this.scene.add(this.ambient);
    const fxgeo=new T.BufferGeometry();this.fxPositions=new Float32Array(1500*3);this.fxColors=new Float32Array(1500*3);fxgeo.setAttribute('position',new T.BufferAttribute(this.fxPositions,3));fxgeo.setAttribute('color',new T.BufferAttribute(this.fxColors,3));fxgeo.setDrawRange(0,0);this.fxPoints=new T.Points(fxgeo,new T.PointsMaterial({map:this.glow,size:.12,transparent:true,vertexColors:true,blending:T.AdditiveBlending,depthWrite:false,toneMapped:false}));this.scene.add(this.fxPoints);
  }
  async buildHand(){
    this.bones=[];
    try{
      const gltf=await new GLTFLoader().loadAsync('./assets/hand-right.glb');this.handModel=gltf.scene;
      const pivot=new T.Group();this.handRig.add(pivot);pivot.quaternion.setFromAxisAngle(v3(0,0,1),Math.PI).multiply(new T.Quaternion().setFromAxisAngle(v3(0,1,0),-Math.PI/2));pivot.scale.setScalar(1.85);
      const wrist=gltf.scene.getObjectByName('wrist');gltf.scene.position.copy(wrist.position).multiplyScalar(-1);pivot.add(gltf.scene);
      const skin=skinMaterial();
      gltf.scene.traverse(o=>{if(o.isMesh){o.geometry=refineHand(o.geometry);o.material=skin;o.frustumCulled=false;o.castShadow=false;}if(o.isBone)this.bones.push({node:o,p:o.position.clone(),q:o.quaternion.clone()});});
      this.fingerNames=['index','middle','ring','pinky'];createNails(this);
    }catch(e){this.failedAssets.push('hand-right.glb');throw new Error('手部模型未加载，请检查连接后重新载入。');}
    const cloth=new T.MeshPhysicalMaterial({color:0x0b101b,roughness:.92,sheen:.5,sheenColor:0x566078});
    const metal=new T.MeshPhysicalMaterial({color:0x080c11,metalness:0,roughness:.48,clearcoat:.12});
    const sleeveGeo=new T.CylinderGeometry(.073,.137,.52,48,20,true);const sa=sleeveGeo.attributes.position;
    for(let i=0;i<sa.count;i++){const y=sa.getY(i),a=Math.atan2(sa.getZ(i),sa.getX(i)),fold=1+.035*Math.sin(y*73+a*3)+.025*Math.cos(a*9+y*27);sa.setX(i,sa.getX(i)*fold);sa.setZ(i,sa.getZ(i)*fold*(.7+.3*(.26-y)/.52));}sleeveGeo.computeVertexNormals();this.mesh(sleeveGeo,cloth,0,-.30,0,1,1,1,this.handRig);
    this.bandShell=this.mesh(new T.CylinderGeometry(.076,.079,.052,48,1,true),metal,0,-.025,0,1,1,.7,this.handRig);this.bandPieces=[];
    this.braceletMaterial=new T.MeshStandardMaterial({color:0x73eaff,emissive:0x00cfff,emissiveIntensity:4,roughness:.4,metalness:0,toneMapped:false});
    for(let i=0;i<8;i++){const a=i*TAU/8;const el=this.box(this.braceletMaterial,Math.cos(a)*.077,-.025,Math.sin(a)*.054,.019,.019,.004,this.handRig);el.rotation.y=-a+Math.PI/2;this.bandPieces.push({mesh:el,p:el.position.clone(),q:el.quaternion.clone(),angle:a});}

    this.handSigil=new T.Mesh(new T.PlaneGeometry(.34,.34),new T.MeshBasicMaterial({map:this.runes,color:jade,transparent:true,opacity:0,blending:T.AdditiveBlending,depthWrite:false,side:T.DoubleSide,toneMapped:false}));this.handSigil.position.set(-.05,.24,-.02);this.handRig.add(this.handSigil);
    this.guardRing=new T.Mesh(new T.PlaneGeometry(1.5,1.5),new T.MeshBasicMaterial({map:this.runes,color:jade,transparent:true,opacity:0,blending:T.AdditiveBlending,depthWrite:false,side:T.DoubleSide,toneMapped:false}));this.guardRing.position.set(0,-.02,-1);this.viewCamera.add(this.guardRing);initCombatFX(this);
  }
  pose(mode,dt){
    const config=GESTURES[mode];const curls=config?.curls||[.08,.14,.22,.31];
    this.currentCurls ||= [0,0,0,0];this.currentSpread ||= [0,0,0,0];
    const bend=(names,curl,spread=0)=>{
      const bones=names.map(name=>this.bones.find(b=>b.node.name===name));if(bones.some(b=>!b))return;
      const spreadQ=new T.Quaternion().setFromAxisAngle(v3(1,0,0),spread);
      for(let j=0;j<bones.length;j++){
        const b=bones[j],angle=-curl*([1.05,1.8,2.2,2.2][j]);
        const q=spreadQ.clone().multiply(new T.Quaternion().setFromAxisAngle(v3(0,0,1),angle));
        if(j===0)b.node.position.copy(b.p);
        else{const prev=bones[j-1];const prevQ=spreadQ.clone().multiply(new T.Quaternion().setFromAxisAngle(v3(0,0,1),-curl*[1.05,1.8,2.2][j-1]));b.node.position.copy(prev.node.position).add(b.p.clone().sub(prev.p).applyQuaternion(prevQ));}
        b.node.quaternion.copy(q).multiply(b.q);
      }
    };
    for(let f=0;f<4;f++){
      this.currentCurls[f]=T.MathUtils.damp(this.currentCurls[f],curls[f],16,dt);
      this.currentSpread[f]=T.MathUtils.damp(this.currentSpread[f],config?.spread[f]||0,16,dt);
      const name=this.fingerNames[f];bend(['proximal','intermediate','distal'].map(p=>`${name}-finger-phalanx-${p}`).concat(`${name}-finger-tip`),this.currentCurls[f],this.currentSpread[f]);
    }
    this.thumbCurl=T.MathUtils.damp(this.thumbCurl||0,config?.thumb||0,14,dt);
    const thumbNames=['thumb-metacarpal','thumb-phalanx-proximal','thumb-phalanx-distal','thumb-tip'];
    const thumbBones=thumbNames.map(n=>this.bones.find(b=>b.node.name===n));
    const targets=[thumbBones[0].p,v3(.006,.002,-.015),v3(.002,-.022,.004),v3(.006,-.025,.018)];
    const f=Math.min(1,this.thumbCurl);
    thumbBones.forEach((b,i)=>b.node.position.copy(b.p).lerp(targets[i],f));
    thumbBones.forEach((b,i)=>{if(i<3){const rest=thumbBones[i+1].p.clone().sub(b.p).normalize(),next=thumbBones[i+1].node.position.clone().sub(b.node.position).normalize();b.node.quaternion.setFromUnitVectors(rest,next).multiply(b.q);}else b.node.quaternion.copy(thumbBones[i-1].node.quaternion);});
  }
  emitParticles(pos,color,n=55,speed=5){const c=new T.Color(color);for(let i=0;i<n;i++){const dir=v3(rng()-.5,rng()-.25,rng()-.5).normalize().multiplyScalar(speed*(.2+rng()));this.particles.push({p:pos.clone(),v:dir,color:c.clone(),life:.4+rng()*.9,max:1.3});}if(this.particles.length>1500)this.particles.splice(0,this.particles.length-1500);}
  shot(from,to,color,life=.3,kind="orb"){const mesh=kind==="sword"?swordMesh():new T.Mesh(new T.SphereGeometry(.07,12,8),new T.MeshBasicMaterial({color,toneMapped:false}));mesh.position.copy(from);if(kind==='sword'){mesh.scale.setScalar(.7);mesh.quaternion.setFromUnitVectors(v3(0,1,0),to.clone().sub(from).normalize());}this.scene.add(mesh);const trail=new T.Line(new T.BufferGeometry().setFromPoints([from,from]),new T.LineBasicMaterial({color,transparent:true,opacity:.85,toneMapped:false}));this.scene.add(trail);this.projectiles.push({from:from.clone(),to:to.clone(),mesh,trail,age:0,life,color});}
  ring(pos,color,size=5){const mesh=new T.Mesh(new T.PlaneGeometry(size,size),new T.MeshBasicMaterial({map:this.runes,color,transparent:true,opacity:.8,blending:T.AdditiveBlending,side:T.DoubleSide,depthWrite:false,toneMapped:false}));mesh.position.copy(pos);this.scene.add(mesh);this.ripples.push({mesh,age:0});}
  clearHazard(){if(this.hazardCircle){this.hazardCircle.removeFromParent();this.hazardCircle.geometry.dispose();this.hazardCircle.material.dispose();this.hazardCircle=null;}}
  effect(e){
    const enemyPos=this.actors?.position(e.enemyId)||this.enemy.position.clone().add(v3(0,.65,.3));
    if(['sword','guard','thunder'].includes(e.type)){this.handMode=e.type;this.handUntil=this.time+({sword:.8,guard:1.1,thunder:1.2}[e.type]);this.handLight.intensity=e.type==='guard'?3:2;handCast(this,e.type);}
    if(e.type==='sword'){this.recoil=.07;const from=this.camera.position.clone().add(v3(.3,-.1,-.7).applyQuaternion(this.camera.quaternion));swordWake(this,from,enemyPos);for(let i=0;i<3;i++)this.shot(from.clone().add(v3((i-1)*.12,0,0)),enemyPos,jade,.48+i*.06,'sword');}
    if(e.type==='thunder'){this.recoil=.1;this.shake=.055;thunder(this,enemyPos);this.handLight.color.set(0xffad35);}
    if(e.type==='guard'){this.guardRing.material.color.set(0xe6cb88);this.handLight.color.set(0xe6cb88);}
    if(e.type==='sword')this.handLight.color.set(jade);
    if(e.type==='spawn'){this.ring(enemyPos,0xaae2ce,4);this.emitParticles(enemyPos,0x8ad2ba,55,5);}
    if(e.type==='enemy-dodge'){this.emitParticles(enemyPos,0x91b7f5,65,6);}
    if(e.type==='enemy-killed'){deathBurst(this,enemyPos,this.actors?.map.get(e.enemyId)?.kind);this.shake=.11;}
    if(e.type==='area'){this.currentArea=e.area;this.scene.fog.color.set([0x41555d,0x657381,0x46676a,0x272331][e.area]);const p=ENCOUNTERS[e.area].camera;this.position.set(e.area===1?bridgeCenterX(p.z):p.x,(p.y??1.75)+(e.area===1?deckHeight(p.z):0),p.z);if(this.skyMaterial)this.skyMaterial.color.set(e.area===3?0x7d779a:e.area===2?0xb2d4d8:0xffffff);this.yaw=0;this.pitch=0;}
    if(e.type==='travel'){this.travelArea=e.area;this.travelDuration=e.duration;this.travelStart=this.time;this.travelFrom=this.camera.position.clone();this.travelTo=v3(ENCOUNTERS[e.area].camera.x,ENCOUNTERS[e.area].camera.y??1.75,ENCOUNTERS[e.area].camera.z);this.yaw=0;this.pitch=0;if(e.area===1){this.gateOpenAt=this.time;this.emitParticles(v3(0,3,-22),gold,80,3);}else{const p=this.camera.position.clone().add(v3(0,2,-10));this.emitParticles(p,gold,350,15);this.ring(p,gold,15);}this.shake=.06;}
    if(e.type==='expose'){this.ring(this.camera.position.clone().add(v3(0,0,-2)),0xaaf7d1,6);}
    if(e.type==='armor-break'){this.emitParticles(enemyPos,gold,160,10);this.ring(enemyPos,gold,5);}
    if(e.type==='hazard-warning'){this.clearHazard();this.hazardCircle=new T.Mesh(new T.RingGeometry(.05,e.position.radius,48),new T.MeshBasicMaterial({color:0xb06eff,transparent:true,opacity:.25,side:T.DoubleSide,depthWrite:false}));this.hazardCircle.rotation.x=-Math.PI/2;this.hazardCircle.position.set(e.position.x,.08,e.position.z);this.scene.add(this.hazardCircle);}
    if(e.type==='hazard-strike'){const p=v3(e.position.x,.2,e.position.z);lightning(this,p.clone().add(v3(0,12,0)),p);this.emitParticles(p,0xb5a4ff,110,8);this.clearHazard();}
    if(e.type==='finish'){this.outcome='victory';this.outcomeAt=this.time;this.ending.start();}
    if(e.type==='defeat'){this.outcome='defeat';this.outcomeAt=this.time;}
    if(e.type==='enemy-hit'){this.actors?.hit(e.enemyId);this.emitParticles(enemyPos,gold,30,3);this.enemyHit=1;}
    if(e.type==='enemy-cast'){const to=this.camera.position.clone();for(let i=0;i<3;i++)this.shot(enemyPos.clone().add(v3((i-1)*.5,.2,0)),to,gold,.8);}
    if(e.type==='parry'){this.shake=.07;this.ring(enemyPos,jade,5);this.shot(this.camera.position,enemyPos,jade,.2);this.emitParticles(enemyPos,jade,120,6);}
    if(e.type==='block'){this.shake=.03;this.emitParticles(this.camera.position.clone().add(v3(0,0,-1)),jade,20,2);}
    if(e.type==='hit')this.shake=.17;
    if(e.type==='dash'){const edge=this.currentArea===1?BRIDGE.safeX:this.currentArea===2?3.5:11.5,center=this.currentArea===1?bridgeCenterX(this.position.z):this.currentArea===2?LAKE_OFFSET.x:0;this.position.x=T.MathUtils.clamp(this.position.x+(this.move.x<0?-2.6:2.6),center-edge,center+edge);this.recoil=.04;}
    if(e.type==='stage'){this.ring(enemyPos,gold,8);this.emitParticles(enemyPos,gold,100,7);}
    if(e.type==='finish'){thunder(this,enemyPos);this.emitParticles(enemyPos,jade,450,12);this.ring(enemyPos,jade,12);this.enemy.visible=false;this.shake=.08;}
    if(e.type==='reset'){this.ending?.reset();clearCombatFX(this);this.outcome=null;this.clearHazard();this.gateOpenAt=Infinity;this.actors?.reset();for(const e of this.spellEffects){this.scene.remove(e.root);disposeEffect(e.root);}this.spellEffects=[];for(const r of this.ripples){this.scene.remove(r.mesh);disposeEffect(r.mesh);}this.ripples=[];this.enemy.visible=true;this.position.set(0,1.75,13);this.startBlend=0;this.yaw=0;this.pitch=0;this.lookTarget=null;this.handUntil=0;this.handMode='idle';this.enemyHit=0;this.shake=0;this.projectiles.forEach(x=>{this.scene.remove(x.mesh,x.trail);disposeEffect(x.mesh);x.trail.geometry.dispose();x.trail.material.dispose();});this.projectiles=[];this.particles=[];}
  }
  resize(){const w=innerWidth,h=innerHeight;this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.viewCamera.aspect=w/h;this.viewCamera.updateProjectionMatrix();this.renderer.setSize(w,h);this.composer.setSize(w,h);}
  quality(high){this.renderer.setPixelRatio(Math.min(devicePixelRatio,high?1.6:1));this.renderer.shadowMap.enabled=high;this.bloom.enabled=high;this.composer.setPixelRatio(this.renderer.getPixelRatio());this.resize();}
  update(dt,state){
    const endingDt=dt;if(this.ending.clock.active&&this.ending.clock.frame.still)dt=0;
    if(!state.paused)this.time+=dt;const t=this.time;
    const active=state.phase==='combat',area=state.area||0,second=area===1;
    if(active&&!state.paused){
      const yaw=this.yaw,forward=v3(Math.sin(yaw),0,-Math.cos(yaw)),right=v3(Math.cos(yaw),0,Math.sin(yaw));
      this.position.addScaledVector(right,this.move.x*dt*5.8).addScaledVector(forward,-this.move.z*dt*5.8);
      const travelGoal=[-7,-58,-119+LAKE_OFFSET.z,-168][area];
      if(state.autoAdvance&&state.phase==='combat'&&this.move.lengthSq()===0)this.position.z=T.MathUtils.damp(this.position.z,travelGoal,.075,dt);
      this.position.z=T.MathUtils.clamp(this.position.z,[-18,-75,-133+LAKE_OFFSET.z,-181][area],[17,-40,-100+LAKE_OFFSET.z,-151][area]);const center=second?bridgeCenterX(this.position.z):area===2?LAKE_OFFSET.x:0;this.position.x=T.MathUtils.clamp(this.position.x,center+[-11.5,-BRIDGE.safeX,-3.5,-11][area],center+[11.5,BRIDGE.safeX,3.5,11][area]);
    }
    const descent=state.phase==='travel'&&this.travelArea===2,journey=descent?Math.min(1,(t-this.travelStart)/this.travelDuration):0;
    this.journeyProgress=descent?journey:null;
    const bridgeView=second||(state.phase==='travel'&&this.travelArea===1&&this.position.z<-26);
    this.scene.fog.near=bridgeView?65:38;this.scene.fog.far=bridgeView?430:140;
    if(this.bridgeGroup)this.bridgeGroup.visible=area<2&&(!descent||journey<.75);
    this.pavilionPassage.visible=descent&&journey>.48&&journey<.84;
    this.descentCliff.visible=(descent&&journey>.62)||area===2;
    const shift=area===2?1:descent?T.MathUtils.smoothstep(journey,.61,.79):0;
    if(this.skyDome){this.skyDome.position.set(LAKE_OFFSET.x*shift,25+LAKE_OFFSET.y*shift,LAKE_OFFSET.z*shift);this.skyMaterial.opacity=descent?1-Math.sin(T.MathUtils.clamp((journey-.49)/.32,0,1)*Math.PI)*.98:1;}
    if(descent&&journey>.5){this.scene.fog.near=8;this.scene.fog.far=120;this.scene.fog.color.set(0x748b91);}
    if(second&&!descent)this.position.y=1.75+deckHeight(this.position.z);
    const desired=state.phase==='ready'?v3(Math.sin(t*.06)*1.7+1,2.7,16):this.position.clone();
    if(active)desired.y+=Math.sin(t*(this.move.lengthSq()?11:5))*(this.move.lengthSq()?.045:.012);
    if(state.phase==='travel'){const f=Math.min(1,(t-this.travelStart)/this.travelDuration);if(this.travelArea===1){const p=gateJourney(this.travelFrom,f);desired.set(p.x,p.y,p.z);}else if(this.travelArea===2){const p=lakeJourney(this.travelFrom,f);desired.set(p.x,p.y,p.z);}else desired.copy(this.travelFrom).lerp(this.travelTo,f);this.position.copy(desired);}
    this.camera.position.lerp(desired,1-Math.exp(-dt*6));
    const ahead=descent?lakeJourney(this.travelFrom,Math.min(1,journey+.025)):null;
    const target=descent?(journey<.98?v3(ahead.x,ahead.y-.5,ahead.z):v3(LAKE_OFFSET.x,LAKE_OFFSET.y+2,LAKE_OFFSET.z-125)):state.phase==='travel'?v3(this.camera.position.x,this.camera.position.y-.5,this.camera.position.z-16):this.actors?.position(state.targetId)||(area===2?v3(LAKE_OFFSET.x,LAKE_OFFSET.y+3,LAKE_OFFSET.z-125):v3(0,3,[-9,-69,-125,-177][area]));
    this.lookTarget||=target.clone();this.lookTarget.lerp(target,1-Math.exp(-dt*5));
    const look=this.lookTarget.clone().add(v3(this.yaw*14,.5+this.pitch*10,0));this.camera.lookAt(look);
    this.shake=Math.max(0,this.shake-dt*.5);if(!state.paused){this.camera.position.x+=(rng()-.5)*this.shake;this.camera.position.y+=(rng()-.5)*this.shake;}
    this.enemy.visible=state.phase==='ready'&&!this.previewPose;
    this.enemy.position.y=2.7+Math.sin(t*1.3)*.22;this.enemy.rotation.y=Math.sin(t*.6)*.12;
    this.actors?.update(dt,state,t);
    if(this.enemyLight)this.enemyLight.position.copy(target).add(v3(0,1,1));
    if(this.bridgeSeal)this.bridgeSeal.rotation.z=-t*.025;for(let i=2;i<4;i++)if(this.realmGroups?.[i])this.realmGroups[i].visible=area===i||(i===2&&descent&&journey>.64);if(this.realmRune)this.realmRune.rotation.z=t*.04;for(const {g,sign}of this.gateDoors||[])g.rotation.y=-sign*Math.min(1.55,Math.max(0,(t-this.gateOpenAt)*1.15));
    for(const [i,cloud]of (this.clouds||[]).entries())cloud.position.x+=(Math.sin(t*.1+i)*.16)*dt;
    this.halo.rotation.z=-t*.14;this.halo.material.opacity=.26+(state.incoming?.launched?.15:0);
    this.halo.material.color.set(state.stage===3?0xf39c69:gold);
    this.core.rotation.y=t;this.core.rotation.z=t*.4;this.core.scale.setScalar(1+Math.sin(t*3)*.12+(state.incoming?.3:0));
    this.aura.material.opacity=state.incoming?.24:.1;
    this.talismans.forEach((p,i)=>{const a=t*.36+i*TAU/8;p.position.set(Math.cos(a)*1.95,.5+Math.sin(a*2)*.5,Math.sin(a)*1.4);p.rotation.set(Math.sin(t+i)*.12,-a+Math.PI/2,Math.sin(a)*.15);});
    this.groundSeal.rotation.z=t*.015;this.groundSeal.material.opacity=.3;
    const aa=this.ambient.geometry.attributes.position;for(let i=0;i<this.ambientBase.length;i++){const p=this.ambientBase[i];aa.setXYZ(i,p[0]+Math.sin(t*.3+i)*.7,(p[1]+t*.1)%14,p[2]+Math.sin(t*.2+i)*.3);}aa.needsUpdate=true;
    for(const p of this.particles){if(!state.paused){p.life-=dt;p.p.addScaledVector(p.v,dt);p.v.y-=dt*1.4;}}this.particles=this.particles.filter(p=>p.life>0);
    this.particles.forEach((p,i)=>{this.fxPositions.set([p.p.x,p.p.y,p.p.z],i*3);const f=Math.max(0,p.life/p.max);this.fxColors.set([p.color.r*f,p.color.g*f,p.color.b*f],i*3);});this.fxPoints.geometry.attributes.position.needsUpdate=true;this.fxPoints.geometry.attributes.color.needsUpdate=true;this.fxPoints.geometry.setDrawRange(0,this.particles.length);
    this.projectiles=this.projectiles.filter(p=>{if(!state.paused)p.age+=dt;const f=Math.min(1,p.age/p.life);p.mesh.position.lerpVectors(p.from,p.to,f);const prev=p.from.clone().lerp(p.to,Math.max(0,f-.12));const a=p.trail.geometry.attributes.position;a.setXYZ(0,prev.x,prev.y,prev.z);a.setXYZ(1,p.mesh.position.x,p.mesh.position.y,p.mesh.position.z);a.needsUpdate=true;
      if(f>=1){this.emitParticles(p.to,p.color,18,3);this.scene.remove(p.mesh,p.trail);disposeEffect(p.mesh);p.trail.geometry.dispose();p.trail.material.dispose();return false;}return true;});
    this.ripples=this.ripples.filter(r=>{if(!state.paused)r.age+=dt;r.mesh.scale.setScalar(.4+r.age*.8);r.mesh.material.opacity=Math.max(0,.8-r.age*.55);r.mesh.rotation.z+=dt*.25;if(r.age>1.5){this.scene.remove(r.mesh);r.mesh.geometry.dispose();r.mesh.material.dispose();return false;}return true;});
    updateCombatFX(this,state.paused?0:dt);
    if(this.lakeWater){this.lakeWater.material.roughness=.08+Math.sin(t*.7)*.025;for(const [i,r]of this.waterRipples.entries()){r.scale.setScalar(1+Math.sin(t*.6+i)*.09);r.material.opacity=.07+Math.sin(t+i)*.035;}}
    updateSpells(this,state.paused?0:dt);const finale=this.ending.clock.active,cast=!finale&&this.handUntil>t?this.handMode:'idle',mode=cast!=='idle'?cast:(finale?'idle':this.previewPose||this.bandPose||'idle');this.pose(mode,state.paused?0:dt);updateNails(this);this.recoil=T.MathUtils.damp(this.recoil,0,11,dt);
    const targetX=cast==='guard'?.25:cast==='sword'?.26:.33,targetY=this.outcome==='defeat'?-.9:cast==='guard'?-.27:cast==='thunder'?-.29:-.30;
    this.handRig.position.x=T.MathUtils.damp(this.handRig.position.x,targetX*Math.min(1,this.viewCamera.aspect/1.3),9,dt);this.handRig.position.y=T.MathUtils.damp(this.handRig.position.y,targetY,9,dt)+Math.sin(t*1.6)*.018*dt;this.handRig.position.z=-.65+this.recoil;
    this.handRig.rotation.z=T.MathUtils.damp(this.handRig.rotation.z,(cast==='guard'?-.18:cast==='sword'?-.28:.07)+this.bandTilt.roll,10,dt);this.handRig.rotation.x=T.MathUtils.damp(this.handRig.rotation.x,this.bandTilt.pitch,10,dt);
    this.handSigil.material.opacity=0;this.handSigil.rotation.z=t*.8;
    this.braceletMaterial.emissive.set(0x00cfff);this.braceletMaterial.emissiveIntensity=T.MathUtils.damp(this.braceletMaterial.emissiveIntensity,mode==='idle'?2.8:4.1,10,dt);
    this.handLight.intensity=T.MathUtils.damp(this.handLight.intensity,cast==='idle'?0:1.5,6,dt);
    this.guardRing.material.opacity=0;this.guardRing.rotation.z=-t*.15;
    updateArt(this,state);this.renderer.toneMappingExposure=this.outcome==='victory'?1.12+Math.sin(Math.min(1,(t-this.outcomeAt)/2)*Math.PI)*.8:area===3?.86:1.12;this.ending.update(endingDt,state.paused);if(this.ending.clock.active&&this.ending.clock.frame.scene){this.ending.render();return;}this.composer.render();this.renderer.autoClear=false;this.renderer.clearDepth();this.renderer.render(this.viewScene,this.viewCamera);this.renderer.autoClear=true;
  }
  diagnostics(){return {webgl:true,ending:this.ending?.diagnostics,daylight:this.daylight,drawCalls:this.renderer.info.render.calls,triangles:this.renderer.info.render.triangles,failedAssets:[...this.failedAssets],handLoaded:!!this.handModel,handMode:this.handMode,handCurls:[...(this.currentCurls||[])],bandPose:this.bandPose,bandTilt:{...this.bandTilt},handRot:[this.handRig.rotation.x,this.handRig.rotation.z],activeSpells:this.spellEffects.length,deathBursts:this.deathBursts?.length||0,handAura:this.auraCast&&this.time-this.auraCast.start<this.auraCast.life?this.auraCast.mode:null,journeyProgress:this.journeyProgress,viewport:[innerWidth,innerHeight],camera:this.camera.position.toArray(),gateAngles:(this.gateDoors||[]).map(d=>d.g.rotation.y)};}
}
