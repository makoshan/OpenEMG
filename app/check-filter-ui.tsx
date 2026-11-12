import React from 'react';
import {createRoot} from 'react-dom/client';
import {CalibrationCapture} from './src/emg8/calibration-capture';
import {PROFILES} from './src/emg8/profiles';
const sleep=(ms=80)=>new Promise(r=>setTimeout(r,ms));
const assert=(ok:unknown,why:string)=>{if(!ok)throw Error(why);};
let now=100000;Date.now=()=>now;
const profile=PROFILES['ghost-seals'];let records=0,stops=0;
const bridge={record:async()=>{records++;return {ok:true};},recordStop:async()=>{stops++;return {ok:true};}};
const noop=()=>{};
const root=createRoot(document.getElementById('root')!);
let st:any={project:{id:'filter-ui'},rig:{kind:'wl8',port:'synthetic',streaming:true},tiers:profile.labels,counts:{train:{wl8:{}}},wl8:{},log:[],busy:false};
let rms:number[]|null=null;
async function render(){root.render(<CalibrationCapture {...{profile,projectId:st.project.id,bridge,st,hand:'left',donning:1,setDonning:noop,placement:'wrist',setPlacement:noop,strap:'',setStrap:noop,setHand:noop,onError:(x:any)=>{throw Error(String(x));},envelope:()=>0,rms,rmsAt:rms?now:0} as any}/>);await sleep();}
const button=()=>[...document.querySelectorAll('button')].find(x=>x.textContent?.includes('开始校准'))!;
async function tick(value:number|null,n=1){for(let i=0;i<n;i++){now+=100;rms=value===null?null:Array(8).fill(value);await render();}}
try{
 await render();assert(button(),'缺开始按钮');assert(button().disabled,'准备期开始按钮必须禁用');assert(records===0,'准备期误录');
 await tick(30,16);assert(!button().disabled,'低幅不能开录');button().click();await sleep();assert(records===1,'首次只能启动一次');
 st={...st,busy:true,progress:{label:profile.labels[0],phase:'NOW',take:1}};await tick(30);
 // 完成首条的同时断流，推进到下一条arm；它必须等待全新有效读数。
 st={...st,busy:false,progress:null,counts:{train:{wl8:{[profile.labels[0]]:1}}}};await tick(null,3);assert(records===1,'断流后的arm误放行');
 await tick(null,15);assert(records===1,'准备期误录');
 await tick(30,20);assert(records===2,'arm恢复低幅后应仅开录一次');assert(stops===0,'低幅恢复被误判接触差暂停');
 st={...st,project:{id:'filter-ui-high'},counts:{train:{wl8:{}}},busy:false,progress:null};await tick(null,2);await tick(500,20);
 assert(button()?.disabled,'真实高幅必须禁止开录');assert(records===2,'高幅误开录');
 console.log('FILTER_UI_PASS 校准实际组件：准备期禁用、下一条arm断流等待、恢复仅录一次、无误暂停、高幅不录');
}catch(e){console.error('FILTER_UI_FAIL '+String(e));root.unmount();}
