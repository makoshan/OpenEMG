// Run: node firmware/check_emg_guide.js (no board or browser required).
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const elements = new Map(), context = new Proxy({}, { get: (o, k) => o[k] || (() => {}) });
const sandbox = { console, Date, URLSearchParams, location: {search: ''}, devicePixelRatio: 1, localStorage: { getItem: () => null, setItem() {} },
  document: { getElementById(id) { if (!elements.has(id)) elements.set(id, { style: {}, clientWidth: 500, getContext: () => context }); return elements.get(id); } },
  requestAnimationFrame(fn) { sandbox.paint = fn; }, setInterval() {}, setTimeout() {}, addEventListener() {}, fetch: () => new Promise(() => {}),
  EventSource: class { constructor() { sandbox.stream = this; } },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(__dirname + '/emg_demo.js', 'utf8'), sandbox);
const html = fs.readFileSync(__dirname + '/emg_guide.html', 'utf8');
vm.runInContext(html.match(/<script>\s*([\s\S]*?)<\/script>/)[1], sandbox);
for (let i = 0; i < 250; i++) sandbox.stream.onmessage({ data: `S ${i * 10} 10 2048 2050 2060 2100 2048 2000 2030 2048 2050 2048` });
assert.equal(vm.runInContext('traces.every(a => a.length === 2000 && a.every(Number.isFinite))', sandbox), true);
assert.equal(vm.runInContext('traces[0][0] === 2048 && traces[2].every(v => v >= 0)', sandbox), true);
vm.runInContext('drawSignals()', sandbox);
assert.match(elements.get('signalStatus').textContent, /实时更新/);
vm.runInContext("st.busy = '录 rest'; st.progress = {phase: 'NOW'}; drawSignals()", sandbox);
assert.match(elements.get('signalStatus').textContent, /录制中 · 实时波形/);
const cuePosts = [];
sandbox.fetch = (url, opts) => { if (String(url).includes('cue-shown')) cuePosts.push(JSON.parse(opts.body)); return Promise.resolve({ json: async () => ({ ok: true }) }); };
sandbox.stream.onmessage({ data: 'CUE ' + JSON.stringify({ phase: '准备录制', label: 'pinch', take: 1, count: 1 }) });
assert.equal(elements.get('big').textContent, '准备录制');
assert.equal(cuePosts.length, 0, '准备录制 must not be reported as the cue');
sandbox.stream.onmessage({ data: 'CUE ' + JSON.stringify({ phase: 'NOW', recording_ack_host_ns: '1700000000000000000', label: 'pinch', take: 1, count: 1 }) });
assert.equal(elements.get('big').textContent, '做！');
assert.equal(cuePosts.length, 1);
assert.equal(typeof cuePosts[0].shown_ms, 'number');
assert.ok(cuePosts[0].shown_ms > 1e12);
assert.equal(cuePosts[0].recording_ack_host_ns, '1700000000000000000');
console.log('Cue clock: 做！ reports shown_ms; 准备录制 does not');
vm.runInContext('st.busy = null; lastSignal = 0; drawSignals()', sandbox);
assert.match(elements.get('signalStatus').textContent, /曲线已暂停/);
sandbox.stream.onmessage({ data: 'S 3000 10 2048 2048 2048 2048 2048 2048 2048 2048 2048 2048' });
assert.equal(vm.runInContext('traces[0].length', sandbox), 10, 'gap must not join two disconnected recordings');
console.log('EMG guide: three real signal traces, bounded history, recording/stale status and gap reset passed');

