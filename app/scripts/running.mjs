// 判断某个 .app 下是否还有进程在跑。macOS 的 ps 在 locale 为空或 C 时把中文路径转义成 M-e… 形式，
// /Applications/原力手环.app 永远匹配不上（2026-10-15 实测：App 在跑也命中 0），所以强制 UTF-8；
// 用 LC_ALL 而不是 LANG，因为用户环境里的 LC_ALL=C 会盖过 LANG。
import { execFileSync, spawn } from 'node:child_process';
import { mkdtempSync, mkdirSync, symlinkSync, rmSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import os from 'node:os';
export const runningUnder=prefix=>execFileSync('ps',['-axo','command='],{encoding:'utf8',env:{...process.env,LC_ALL:'en_US.UTF-8'}})
 .split('\n').some(l=>l.trim().startsWith(prefix));

// 自检：node scripts/running.mjs —— 在中文 .app 路径下起一个 sleep，故意把本进程 locale 设成 C，仍必须认得出来。
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 process.env.LC_ALL='C';process.env.LANG='';
 const dir=mkdtempSync(path.join(os.tmpdir(),'yuanli-running-'));
 const app=path.join(dir,'原力手环自检.app'),bin=path.join(app,'Contents/MacOS');
 mkdirSync(bin,{recursive:true});symlinkSync('/bin/sleep',path.join(bin,'原力手环自检'));
 const child=spawn(path.join(bin,'原力手环自检'),['30']);
 try{
  await new Promise(r=>setTimeout(r,300));
  if(!runningUnder(app+'/Contents/'))throw Error('自检失败：中文路径下的进程在跑却没认出来');
  child.kill();await new Promise(r=>child.once('exit',r));
  if(runningUnder(app+'/Contents/'))throw Error('自检失败：进程已退出仍判为在跑');
  console.log('running.mjs 自检通过：中文路径进程在跑→true，退出后→false');
 }finally{child.kill();rmSync(dir,{recursive:true,force:true});}
}
