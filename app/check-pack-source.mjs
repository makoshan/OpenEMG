import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { record, verify } from './scripts/package-provenance.mjs';
const tmp=mkdtempSync(path.join(os.tmpdir(),'yuanli-provenance-'));
try {
 for(const d of ['app/dist','app/electron','app/game','firmware/c08b-bringup/tools','host','python'])mkdirSync(path.join(tmp,d),{recursive:true});
 writeFileSync(path.join(tmp,'app/dist/main.js'),'已审源码');writeFileSync(path.join(tmp,'firmware/c08b-bringup/tools/decode_bringup.py'),'# ok\n');record(tmp,'a'.repeat(40));assert.equal(verify(tmp).commit,'a'.repeat(40));
 writeFileSync(path.join(tmp,'app/dist/main.js'),'旧包混入');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'b'.repeat(40));writeFileSync(path.join(tmp,'app/electron/extra.cjs'),'额外代码');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'c'.repeat(40));writeFileSync(path.join(tmp,'app/package.json'),'{"main":"bad.cjs"}');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'d'.repeat(40));writeFileSync(path.join(tmp,'python/extra.py'),'bad');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'e'.repeat(40));mkdirSync(path.join(tmp,'python/__pycache__'));writeFileSync(path.join(tmp,'python/__pycache__/old.pyc'),'旧缓存');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'f'.repeat(40));writeFileSync(path.join(tmp,'python/__pycache__/old.pyc'),'替换缓存');assert.throws(()=>verify(tmp),/不一致/);
 record(tmp,'0'.repeat(40));writeFileSync(path.join(tmp,'firmware/c08b-bringup/tools/extra.pyc'),'篡改固件工具');assert.throws(()=>verify(tmp),/不一致/);
 rmSync(path.join(tmp,'firmware'),{recursive:true,force:true});assert.throws(()=>verify(tmp),/不一致/);assert.throws(()=>record(tmp,'1'.repeat(40)),/firmware/);
 console.log('构建来源检查：原包通过、篡改和多余文件及缺失固件目录均拒绝');
} finally {rmSync(tmp,{recursive:true,force:true});}
