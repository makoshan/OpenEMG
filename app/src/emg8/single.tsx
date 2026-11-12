'use client';
// 单通道（Cheez + ESP32-S3）工作室：顶栏、五步、卡片和八通道 EmgStudio 一个样（Mako 2026-10-13「单通道的样子跟 8 通道做成一样」）。
// 后端是 host/emg_web.py 单通道接口，经主进程 emg8-single-ipc.cjs 转发；每条 2 秒。
// 动作组：原五类（放松 / 捏合 / 搓动 / 响指 / 握拳），或和八通道同一份清单（emg8-profiles.json）里的任一组——单通道认不认得出要实测（Mako 2026-10-14）。
// 旧引导页的预演 / 诊断 / 三类对照收进「更多录法」（iframe 嵌原页面），主流程只留：录动作 → 训练 → 用手势。
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import type { Result } from '../desktop-bridge';
import { LABEL_CN } from './contract';
import { PROFILES, type ProfileId } from './profiles';
import { grayTitle } from './gray-title';
import { Led, Stepper } from './instrument';
import { Waveform, type WaveHandle } from './wave';
import './emg8.css';
import './thumb-capture.css';
import './single.css';

const GESTURES = ['rest', 'pinch', 'rub', 'snap', 'fist'];
const CN: Record<string, string> = { rest: '放松', pinch: '捏合', rub: '搓动', snap: '响指', fist: '握拳' };
const HOW: Record<string, string> = { rest: '手自然放松，别动', pinch: '拇指食指轻捏一下', rub: '拇指在食指侧面搓三下', snap: '打一个响指', fist: '握一下拳再松开' };
// 'five' = 单通道原五类；其余 = 八通道动作组。训练类别 = labels，录制按钮 = captureLabels ?? labels
type GroupId = 'five' | ProfileId;
// 经典 16 是八通道的「任选动作」流程，单通道不列
const groupIds = ['five', ...Object.keys(PROFILES).filter((k) => PROFILES[k as ProfileId].layout !== 'classic')] as GroupId[];
const groupOf = (id: GroupId) => id === 'five' ? { name: '五类手势（单通道原版）', labels: GESTURES, capture: GESTURES }
  : { name: PROFILES[id].name, labels: PROFILES[id].labels, capture: PROFILES[id].captureLabels ?? PROFILES[id].labels };
const nameOf = (id: GroupId, l: string) => (id === 'five' ? CN[l] : undefined) ?? (id !== 'five' ? PROFILES[id].gestures?.[l]?.name : undefined) ?? LABEL_CN[l] ?? CN[l] ?? l;
const howOf = (id: GroupId, l: string) => (id === 'five' ? HOW[l] : undefined) ?? (id !== 'five' ? PROFILES[id].gestures?.[l]?.cue : undefined) ?? HOW[l] ?? '';
const isRest = (l?: string) => l === 'rest' || !!l?.endsWith('_rest');
type Split = 'train' | 'validation' | 'test';
// 训练脚本的下限（emg_gesture_train.dataset）：训练每类 30 条，验证、测试每类 10 条
const TARGET: Record<Split, number> = { train: 30, validation: 10, test: 10 };
const SPLIT_CN: Record<Split, string> = { train: '训练', validation: '验证', test: '独立测试' };
const MV = 3600 / 4096;                         // ADC 一格 = 0.88 mV（emg_guide.html 同一换算）
const RANGES = [50, 100, 200, 500, 1000];       // 波形量程，ADC 端 mV

