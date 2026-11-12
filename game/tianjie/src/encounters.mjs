import {LAKE_OFFSET,LAKE_ENTRY} from './bridge-route.mjs';
export const ENCOUNTERS = [
 {name:'失序山门',subtitle:'破开山门，找回掌纹中的路',camera:{x:0,z:13},enemies:[
  {id:'gate-wisp',kind:'wisp',name:'游魇',hp:88,x:-5,z:-3,delay:1.8},
  {id:'gate-shade',kind:'shade',name:'掠影',hp:104,x:5,z:-8,delay:3.6},
  {id:'gate-keeper',kind:'keeper',name:'守山夜魇',hp:240,x:0,z:-15,delay:6},
 ]},
 {name:'悬天索桥',subtitle:'一线悬桥，云下有魇 · 连剑截断蜻蜓妖扑击',camera:{x:0,z:-43},enemies:[
  {id:'bridge-shade',kind:'manta',name:'巡云鳐',hp:112,x:-4,z:-58,delay:.9},
  {id:'bridge-wisp',kind:'manta',name:'裂风云鳐',hp:96,x:4,z:-53,delay:2.6},
  {id:'bridge-keeper',kind:'dragonfly',name:'琉璃蜻蜓妖',hp:360,x:0,z:-69,delay:5.5},
 ]},
 {name:'镜湖回廊',subtitle:'先结破邪印破镜障，再进攻',camera:{...LAKE_ENTRY},enemies:[
  {id:'lake-reflection-a',kind:'reflection',name:'流光镜影',hp:112,x:LAKE_OFFSET.x+(-4),z:LAKE_OFFSET.z+(-116),delay:1},
  {id:'lake-reflection-b',kind:'reflection',name:'寒玉镜影',hp:112,x:LAKE_OFFSET.x+(4),z:LAKE_OFFSET.z+(-120),delay:2.3},
  {id:'lake-mirror',kind:'mirror',name:'镜湖灵魄',hp:288,x:LAKE_OFFSET.x+(0),z:LAKE_OFFSET.z+(-128),delay:4.5},
 ]},
 {name:'雷狱天台',subtitle:'避开地面雷圈，以五雷诀破甲',camera:{x:0,z:-155},enemies:[
  {id:'storm-phoenix',kind:'phoenix',name:'焚羽妖凰',hp:156,x:-5,z:-168,delay:1},
  {id:'storm-golem',kind:'golem',name:'雷铸石傀',hp:220,x:5,z:-172,delay:2.8},
  {id:'storm-lord',kind:'thunderlord',name:'执雷天像',hp:420,x:0,z:-181,delay:5.5},
 ]},
];
export const enemyConfig = id => ENCOUNTERS.flatMap(a=>a.enemies).find(e=>e.id===id);

export const TOTAL_ENEMIES = ENCOUNTERS.reduce((n,a)=>n+a.enemies.length,0);