vm.runInContext("st.gesture_counts={train:{rest:30,light:30,hard:30},validation:{},test:{}}", sandbox);
assert.equal(vm.runInContext('current().label',sandbox),'pinch','old effort labels must not complete new gestures');
vm.runInContext("st.gesture_counts={train:{rest:30,pinch:30,rub:30,snap:30,fist:30},validation:{},test:{}}",sandbox);
assert.equal(vm.runInContext('current().id',sandbox),'validationWear');
// Re-recording one label (rub redefined): other labels already have validation samples, rewear must still be asked.
vm.runInContext("st.gesture_counts={train:{rest:30,pinch:30,rub:30,snap:30,fist:30},validation:{rest:10,pinch:10,rub:0,snap:10,fist:10},test:{rest:10,pinch:10,rub:0,snap:10,fist:10}}",sandbox);
assert.equal(vm.runInContext('current().id',sandbox),'validationWear');
vm.runInContext("st.gesture_counts.validation.rub=10",sandbox);
assert.equal(vm.runInContext('current().id',sandbox),'testWear');
console.log('Guide steps: five gesture labels and independent validation stage passed');
vm.runInContext("st.gesture_counts={train:{rest:30,pinch:30,rub:30,snap:30,fist:30},validation:{rest:10,pinch:10,rub:10,snap:10,fist:10},test:{rest:10,pinch:10,rub:10,snap:10,fist:10}}; st.rehearsal={training_eligible:false}; render()", sandbox);
assert.match(elements.get('cue').textContent, /本轮不用于训练/, 'legacy five-class completion must not read as trainable');
assert.equal(elements.get('trainingLink').hidden, true);
assert.match(elements.get('go').textContent, /先预演 5 条/);
vm.runInContext("st.rehearsal={training_eligible:true}; render()", sandbox);
assert.equal(elements.get('cue').textContent, '五类数据已采齐');
assert.equal(elements.get('trainingLink').hidden, false);
console.log('Legacy completion: title gated on rehearsal.training_eligible passed');

vm.runInContext('lastSignal = 0; wornNow = true; updateWearStatus()', sandbox);
assert.match(elements.get('wtxt').textContent, /无法判断接触/);
assert.equal(vm.runInContext('wornNow', sandbox), false);
vm.runInContext('lastSignal = Date.now(); wornNow = false; updateWearStatus()', sandbox);
assert.match(elements.get('wtxt').textContent, /接触检测未通过/);
vm.runInContext('wornNow = true; updateWearStatus()', sandbox);
assert.equal(elements.get('wtxt').textContent, '电极贴着');
console.log('Wear status: missing signal cannot claim bad electrode contact PASS');

const scopeSandbox = { ...sandbox, location:{search:'?view=scope'}, document:{...sandbox.document,body:{classList:{add(){}}},querySelector(){return {}}} };
scopeSandbox.EventSource=class { constructor(){scopeSandbox.stream=this;} };
vm.createContext(scopeSandbox);
vm.runInContext(fs.readFileSync(__dirname + '/emg_demo.js', 'utf8'), scopeSandbox);
vm.runInContext(html.match(/<script>\s*([\s\S]*?)<\/script>/)[1], scopeSandbox);
for(let i=0;i<1100;i++)scopeSandbox.stream.onmessage({data:`S ${i*10} 10 2048 2050 2060 2100 2048 2000 2030 2048 2050 2048`});
assert.equal(vm.runInContext('traces[0].length',scopeSandbox),10000);
vm.runInContext("windowSamples=10000; $('freeze').onclick()",scopeSandbox);
const snapshot=vm.runInContext('JSON.stringify(visibleTraces())',scopeSandbox);
scopeSandbox.stream.onmessage({data:'S 11000 10 2001 2001 2001 2001 2001 2001 2001 2001 2001 2001'});
assert.equal(vm.runInContext('JSON.stringify(visibleTraces())',scopeSandbox),snapshot,'pause must freeze display');
assert.equal(vm.runInContext('traces[0].at(-1)',scopeSandbox),2001,'pause must not stop receiving');
vm.runInContext("$('freeze').onclick(); drawSignals()",scopeSandbox);
assert.notEqual(vm.runInContext('JSON.stringify(visibleTraces())',scopeSandbox),snapshot,'resume must return to live samples');
console.log('Scope: 10 s bounded history, pause snapshot, continued acquisition and resume PASS');
// Locked ranges must survive a stronger signal; auto range must include it again.
elements.get('autoScale').checked = true;
vm.runInContext('drawSignals()', sandbox);
const lockedRanges = vm.runInContext('JSON.stringify(plotRanges)', sandbox);
elements.get('autoScale').checked = false;
vm.runInContext('traces[1].push(9000); drawSignals()', sandbox);
assert.equal(vm.runInContext('JSON.stringify(plotRanges)', sandbox), lockedRanges);
elements.get('autoScale').checked = true;
vm.runInContext('drawSignals()', sandbox);
assert.ok(vm.runInContext('plotRanges[1][1] > 9000', sandbox));
console.log('Plot ranges: lock preserves comparison scale; auto includes new peaks PASS');