type Report = { balanced_accuracy: number; accuracy: number; recall: Record<string, number>; samples: number };
type FiveRun = { id: string; model: string; validation?: Report; test?: Report | null; note?: string };
type Progress = { label?: string; take?: number; count?: number; phase?: string };
export type SingleState = {
  project: { id: string; name: string } | null;
  rig: { port: string | null; kind: string | null; banner: string; streaming: boolean; error?: string };
  gesture_counts: Record<Split, Record<string, number>>;
  busy: string | null; progress: Progress; log: string[];
  capture_issue: { label: string; split: string; reason: string; stopped?: boolean } | null;
  gesture_training: { runs: FiveRun[]; frozen: string | null } | null;
  gesture_group?: string;
  live1: { run_id: string; last: { label: string; raw: string; t: number } | null } | null;
};
type Batch = { type: 'batch'; samples: number[]; worn: number | null; cue: Progress | null; preds: { label: string }[]; t: number } | { type: 'error'; message: string };
export type Emg1Bridge = {
  state: (a?: { group?: GroupId }) => Promise<Result<SingleState>>;
  record: (projectId: string, a: { label: string; split: Split; count: number; group?: GroupId; donning?: number; countdown?: number }) => Promise<Result<{ ok: true }>>;
  recordStop: (projectId: string) => Promise<Result<{ ok: true }>>;
  train: (projectId: string, a: { action: 'train' | 'evaluate'; model?: 'lda' | 'svm'; runId?: string; group?: GroupId }) => Promise<Result<{ ok: true }>>;
  live: (projectId: string, a: { action: 'start' | 'stop'; runId?: string; group?: GroupId }) => Promise<Result<{ ok: true; run_id?: string }>>;
  guideUrl: () => Promise<Result<string>>;
  streamStart: (projectId: string) => Promise<Result<true>>;
  streamStop: () => Promise<Result<true>>;
  onEvent: (cb: (e: Batch) => void) => () => void;
};
export const emg1Bridge = (): Emg1Bridge | undefined =>
  typeof window === 'undefined' ? undefined : (window as unknown as { pt?: { emg1?: Emg1Bridge } }).pt?.emg1;

type Tab = 'connect' | 'wear' | 'capture' | 'train' | 'live' | 'more';
const STEPS: Tab[] = ['connect', 'wear', 'capture', 'train', 'live'];
const load = <T,>(k: string, d: T): T => { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v) as T; } catch { return d; } };
const save = (k: string, v: unknown) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* 预览里可能不可用 */ } };
const pct = (v?: number) => (v == null ? '—' : `${Math.round(v * 100)}%`);

