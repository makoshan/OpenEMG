import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
export function hashes(root) {
 const out={};
 for (const dir of ['app','firmware','host','python']) {
  const walk=p=>{for(const e of readdirSync(path.join(root,p),{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name,'en'))){const rel=p+'/'+e.name;if(e.isSymbolicLink())throw Error('运行文件不能是软链：'+rel);if(e.isDirectory()){walk(rel);}else out[rel]=createHash('sha256').update(readFileSync(path.join(root,rel))).digest('hex');}};walk(dir);
 }
 return out;
}
export function verify(root) {
 const info=JSON.parse(readFileSync(path.join(root,'build-info.json'),'utf8'));
 if(!/^[a-f0-9]{40}$/.test(info.commit))throw Error('缺少有效源码提交号');
 if(JSON.stringify(hashes(root))!==JSON.stringify(info.files))throw Error('包内文件与构建清单不一致，拒绝安装');
 return info;
}
export function record(root,commit) {writeFileSync(path.join(root,'build-info.json'),JSON.stringify({commit,builtAt:new Date().toISOString(),files:hashes(root)},null,2)+'\n');verify(root);}