assert.equal(vm.runInContext('env.n', sandbox), 20);
assert.equal(typeof sandbox.paint, 'function');
vm.runInContext('shown=42; paintFrame()', sandbox);
assert.equal(elements.get('mv').textContent, '42');
elements.get('envelopeWindow').value='100'; elements.get('envelopeWindow').onchange();
assert.equal(vm.runInContext('env.n',scopeSandbox),100);
assert.equal(vm.runInContext('traces[0].length',scopeSandbox),0);
assert.doesNotMatch(html, /transition:height|shown \* \.7/);
console.log('Low latency display: animation frames, direct meter, selectable RMS window PASS');

const stored = new Map();
scopeSandbox.localStorage.getItem = key => stored.get(key) || null;
scopeSandbox.localStorage.setItem = (key,value) => stored.set(key,value);
vm.runInContext(`st.busy=null; st.gesture_counts={train:{rest:30,pinch:30,rub:30,snap:30,fist:30},validation:{rest:10,pinch:10,rub:10,snap:1,fist:0},test:{}};st.capture_issue={label:'snap',split:'validation',reason:'SMR',stopped:true}; mem.set('emg.rewear.validationWear','1'); render();`,scopeSandbox);
assert.equal(vm.runInContext('current().label',scopeSandbox),'snap');
vm.runInContext('deferButton.onclick()',scopeSandbox);
assert.equal(vm.runInContext('current().label',scopeSandbox),'fist');
assert.equal(vm.runInContext('st.gesture_counts.validation.snap',scopeSandbox),1);
assert.equal(elements.get('captureIssue').hidden,true);
vm.runInContext('resumeButton.onclick()',scopeSandbox);
assert.equal(vm.runInContext('current().label',scopeSandbox),'snap');
console.log('Deferred quality failure: next action, honest counts, return to pending action PASS');

// Dedicated training page: no acquisition stream, truthful task state and next action.
const trainingElements = new Map();
let streamsOpened = 0;
const trainingSandbox = { ...sandbox, location:{search:'?view=train&project=fixture'},
  document:{body:{classList:{add(){}}},querySelector(){return {style:{}}},getElementById(id){if(!trainingElements.has(id))trainingElements.set(id,{style:{},getContext:()=>context});return trainingElements.get(id);}},
  EventSource:class {constructor(){streamsOpened++;}},requestAnimationFrame(){throw Error('training page must not draw live signals');} };