export function SingleStudio({ projectId, deviceSlot }: { projectId: string; deviceSlot?: ReactNode }) {
  const bridge = emg1Bridge();
  const key = (k: string) => `emg1:${projectId}:${k}`;
  const [tab, setTab] = useState<Tab>(() => load(key('tab'), 'connect'));
  const [gid, setGid] = useState<GroupId>(() => { const v = load<string>(key('group'), 'five'); return (groupIds as string[]).includes(v) ? v as GroupId : 'five'; });
  const group = groupOf(gid);
  const [st, setSt] = useState<SingleState | null>(null);
  const [err, setErr] = useState('');
  const [range, setRange] = useState(200);
  const [connection, reconnect] = useState(0);
  const [flow, setFlow] = useState({ hz: 0, worn: null as number | null, rms: null as number | null, at: 0 });
  const [cue, setCue] = useState<Progress | null>(null);
  const [pred, setPred] = useState<string | null>(null);
  const [since, setSince] = useState(0);          // 服务就绪（streamStart 返回）的时刻；0 = 服务还在启动，不算超时
  const wave = useRef<WaveHandle>(null);
  const mid = useRef<number | null>(null);
  const acc = useRef({ n: 0, t0: Date.now(), sq: 0, sqn: 0 });
  useEffect(() => { save(key('tab'), tab); }, [tab]);   // eslint-disable-line react-hooks/exhaustive-deps
  // 不清空 st：忙碌 / 识别中是全局状态，清掉会让选择框在新状态回来前的那一下可点；旧组的计数由 poll 丢弃晚到包、立刻重取
  useEffect(() => { save(key('group'), gid); setPred(null); }, [gid]);   // eslint-disable-line react-hooks/exhaustive-deps

  // 数据流：主进程起单通道服务并订阅 /api/emg/stream；这里只收 50 ms 一包
  useEffect(() => {
    if (!bridge) return;
    setSince(0); setErr('');
    const off = bridge.onEvent((e) => {
      if (e.type === 'error') { setErr(e.message); return; }
      if (e.cue) setCue(e.cue);
      if (e.preds.length) setPred(e.preds[e.preds.length - 1].label);
      if (!e.samples.length) return;
      // 去掉慢漂的中点（电极偏置随接触和温度变），换成 ADC 端 mV
      const frames: number[][] = [];
      for (const v of e.samples) {
        mid.current = mid.current == null ? v : mid.current + (v - mid.current) * 0.002;
        const mv = (v - mid.current) * MV;
        frames.push([mv]); acc.current.sq += mv * mv; acc.current.sqn++;
      }
      wave.current?.push(frames);
      const a = acc.current; a.n += e.samples.length;
      const dt = Date.now() - a.t0;
      if (dt >= 500) {
        setFlow({ hz: a.n * 1000 / dt, worn: e.worn, rms: Math.sqrt(a.sq / Math.max(1, a.sqn)), at: Date.now() });
        a.n = 0; a.t0 = Date.now(); a.sq = 0; a.sqn = 0;
      }
    });
    void bridge.streamStart(projectId).then((r) => { if (!r.ok) setErr(r.message); else setSince(Date.now()); });
    return () => { off(); void bridge.streamStop(); };
  }, [bridge, projectId, connection]);

  const poll = useCallback(async () => {
    if (!bridge) return;
    const r = await bridge.state({ group: gid });
    // 切组途中晚到的旧组状态不要；旧版 host 不回 gesture_group，只会是原五类
    if (r.ok && (r.value.gesture_group ?? 'five') === gid) setSt(r.value);
  }, [bridge, gid]);
  useEffect(() => { void poll(); const t = setInterval(() => void poll(), 1000); return () => clearInterval(t); }, [poll]);
  // 录制时服务端每秒更新 progress；CUE 只在「做！」那一刻推，两者取新的
  const progress = st?.busy ? (cue?.phase === 'NOW' && st.progress?.phase !== 'NOW' ? cue : st.progress) : null;
  useEffect(() => { if (!st?.busy) setCue(null); }, [st?.busy]);

  if (!bridge) return <section className="v3-area"><h2>单通道肌电工作室</h2><p className="v3-note">只在桌面版里有：浏览器碰不到本机采集服务。</p></section>;

  const now = Date.now();
  const online = flow.at > 0 && now - flow.at < 1500;
  const worn = online && flow.worn != null && flow.worn >= 0.8;
  // 切组后新组状态回来前（≤1 次轮询），st 还是旧组的：计数和模型只认本组的，忙碌 / 识别中仍按 st（全局）
  const view: SingleState | null = st && ((st.gesture_group ?? 'five') === gid ? st : { ...st, gesture_counts: { train: {}, validation: {}, test: {} }, gesture_training: null });
  const counts = view?.gesture_counts;
  const full = (split: Split) => !!counts && group.labels.every((g) => (counts[split]?.[g] ?? 0) >= TARGET[split]);
  const runs = view?.gesture_training?.runs ?? [];
  const live = st?.live1 ?? null;
  const steps = [
    { t: '连上', s: online ? `${Math.round(flow.hz)} Hz` : '等数据', done: online },
    { t: '戴好', s: worn ? '电极贴着' : '检查接触', done: worn },
    { t: '录动作', s: full('train') && full('validation') ? '够训练了' : `${group.labels.length} 类各 30+10 条`, done: full('train') && full('validation') },
    { t: '训练', s: runs.length ? `验证 ${pct(runs[0].validation?.balanced_accuracy)}` : '还没训练', done: runs.length > 0 },
    { t: '用手势', s: live ? '识别中' : '未开启', done: !!live },
  ];
  const current = Math.max(0, STEPS.indexOf(tab));
  const busy = !!st?.busy;
  const starting = since === 0 && !err;
  const timedOut = !online && since > 0 && now - since > 15000;

  return <div className="emg8" data-guided="on">
    <div className="emg8-chrome">
      <header className="emg8-head">
        <div className="emg8-project-heading"><h2>单通道 · {group.name}</h2><small title={st?.project?.name}>{st?.project?.name ?? '临时数据（假台架）'} · {st?.rig.banner || '未连接'}</small></div>
        <span className="ins-cap" role="status"><Led state={online ? 'on' : 'off'} /> {online ? `在线 · ${Math.round(flow.hz)} Hz` : '未连接'} · {st?.busy ?? '空闲'}</span>
        <div className="emg8-row tight">{deviceSlot}
          <select aria-label="训练手势组" value={gid} disabled={busy || !!live} title={grayTitle(!!live && '先停下识别再换动作组')} onChange={(e) => setGid(e.target.value as GroupId)}>{groupIds.map((id) => <option key={id} value={id}>{groupOf(id).name}</option>)}</select></div>
      </header>
      <div className="ins-stepbar"><Stepper steps={steps} current={tab === 'more' ? -1 : current} onPick={(i) => setTab(STEPS[i])} />
        <div className="ins-more"><button aria-pressed={tab === 'more'} onClick={() => setTab('more')}>更多录法</button></div></div>
    </div>
    {err && <p className="emg8-warn">{err}</p>}
    {st?.capture_issue && <p className="emg8-warn">{nameOf(gid, st.capture_issue.label)} 没收下：{st.capture_issue.reason}{st.capture_issue.stopped ? '（已暂停，下一次只试录 1 条）' : ''}</p>}

    <main className="emg8-body">
      {tab === 'connect' && <section className="emg8-card ins-stage">
        <div className="ins-corner"><span className="ins-cap">步骤 1 · 连接</span><span className="ins-cap"><Led state={online ? 'on' : timedOut ? 'warn' : 'off'} /> {online ? '在线' : timedOut ? '没有数据' : starting ? '服务启动中' : '等数据'}</span></div>
        <div className="emg1-dial" data-on={online ? '1' : undefined}><b>{online ? '1 / 1' : timedOut ? '15 s' : '…'}</b><small>{online ? `${Math.round(flow.hz)} Hz` : starting ? '启动采集服务' : '等数据'}</small></div>
        <h2 className="ins-headline">{online ? '板子醒了' : timedOut ? '15 秒没收到数据' : starting ? '正在启动采集服务' : '正在唤醒板子'}</h2>
        <p className="ins-sub">{online ? '1 路在出数据' : err || (timedOut ? '插好 USB 线（ESP32-S3 / XIAO），点「重新连接」' : starting ? '第一次打开要多等一会儿（电脑忙时可能半分钟）' : '正在确认电脑有没有看到板子')}</p>
        <div className="ins-actions">{online ? <button className="emg8-primary ins-next" onClick={() => setTab('wear')}>去戴好它 →</button> : <button className={timedOut ? 'emg8-primary' : ''} disabled={busy} onClick={() => reconnect((n) => n + 1)}>重新连接</button>}</div>
        <p className="ins-honest">灯只在收到数据后才亮；固件不是 emg_usb / emg_imu_usb 时会显示「没找到板子」</p>
      </section>}

      {tab === 'wear' && <section className="emg8-card ins-stage">
        <div className="ins-corner"><span className="ins-cap">步骤 2 · 佩戴</span><span className="ins-cap"><Led state={worn ? 'on' : online ? 'warn' : 'off'} /> {online ? `接触 ${pct(flow.worn ?? undefined)}` : '未连接'}</span></div>
        <div className="emg1-dial" data-on={worn ? '1' : undefined}><b>{flow.rms == null || !online ? '—' : flow.rms.toFixed(1)}</b><small>mV 底噪（ADC 端）</small></div>
        <h2 className="ins-headline">{!online ? '先连上板子' : worn ? '电极贴着' : '接触检测没通过'}</h2>
        <p className="ins-sub">{!online ? '回到第 1 步' : worn ? '手放松，前臂搁稳，看下面波形是不是平的' : '电极沾点水压紧皮肤，参考电极贴在骨头上'}</p>
        <div className="emg1-wave"><Waveform ref={wave} rangeUv={range} channels={1} unit="mV" showGyro={false} rms={flow.rms != null ? [flow.rms] : undefined} /></div>
        <div className="ins-actions"><button className={worn ? 'emg8-primary ins-next' : ''} disabled={!online} title={grayTitle(!online && '还没连上板子')} onClick={() => setTab('capture')}>开始录动作 →</button></div>
        <p className="ins-honest">接触由固件判断（每 10 个采样里贴着的比例）；电脑请用电池供电，断开充电器和扩展坞</p>
      </section>}

      {tab === 'capture' && <Capture key={gid} gid={gid} st={view} bridge={bridge} projectId={projectId} online={online} progress={progress} onError={setErr}
        wave={<div className="emg1-wave"><div className="emg1-range"><label>量程 <select value={range} onChange={(e) => setRange(Number(e.target.value))}>{RANGES.map((v) => <option key={v} value={v}>±{v} mV</option>)}</select></label></div><Waveform ref={wave} rangeUv={range} channels={1} unit="mV" showGyro={false} rms={flow.rms != null ? [flow.rms] : undefined} /></div>}
        onNext={() => setTab('train')} />}

      {tab === 'train' && <Train gid={gid} st={view} bridge={bridge} projectId={projectId} full={full} onError={setErr} onLive={() => setTab('live')} />}

      {tab === 'live' && <section className="emg8-card ins-stage">
        <div className="ins-corner"><span className="ins-cap">步骤 5 · 用手势</span><span className="ins-cap"><Led state={live ? 'rec' : 'off'} /> {live ? `模型 ${live.run_id}` : '未开启'}</span></div>
        <div className="emg1-dial big" data-on={live ? '1' : undefined}><b>{live && pred ? nameOf(gid, pred) : '—'}</b><small>{live ? '最近 3 次判断的多数' : runs.length ? '点「开始识别」' : '先去训练'}</small></div>
        <h2 className="ins-headline">{live ? '做一个动作试试' : '实时识别'}</h2>
        <p className="ins-sub">{live ? '每 0.25 秒用最近 2 秒判一次；录动作时会自动停下' : runs.length ? `用最新模型 ${runs[0].id}（${runs[0].model}）` : `「${group.name}」还没有训练好的模型`}</p>
        <div className="emg1-wave"><Waveform ref={wave} rangeUv={range} channels={1} unit="mV" showGyro={false} rms={flow.rms != null ? [flow.rms] : undefined} /></div>
        <div className="ins-actions">
          {live ? <button onClick={() => void bridge.live(projectId, { action: 'stop', group: gid }).then((r) => { setPred(null); if (!r.ok) setErr(r.message); void poll(); })}>停下识别</button>
            : <button className="emg8-primary" disabled={!runs.length || !online || busy} title={grayTitle(!runs.length && '先去训练这个动作组的模型', !online && '还没连上板子')} onClick={() => void bridge.live(projectId, { action: 'start', runId: runs[0]?.id, group: gid }).then((r) => { if (!r.ok) setErr(r.message); void poll(); })}>开始识别</button>}
        </div>
        <p className="ins-honest">离线验证准确率不等于连续识别准确率：连续识别和误触发还没验收</p>
      </section>}

      {tab === 'more' && <More bridge={bridge} />}
    </main>
  </div>;
}

