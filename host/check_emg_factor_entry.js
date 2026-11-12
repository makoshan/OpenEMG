// Embedded clients prohibit modal dialogs. Exercise the actual entry handlers without them.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/emg_guide.html','utf8');
const elements={factorSetup:{hidden:true},factorCondition:{value:'位置 A · 当前位置',focus(){}},factorError:{},factorConfirm:{},factorCheckStart:{}};
let calls=[];
const box={$:id=>elements[id],st:{},projectId:'project',params:new URLSearchParams('embed=1'),location:{},
 window:{prompt(){throw Error('modal forbidden')}},post:async(u,b)=>{calls.push({u,b});return {id:'new'};}};
vm.createContext(box);
vm.runInContext(html.slice(html.indexOf('async function enterFactorCheck()'),html.indexOf("$('session').value")),box);
(async()=>{
 elements.factorCheckStart.onclick();assert.equal(elements.factorSetup.hidden,false);assert.equal(calls.length,0);
 await elements.factorConfirm.onclick();assert.equal(calls[0].b.factor,'位置 A · 当前位置');assert.match(box.location.href,/factorcheck=1&embed=1/);
 elements.factorCondition.value=' ';await elements.factorConfirm.onclick();assert.equal(calls.length,1);assert.match(elements.factorError.textContent,/填写/);
 elements.factorCondition.value='A';box.post=async()=>({error:'录制中'});await elements.factorConfirm.onclick();assert.equal(elements.factorError.textContent,'录制中');
 box.post=async()=>{throw Error('offline')};await elements.factorConfirm.onclick();assert.match(elements.factorError.textContent,/连接/);assert.equal(elements.factorConfirm.disabled,false);
 box.st.factor_check={id:'existing'};box.post=async(u,b)=>{assert.equal(b.factor,'');return {id:'existing'}};await elements.factorCheckStart.onclick();
 console.log('PASS: modal-free entry, explicit condition, embedded navigation, validation, server/network failures and resume');
})().catch(e=>{console.error(e);process.exitCode=1});