vm.createContext(trainingSandbox);
vm.runInContext(fs.readFileSync(__dirname+'/emg_demo.js','utf8'),trainingSandbox);
vm.runInContext(html.match(/<script>\s*([\s\S]*?)<\/script>/)[1],trainingSandbox);
assert.equal(streamsOpened,0);
vm.runInContext('render()',trainingSandbox);
assert.equal(trainingElements.get('trainingPanel').hidden,false);
assert.equal(trainingElements.get('trainStart').disabled,true);
assert.match(trainingElements.get('trainNext').textContent,/返回采集/);
vm.runInContext("st.gesture_counts=Object.fromEntries(['train','validation','test'].map(s=>[s,Object.fromEntries(ACTIONS.map(([l])=>[l,s==='train'?30:10]))]));st.busy='五类训练';render()",trainingSandbox);
assert.equal(trainingElements.get('trainProgress').hidden,false);
assert.match(trainingElements.get('trainPhase').textContent,/正在训练与验证/);
assert.match(trainingElements.get('trainNext').textContent,/尚未提供逐轮进度/);
vm.runInContext("st.busy=null;st.gesture_training={runs:[{id:'fixture',model:'lda',validation:{balanced_accuracy:.5,recall:{rest:.5},labels:['rest'],confusion:[[5]]},warnings:[],note:'fixture'}]};render()",trainingSandbox);
assert.match(trainingElements.get('trainNext').textContent,/先试 SVM/);
assert.equal(trainingElements.get('trainEvaluate').disabled,true);
vm.runInContext("st.gesture_training.runs[0].test={balanced_accuracy:.6};render()",trainingSandbox);
assert.match(trainingElements.get('trainNext').textContent,/新采集的独立测试集/);
vm.runInContext("st.log=['五类训练 出错：fixture'];render()",trainingSandbox);
assert.match(trainingElements.get('trainPhase').textContent,/失败/);
assert.match(trainingElements.get('trainNext').textContent,/不代表本次/);
assert.match(html,/body button:not\(\.ghost\)\{color:var\(--panel\)\}/);
assert.doesNotMatch(html,/<progress[^>]*value=/,'no fabricated training percentage');
console.log('Training workspace: no stream, data gate, busy progress, low-score advice and failure state PASS');

// Recommendations select existing reports; they never silently train or open test data.
vm.runInContext("st.log=[];st.gesture_training={runs:['lda','svm','cnn'].map((model,i)=>({id:model,model,validation:{balanced_accuracy:i===1?.66:.5,recall:{pinch:.2,rub:.3},labels:['pinch','rub'],confusion:[[2,8],[7,3]]},warnings:['样本工频提醒'],note:''}))};$('trainRun').value='cnn';render()",trainingSandbox);
assert.match(trainingElements.get('decisionTitle').textContent,/SVM/);
trainingElements.get('decisionAction').onclick();
assert.equal(trainingElements.get('trainRun').value,'svm');
assert.match(trainingElements.get('confusionLead').textContent,/捏合 → 搓动，8\/10/);
assert.match(trainingElements.get('decisionText').textContent,/3 个模型，3 个出现 捏合 → 搓动 至少 2 次，没有一个能把两者分开。这两类在当前单通道数据上难分/);
assert.doesNotMatch(trainingElements.get('decisionText').textContent,/工频/);
assert.match(trainingElements.get('friendlyResult').textContent,/捏合/);
vm.runInContext("st.gesture_training.runs[1].validation.balanced_accuracy=.82;render()",trainingSandbox);
assert.equal(trainingElements.get('trainEvaluate').disabled,false);
vm.runInContext("st.gesture_training.frozen='svm';render()",trainingSandbox);
assert.match(trainingElements.get('decisionTitle').textContent,/已选定/);
assert.equal(trainingElements.get('decisionAction').hidden,true);
console.log('Action advice: compare existing best, inspect data, validation gate and frozen state PASS');

