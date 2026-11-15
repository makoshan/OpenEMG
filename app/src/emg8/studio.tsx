'use client';
// 八通道肌电工作室：顶部常驻状态行（主方案 8.5 节）+ 波形与电极环常驻 + 采集 / 训练 / 识别三页 + 舞台模式。
// 数据全部来自本机采集服务（firmware/emg_web.py --wl8），经主进程 desktop/emg8-ipc.cjs 转发。
import { motion } from 'motion/react';
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Bench } from './bench';
import { Capture, CABLE_CN, CH0_CN, WearContext, type CableDir, type Ch0Site } from './capture';
import { guardRecord } from './gesture-actions';
import { Control, CURSOR_MODE_CN } from './control';
import type { AbState, CursorTick, Emg8Bridge, Hand, Pred, ServiceState } from './contract';
import { CH_COLORS, emg8Bridge, LABEL_CN } from './contract';
import { classicView, matchesProfile, PROFILES, profileId, trainingBlock, type ClassicPick, type ProfileId } from './profiles';
import { applyClassicNames, ClassicCapture, ClassicPorts } from './classic';
import { storedGate } from './recognition-gate';
import { Led, NOISE_LIMIT_UV, Stepper, overRange } from './instrument';
import { isC08bTier, shouldAutoReconnect } from './link';
import { SetupView, type WearCheck } from './setup';
import { Live } from './live';
import { Workbench, type WorkbenchSub } from './workbench';
import { ElectrodeRing } from './ring';
import { SignalStream } from './signal';
import { Train } from './train';
import { Waveform, type WaveHandle } from './wave';
import { GestureLibrary } from './gesture-library';
import './emg8.css';
import './thumb-capture.css';

type Tab = 'setup' | 'capture' | 'train' | 'live' | 'control' | 'bench' | 'data' | 'guide';
// 引导模式五步：① 连上 ② 戴好（同一个 setup 页的两半）③ 录动作 ④ 训练 ⑤ 用手势
const GUIDED: [Tab, 0 | 1][] = [['setup', 0], ['setup', 1], ['capture', 0], ['train', 0], ['live', 0]];
const STABLE_N = 3;                                            // 服务端 100 ms 出一次 → 300 ms
const TABS: [Tab, string][] = [['capture', '① 采集'], ['train', '② 训练'], ['live', '③ 识别'], ['control', '④ 控制'], ['bench', '⑤ 基准'], ['data', '⑥ 数据台'], ['guide', '动作库']];
// 训练手势组下拉只列这些（2026-10-16 Mako：手势训练只留结印三类）。其它组的定义、录音、模型都还在，要用时把 id 加回来。
// 2026-10-22 Mako 加回捏合 / 握拳：普通组，多次佩戴没有重戴集时服务端按佩戴编号留一次佩戴估分。结印放第一个，仍是默认组。
const SHOWN: ProfileId[] = ['ghost-seals', 'grasp'];
const WAVE_UV = [100, 200, 250, 500, 2000];   // 200：唯理软件「实时EMG波形」右上角的量程，说明书截图里停在 200
const load = <T,>(k: string, d: T): T => { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v) as T; } catch { return d; } };
const agoText = (ms: number) => { const m = Math.round(ms / 60000); return m < 60 ? `${m} 分钟` : `${Math.floor(m / 60)} 小时 ${m % 60} 分钟`; };
const save = (k: string, v: unknown) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* 预览里可能不可用 */ } };

