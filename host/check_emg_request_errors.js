const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/emg_guide.html','utf8');
const error={};const box={$:()=>error,H:{},fetch:null};vm.createContext(box);
vm.runInContext(html.slice(html.indexOf('function showActionError'),html.indexOf('const mem ='))+'\nglobalThis.send=post;',box);
(async()=>{
 box.fetch=async()=>({ok:false,status:400,json:async()=>({error:'已达上限'})});
 assert.equal((await box.send('/record',{})).error,'已达上限');assert.equal(error.hidden,false);assert.equal(error.textContent,'已达上限');
 box.fetch=async()=>{throw Error('offline')};assert.match((await box.send('/record',{})).error,/连接/);
 box.fetch=async()=>({ok:true,json:async()=>({ok:true})});await box.send('/record',{});assert.equal(error.hidden,true);
 assert(!html.includes('alert(r.error)'),'embedded errors must not depend on modal dialogs');
 console.log('PASS: server and network errors visible without modals; successful retry clears error');
})().catch(e=>{console.error(e);process.exitCode=1});