vm.runInContext("trainingUnavailable('fixture disconnect')",trainingSandbox);
assert.equal(trainingElements.get('trainStart').disabled,true);
assert.equal(trainingElements.get('trainEvaluate').disabled,true);
assert.equal(trainingElements.get('trainProgress').hidden,true);
assert.match(trainingElements.get('trainPhase').textContent,/不可用/);
assert.match(trainingElements.get('trainNext').textContent,/重新连接/);
assert.equal(trainingElements.get('trainRun').disabled,true,'stale report selection must not re-enable actions');
(async () => {
  // End the fixture's intentionally unresolved startup fetch before testing failures.
  vm.runInContext('refreshing=false',trainingSandbox);
  trainingSandbox.fetch = async () => { throw Error('offline'); };
  await vm.runInContext('refresh()',trainingSandbox);
  assert.match(trainingElements.get('trainStatus').textContent,/无法连接/);
  trainingSandbox.fetch = async () => ({json:async()=>({project:{id:'other'}})});
  await vm.runInContext('refresh()',trainingSandbox);
  assert.match(trainingElements.get('trainStatus').textContent,/其他工程/);
  console.log('Training service disconnect and project mismatch disable actions PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
// Historical high scores from other samples must not drive recommendations.
vm.runInContext(`st.busy=null;st.log=[];st.gesture_training={runs:[{id:'current',dataset_id:'new',model:'svm',validation:{balanced_accuracy:.62,recall:{pinch:.2},labels:['pinch'],confusion:[[2]]},warnings:[]},{id:'old',dataset_id:'old',model:'rf',validation:{balanced_accuracy:.99,recall:{pinch:1},labels:['pinch'],confusion:[[10]]},warnings:[]}]};$('trainRun').value='current';render()`,trainingSandbox);
assert.doesNotMatch(trainingElements.get('decisionText').textContent,/99%/);
console.log('Comparison excludes historical datasets PASS');
// The Mac-hosted training page may visualize saved results, but must not invent absent training scores.
vm.runInContext(`st.busy=null;st.log=[];st.gesture_training={frozen:null,runs:[
 {id:'svm-chart',dataset_id:'chart',model:'svm',training:{balanced_accuracy:.98},validation:{balanced_accuracy:.54,recall:{rub:.1},labels:['rub'],confusion:[[1]]},warnings:[],note:''},
 {id:'lda-chart',dataset_id:'chart',model:'lda',validation:{balanced_accuracy:.66,recall:{rub:.1},labels:['rub'],confusion:[[1]]},warnings:[],note:''}
]};$('trainRun').value='svm-chart';render()`, trainingSandbox);
assert.match(trainingElements.get('scoreChart').innerHTML, /98%|54%|66%/);
assert.match(trainingElements.get('scoreNote').textContent, /训练 98.0%，重戴 54.0%/);
vm.runInContext("$('trainRun').value='lda-chart';render()", trainingSandbox);
assert.match(trainingElements.get('scoreNote').textContent, /没有保存训练集预测/);
console.log('Result chart: same-dataset rewear bars and absent-training disclosure PASS');
vm.runInContext("st.busy=null;st.gesture_training={frozen:null,runs:['lda','svm','cnn'].map(model=>({id:model+'-spread',dataset_id:'spread',model,validation:{balanced_accuracy:model==='svm'?.41:.4,recall:{rest:.4},labels:['rest','pinch','rub'],confusion:[[4,3,3],[3,4,3],[3,3,4]]},warnings:['样本工频提醒'],note:''}))};$('trainRun').value='svm-spread';render()", trainingSandbox);
trainingElements.get('qualityDetails').open = false;
assert.match(trainingElements.get('decisionText').textContent, /工频/);
assert.doesNotMatch(trainingElements.get('decisionText').textContent, /难分/);
trainingElements.get('decisionAction').onclick();
assert.equal(trainingElements.get('qualityDetails').open, true);
console.log('Spread errors still point at mains hum PASS');
// Two sample lists that differ only in rub must say so. The same lists must not.
vm.runInContext(`st.busy=null;st.log=[];st.gesture_training={frozen:null,runs:[
 {id:'20260928-120000-svm-new',dataset_id:'new',model:'svm',samples:{rest:'aa',pinch:'bb',rub:'newrub',snap:'cc',fist:'dd'},validation:{balanced_accuracy:.62,recall:{pinch:.2},labels:['rest','pinch','rub','snap','fist'],confusion:[[7,3,0,0,0],[8,2,0,0,0],[0,0,8,2,0],[0,0,0,9,1],[0,1,0,2,7]]},warnings:[],note:''},
 {id:'20260927-120000-svm-old',dataset_id:'old',model:'svm',samples:{rest:'aa',pinch:'bb',rub:'oldrub',snap:'cc',fist:'dd'},validation:{balanced_accuracy:.8,recall:{pinch:.8},labels:['rest','pinch','rub','snap','fist'],confusion:[[8,1,1,0,0],[2,8,0,0,0],[0,4,1,4,1],[0,0,0,8,2],[0,0,2,0,8]]},warnings:[],note:''}
]};$('trainRun').value='20260928-120000-svm-new';render()`, trainingSandbox);
assert.match(trainingElements.get('datasetDelta').textContent, /只有搓动换了/);
assert.match(trainingElements.get('datasetDelta').textContent, /捏合样本没变，识别从 8\/10 降到 2\/10/);
assert.match(trainingElements.get('confusionLead').textContent, /捏合 → 放松，8\/10/);
vm.runInContext(`st.gesture_training.runs[0].samples.rub='oldrub';render()`, trainingSandbox);
assert.doesNotMatch(trainingElements.get('datasetDelta').textContent || '', /只有搓动换了/);
console.log('Dataset fingerprint: only rub changed PASS');
// Real service lists "20260928-tuned-v1-*" (old data, no time) before "20260928-170809-*"; first load must pick the newest.
vm.runInContext(`st.gesture_training={frozen:null,runs:['20260928-tuned-v1-svm','20260928-170809-lda'].map(id=>({id,model:'svm',validation:{balanced_accuracy:.6,recall:{rest:.6},labels:['rest'],confusion:[[6]]},warnings:[],note:''}))};$('trainRun').value='';render()`, trainingSandbox);
assert.equal(trainingElements.get('trainRun').value, '20260928-170809-lda');
assert.match(trainingElements.get('trainRun').innerHTML, /^<option value="20260928-170809-lda"/);
console.log('Training page opens on the newest timestamped run PASS');
// The best model confusing a pair is not "hard on one channel" when a peer on the same data separates it (real case: LDA+features fist→rub 4/10, shape SVM 0/10).
vm.runInContext(`st.gesture_training={frozen:null,runs:[['lda',.7,[[2,8],[1,9]]],['svm',.6,[[10,0],[5,5]]],['cnn',.5,[[3,7],[3,7]]]].map(([model,score,confusion])=>({id:model+'-pair',dataset_id:'pair',model,validation:{balanced_accuracy:score,recall:{pinch:.2},labels:['pinch','rub'],confusion},warnings:[],note:''}))};$('trainRun').value='lda-pair';render()`, trainingSandbox);
assert.match(trainingElements.get('decisionTitle').textContent, /先别改动作，捏合和搓动信号里分得开/);
assert.match(trainingElements.get('decisionText').textContent, /SVM的 捏合 → 搓动 只有 0\/10，捏合认对 10\/10；当前模型是 8\/10/);
assert.doesNotMatch(trainingElements.get('decisionText').textContent, /难分/);
assert.equal(trainingElements.get('decisionAction').hidden, true, 'no jump: the lower-scoring peer would bounce straight back');
// The shape SVM named by that advice must stay in the score chart next to a newer plain SVM.
vm.runInContext(`st.gesture_training.runs.push({id:'20260928-130609-svm-shape',dataset_id:'pair',model:'svm',representation:'rms-shape-v1',validation:{balanced_accuracy:.66,recall:{pinch:.2},labels:['pinch','rub'],confusion:[[2,8],[2,8]]},warnings:[],note:''});render()`, trainingSandbox);
assert.match(trainingElements.get('scoreChart').innerHTML, /SVM · 归一化包络[\s\S]*66%/);
assert.match(trainingElements.get('scoreChart').innerHTML, /<span>SVM<\/span>[\s\S]*60%/);
console.log('Pair advice: a peer that separates the pair beats "hard on one channel" PASS');
// Real case 2026-09-29: rub/snap validation archived as same-wear. Ranking, gating and the worst cell use only re-worn classes.
vm.runInContext(`st.gesture_training={frozen:null,runs:[
 {id:'20260928-170809-lda',dataset_id:'sw',model:'lda',rewear:{excluded:['rub','snap'],score:.6},validation:{balanced_accuracy:.72,recall:{rest:.8,pinch:.6,rub:1,snap:1,fist:.4},labels:['rest','pinch','rub','snap','fist'],confusion:[[8,2,0,0,0],[4,6,0,0,0],[0,0,10,0,0],[0,0,0,10,0],[0,0,3,3,4]]},warnings:[],note:''},
 {id:'20260928-170740-svm',dataset_id:'sw',model:'svm',rewear:{excluded:['rub','snap'],score:.7},validation:{balanced_accuracy:.62,recall:{rest:.7,pinch:.7,rub:.1,snap:.7,fist:.7},labels:['rest','pinch','rub','snap','fist'],confusion:[[7,3,0,0,0],[3,7,0,0,0],[0,9,1,0,0],[0,0,0,7,3],[0,0,1,2,7]]},warnings:[],note:''},
 {id:'20260928-170700-cnn',dataset_id:'sw',model:'cnn',rewear:{excluded:['rub','snap'],score:.5},validation:{balanced_accuracy:.5,recall:{rest:.5},labels:['rest','pinch','rub','snap','fist'],confusion:[[5,5,0,0,0],[5,5,0,0,0],[0,0,5,5,0],[0,0,5,5,0],[0,0,5,0,5]]},warnings:[],note:''}]};$('trainRun').value='';render()`, trainingSandbox);
assert.match(trainingElements.get('decisionTitle').textContent, /先查看表现更好的 SVM/, 'rank by re-worn classes, not the five-class 72%');
assert.match(trainingElements.get('trainRun').innerHTML, /重戴 3 类 60%/);
assert.match(trainingElements.get('friendlyResult').textContent, /真实重戴的放松、捏合、握拳平均识别率 60%（搓动、响指的验证是同次佩戴，不计入）/);
assert.match(trainingElements.get('scoreChart').innerHTML, /SVM[\s\S]*70%[\s\S]*LDA[\s\S]*60%/);
vm.runInContext(`$('trainRun').value='20260928-170740-svm';render()`, trainingSandbox);
assert.doesNotMatch(trainingElements.get('confusionLead').textContent, /^搓动/, 'a same-wear row must not be the headline');
assert.match(trainingElements.get('confusionGrid').innerHTML, /搓动、响指的验证是同次佩戴/);
assert.equal((trainingElements.get('confusionGrid').innerHTML.match(/class="same-wear"/g) || []).length, 2, 'dim exactly the two same-wear rows');
console.log('Same-wear validation: ranking, labels and worst cell use re-worn classes only PASS');

const diagnosticSandbox = {...sandbox, location:{search:'?diagnostic=1'}, document:{...sandbox.document}};
vm.createContext(diagnosticSandbox);
vm.runInContext(fs.readFileSync(__dirname + '/emg_demo.js', 'utf8'), diagnosticSandbox);
vm.runInContext(html.match(/<script>\s*([\s\S]*?)<\/script>/)[1], diagnosticSandbox);
assert.equal(vm.runInContext('STEPS.filter(s=>s.n).length', diagnosticSandbox),45);
assert.equal(vm.runInContext("STEPS.filter(s=>s.id?.startsWith('diagnosticWear')).length", diagnosticSandbox),3);
vm.runInContext("st.diagnostic={confirmed:[1],counts:{'wear-1':{rest:0,pinch:0,rub:0}}}; st.gesture_counts={train:{rest:30,pinch:30,rub:30}}", diagnosticSandbox);
assert.equal(vm.runInContext('current().set', diagnosticSandbox),'wear-1');
assert.equal(vm.runInContext('have(current())', diagnosticSandbox),0);
console.log('Diagnostic guide: 45 interleaved takes, three wear confirmations, old counts excluded PASS');


const factorSandbox = {...sandbox, location:{search:'?factorcheck=1'}, document:{...sandbox.document}};
vm.createContext(factorSandbox);
vm.runInContext(fs.readFileSync(__dirname + '/emg_demo.js', 'utf8'), factorSandbox);
vm.runInContext(html.match(/<script>\s*([\s\S]*?)<\/script>/)[1], factorSandbox);
assert.equal(vm.runInContext('STEPS.filter(s=>s.n).length', factorSandbox), 15);
assert.equal(vm.runInContext("STEPS.filter(s=>s.set==='train' || s.set==='test' || s.label==='snap' || s.label==='fist').length", factorSandbox), 0);
assert.equal(vm.runInContext("JSON.stringify(STEPS.filter(s=>s.n).map(s=>s.label))", factorSandbox), JSON.stringify(['rest','pinch','rub','rest','pinch','rub','rest','pinch','rub','rest','pinch','rub','rest','pinch','rub']));
assert.match(vm.runInContext("STEPS.find(s=>s.label==='pinch').hint", factorSandbox), /不要握拳/);
assert.match(vm.runInContext("STEPS.find(s=>s.id==='factorWear').hint", factorSandbox), /只改一个条件/);
vm.runInContext("st.factor_check={confirmed:[1],counts:{'wear-1':{rest:1,pinch:0,rub:0}}}; st.gesture_counts={train:{rest:30,pinch:30,rub:30}}", factorSandbox);
assert.equal(vm.runInContext('current().label', factorSandbox), 'pinch');
assert.equal(vm.runInContext('have(current())', factorSandbox), 0);
console.log('Factor check: one wear, rest/pinch/rub alternate, old counts excluded PASS');

vm.runInContext("st.gesture_training={get runs(){throw Error('capture read training reports')}};render()",sandbox);
console.log('Capture render skips hidden model reports PASS');

const rehearsalSandbox = {...sandbox, location:{search:'?rehearsal=1'}, document:{...sandbox.document},performance:{now:()=>1000}};
rehearsalSandbox.EventSource=class {constructor(){rehearsalSandbox.stream=this;}};
vm.createContext(rehearsalSandbox);
vm.runInContext(fs.readFileSync(__dirname+'/emg_demo.js','utf8'),rehearsalSandbox);
vm.runInContext(html.match(/<script>\s*([\s\S]*?)<\/script>/)[1],rehearsalSandbox);
assert.equal(vm.runInContext('STEPS.filter(s=>s.n).length',rehearsalSandbox),5);
assert.match(vm.runInContext("STEPS.find(s=>s.label==='rub').hint",rehearsalSandbox),/滑动一次/);
vm.runInContext("st.rehearsal={id:'new',counts:{'wear-1':{rest:0}}};st.gesture_counts={train:{rest:30,pinch:30,rub:30,snap:30,fist:30}}",rehearsalSandbox);
assert.equal(vm.runInContext('current().label',rehearsalSandbox),'rest');
const phasePosts=[];
rehearsalSandbox.fetch=async(u,o)=>{if(u.includes('cue-shown'))phasePosts.push(JSON.parse(o.body));return {ok:true,json:async()=>({})};};
rehearsalSandbox.stream.onmessage({data:'CUE '+JSON.stringify({phase:'NOW',label:'pinch',take:1,count:1,recording_ack_host_ns:'1700000000000000000'})});
vm.runInContext('paintRehearsalCue()',rehearsalSandbox);assert.equal(elements.get('big').textContent,'先放松');
rehearsalSandbox.performance.now=()=>1450;vm.runInContext('paintRehearsalCue()',rehearsalSandbox);assert.equal(elements.get('big').textContent,'做！');
rehearsalSandbox.performance.now=()=>2450;vm.runInContext('paintRehearsalCue()',rehearsalSandbox);assert.equal(elements.get('big').textContent,'松开');
assert.deepEqual(phasePosts.map(p=>p.phase),['relax','action','release']);
vm.runInContext("st.busy=null;st.progress={};st.rehearsal.counts['wear-1']={rest:1,pinch:1,rub:1,snap:1,fist:1};render()",rehearsalSandbox);
assert.equal(elements.get('go').disabled,true);assert.match(elements.get('cue').textContent,/等待检查/);
console.log('Rehearsal: five isolated trials, single rub, timed phase receipts, no automatic training PASS');
