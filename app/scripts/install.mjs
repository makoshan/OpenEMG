// 统一安装入口：先 --check；用户允许退出后关掉App，再 --install。拒绝旧源码、篡改包和运行中覆盖。
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, renameSync, appendFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { randomUUID } from 'node:crypto';
import { verify } from './package-provenance.mjs';
import { runningUnder } from './running.mjs';
const [source, expected, mode='--check']=process.argv.slice(2);
if(!source||!expected||!['--check','--install'].includes(mode))throw Error('用法：node scripts/install.mjs <新.app绝对路径> <完整提交号> [--check|--install]');
const target='/Applications/OpenEMG.app';
// 2026-10-16 改名前的安装位置：装新包时一并挪进备份，不留两个 App（数据目录是同一个）
const legacy='/Applications/原力手环.app';
if([target,legacy].includes(path.resolve(source)))throw Error('源包不能是已安装目录');
const git=(...args)=>execFileSync('git',args,{encoding:'utf8'}).trim();
const info=verify(path.join(source,'Contents/Resources'));
if(info.commit!==expected)throw Error('目标提交号不匹配');
const sameBuild=root=>{const next=verify(root);if(next.commit!==expected||JSON.stringify(next.files)!==JSON.stringify(info.files))throw Error('复制期间源包被替换，拒绝安装');return next;};
const cache=path.join(os.homedir(),'.cache/yuanli-app-backup');mkdirSync(cache,{recursive:true});
const lock=path.join(cache,'install.lock');
let locked=false, staged=null;
try {
 if(mode==='--install'){
  try{mkdirSync(lock);}catch{throw Error('已有安装任务持锁，请先确认该任务已结束：'+lock);}
  locked=true;writeFileSync(path.join(lock,'owner.json'),JSON.stringify({pid:process.pid,commit:info.commit}));
 }
 const check=()=>{
  git('fetch','origin');git('merge-base','--is-ancestor','origin/main',info.commit);
  let previous=null;
  const installed=existsSync(target)?target:legacy;
  if(existsSync(installed+'/Contents/Resources/build-info.json')){previous=verify(installed+'/Contents/Resources').commit;git('merge-base','--is-ancestor',previous,info.commit);}
  if(mode==='--install'){
   if(runningUnder(target+'/Contents/')||runningUnder(legacy+'/Contents/'))throw Error('App或采集服务仍运行，先正常退出，不覆盖运行包');
  }
  return previous;
 };
 let previous=check();console.log(JSON.stringify({checked:true,commit:info.commit,previous:previous??'旧包无来源清单'}));
 if(mode==='--install'){
  staged=target+'.new-'+randomUUID();execFileSync('ditto',[source,staged]);sameBuild(staged+'/Contents/Resources');
  previous=check(); // 长复制结束后再核主干、旧包和进程，锁外的手动安装也不能被静默覆盖。
  const backup=path.join(cache,'verified-'+Date.now()+'-'+randomUUID().slice(0,8));mkdirSync(backup);
  const old=path.join(backup,'OpenEMG.app'),oldLegacy=path.join(backup,'原力手环.app');
  if(existsSync(target))renameSync(target,old);
  try{if(existsSync(legacy))renameSync(legacy,oldLegacy);renameSync(staged,target);staged=null;sameBuild(target+'/Contents/Resources');}
  catch(e){if(existsSync(target))renameSync(target,path.join(backup,'failed-new.app'));if(existsSync(old))renameSync(old,target);if(existsSync(oldLegacy))renameSync(oldLegacy,legacy);throw e;}
  appendFileSync(path.join(cache,'installations.jsonl'),JSON.stringify({at:new Date().toISOString(),commit:info.commit,previous,backup})+'\n');
  console.log('已安装并读回校验：'+info.commit+'；备份：'+backup);
 }
} finally {if(staged&&existsSync(staged))rmSync(staged,{recursive:true,force:true});if(locked)rmSync(lock,{recursive:true});}
