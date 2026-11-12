import * as T from 'three';
import {EndingClock} from './ending-timeline.mjs';
const TAU=Math.PI*2,V=(x=0,y=0,z=0)=>new T.Vector3(x,y,z);
const seeded=(seed=>()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;})(8127);
function cloudTexture(){
 const c=document.createElement('canvas');c.width=512;c.height=256;const x=c.getContext('2d');
 for(let i=0;i<55;i++){const px=80+seeded()*350,py=90+seeded()*85,r=24+seeded()*56,g=x.createRadialGradient(px,py,0,px,py,r);g.addColorStop(0,'rgba(222,237,247,.16)');g.addColorStop(.45,'rgba(185,211,229,.08)');g.addColorStop(1,'rgba(160,190,219,0)');x.fillStyle=g;x.fillRect(px-r,py-r,r*2,r*2);}
 return new T.CanvasTexture(c);
}
// Reusable cloud-sea victory scene; the player and combat world stay untouched.
export class AscensionEnding{
 constructor(world){this.world=world;this.clock=new EndingClock();this.scene=new T.Scene();this.scene.fog=new T.FogExp2(0x9bb5c2,.0018);this.camera=new T.PerspectiveCamera(49,1,.1,650);this.built=false;this.materials=[];this.featherParts=[];}
 async init(){[this.backdrop,this.heaven]=await Promise.all([this.world.texture('ending-cloudsea.jpg'),this.world.texture('ending-heaven.jpg')]);if(this.heaven){this.heaven.colorSpace=T.SRGBColorSpace;this.heaven.wrapS=this.heaven.wrapT=T.ClampToEdgeWrapping;}if(this.backdrop){this.backdrop.colorSpace=T.SRGBColorSpace;this.backdrop.wrapS=this.backdrop.wrapT=T.ClampToEdgeWrapping;}}
 restoreBand(){this.world.bandShell.visible=true;for(const b of this.world.bandPieces){b.mesh.position.copy(b.p);b.mesh.quaternion.copy(b.q);}}
 start(){this.restoreBand();this.clock.start(window.matchMedia('(prefers-reduced-motion: reduce)').matches);if(!this.built)this.build();this.world.handRig.scale.setScalar(.82);this.world.handRig.rotation.y=0;}
 reset(){this.restoreBand();this.clock.reset();this.world.handRig.visible=true;this.world.handRig.scale.setScalar(.82);this.world.handRig.rotation.y=0;}
 skip(){this.clock.skip();}
 build(){
  const w=this.world;this.built=true;this.scene.add(new T.HemisphereLight(0xc4e7ff,0x263941,2.4));
  const sun=new T.DirectionalLight(0xffdc9d,4);sun.position.set(-35,55,8);this.scene.add(sun);const rim=new T.DirectionalLight(0x7db8dd,2.5);rim.position.set(20,15,-35);this.scene.add(rim);
  const sky=new T.Mesh(new T.SphereGeometry(450,40,24),new T.ShaderMaterial({side:T.BackSide,depthWrite:false,uniforms:{},vertexShader:'varying vec3 vP;void main(){vP=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:`varying vec3 vP;
   void main(){vec3 d=normalize(vP);float h=clamp(d.y*.85+.18,0.,1.);vec3 c=mix(vec3(.65,.73,.72),vec3(.045,.13,.23),pow(h,.6));vec3 s=normalize(vec3(-.28,.25,-.9));float a=acos(clamp(dot(d,s),-1.,1.));c+=vec3(1.,.69,.28)*(.18*exp(-a*3.)+.6*exp(-a*21.)+.85*(1.-smoothstep(.043,.048,a)));gl_FragColor=vec4(c,1.);}` }));if(this.backdrop){
   // A moving cloud layer with depth-dependent advection; mountains remain stable.
   this.skyUniforms={map:{value:this.backdrop},heaven:{value:this.heaven||this.backdrop},crack:{value:0},opening:{value:0},beacon:{value:0},time:{value:0},aspect:{value:1},travel:{value:0}};
   const mat=new T.ShaderMaterial({depthTest:false,depthWrite:false,uniforms:this.skyUniforms,
    vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,1.,1.);}',
    fragmentShader:`uniform sampler2D map;uniform sampler2D heaven;uniform float time;uniform float aspect;uniform float travel;uniform float crack;uniform float opening;uniform float beacon;varying vec2 vUv;
     float noise(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
     void main(){vec2 uv=vUv;float source=1672./941.;if(aspect<source)uv.x=(uv.x-.5)*aspect/source+.5;else uv.y=(uv.y-.5)*source/aspect+.5;
      vec2 realm=(uv-vec2(.5,.58))*(1.-travel*.15)+vec2(.5,.58);
      float cloud=1.-smoothstep(.25,.55,realm.y);realm.x+=cloud*sin(realm.y*19.+time*.55)*.007;realm.y+=cloud*sin(realm.x*14.+time*.5)*.006;
      vec3 bright=texture2D(heaven,clamp(realm,.002,.998)).rgb;
      vec2 old=uv;old.x+=sign(uv.x-.5)*opening*.22;old.y+=sin(uv.x*12.+time*.2)*.012;
      vec3 storm=texture2D(map,clamp(old,.002,.998)).rgb*vec3(.12,.19,.29);
      float center=.5+sin(vUv.y*19.)*.009+sin(vUv.y*51.)*.003;
      float width=opening*.82;float dist=abs(vUv.x-center);
      float edge=dist-width;
      float revealed=1.-smoothstep(-.004,.008,edge);
      float height=1.-smoothstep(crack*.92,crack*.92+.06,abs(vUv.y-.48));
      revealed*=height*crack;
      vec3 color=mix(storm,bright,revealed);
      float seam=exp(-abs(edge)*450.)*height*crack*(1.-smoothstep(.65,1.,opening));
      color+=vec3(2.5,1.15,.25)*seam;
      float branch=abs(abs(vUv.x-center)-(.04*sin(vUv.y*13.)+.018));
      color+=vec3(.65,.31,.08)*exp(-branch*600.)*crack*(1.-opening)*height*.5;
      vec2 lamp=realm-vec2(.5,.635);float d=length(lamp*vec2(1.,.6));color+=vec3(2.6,1.1,.22)*exp(-d*190.)*beacon;
      gl_FragColor=vec4(color,1.);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
     }`});
   const plate=new T.Mesh(new T.PlaneGeometry(2,2),mat);plate.frustumCulled=false;plate.renderOrder=-100;this.scene.add(plate);sky.geometry.dispose();sky.material.dispose();
  }else this.scene.add(sky);
  // Gold currents rise into an open sky: no statue or duplicated landscape geometry.
  this.currents=[];
  for(let j=0;j<7;j++){
   const points=[];for(let i=0;i<=100;i++){const u=i/100,a=u*TAU*1.05+j*TAU/7,r=(1-u)*12+1.3;points.push(V(Math.cos(a)*r,-9+u*48,Math.sin(a)*r-12));}
   const curve=new T.CatmullRomCurve3(points),material=new T.ShaderMaterial({uniforms:{time:{value:0},strength:{value:0},phase:{value:j*.137}},transparent:true,depthWrite:false,blending:T.AdditiveBlending,toneMapped:false,vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'uniform float time;uniform float strength;uniform float phase;varying vec2 vUv;void main(){float head=fract(time*.32+phase);float trail=mod(head-vUv.x+1.,1.);float glow=exp(-trail*22.);gl_FragColor=vec4(vec3(1.,.71,.28)*(1.+glow*2.),strength*(.04+glow*.96));}'});
   const stream=new T.Mesh(new T.TubeGeometry(curve,100,j%2?.035:.065,5,false),material);this.scene.add(stream);this.currents.push(stream);
  }
  this.halo=new T.Group();this.halo.position.set(0,37,-12);this.scene.add(this.halo);
  for(let i=0;i<3;i++){const ring=new T.Mesh(new T.RingGeometry(3+i*1.3,3.025+i*1.3,160),new T.MeshBasicMaterial({color:0xffdf9e,transparent:true,opacity:0,depthWrite:false,blending:T.AdditiveBlending,toneMapped:false,side:T.DoubleSide}));this.halo.add(ring);}
  this.sun=new T.Sprite(new T.SpriteMaterial({map:w.glow,color:0xffdfb2,transparent:true,opacity:0,depthWrite:false,blending:T.AdditiveBlending,toneMapped:false}));this.sun.position.copy(this.halo.position);this.sun.scale.set(34,34,1);this.scene.add(this.sun);
  const cloud=cloudTexture();this.clouds=[];
  for(let i=0;i<48;i++){const sprite=new T.Sprite(new T.SpriteMaterial({map:cloud,color:i%3?0xb8d3e1:0xffdfad,transparent:true,opacity:.54,depthWrite:false,fog:true})),a=i*2.399,r=i<10?12+seeded()*17:35+seeded()*150;sprite.position.set(i<10?(i%2?1:-1)*(10+i*2):Math.cos(a)*r,i<10?1+i*.6:-4+seeded()*5,i<10?16-i*3:Math.sin(a)*r);sprite.scale.set(55+seeded()*55,14+seeded()*15,1);this.scene.add(sprite);this.clouds.push({sprite,x:sprite.position.x,y:sprite.position.y,z:sprite.position.z,phase:i});}
  this.rings=[];for(let i=0;i<3;i++){const ring=new T.Mesh(new T.PlaneGeometry(1,1),new T.MeshBasicMaterial({map:w.runes,color:0xf3c98c,transparent:true,opacity:.25,depthWrite:false,side:T.DoubleSide,blending:T.AdditiveBlending,toneMapped:false}));ring.rotation.x=-Math.PI/2;ring.position.y=-1+i*1.8;ring.scale.setScalar(45+i*21);this.scene.add(ring);this.rings.push(ring);}
  // Sparse cranes/feathers provide scale and an upward current, not a particle wall.
  const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute([0,.6,0,-.12,.05,.025,0,-.35,0,.12,.05,.025],3));geo.setIndex([0,1,2,0,2,3]);geo.computeVertexNormals();
  this.feathers=new T.InstancedMesh(geo,new T.MeshBasicMaterial({color:0xffe4a8,side:T.DoubleSide,toneMapped:false,transparent:true,opacity:.85}),180);this.feathers.instanceMatrix.setUsage(T.DynamicDrawUsage);this.feathers.frustumCulled=false;this.scene.add(this.feathers);this.dummy=new T.Object3D();
  this.sparks=new T.Points(new T.BufferGeometry(),new T.PointsMaterial({map:w.glow,color:0xffd490,size:.4,transparent:true,opacity:.6,depthWrite:false,blending:T.AdditiveBlending}));const p=new Float32Array(300*3);for(let i=0;i<300;i++){p[i*3]=(seeded()-.5)*100;p[i*3+1]=seeded()*60;p[i*3+2]=(seeded()-.5)*70;}this.sparks.geometry.setAttribute('position',new T.BufferAttribute(p,3));this.scene.add(this.sparks);
  this.burst=new T.Group();w.viewCamera.add(this.burst);this.burstRays=[];
  for(let i=0;i<48;i++){const ray=new T.Mesh(new T.PlaneGeometry(.002,1),new T.MeshBasicMaterial({color:0xffd38b,transparent:true,opacity:0,depthWrite:false,blending:T.AdditiveBlending,toneMapped:false,side:T.DoubleSide}));this.burst.add(ray);this.burstRays.push(ray);}
  // A visible tether joins the hand's fingertip to the opening in the sky.
  const tetherGeo=new T.BufferGeometry().setFromPoints([V(),V(),V()]);
  this.tether=new T.Line(tetherGeo,new T.LineBasicMaterial({color:0xffdc8d,transparent:true,opacity:0,depthWrite:false,blending:T.AdditiveBlending,toneMapped:false}));w.viewCamera.add(this.tether);this.tether.frustumCulled=false;
  // Foreground feathers remain attached to the cinematic hand during the unsealing shot.
  const fg=this.foreground=new T.Group();w.viewCamera.add(fg);for(let i=0;i<72;i++){const m=new T.Mesh(geo,new T.MeshBasicMaterial({color:0xffe4a8,side:T.DoubleSide,transparent:true,opacity:0,depthWrite:false,toneMapped:false}));fg.add(m);this.featherParts.push(m);}fg.visible=false;
 }
 update(dt,paused){
  const f=this.clock.tick(dt,paused);if(!this.clock.active){if(this.foreground)this.foreground.visible=false;if(this.burst)this.burst.visible=false;if(this.tether)this.tether.visible=false;return;}
  const w=this.world,t=this.clock.reduced?15:f.time;
  // Keep the whole sleeve, band and hand together. The band brightens; nothing breaks off.
  const fitHand=Math.min(1,w.viewCamera.aspect/1.3);
  w.handRig.position.set((.25-f.lift*.11-f.push*.07)*fitHand,-.30+f.lift*.12-f.push*.045-(1-f.hand)*.8,-.65+f.lift*.045-f.push*.24);
  w.handRig.rotation.set(-f.lift*.12-f.push*.12,0,.07-f.lift*.13-f.push*.12);w.handRig.scale.setScalar(.82);
  w.handLight.color.set(0xffdf9f);w.handLight.intensity=(1+f.lift*3)*f.hand;w.braceletMaterial.emissiveIntensity=3+f.lift*4;
  w.handRig.visible=f.hand>0;this.foreground.visible=f.hand>0;w.handRig.updateMatrix();
  this.palm=V(-.015,.23,-.01).applyMatrix4(w.handRig.matrix);
  this.tether.visible=f.scene&&f.hand>0;const tip=V(-.025,.38,0).applyMatrix4(w.handRig.matrix),end=V(0,.12,-1.4),mid=tip.clone().lerp(end,.5);mid.x+=Math.sin(t*9)*.008*f.crack;
  const ta=this.tether.geometry.attributes.position;[tip,mid,end].forEach((p,i)=>ta.setXYZ(i,p.x,p.y,p.z));ta.needsUpdate=true;this.tether.material.opacity=f.crack*(1-f.push)*.9;
  this.burst.visible=!this.clock.reduced&&f.push>0&&t<6.3;const shock=T.MathUtils.clamp((t-4.6)/1.5,0,1);
  this.burstRays.forEach((ray,i)=>{const a=i*TAU/48,r=.03+shock*(.6+(i%5)*.06);ray.position.set(Math.cos(a)*r,Math.sin(a)*r,-.85);ray.rotation.z=a-Math.PI/2;ray.scale.y=.04+shock*.27;ray.material.opacity=(1-shock)*f.push*.65;});
  this.featherParts.forEach((m,i)=>{const age=Math.max(0,t-2.4-i*.018),u=(age*.55+i*.137)%1,a=i*2.399+t*.65,r=.012+u*u*.15;
   m.position.copy(this.palm).add(V(Math.cos(a)*r,u*.8, -u*.7+Math.sin(a)*r*.25));m.rotation.set(t+i,a,i*.6);m.scale.setScalar((.015+(i%4)*.005)*(1-u*.65));m.material.opacity=age>0?f.feathers*(1-u)*.85:0;
  });
  if(!f.scene)return;
  if(this.skyUniforms){this.skyUniforms.time.value=t;this.skyUniforms.aspect.value=w.camera.aspect;this.skyUniforms.travel.value=f.pull;this.skyUniforms.crack.value=f.crack;this.skyUniforms.opening.value=f.release;this.skyUniforms.beacon.value=f.beacon;}
  this.camera.aspect=w.camera.aspect;this.camera.updateProjectionMatrix();const fit=Math.max(1,1.4/this.camera.aspect),pull=f.pull;
  this.camera.position.set(Math.sin(f.release*.6)*4*fit,12+f.pull*13,(56-f.pull*30)*fit);this.camera.lookAt(0,19+f.pull*12,-12);
  const rise=f.release,fade=1-f.darken;
  this.currents.forEach((r,i)=>{r.material.uniforms.time.value=t;r.material.uniforms.strength.value=rise*fade;r.scale.setScalar(.8+rise*.2);r.geometry.setDrawRange(0,Math.floor(r.geometry.index.count*rise/3)*3);});
  this.halo.children.forEach((r,i)=>{r.material.opacity=(.08+i*.025)*rise*fade;r.scale.setScalar(1+f.bloom*(.7+i*.1));});
  this.halo.lookAt(this.camera.position);this.sun.material.opacity=(.025+f.bloom*.07)*rise*fade;
  this.clouds.forEach(({sprite,x,y,z,phase})=>{sprite.position.set(x+Math.sign(x||1)*f.release*48+Math.sin(t*.22+phase)*5,y+Math.sin(t*.3+phase)*1.8,z+f.pull*28);sprite.material.opacity=(.16+f.release*.38)*(1-f.darken);});
  this.rings.forEach((r,i)=>{r.rotation.z=t*(i%2?-.025:.02);r.material.opacity=(.16+i*.015)*f.reveal;});
  for(let i=0;i<180;i++){const y=(i*.61+t*(2+(i%4)*.35))%55-9,a=i*2.399+t*.35,r=(1-(y+9)/55)*13+1.5;this.dummy.position.set(Math.cos(a)*r,y,Math.sin(a)*r-12);this.dummy.rotation.set(t*.5+i,a,t*.7+i);this.dummy.scale.setScalar(.18+(i%4)*.07);this.dummy.updateMatrix();this.feathers.setMatrixAt(i,this.dummy.matrix);}this.feathers.instanceMatrix.needsUpdate=true;this.feathers.material.opacity=f.release*(.75-f.pull*.3);
 }
 render(){const w=this.world,pass=w.composer.passes[0];pass.scene=this.scene;pass.camera=this.camera;w.renderer.toneMappingExposure=1.05;try{w.composer.render();if(this.clock.frame.hand>0){w.renderer.autoClear=false;w.renderer.clearDepth();w.renderer.render(w.viewScene,w.viewCamera);w.renderer.autoClear=true;}}finally{pass.scene=w.scene;pass.camera=w.camera;}}
 get diagnostics(){return {active:this.clock.active,handVisible:this.world.handRig.visible,handPosition:this.world.handRig.position.toArray(),palm:this.palm?.toArray(),cloudPosition:this.clouds?.[0].sprite.position.toArray(),skyTime:this.skyUniforms?.time.value,riftOpening:this.skyUniforms?.opening.value,beaconLight:this.skyUniforms?.beacon.value,heavenLoaded:!!this.heaven,handYaw:this.world.handRig.rotation.y,bandRestored:this.world.bandShell.visible&&this.world.bandPieces.every(b=>b.mesh.position.distanceTo(b.p)<.0001),...this.clock.frame,lightCurrents:this.currents?.length||0,camera:this.camera.position.toArray()};}
}
