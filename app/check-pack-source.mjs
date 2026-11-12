import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { record, verify } from './scripts/package-provenance.mjs';
const tmp=mkdtempSync(path.join(os.tmpdir(),'yuanli-provenance-'));
try {
 for(const d of ['app/dist','app/electron','app/game','host','python'])mkdirSync(path.join(tmp,d),{recursive:true});
 writeFileSync(path.join(tmp,'app/dist/main.js'),'已审源码');record(tmp,'a'.repeat(40));assert.equal(verify(tmp).commit,'a'.repeat(40));
 writeFileSync(path.join(tmp,'app/dist/main.js'),'旧包混入');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'b'.repeat(40));writeFileSync(path.join(tmp,'app/electron/extra.cjs'),'额外代码');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'c'.repeat(40));writeFileSync(path.join(tmp,'app/package.json'),'{"main":"bad.cjs"}');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'d'.repeat(40));writeFileSync(path.join(tmp,'python/extra.py'),'bad');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'e'.repeat(40));mkdirSync(path.join(tmp,'python/__pycache__'));writeFileSync(path.join(tmp,'python/__pycache__/old.pyc'),'旧缓存');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'f'.repeat(40));writeFileSync(path.join(tmp,'python/__pycache__/old.pyc'),'替换缓存');assert.throws(()=>verify(tmp),/不一致/);
 console.log('构建来源检查：原包通过、篡改和多余文件拒绝');
} finally {rmSync(tmp,{recursive:true,force:true});}
