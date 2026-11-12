import * as T from 'three';
import {PAVILION_ANCHOR as A,LAKE_OFFSET} from './bridge-route.mjs';
// Close-range interior of the painted pavilion, revealed only when the camera reaches it.
export function buildPavilionPassage(world){
 const root=new T.Group();root.name='original-pavilion-interior';root.position.set(A.x,A.y,A.z-4.5);root.visible=false;world.scene.add(root);world.pavilionPassage=root;
 const M=world.materials,timber=new T.MeshStandardMaterial({color:0x3a3029,roughness:.9}),stone=new T.MeshStandardMaterial({color:0x9caaa0,map:M.stone.map,roughness:.86});
 world.box(stone,0,-.14,0,7,.28,11,root);
 for(const side of [-1,1])for(const z of [-4.5,0,4.5]){
  world.cylinder(timber,.18,.25,5.8,side*2.7,2.9,z,root,12);world.box(stone,side*2.7,.2,z,.65,.4,.65,root);
  world.box(timber,0,5.5,z,6.4,.35,.35,root);
 }
 world.box(timber,0,5.9,0,7,.35,11,root);
 for(const x of [-2.7,2.7]){world.box(timber,x,1,0,.12,.12,8,root);world.box(timber,x,.45,0,.1,.1,8,root);}
 for(const x of [-2,2])for(const z of [-3,3])world.box(M.light,x,4.8,z,.25,.55,.25,root);
 // The far side opens onto a vertical rock face with the water visible below it.
 const cliff=new T.Group();world.scene.add(cliff);cliff.visible=false;world.descentCliff=cliff;
 for(const side of [-1,1])world.mesh(new T.IcosahedronGeometry(1,2),M.stone,A.x+side*13,(A.y+LAKE_OFFSET.y)/2,A.z-8,8,(A.y-LAKE_OFFSET.y)/2+5,11,cliff);
}