function Capture({ gid, st, bridge, projectId, online, progress, onError, wave, onNext }: {
  gid: GroupId; st: SingleState | null; bridge: Emg1Bridge; projectId: string; online: boolean; progress: Progress | null; onError: (m: string) => void; wave: ReactNode; onNext: () => void;
}) {
  const [split, setSplit] = useState<Split>('train');
  const group = groupOf(gid);
  const [label, setLabel] = useState<string>(group.capture[0]);
  const [count, setCount] = useState(5);
  const counts = st?.gesture_counts?.[split];
  const busy = !!st?.busy;
  const recording = busy && !!progress?.label;
  const record = async () => {
    const r = await bridge.record(projectId, { label, split, count, group: gid });
    if (!r.ok) onError(r.message);
  };
  const phase = progress?.phase;
  const big = !recording ? nameOf(gid, label) : phase === 'NOW' ? (isRest(progress?.label) ? '保持放松' : '做！') : phase && /^\d$/.test(phase) ? phase : '准备';
  const enough = !!st && group.labels.every((g) => (st.gesture_counts.train?.[g] ?? 0) >= TARGET.train && (st.gesture_counts.validation?.[g] ?? 0) >= TARGET.validation);
  return <section className="emg8-card emg1-capture">
    <div className="emg1-cap-left">
      <div className="ins-corner static"><span className="ins-cap">步骤 3 · 录动作</span><span className="ins-cap"><Led state={recording ? 'rec' : online ? 'on' : 'off'} /> {recording ? `第 ${progress?.take} / ${progress?.count} 条` : online ? '就绪' : '未连接'}</span></div>
      <div className="emg1-seg" role="group" aria-label="数据集">{(Object.keys(TARGET) as Split[]).map((s) => <button key={s} aria-pressed={split === s} disabled={busy} onClick={() => setSplit(s)}>{SPLIT_CN[s]} · 每类 {TARGET[s]}</button>)}</div>
      <ol className="emg1-gestures">{group.capture.map((g) => { const n = counts?.[g] ?? 0; return <li key={g}><button aria-pressed={label === g} disabled={busy} onClick={() => setLabel(g)}>
        <b>{nameOf(gid, g)}</b><small>{howOf(gid, g)}</small><span className="emg1-bar"><i style={{ width: `${Math.min(1, n / TARGET[split]) * 100}%` }} /></span><em>{n} / {TARGET[split]}</em></button></li>; })}</ol>
      <div className="emg1-cue" data-now={phase === 'NOW' ? '1' : undefined}><b>{big}</b><small>{recording ? (progress?.label ? howOf(gid, progress.label) : '') : `每条 2 秒：先放松，听到「做！」做一次，松开`}</small></div>
      <div className="ins-actions">
        {recording ? <button onClick={() => void bridge.recordStop(projectId).then((r) => { if (!r.ok) onError(r.message); })}>停下这一批</button>
          : <><label className="emg1-count">每批 <select value={count} disabled={busy} onChange={(e) => setCount(Number(e.target.value))}>{[1, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}</select> 条</label>
            <button className="emg8-primary" disabled={!online || busy} title={grayTitle(!online && '还没连上板子')} onClick={() => void record()}>录「{nameOf(gid, label)}」</button>
            {enough && <button className="ins-next" onClick={onNext}>去训练 →</button>}</>}
      </div>
      <p className="ins-honest">{st?.log?.slice(-1)[0] ?? '训练要每类 30 条训练 + 10 条验证；独立测试 10 条只在验收时打开'}</p>
    </div>
    {wave}
  </section>;
}

function Train({ gid, st, bridge, projectId, full, onError, onLive }: {
  gid: GroupId; st: SingleState | null; bridge: Emg1Bridge; projectId: string; full: (s: Split) => boolean; onError: (m: string) => void; onLive: () => void;
}) {
  const [model, setModel] = useState<'lda' | 'svm'>('lda');
  const runs = st?.gesture_training?.runs ?? [];
  const frozen = st?.gesture_training?.frozen ?? null;
  const busy = !!st?.busy;
  const ready = full('train') && full('validation');
  const labels = groupOf(gid).labels;
  const go = (a: Parameters<Emg1Bridge['train']>[1]) => void bridge.train(projectId, { ...a, group: gid }).then((r) => { if (!r.ok) onError(r.message); });
  return <section className="emg8-card emg1-train">
    <div className="ins-corner static"><span className="ins-cap">步骤 4 · 训练</span><span className="ins-cap"><Led state={busy ? 'rec' : runs.length ? 'on' : 'off'} /> {st?.busy ?? (runs.length ? `${runs.length} 个模型` : '还没训练')}</span></div>
    <div className="emg1-train-head">
      <label>模型 <select value={model} disabled={busy} onChange={(e) => setModel(e.target.value as 'lda' | 'svm')}><option value="lda">LDA（快）</option><option value="svm">SVM</option></select></label>
      <button className="emg8-primary" disabled={!ready || busy || !!frozen} title={grayTitle(!!frozen && '模型已冻结进独立验收', !ready && '每类先录够 30 条训练 + 10 条验证')} onClick={() => go({ action: 'train', model })}>开始训练</button>
      {runs.length > 0 && <button className="ins-next" onClick={onLive}>去用手势 →</button>}
    </div>
    {!runs.length ? <p className="ins-sub">{ready ? '数据够了，点「开始训练」' : '每类录够 30 条训练 + 10 条验证后才能训练'}</p>
      : <table className="emg1-runs"><thead><tr><th>模型</th><th>验证（均衡准确率）</th>{labels.map((g) => <th key={g}>{nameOf(gid, g)}</th>)}<th>独立测试</th><th /></tr></thead>
        <tbody>{runs.map((r) => <tr key={r.id}><td title={r.id}>{r.model} · {r.id.slice(4, 13)}</td><td><b>{pct(r.validation?.balanced_accuracy)}</b></td>
          {labels.map((g) => <td key={g}>{pct(r.validation?.recall?.[g])}</td>)}
          <td>{r.test ? <b>{pct(r.test.balanced_accuracy)}</b> : frozen === r.id ? '验收中' : '—'}</td>
          <td>{!r.test && <button disabled={busy || !full('test') || (!!frozen && frozen !== r.id)} title={!full('test') ? '每类先录够 10 条独立测试' : '用独立测试集验收这个模型；做完后不能再拿测试集挑模型'} onClick={() => go({ action: 'evaluate', runId: r.id })}>独立验收</button>}</td></tr>)}</tbody></table>}
    <p className="ins-honest">离线整条分类的准确率；独立测试集只用一次，用完模型就冻结</p>
  </section>;
}

function More({ bridge }: { bridge: Emg1Bridge }) {
  const [url, setUrl] = useState('');
  const [err, setErr] = useState('');
  useEffect(() => { void bridge.guideUrl().then((r) => { if (r.ok) setUrl(r.value); else setErr(r.message); }); }, [bridge]);
  return <section className="emg8-card emg1-more">
    <div className="ins-corner static"><span className="ins-cap">更多录法 · 预演 / 诊断 45 条 / 三类对照</span></div>
    {err ? <p className="emg8-warn">{err}</p> : url ? <iframe title="单通道引导录制（旧页面）" src={url} sandbox="allow-scripts allow-same-origin allow-downloads" referrerPolicy="no-referrer" /> : <p className="ins-sub">正在打开…</p>}
  </section>;
}
