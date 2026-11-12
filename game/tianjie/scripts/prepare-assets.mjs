import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const target=path.join(root,'dist/assets');await mkdir(target,{recursive:true});
const manifest=JSON.parse(await readFile(path.join(root,'assets-manifest.json'),'utf8'));
const local=process.argv[2];
for(const asset of manifest){
 let data;
 if(local)data=await readFile(path.join(path.resolve(local),asset.file));
 else {const r=await fetch(asset.url,{signal:AbortSignal.timeout(60000)});if(!r.ok)throw new Error(`${asset.file}: HTTP ${r.status}`);data=Buffer.from(await r.arrayBuffer());}
 if(createHash('sha256').update(data).digest('hex')!==asset.sha256)throw new Error(`Checksum mismatch: ${asset.file}`);
 await writeFile(path.join(target,asset.file),data);console.log(`Prepared ${asset.file}`);
}
await copyFile(path.join(root,'node_modules/three/LICENSE'),path.join(target,'three-LICENSE.txt'));
// Authored assets live in the App bundle; fresh standalone builds use the same files.
const artSource=local?path.resolve(local):path.resolve(root,'../../app/game/tianjie/assets');
for(const file of ['sky-mountains.png','zhangtian-logo.png','sky-night.jpg','seal-sword.png','seal-guard.png','seal-thunder.png','game-icon.png','ending-cloudsea.jpg','ending-heaven.jpg'])await copyFile(path.join(artSource,file),path.join(target,file));
console.log('Assets ready. Authored sky, gesture icons and logo copied from the canonical App asset directory.');
