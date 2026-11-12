import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';import {refineHand} from '../src/hand-detail.mjs';
test('hand subdivision preserves categorical bones and normalized finite skin weights',async()=>{
 const b=await readFile(new URL('../../../app/game/tianjie/assets/hand-right.glb',import.meta.url));const gltf=await new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');let meshes=0;
 gltf.scene.traverse(o=>{if(!o.isSkinnedMesh)return;meshes++;const before=o.geometry,g=refineHand(before),weights=g.attributes.skinWeight,indices=g.attributes.skinIndex;
 assert.equal(g.index.count,before.index.count*4);assert.ok(g.attributes.position.count>before.attributes.position.count);
 for(let i=0;i<weights.count;i++){let sum=0;for(let j=0;j<4;j++){const bone=indices.array[i*4+j],w=weights.array[i*4+j];assert.ok(Number.isInteger(bone)&&bone>=0&&bone<o.skeleton.bones.length);assert.ok(Number.isFinite(w)&&w>=0&&w<=1);sum+=w;}assert.ok(Math.abs(sum-1)<1e-5);}
 assert.ok([...g.attributes.position.array,...g.attributes.normal.array].every(Number.isFinite));
 // Exercise actual skinning in all fingers rather than trusting the attribute names alone.
 o.geometry=g;for(const bone of o.skeleton.bones)if(bone.name.includes('phalanx'))bone.rotateZ(-.2);gltf.scene.updateMatrixWorld(true);o.skeleton.update();for(let i=0;i<g.attributes.position.count;i+=7)assert.ok(o.getVertexPosition(i,new (g.boundingSphere.center.constructor)()).toArray().every(Number.isFinite));
 });assert.equal(meshes,1);
});