// deviceSlot：外壳的「设备」选择（16 / 8 / 2 / 单通道）放进顶栏，不再浮在页面右上角压住回放横幅
export function EmgStudio({ projectId, deviceTier, deviceSlot }: { projectId: string; deviceTier?: string; deviceSlot?: ReactNode }) {
  const raw = emg8Bridge();
  const key = (k: string) => `emg8:${projectId}:${k}`;
  const [tab, setTab] = useState<Tab>(() => load(key('tab'), 'setup'));                       // 第一次打开从「① 连上」走，不直接落在录动作页（2026-10-09 走查）
  const [stage, setStage] = useState<boolean>(() => load('emg8:stage', false));
  const [hand, setHand] = useState<Hand>(() => load(key('hand'), 'left'));
  const [donning, setDonning] = useState<number>(() => load(key('donning'), 1));
  const [placement, setPlacement] = useState<string>(() => load(key('placement'), '腕部贴掌根 · 酒精+沾水 · 前臂搁床'));
  const [strap, setStrap] = useState<number | null>(() => { const v = load<unknown>(key('strap'), null); return Number.isInteger(v) && (v as number) >= 1 && (v as number) <= 20 ? v as number : null; });
  const [cable, setCable] = useState<CableDir | null>(() => { const v = load<unknown>(key('cable'), null); return typeof v === 'string' && v in CABLE_CN ? v as CableDir : null; });
  const [ch0, setCh0] = useState<Ch0Site | null>(() => { const v = load<unknown>(key('ch0'), null); return typeof v === 'string' && v in CH0_CN ? v as Ch0Site : null; });
  useEffect(() => { save(key('cable'), cable); save(key('ch0'), ch0); }, [cable, ch0]); // eslint-disable-line react-hooks/exhaustive-deps
  // 所有录制页都经过这里的 record：带上戴法；编号可能过期时先弹窗问是不是重新戴了（shouldAskRewear）。上一条录音的编号和时间按工程存，App 重启后还在。
  const [rewearAsk, setRewearAsk] = useState<{ donning: number; at: number; answer: (n: number) => void } | null>(null);
  const now = useRef({ cable, ch0, linkSince: null as number | null | undefined });
  const bridge = useMemo<Emg8Bridge | undefined>(() => {
    if (!raw) return raw;
    const v = load<{ donning?: unknown; at?: unknown } | null>(key('lastRecord'), null);   // 上一条录音的编号和时间按工程存，App 重启后还在
    const last = v && Number.isInteger(v.donning) && typeof v.at === 'number' ? v as { donning: number; at: number } : null;
    return { ...raw, record: guardRecord(raw.record, {
      last, changed: setDonning, saved: (l) => save(key('lastRecord'), l),
      ask: (l) => new Promise<number>((answer) => setRewearAsk({ ...l, answer })).finally(() => setRewearAsk(null)),
      extra: () => ({ cable_dir: now.current.cable ?? undefined, ch0_site: now.current.ch0 ?? undefined, linkSince: now.current.linkSince }),
    }) };
  }, [raw]); // eslint-disable-line react-hooks/exhaustive-deps
  const askRef = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (rewearAsk && !askRef.current?.open) askRef.current?.showModal(); }, [rewearAsk]);
  const [group, setGroup] = useState<ProfileId>(() => { const id = profileId(load(key('profile6'), SHOWN[0])); return SHOWN.includes(id) ? id : SHOWN[0]; });   // 记住的是已收起的组（AI 六类、鼠标五类…）就落回结印
  const base = PROFILES[group];
  const [classicPick, setClassicPick] = useState<ClassicPick>(() => load(key('classic'), { picked: [1, 2, 3, 4], names: {} }));   // 经典 5 步：勾了哪些动作、改的名字
  const classic = base.layout === 'classic';
  const profile = useMemo(() => { if (!classic) return base; applyClassicNames(base, classicPick); return classicView(base, classicPick); }, [base, classic, classicPick]);
  useEffect(() => { save(key('classic'), classicPick); }, [classicPick]); // eslint-disable-line react-hooks/exhaustive-deps
  const [range, setRange] = useState(500);
  const [connection, reconnect] = useState(0);
  const [st, setSt] = useState<ServiceState | null>(null);
  const [ab, setAb] = useState<AbState | null>(null);
  const [err, setErr] = useState('');
  const [rms, setRms] = useState<number[] | null>(null);
  const [viewRms, setViewRms] = useState<number[] | null>(null);   // 去噪链的读数：只给波形和八路读数，门不用
  const [rmsAt, setRmsAt] = useState(0);   // 最后真实EMG批次的到达时间；重画旧值不算新数据
  const [pred, setPred] = useState<Pred | null>(null);
  const [tick, setTick] = useState<CursorTick | null>(null);
  const [liveRun, setLiveRun] = useState<string | null>(null);
  const [armMouse, setArmMouse] = useState(false);
  useEffect(() => { if (armMouse) setArmMouse(false); }, [armMouse]); // 识别页挂载时读走这一次，离开再回来不会重新打开真鼠标
  const [latestRun, setLatestRun] = useState<string | null>(null);             // 本手势组最新模型：重启后识别页也能直接开始
  // 本组练出新模型就放掉上一次手选的模型：否则重新校准后「开始识别」还用旧模型（2026-10-14 Mako 结印测试：校准完仍在用 21:43 的模型）
  useEffect(() => { if (latestRun) setLiveRun((id) => (id === latestRun ? id : null)); }, [latestRun]);
  const [setupSub, setSetupSub] = useState<0 | 1>(0);
  const [workbenchSub, setWorkbenchSub] = useState<WorkbenchSub>(() => (isC08bTier(deviceTier) ? 'device' : 'record'));
  const [wear, setWear] = useState<WearCheck | null>(() => load(key('wear'), null));
  const [since, setSince] = useState(0);                                        // 这次连接从什么时候开始等数据
  const [quiet, setQuiet] = useState(() => load('emg8:nav-hidden', false));    // 训练时收起工程顶栏、手势组和步骤
  const env = useRef(0), rangeRef = useRef(500);
  const [flow, setFlow] = useState({ hz: 0, dropped: 0, imuAge: Infinity, online: false });
  const wave = useRef<WaveHandle>(null);
  const signalStream = useRef(new SignalStream()), viewStream = useRef(new SignalStream('view'));   // gate 链喂放松/戴好检查，view 链只喂画面
  const stats = useRef({ n: 0, since: 0, lastImu: 0, lastData: 0, lastEmgAt: 0, dropped: 0 });
  const vote = useRef({ cand: '', n: 0, top: '' });            // 连续 STABLE_N 次同一类才换显示，免得 100 ms 一跳

  useEffect(() => { save(key('tab'), tab); save(key('hand'), hand); save(key('donning'), donning); save(key('placement'), placement); save(key('strap'), strap); }, [tab, hand, donning, placement, strap]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { save('emg8:stage', stage); }, [stage]);
  useEffect(() => { save(key('wear'), wear); }, [wear]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { rangeRef.current = range; }, [range]);
  useEffect(() => { save(key('profile6'), group); }, [group]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { save('emg8:nav-hidden', quiet); }, [quiet]);
  useEffect(() => {
    const root = document.querySelector('.v3');
    if (!root || !profile.gestures) return;
    if (quiet) root.setAttribute('data-train-focus', '1');
    else root.removeAttribute('data-train-focus');
    return () => { root.removeAttribute('data-train-focus'); };
  }, [quiet, profile]);
  const changeGroup = async (value: string) => {
    if (classic && st?.wl8?.ctrl?.open) void bridge?.ctrl?.(projectId, { action: 'close' });   // 控制串口只跟经典组走
    if (st?.wl8?.live) { const r = await bridge?.live(projectId, { action: 'stop' }); if (r && !r.ok) { setErr(r.message); return; } }
    vote.current = { cand: '', n: 0, top: '' }; setPred(null); setLiveRun(null); setGroup(profileId(value));
  };
  const cursorMode = st?.wl8?.cursor?.mode;
  const moving = useRef(false);
  useEffect(() => { moving.current = cursorMode === 'move' || cursorMode === 'drag'; }, [cursorMode]);
  useEffect(() => () => { if (moving.current) void bridge?.cursor(projectId, { action: 'log' }); }, [bridge, projectId]);   // 离开工作室：光标退回演练

  // 状态轮询：录制中 300 ms 一次，平时 800 ms
  const poll = useCallback(async () => {
    if (!bridge) return;
    const r = await bridge.state();
    if (r.ok) { setSt(r.value); setErr((e) => (e.startsWith('采集服务') ? '' : e)); } else setErr(r.message);
    const a = await bridge.abState({ hand, donning }); if (a.ok) setAb(a.value);
  }, [bridge, hand, donning]);
  const busy = !!st?.busy;
  const anyOver = !!viewRms && viewRms.some((v) => overRange(v, range));
  const calibrating = st?.wl8?.cursor?.mode === 'calibrating';     // 校准时 0.25 s 一读：口令卡和语音对齐（语音已在服务端提前 1.2 s 发）
  useEffect(() => { void poll(); const t = setInterval(() => void poll(), calibrating ? 250 : busy ? 300 : 800); return () => clearInterval(t); }, [poll, busy, calibrating]);
  const linkSeen = useRef<string | undefined>(undefined);
  const autoAt = useRef(0);
  useEffect(() => {
    const link = st?.rig.link;
    const prev = linkSeen.current;
    linkSeen.current = link;
    if (shouldAutoReconnect(prev, link, performance.now() - autoAt.current)) {
      autoAt.current = performance.now();
      reconnect((n) => n + 1);
    }
  }, [st?.rig.link, reconnect]);

  const rigChannels = st?.rig.n_channels ?? 8;
  const rigFs = st?.rig.fs_Hz ?? 2000;
  const tierSeen = useRef(deviceTier);
  useEffect(() => {
    if (tierSeen.current === deviceTier) return;
    tierSeen.current = deviceTier;
    if (isC08bTier(deviceTier)) setWorkbenchSub('device');
    setErr('');
    const t = setTimeout(() => { void poll(); reconnect((n) => n + 1); }, 140);
    return () => clearTimeout(t);
  }, [deviceTier, poll]);
  useEffect(() => {
    const c1 = signalStream.current.setSpec(rigChannels, rigFs);
    const c2 = viewStream.current.setSpec(rigChannels, rigFs);
    if (c1 || c2) { setRms(null); setViewRms(null); setRmsAt(0); }
  }, [rigChannels, rigFs]);

  // 实时数据流
  useEffect(() => {
    if (!bridge) return;
    const clearPrediction = () => { vote.current = { cand: '', n: 0, top: '' }; setPred(null); };
    const clearSignal = () => { clearPrediction(); signalStream.current.reset(); viewStream.current.reset(); setRms(null); setViewRms(null); setRmsAt(0); env.current = 0; stats.current.lastData = 0; stats.current.lastEmgAt = 0; };
    clearSignal();
    const off = bridge.onEvent((e) => {
      if (e.type === 'boundary') { clearSignal(); return; }
      if (e.type === 'error') { clearSignal(); }
      if (e.type === 'error') { if (e.code !== 'no-receiver') setErr(e.message); return; }
      const now = performance.now(), s = stats.current;
      if (e.emg.length) {
        const { frames, boundary } = signalStream.current.push(e.emg, now, e.sampleIndex, e.dropped);
        const view = viewStream.current.push(e.emg, now, e.sampleIndex, e.dropped);   // 同一批原始帧过两条链；边界判定两边条件相同
        if (boundary) { clearPrediction(); setRms(null); setViewRms(null); setRmsAt(0); }
        if (!frames.length) return;
        wave.current?.push(view.frames);
        // 走纸记录条：这一批 8 路平均绝对幅度，按量程的 1/4 归一（放松约在底部，动作鼓起来）
        env.current = Math.min(1, frames.reduce((a, f) => a + f.reduce((b, x) => b + Math.abs(x), 0) / f.length, 0) / frames.length / (rangeRef.current / 4));
        s.n += e.emg.length; s.lastData = now; s.lastEmgAt = Date.now(); s.dropped = e.dropped;
      }
      if (e.imu.length) { wave.current?.pushGyro(e.imu); s.lastImu = now; }
      if (e.cursor) setTick(e.cursor);
      if (e.preds.length) {
        const v = vote.current;
        for (const p of e.preds) { if (p.top === v.cand) v.n++; else { v.cand = p.top; v.n = 1; } if (v.n >= STABLE_N) v.top = v.cand; }
        setPred({ ...e.preds[e.preds.length - 1], stable: v.top || undefined });
      }
    });
    stats.current.since = performance.now(); stats.current.lastData = 0; stats.current.lastEmgAt = 0; signalStream.current.reset(); viewStream.current.reset(); setRms(null); setViewRms(null); setRmsAt(0); setSince(performance.now());
    void bridge.streamStart(projectId).then((r) => { if (!r.ok) setErr(r.message); });
    const t = setInterval(() => {
      const s = stats.current, now = performance.now(), dt = (now - s.since) / 1000;
      if (dt >= .5) setFlow({ hz: dt > 0 ? s.n / dt : 0, dropped: s.dropped, imuAge: s.lastImu ? now - s.lastImu : Infinity, online: now - s.lastData < 500 });
      if (dt >= .5) { s.n = 0; s.since = now; }
      if (signalStream.current.expire(now)) { clearPrediction(); s.lastEmgAt = 0; env.current = 0; }
      viewStream.current.expire(now);
      const values = signalStream.current.values();
      setRms(values); setViewRms(viewStream.current.values()); setRmsAt(values ? s.lastEmgAt : 0);
    }, 100);
    return () => { off(); clearInterval(t); void bridge.streamStop(); };
  }, [bridge, projectId, connection]);

  const trainDone = st?.wl8?.train?.running ? null : st?.wl8?.train?.run_id;
  useEffect(() => {
    if (!bridge || st?.project?.id !== projectId) return;
    let off = false;
    void bridge.runs().then((r) => { if (!off && r.ok) setLatestRun(r.value.find((x) => matchesProfile(x, profile))?.id ?? null); });
    return () => { off = true; };
  }, [bridge, st?.project?.id, projectId, profile, trainDone]);
  const envelope = useCallback(() => (performance.now() - stats.current.lastData < 500 ? env.current : 0), []);

  const studioTitle = rigChannels === 8 ? '八通道肌电工作室' : `${rigChannels} 通道肌电工作室`;
  const chLabel = rigChannels === 8 ? '八路' : `${rigChannels} 路`;
  if (!bridge) return <section className="v3-area"><h2>{studioTitle}</h2><p className="v3-note">只在桌面版里有：浏览器碰不到本机采集服务。</p></section>;
  const replay = st?.rig.replay ?? st?.wl8?.replay;
  const mismatch = st && st.project && st.project.id !== projectId;
  const notWl8 = st && st.rig.kind !== 'wl8';
  const liveTop = st?.wl8?.live ? pred?.stable : null;
  const guided = !!profile.gestures;
  const online = flow.online && !!st?.rig.streaming;
  const wearOk = wear?.donning === donning && wear.perChannel.every((v) => v <= NOISE_LIMIT_UV);   // 与戴好页同口径：各路贴好就算过，条件告警只提醒（复核 P2）
  // 「戴好」的勾要跟着当前信号走：不在录的时候，最近 5 s 每路最低 RMS（样本跨度 ≥4 s）仍超红线 1.2 倍就撤勾（2026-10-12：勾着但 8 路全红）。
  // 窗与余量对齐服务端检查（wl8_ab 测 5 s、滤 19 次谐波；前端只滤 3 次，读数偏高），免得刚检查过又被撤（复核 P2）
  const wearHist = useRef<{ t: number; v: number[] }[]>([]);
  if (!online || busy || (wearHist.current[0] && wearHist.current[0].v.length !== rigChannels)) wearHist.current = [];
  else if (rms && rms.length === rigChannels && wearHist.current.at(-1)?.v !== rms) { const now = Date.now(); wearHist.current = [...wearHist.current, { t: now, v: rms }].filter((h) => now - h.t <= 5000); }
  const wh = wearHist.current, liveFloor = wh.length >= 3 && wh[wh.length - 1].t - wh[0].t >= 4000 ? Array.from({ length: rigChannels }, (_, c) => Math.min(...wh.map((h) => h.v[c]))) : null;
  const wearStale = !!liveFloor && liveFloor.some((v) => v > NOISE_LIMIT_UV * 1.2);
  const steps = [
    { t: '连上', s: '唤醒手环', done: online },
    { t: '戴好', s: wearOk && wearStale ? '底噪又高了' : '检查贴合', done: wearOk && !wearStale },
    { t: '录动作', s: profile.calibrate ? `每类 ${profile.calibrate.minTrain ?? profile.minTrain} 次` : `每类 ${profile.minTrain} 条`, done: !trainingBlock(st, profile, projectId) },
    { t: '训练', s: '分开每一类', done: !!latestRun },
    { t: '用手势', s: '实时识别', done: !!st?.wl8?.live },
  ];
  const current = GUIDED.findIndex(([k, s]) => k === tab && (k !== 'setup' || s === setupSub));
  const pick = (i: number) => { const [k, s] = GUIDED[i]; setSetupSub(s); setTab(k); };
  if (!guided && tab === 'setup') setTab('capture');                   // 非引导手势组没有连上 / 戴好页
  const onCapture = guided && tab === 'capture';
  const hideNav = guided && quiet;
  const signal = <section className="emg8-signal"><Waveform ref={wave} rangeUv={range} channels={rigChannels} fsHz={rigFs} rms={viewRms ?? undefined} showGyro={!onCapture} /><ElectrodeRing values={viewRms} max={range} channels={rigChannels} hand={hand} label="实时 RMS µV" /></section>;

  now.current = { cable, ch0, linkSince: st?.rig.link_since };   // 包过的 record 读最新值，不重建 bridge
  return <WearContext.Provider value={{ cable, ch0, setCable, setCh0 }}><div className="emg8" data-channels={rigChannels} data-stage={stage ? 'on' : undefined} data-guided={guided ? 'on' : undefined}>
    {replay && <div className="emg8-replay">▶ 回放 · {replay} · 这不是现场数据</div>}
    <div className={guided ? 'emg8-chrome' : undefined} data-focus={hideNav ? '1' : undefined}>
    {guided && <button type="button" className="emg8-focus" aria-pressed={quiet} onClick={() => setQuiet((v) => !v)}>{quiet ? '展开导航' : '收起导航'}</button>}
    {!hideNav && <header className="emg8-head">
      <div className="emg8-project-heading"><h2>{guided ? profile.name : studioTitle}</h2><small title={st?.project?.name}>{st?.project?.name ?? '采集服务未绑定工程'} · {hand === 'left' ? '左手' : '右手'} · 第 {donning} 次佩戴</small></div>
      {guided ? <span className="ins-cap" role="status"><Led state={online ? 'on' : 'off'} /> <span className="emg8-spec-badge">{rigChannels} CH · {rigFs} Hz</span> {online ? `在线 · ${Math.round(flow.hz)} Hz · 丢帧 ${flow.dropped}` : '未连接'} · {st?.busy ?? '空闲'}</span> : <nav className="emg8-tabs" aria-label="工作室页面">{TABS.map(([k, t]) => <button key={k} aria-pressed={tab === k} onClick={() => setTab(k)}>
        {tab === k && <motion.i className="emg8-tab-pill" layoutId="emg8-tab-pill" transition={{ type: 'spring', stiffness: 420, damping: 32 }} />}<span>{t}</span></button>)}</nav>}
      <div className="emg8-row tight">
        {deviceSlot}
        {!guided && <span className="emg8-spec-badge">{rigChannels} CH · {rigFs} Hz</span>}
        {!guided && <button disabled={busy} onClick={() => reconnect((n) => n + 1)}>重新连接</button>}
        <select aria-label="训练手势组" value={group} disabled={busy || !!ab?.active} onChange={(e) => void changeGroup(e.target.value)}>{SHOWN.map((id) => <option key={id} value={id}>{PROFILES[id].name}</option>)}</select>
        {!guided && <><select value={range} onChange={(e) => setRange(Number(e.target.value))} aria-label="量程">{WAVE_UV.map((v) => <option key={v} value={v}>±{v} µV</option>)}</select>
        <button onClick={() => setStage(!stage)} aria-pressed={stage}>{stage ? '☀ 日常' : '🎤 舞台模式'}</button></>}
      </div>
    </header>}

    {!hideNav && (guided ? <div className="ins-stepbar"><Stepper steps={steps} current={current} onPick={pick} /><div className="ins-more">{([['control', '控制'], ['bench', '基准'], ['data', '数据台'], ['guide', '动作库']] as [Tab, string][]).map(([k, s]) => <button key={k} aria-pressed={tab === k} onClick={() => setTab(k)}>{s}</button>)}</div></div> : <div className="emg8-status" role="status">
      <div><i className={flow.online ? 'g' : 'r'} />设备<b>{st?.rig.banner || (st ? '未连接' : '采集服务未响应')}</b></div>
      <div><i className={flow.online ? 'g' : 'r'} />采样<b>{flow.online ? `${Math.round(flow.hz)} Hz · 丢帧 ${flow.dropped}` : '无数据'}</b></div>
      <div><i className={flow.imuAge < 300 ? 'g' : 'y'} />IMU 数据年龄<b>{Number.isFinite(flow.imuAge) ? `${Math.round(flow.imuAge)} ms` : '—'}</b></div>
      <div><i className={cursorMode === 'move' || cursorMode === 'drag' ? 'r' : 'y'} />模式<b>{CURSOR_MODE_CN[cursorMode ?? 'off']}</b></div>
      <div>识别<b>{liveTop ? (LABEL_CN[liveTop] ?? liveTop) : '未开启'}</b></div>
      <div>录制<b>{st?.busy ?? '空闲'}</b></div>
    </div>)}
    </div>
    {/* 多路段放在钉顶的 chrome 外面：校准页它是左侧整栏（Mako 2026-10-12），其他录动作页跟着内容走 */}
    {onCapture && <section className="emg8-channels" aria-label={`${chLabel}实时信号`}>
      <div className="emg8-channels-bar"><b>{chLabel}</b><span className="emg8-spec-badge">{rigChannels} CH · {rigFs} Hz</span><label>量程 <select value={range} onChange={(e) => setRange(Number(e.target.value))} aria-label="量程">{WAVE_UV.map((v) => <option key={v} value={v}>±{v} µV</option>)}</select></label>{anyOver && range < WAVE_UV[WAVE_UV.length - 1] && <button type="button" className="emg8-range-up" onClick={() => setRange(WAVE_UV[WAVE_UV.length - 1])}>换到 ±{WAVE_UV[WAVE_UV.length - 1]} µV</button>}</div>
      {/* RMS × 3 ≈ 峰值，超过量程的那一路标「超量程」，波形在那条上已顶格（2026-10-12 截图 8 条全是色块） */}
      <ol className="emg8-ch-readout">{Array.from({ length: rigChannels }, (_, i) => { const v = viewRms?.[i]; const over = overRange(v, range); return <li key={i} className={over ? 'over' : undefined} style={{ ['--ch-col' as string]: CH_COLORS[i % CH_COLORS.length] }}><b>CH{i + 1}</b><span>{Number.isFinite(v as number) ? `${Math.round(v as number)} µV` : '—'}{over ? ' · 超量程' : ''}</span></li>; })}<li className="note" title="波形和读数：45 Hz 高通 + 50 Hz 各次谐波陷波（最高至奈奎斯特安全边界或 900 Hz）。放松检查、戴好检查和 82.5 / 150 µV 两条线用检查口径（20 Hz 高通 + 50 Hz 陷波 Q=5 + 100/150 Hz 陷波 Q=30），不用这里的去噪显示。">已去噪显示 · 检查另用检查口径</li></ol>
      {signal}
    </section>}
    {(err || mismatch || notWl8) && <p className="emg8-warn">{mismatch ? '采集服务绑定的是另一个工程，录制会被拒绝。' : notWl8 ? '采集服务未切到多通道模式。' : err}</p>}

    {!guided && tab !== 'control' && tab !== 'bench' && tab !== 'guide' && signal}

    <motion.main key={`${tab}:${tab === 'setup' ? setupSub : group}`} className="emg8-body" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .35, ease: [0.16, 1, 0.3, 1] }}>
      {tab === 'setup' && <SetupView stale={wearOk && wearStale} sub={setupSub} online={online} hz={flow.hz} dropped={flow.dropped} rms={rms} range={range} hand={hand} donning={donning} since={since} st={st} projectId={projectId} bridge={bridge}
        deviceTier={deviceTier} wear={wear} busy={busy} onWear={setWear} onReconnect={() => reconnect((n) => n + 1)} onNext={() => pick(setupSub === 0 ? 1 : 2)}
        onOpenHardware={() => { setWorkbenchSub('device'); setTab('data'); }} onError={setErr} />}
      {tab === 'setup' && setupSub === 0 && classic && <ClassicPorts bridge={bridge} projectId={projectId} st={st} labels={profile.labels} runId={latestRun} onReconnect={() => reconnect((n) => n + 1)} onError={setErr} />}
      {tab === 'capture' && classic && <ClassicCapture base={base} pick={classicPick} setPick={setClassicPick} profile={profile} projectId={projectId} bridge={bridge} st={st} ab={ab} hand={hand} setHand={setHand} donning={donning} setDonning={setDonning}
        placement={placement} setPlacement={setPlacement} strap={strap} setStrap={setStrap} onError={setErr} rms={rms} rmsAt={rmsAt}
        onTrained={(id) => { setLiveRun(id); setTab('live'); void bridge.live(projectId, { action: 'start', runId: id, ...storedGate(true) }).then((r) => { if (!r.ok) setErr(r.message); }); }} />}
      {tab === 'capture' && !classic && <Capture envelope={guided && online ? envelope : undefined} profile={profile} projectId={projectId} bridge={bridge} st={st} ab={ab} hand={hand} setHand={setHand} donning={donning} setDonning={setDonning}
        placement={placement} setPlacement={setPlacement} strap={strap} setStrap={setStrap} onError={setErr} rms={rms} rmsAt={rmsAt} onReconnect={() => reconnect((n) => n + 1)} onRewear={() => pick(1)}
        onTrained={(id, opts) => { setLiveRun(id); setArmMouse(!!opts?.armMouse); setTab('live'); void bridge.live(projectId, { action: 'start', runId: id }).then((r) => { if (!r.ok) setErr(r.message); }); }} />}
      {tab === 'train' && <Train profile={profile} projectId={projectId} bridge={bridge} st={st} hand={hand} onError={setErr} onLive={(id) => { setLiveRun(id); setTab('live'); }} />}
      {tab === 'bench' && <Bench mode={cursorMode ?? 'off'} donning={donning} />}
      {tab === 'data' && <Workbench projectId={projectId} bridge={bridge} hand={hand} donning={donning} placement={placement} initialSub={workbenchSub} onSubChange={setWorkbenchSub} />}
      {tab === 'control' && <Control projectId={projectId} bridge={bridge} cs={st?.wl8?.cursor ?? null} tick={tick} hand={hand} onError={setErr} />}
      {tab === 'live' && <Live donning={donning} rms={rms} rmsAt={rmsAt} profile={profile} projectId={projectId} bridge={bridge} st={st} pred={pred} runId={liveRun ?? latestRun} armMouse={armMouse} onError={setErr} onRewear={() => pick(2)} />}
      {tab === 'guide' && <GestureLibrary hand={hand} onHandChange={setHand} />}
    </motion.main>
    {guided && !onCapture && tab !== 'control' && tab !== 'bench' && tab !== 'setup' && tab !== 'guide' && <details className="emg8-thumb-details emg8-thumb-signals"><summary>{chLabel}实时信号与电极分布 · 展开查看</summary><div className="emg8-thumb-details-body"><label>波形量程 <select value={range} onChange={(e) => setRange(Number(e.target.value))} aria-label="量程">{WAVE_UV.map((v) => <option key={v} value={v}>±{v} µV</option>)}</select></label>{signal}<p className="emg8-fine">IMU 数据年龄：{Number.isFinite(flow.imuAge) ? `${Math.round(flow.imuAge)} ms` : '—'}。模式：{CURSOR_MODE_CN[cursorMode ?? 'off']}。识别：{liveTop ? LABEL_CN[liveTop] : '未开启'}。</p></div></details>}
    {rewearAsk && <dialog ref={askRef} className="emg8-rewear-ask" aria-labelledby="emg8-rewear-ask-t" onCancel={(e) => e.preventDefault()} onClose={() => rewearAsk.answer(rewearAsk.donning)}>
      <h3 id="emg8-rewear-ask-t">这是同一次佩戴吗？</h3>
      <p>上一条录音是 {agoText(Date.now() - rewearAsk.at)}前（第 {rewearAsk.donning} 次佩戴）。摘下再戴，电极位置会变，要算新的一次。</p>
      <div className="emg8-row tight"><button onClick={() => rewearAsk.answer(rewearAsk.donning)}>还是第 {rewearAsk.donning} 次，没摘过</button>
        <button className="emg8-primary" disabled={rewearAsk.donning >= 20} title={rewearAsk.donning >= 20 ? '佩戴次数已经到 20' : undefined} onClick={() => rewearAsk.answer(rewearAsk.donning + 1)}>重新戴了 → 第 {Math.min(20, rewearAsk.donning + 1)} 次</button></div>
      <p className="emg8-fine">选「重新戴了」后顺手核一下右栏的线缆朝向和 CH1 位置。</p>
    </dialog>}
  </div></WearContext.Provider>;
}
