'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { Emg8Bridge, ServiceState } from './contract';
import { LABEL_CN } from './contract';
import { EventTape, Flap, Gauge } from './instrument';
import type { Profile } from './profiles';
import { MetaSequence, motionDirection, type MotionCalibration } from './meta-sequence';
import { ACCESSIBILITY_HINT, bandSignal, accessibilityBlocks, armFromGestureStart, GAME_NAME, gestureTrust, GestureTrigger, mouseOutputOn, mousePreset, sealToGame, signalReady, examPlan, examScore, EXAM_DO_MS, EXAM_REST_MS, type ExamTrial, bandIdle, bandLive, gatedWatch, rewearHint, withRewearHint, type BandStatus } from './gesture-actions';
import type { Result } from '../desktop-bridge';

// 结印小游戏（electron/game.cjs）：只在 App 里有；网页版没有这个口
type GameBridge = { open: () => Promise<Result<boolean>>; gesture: (g: string, conf: number) => Promise<Result<{ accepted: boolean; code: string; message: string }>>; band?: (s: BandStatus) => Promise<Result<boolean | 'closed'>> };
const OFFER_MS = 5000;   // 「请放松：第 N 路偏高」持续这么久才给手动屏蔽按钮。握着印也会卡满 5 秒，所以按钮文字要人先确认松手
const gameBridge = () => (window as unknown as { pt?: { game?: GameBridge } }).pt?.game;
import { linkAdvice, linkLine } from './link';
import { lanePlan, RestSignalGate } from './rest-signal';
import { NOISE_LIMIT_UV } from './instrument';
import { ContinuousValidation } from './continuous-validation';
import { grayTitle } from './gray-title';
import { RecognitionControls, useRecognitionGate } from './recognition-gate';

export function MetaLive({ profile, projectId, bridge, st, runId, donning, onError, armMouse = false, rms, rmsAt = 0, onRewear }: { profile: Profile; projectId: string; bridge: Emg8Bridge; st: ServiceState | null; runId: string | null; donning: number; onError: (m: string) => void; armMouse?: boolean; rms?: number[] | null; rmsAt?: number; onRewear?: () => void }) {
  const on = !!st?.wl8?.live && st.project?.id === projectId;
  const [command, setCommand] = useState('先开始识别，再放松手指');
  // 跨佩戴用旧模型：每次佩戴校准的组，当前模型 created 早于手环最近一次重新出数据（rig.link_since）就提醒先重新校准；只提醒不拦截（2026-10-16）
  const [runCreated, setRunCreated] = useState<string | null>(null);
  const rewear = profile.calibrate && !st?.rig.replay && !st?.wl8?.replay ? rewearHint(runCreated, st?.rig.link_since) : null;   // 回放一开播就记 link_since，任何模型都「早于」它，回放页不提醒（复核建议）
  const rewearRef = useRef(''); rewearRef.current = rewear?.short ?? '';   // 游戏载荷的定时器里读
  // 认对测试（结印组）：按提示做，记游戏会收到的那一下；测试期间不送游戏
  type Exam = { plan: string[]; i: number; phase: 'rest' | 'do' | 'done'; until: number; trials: ExamTrial[] };
  const [exam, setExam] = useState<Exam | null>(null);
  const [validationBusy, setValidationBusy] = useState(false);
  const validationBusyRef = useRef(false); validationBusyRef.current = validationBusy;
  const validationLog = useRef<((kind: string, data?: Record<string, unknown>) => void) | null>(null);
  const examOn = useRef(false);
  examOn.current = !!exam && exam.phase !== 'done';
  const startExam = () => { const plan = examPlan(profile.labels.filter((l) => l !== profile.labels[0]), 7); setExam({ plan, i: 0, phase: 'rest', until: Date.now() + EXAM_REST_MS, trials: plan.map((target) => ({ target, got: null, restFires: 0, paused: false })) }); };
  const markTrial = (f: (t: ExamTrial, phase: Exam['phase']) => ExamTrial) => setExam((x) => x && x.phase !== 'done' ? { ...x, trials: x.trials.map((t, k) => k === x.i ? f(t, x.phase) : t) } : x);
  const [contact, setContact] = useState('—');
  const [events, setEvents] = useState<{ id: number; t: string; text: string; ok: boolean }[]>([]);
  const [conf, setConf] = useState(0);
  const t0 = useRef(Date.now());
  const [value, setValue] = useState(50);
  const [mode, setMode] = useState<'knob' | 'scroll'>('knob');
  const [target, setTarget] = useState('音量');
  const [cal, setCal] = useState<MotionCalibration | null>(null);
  const sequence = useRef(new MetaSequence());
  // 鼠标八类：识别 → 边沿触发 → 绑定动作。从「开始用手势」进来时直接启用；手环没帧时开关开着也不发。
  const trigger = useRef(new GestureTrigger(profile.labels[0], profile.game === 'tianjie'));   // 结印游戏：识别到就出招，不等放松
  trigger.current.continuous = profile.game === 'tianjie' && !examOn.current;   // 认对测试照旧要先放松，否则按住重发会记成放松段误出招
  const [output, setOutput] = useState(() => armFromGestureStart(profile.protocol, armMouse));
  const [step, setStep] = useState(120);
  const [latency, setLatency] = useState<number | null>(null);
  const outputRef = useRef(false), stepRef = useRef(120);
  const fresh = signalReady(!!st?.rig.streaming, st?.rig.link);
  const ready = on && !st?.rig.replay && !st?.wl8?.replay && fresh;
  // 推给游戏的手环状态：没在识别时按连接情况算；识别中由下面的数据循环逐帧改
  const band = useRef<BandStatus>(bandIdle(false, false, false, ''));
  if (!ready) band.current = bandIdle(fresh, on, !!st?.rig.replay || !!st?.wl8?.replay, st?.rig.link && st.rig.link !== 'streaming' ? linkAdvice(st.rig.link, st.rig.link_detail).title : '');
  else if (band.current.state !== 'live' && band.current.state !== 'paused') band.current = { state: 'live', text: '识别中 · 先放松', pose: '', acc: null };
  useEffect(() => {   // 约 10 次 / 秒；上一次没回来就跳过，不排队。游戏没开时主进程直接回 closed
    const game = gameBridge();
    if (profile.game !== 'tianjie' || !game?.band) return;
    let busy = false;
    const timer = setInterval(() => {
      if (busy) return; busy = true;
      // 识别中额外带上肌电一栏和识别一栏（左下角面板）；没在识别只发原来的一行状态
      const b = band.current, live = b.state === 'live' || b.state === 'paused';
      const rec = recRef.current.until > Date.now() ? recRef.current.text : recRef.current.live;
      void game.band!(withRewearHint(live ? { ...b, ...panelRef.current, rec } : b, rewearRef.current)).finally(() => { busy = false; });
    }, 100);
    return () => clearInterval(timer);
  }, [profile.game]);
  useEffect(() => { if (!ready) setExam((x) => (x && x.phase !== 'done' ? null : x)); }, [ready]);   // 识别停了 / 断了就作废这轮测试
  const signalGate = useMemo(() => new RestSignalGate(NOISE_LIMIT_UV, profile.game === 'tianjie' ? 'session' : 'periodic'), [projectId, runId, st?.wl8?.live?.run_id, donning, ready, profile.game]);
  const [signalCheck, setSignalCheck] = useState(() => signalGate.status(Date.now()));
  useEffect(() => { signalGate.observe(rms, rmsAt, Date.now()); }, [signalGate, rms, rmsAt]);
  // 屏蔽坏路：放松检查里 1–2 路过线、缺它们仍认得准 → 服务端删掉这几路特征，放松门不再被它们挡住（贴好了下一次检查自动取消）
  const [laneDrop, setLaneDrop] = useState<number[] | null>(null);
  // 手动屏蔽：放松检查连续卡在 1–2 路偏高满 OFFER_MS 才给按钮（松印后短暂偏高不闪）。记在当前这个门上，停止识别、换模型、重戴会换门，自动作废
  const [manual, setManual] = useState<{ gate: RestSignalGate; lanes: number[] } | null>(null);
  const manualLanes = manual?.gate === signalGate ? manual.lanes : [];
  const manualKey = manualLanes.join(',');
  const [offer, setOffer] = useState<number[]>([]);
  const blocked = useRef(0);   // 从什么时候起连续卡在 1–2 路偏高；0 = 没卡。偏高的是哪几路可以变（某路在 150 µV 上下跳），不清零
  // 只有结印组（select）把屏蔽发给服务端；别的协议前端也不放过坏路，免得前后端不一致（复核 P1：鼠标协议会动真鼠标）
  // 手动屏蔽不看留一分数（minScore 0）：用户自己选的，认对估计照旧写在 maskNote 里
  const lanes = profile.protocol !== 'select' ? { mask: [] as number[], estimate: null } : manualLanes.length ? lanePlan(manualLanes, laneDrop, 0) : lanePlan(signalCheck.stuck, laneDrop);
  const maskKey = lanes.mask.join(',');
  const maskRef = useRef(''); maskRef.current = maskKey;   // 数据循环里核对服务端实际屏蔽的路
  // 游戏面板：肌电一栏随放松检查和屏蔽实时算；识别一栏 live = 当前认成什么，text 是出招结果，保留 1.5 秒
  const panelRef = useRef(bandSignal(signalCheck, lanes.mask, !!rms && Date.now() - rmsAt < 1000));
  panelRef.current = bandSignal(signalCheck, lanes.mask, !!rms && Date.now() - rmsAt < 1000);
  const recRef = useRef({ live: '', text: '', until: 0 });
  useEffect(() => { signalGate.setIgnore(maskKey ? maskKey.split(',').map(Number) : []); }, [signalGate, maskKey]);
  useEffect(() => { signalGate.force(manualKey ? manualKey.split(',').map(Number) : []); }, [signalGate, manualKey]);
  const recognition = useRecognitionGate(bridge, projectId, on, onError, st?.wl8?.live?.last, profile.protocol === 'select' ? lanes.mask : undefined);
  // 按钮屏蔽「已屏蔽的 ∪ 现在偏高的」：只给偏高的会把已自动屏蔽的路放开，点完又卡住（复核 #102 P1）；合起来超过 2 路不给
  const offerLanes = offer.length ? [...new Set([...lanes.mask, ...offer])].sort((a, b) => a - b) : [];
  const maskNote = !lanes.mask.length ? '' : `已屏蔽第 ${lanes.mask.join('、')} 路（${manualLanes.length ? '手动' : '没贴好'}）${lanes.estimate != null ? ` · ${lanes.mask.length > 1 ? '单缺其中一路' : '缺它'}认对约 ${Math.round(lanes.estimate * 100)}%${lanes.mask.length > 1 ? '（两路同缺未估）' : ''}` : ''}`;
  useEffect(() => {
    blocked.current = 0; setOffer([]);   // 换门重新计时
    const timer = setInterval(() => {
      const now = Date.now(), check = signalGate.status(now); setSignalCheck(check);
      const stuck = !check.allowed && check.high.length > 0 && check.high.length <= 2;   // ≥3 路是用力，不给屏蔽
      if (!stuck) blocked.current = 0; else blocked.current ||= now;
      setOffer(stuck && now - blocked.current >= OFFER_MS ? check.high : []);
      if (ready && !check.allowed) { if (profile.game !== 'tianjie') trigger.current.reset(); sequence.current.reset(); setContact('等待放松检查'); setCommand(check.text); }
    }, 100);
    return () => clearInterval(timer);
  }, [signalGate, ready]);
  // 每题提示放松时重新检查；动作题固定4秒，不用动作信号反推接触。
  useEffect(() => { if (exam?.phase === 'rest') signalGate.reset(Date.now()); }, [signalGate, exam?.phase, exam?.i]);
  useEffect(() => {
    if (!exam || exam.phase === 'done') return;
    const timer = setInterval(() => setExam((x) => {
      if (!x || x.phase === 'done' || Date.now() < x.until) return x;
      if (x.phase === 'rest' && !signalGate.status(Date.now()).allowed) return x;
      if (x.phase === 'rest') return { ...x, phase: 'do', until: Date.now() + EXAM_DO_MS };
      return x.i + 1 >= x.plan.length ? { ...x, phase: 'done' } : { ...x, i: x.i + 1, phase: 'rest', until: Date.now() + EXAM_REST_MS };
    }), 100);
    return () => clearInterval(timer);
  }, [exam?.phase, exam?.i, signalGate]); // eslint-disable-line react-hooks/exhaustive-deps
  const trusted = st?.wl8?.cursor?.trusted;
  const [appTrusted, setAppTrusted] = useState<boolean | null>(null);
  const askedAccess = useRef(false);
  const gate = gestureTrust(trusted, appTrusted);
  const accessBlocked = accessibilityBlocks(gate);
  useEffect(() => { outputRef.current = mouseOutputOn(!!ready, output, gate); stepRef.current = step; }, [ready, output, gate, step]);
  useEffect(() => {
    if (profile.protocol !== 'mouse' || !bridge.access) return;
    let stop = false;
    const pull = () => void bridge.access?.(false).then((r) => { if (!stop && r.ok) setAppTrusted(r.value.trusted); });
    pull();
    const timer = setInterval(pull, 1500);
    return () => { stop = true; clearInterval(timer); };
  }, [bridge, profile.protocol]);
  useEffect(() => {
    if (!output) { askedAccess.current = false; return; }
    if (profile.protocol !== 'mouse' || askedAccess.current || !bridge.access) return;
    askedAccess.current = true;
    void bridge.access(true).then((r) => { if (r.ok) setAppTrusted(r.value.trusted); });
  }, [bridge, output, profile.protocol]);
  const activeId = st?.wl8?.live?.run_id ?? runId;
  useEffect(() => {
    let cancelled = false; setCal(null); setLaneDrop(null); setRunCreated(null);
    if (activeId) void bridge.run(activeId).then((r) => { if (!cancelled && r.ok) { setRunCreated(r.value.created ?? null); const v = r.value as unknown as { motion_calibration?: MotionCalibration; lane_drop?: number[] }; setCal(v.motion_calibration ?? null); setLaneDrop(Array.isArray(v.lane_drop) && v.lane_drop.length === 8 ? v.lane_drop : null); } });
    return () => { cancelled = true; };
  }, [bridge, projectId, activeId]);
  useEffect(() => {
    sequence.current.reset(); trigger.current.reset();
    const blocked = !!st?.rig.link && st.rig.link !== 'streaming';
    setCommand(ready ? (output && profile.protocol === 'mouse' ? (accessBlocked ? ACCESSIBILITY_HINT : '先放松手指，再做动作。鼠标会跟着动') : '先放松手指，再做动作') : blocked ? linkLine(st?.rig.link, st?.rig.link_detail) : '未开始／数据不可用');
    setContact('—');
    if (!ready) { outputRef.current = false; return; }
    let lastImu = 0, lastPred = 0, dropped: number | null = null, paused = false;
    const show = (text: string) => { setCommand(text); setEvents((xs) => [...xs, { id: Date.now() + Math.random(), t: `${((Date.now() - t0.current) / 1000).toFixed(1)}s`, text, ok: true }].slice(-6)); };
    // 触发一次绑定动作；at = 服务端出这个预测的时刻，用来量「识别到执行」的延迟
    const fire = (label: string, at: number) => {
      const act = mousePreset(stepRef.current)[label];
      if (!act) return;
      if (act.kind === 'move') { show('光标在「控制」页，转手腕'); return; }
      show(`${LABEL_CN[label] ?? label} → ${act.text}`);
      if (!outputRef.current || act.kind === 'none') return;
      void bridge.action(projectId, { action: act.kind, dx: act.dx, dy: act.dy }).then((r) => {
        if (!r.ok) {
          outputRef.current = false;
          if (r.code === 'accessibility' || r.message.includes('辅助功能')) { setAppTrusted(false); setCommand(ACCESSIBILITY_HINT); return; }
          setOutput(false); setCommand(`鼠标输出已关闭：${r.message}`); return;
        }
        if (!r.value.ok) { setCommand(`没执行：${r.value.skipped ?? '服务端未执行'}`); return; }      // 冷却中 / AI 确认中
        setLatency(Math.round(Date.now() - at));
      });
    };
    // 丢帧、预测时间对不上、数据过期、流报错：只取消当次动作，不重做放松检查；断开超过 BREAK_MS 由 RestSignalGate 自己撤销（Mako 2026-10-15）
    const off = bridge.onEvent((e) => {
      if (e.type !== 'batch') { const gap = e.type === 'boundary'; recRef.current.live = '—'; band.current = { state: 'live', text: gap ? '识别中 · 信号不连续' : '识别中 · 数据中断', pose: '', acc: null }; sequence.current.reset(); trigger.current.reset(); lastPred = 0; if (examOn.current) markTrial((t) => ({ ...t, paused: true })); setContact('—'); setConf(0); setCommand(gap ? '信号不连续，动作已取消' : '数据中断，动作已取消'); return; }
      const now = Date.now();
      if (e.emg.length) signalGate.heartbeat(now);   // 肌电在流：显示 RMS 稳定期里放行不过期；只有 IMU / 预测的批次不算
      if (dropped !== null && e.dropped > dropped) { sequence.current.reset(); trigger.current.reset(); lastPred = 0; if (examOn.current) markTrial((t) => ({ ...t, paused: true })); setContact('—'); setConf(0); setCommand('丢帧，动作已取消'); recRef.current.live = '—'; band.current = { state: 'live', text: '识别中 · 信号不连续', pose: '', acc: null }; dropped = e.dropped; return; }
      dropped = e.dropped;
      // 这一批加速度均值（第 4–6 列，原始计数）：游戏只用方向算手腕倾角
      const acc = e.imu.length ? [3, 4, 5].map((i) => e.imu.reduce((sum, row) => sum + row[i], 0) / e.imu.length) : band.current.acc;
      for (const p of e.preds) {
        if (Object.keys(p.probs).length !== profile.labels.length || !profile.labels.every((l) => l in p.probs) || Math.abs(now - p.t * 1000) > 300) { sequence.current.reset(); trigger.current.reset(); lastPred = 0; if (examOn.current) markTrial((t) => ({ ...t, paused: true })); setContact('—'); setConf(0); setCommand('信号不连续，动作已取消'); recRef.current.live = '—'; band.current = { state: 'live', text: '识别中 · 信号不连续', pose: '', acc: null }; continue; }
        const check = signalGate.status(now);
        // 结印组：服务端还没换成前端要的屏蔽（tune 没回来 / 失败），这条预测仍可能用了坏路，按没通过处理
        if (check.allowed && profile.protocol === 'select' && (p.mask ?? []).join(',') !== maskRef.current) { check.allowed = false; check.text = '正在同步屏蔽的路，暂不出招'; }
        if (!check.allowed) {
          validationLog.current?.('gate', { allowed: false, reason: check.text, prediction_t: p.t, prediction: p.validation });
          if (examOn.current) markTrial((t, ph) => ph === 'do' ? { ...t, paused: true } : t);
          paused = true; sequence.current.reset();
          // 结印：等待期间先上膛。放行时若这下印已经稳住，下一帧就出，不必再放松一次。认对测试仍整段作废。
          if (profile.game === 'tianjie' && !examOn.current) { trigger.current.watch(p.top, p.probs[p.top] ?? 0); lastPred = now; }
          else { trigger.current.reset(); lastPred = 0; }
          setContact('等待放松检查'); setCommand(check.text);
          const watch = gatedWatch(p.top, p.probs[p.top] ?? 0, LABEL_CN[p.top] ?? p.top, acc, !!p.gate?.blocked);
          setConf(p.gate?.blocked ? 0 : (p.probs[p.top] ?? 0));
          recRef.current.live = watch.live; band.current = watch.band; continue;
        }
        if (paused) { paused = false; setCommand(profile.game === 'tianjie' && trigger.current.primed() ? '检查通过，做动作就会出招' : '检查通过，先放松再做动作'); }
        if (p.gate?.blocked) { setContact('幅度不够'); setConf(0); }
        else { setContact((p.probs[p.top] ?? 0) >= .65 ? LABEL_CN[p.top] ?? p.top : '不确定，已取消动作'); setConf(p.probs[p.top] ?? 0); }
        band.current = p.gate?.blocked ? { state: 'live', text: '识别中 · 放松', pose: '', acc } : bandLive(p.top, p.probs[p.top] ?? 0, LABEL_CN[p.top] ?? p.top, acc);
        recRef.current.live = p.gate?.blocked ? '幅度不够 · 当放松' : `${LABEL_CN[p.top] ?? p.top} ${(p.probs[p.top] ?? 0).toFixed(2)}${(p.probs[p.top] ?? 0) < .65 ? ' · 不确定' : ''}`;
        if (profile.protocol === 'mouse' || profile.protocol === 'select') {  // 不走 Meta 组合时序。鼠标才发动作；AI 六类只记类名
          lastPred = now;
          const fired = trigger.current.push(p.top, p.probs[p.top] ?? 0, now);
          if (validationBusyRef.current) {
            if (fired) validationLog.current?.('trigger', { label: fired, confidence: p.probs[fired] ?? 0, eligible_game: (p.probs[fired] ?? 0) >= .8, prediction_t: p.t, prediction: p.validation });
            continue; // 验证录制只记实际触发，不发送游戏或鼠标。
          }
          if (fired && profile.protocol === 'mouse') fire(fired, p.t * 1000);
          if (fired && profile.protocol === 'select' && examOn.current) { markTrial((t, ph) => ph === 'do' ? (t.got ? t : { ...t, got: fired }) : { ...t, restFires: t.restFires + 1 }); continue; }
          if (fired && profile.protocol === 'select') {
            const game = gameBridge(), g = sealToGame(fired, p.probs[fired] ?? 0);
            if (!game || profile.game !== 'tianjie') { show(LABEL_CN[fired] ?? fired); continue; }
            // 结印组：送进游戏；游戏没开、置信不够、被拒都如实写进识别记录并显示在游戏左下角识别一栏 1.5 秒；冷却拒绝只写小栏不刷大字
            const out = (t: string, soft = false) => { recRef.current.text = t; recRef.current.until = Date.now() + 1500; if (!soft) show(t); };   // soft：只写小栏，不刷大字
            if ('skip' in g) { out(`${LABEL_CN[fired] ?? fired} · ${g.skip}`); continue; }
            const name = LABEL_CN[fired] ?? fired;
            void game.gesture(g.gesture, g.confidence).then((r) => out(!r.ok ? `${name} · 送游戏失败：${r.message}` : r.value.accepted ? `${name} → ${GAME_NAME[g.gesture]}出招` : `${name} · ${r.value.message}`, r.ok && !r.value.accepted && r.value.code === 'cooldown'));   // 按住期间撞上冷却的那几下只记小栏（复核 M1）
          }
          continue;
        }
        // 新捏合只在静止时建立；移动产生的肌电不能直接开启旋钮。
        if (profile.protocol === 'motion' && p.top === 'motion_hold' && !sequence.current.held) {
          const row = e.imu.at(-1);
          const bias = cal?.bias;
          if (!row || !bias || Math.hypot(...row.slice(0, 3).map((v, i) => v * .0012 - bias[i])) > .1) { sequence.current.reset(); trigger.current.reset(); lastPred = 0; continue; }
        }
        lastPred = now;
        sequence.current.push(p.top, p.probs[p.top] ?? 0, p.t * 1000).forEach(show);
        if ((p.probs[p.top] ?? 0) < .65) setCommand('不确定，请重新放松');
      }
      if (profile.protocol === 'motion' && e.imu.length) {
        const dt = lastImu ? Math.min(.1, (now - lastImu) / 1000) : 0; lastImu = now;
        if (!sequence.current.held || now - lastPred > 300 || cal?.donning !== donning || !cal) return;
        const avg = [0, 1, 2].map((i) => e.imu.reduce((sum, row) => sum + row[i], 0) / e.imu.length);
        const direction = motionDirection(avg, cal, mode);
        if (direction && dt > 0) {
          setCommand(LABEL_CN[direction.label]);
          if (mode === 'knob') setValue((v) => Math.max(0, Math.min(100, v + direction.speed * dt * (direction.label === 'motion_cw' ? 30 : -30))));
        }
      }
    });
    const timer = setInterval(() => {
      const now = Date.now(); sequence.current.expire(now).forEach(show);
      if (lastPred && now - lastPred > 300) { sequence.current.reset(); trigger.current.reset(); lastPred = 0; if (examOn.current) markTrial((t) => ({ ...t, paused: true })); setContact('—'); setConf(0); setCommand('数据过期，动作已取消'); recRef.current.live = '—'; band.current = { state: 'live', text: '识别中 · 数据过期', pose: '', acc: null }; }
    }, 50);
    return () => { off(); clearInterval(timer); sequence.current.reset(); recRef.current = { live: '', text: '', until: 0 }; };
  }, [bridge, projectId, profile, ready, output, accessBlocked, activeId, cal, donning, mode, target, st?.rig.link, st?.rig.link_detail, signalGate]);
  const toggle = async () => { const r = await bridge.live(projectId, on ? { action: 'stop' } : { action: 'start', runId: runId ?? undefined, thresholdUv: recognition.thresholdUv, sensitivity: recognition.sensitivity }); if (!r.ok) onError(r.message); };
  return <div className="emg8-live"><section className="emg8-card emg8-live-head"><div><h3>{profile.protocol === 'select' ? `${profile.labels.length} 类识别` : '组合动作试用'}</h3><small>{profile.windowMs ?? 200} ms 信号窗 · 每 50 ms 更新 · 仅本页反馈</small></div><button className={on ? 'emg8-stop' : 'emg8-primary'} onClick={toggle} disabled={validationBusy || (!on && !runId)} title={grayTitle(!on && !runId && '先在训练页生成一个模型')}>{on ? '停止识别' : '开始识别'}</button></section>
{rewear && <p className="emg8-warn emg8-rewear" role="alert"><span><b>{rewear.short}。</b><small>{rewear.detail}</small></span>{onRewear && <button type="button" onClick={onRewear}>去采集页</button>}</p>}
<div className="emg8-thumb-workgrid"><section className="emg8-card"><div className="ins-live">{[...command].length <= 8 ? <Flap text={command} dim={!ready} /> : <h2 role="status">{command}</h2>}<Gauge value={ready ? conf : 0} threshold={.65} /><span className="ins-cap">信号：{signalCheck.text}{maskNote && ` · ${maskNote}`} · 认成：{contact} · 红线 = 0.65</span>
        {profile.protocol === 'select' && ready && offerLanes.length > 0 && offerLanes.length <= 2 && <button type="button" onClick={() => setManual({ gate: signalGate, lanes: offerLanes })} title="手完全松开了这几路还偏高，多半没贴好。还握着印时别点：会把动作最强的路屏蔽掉（2026-10-15 握印录音里同样会出这个按钮）。屏蔽后缺这几路继续认；停止识别后恢复">松手后仍偏高 · 屏蔽第 {offerLanes.join('、')} 路</button>}</div>
      {profile.protocol === 'motion' ? <><div className="emg8-form"><label>试用动作<select value={mode} onChange={(e) => setMode(e.target.value as 'knob' | 'scroll')}><option value="knob">捏住转腕</option><option value="scroll">捏住摆臂</option></select></label><label>转腕用途<select value={target} onChange={(e) => setTarget(e.target.value)}>{['音量', '亮度', '缩放'].map((x) => <option key={x}>{x}</option>)}</select></label></div>{mode === 'knob' && <p>{target}试用：<b>{Math.round(value)}%</b><progress value={value} max={100} /></p>}<p className="emg8-fine">{cal?.status === 'calibrated' && cal.donning === donning ? '当前佩戴方向已校准。先静止捏住，再转动；松开即停止。' : cal?.reason ?? '请在采集页录完六个运动方向，每类至少 3 条，再重新训练。'}{cal?.status === 'calibrated' && cal.donning !== donning ? '佩戴已改变，方向校准失效，请重录。' : ''}</p></> : profile.protocol === 'mouse' ? <div className="ins-bind">
        <table><tbody>{Object.entries(mousePreset(step)).filter(([l]) => profile.labels.includes(l)).map(([l, a]) => <tr key={l}><td>{LABEL_CN[l] ?? l}</td><td>{a.text}</td></tr>)}</tbody></table>
        <div className="emg8-form"><label>每次挪<select value={step} onChange={(e) => setStep(Number(e.target.value))}>{[60, 120, 240].map((v) => <option key={v} value={v}>{v} 像素</option>)}</select></label>
          <button className={output ? 'emg8-stop' : 'emg8-primary'} disabled={!ready && !output} title={grayTitle(!output && !on && '先开始识别', !output && (!!st?.rig.replay || !!st?.wl8?.replay) && '正在回放，不能动真鼠标', !output && on && !fresh && '手环还没有新数据')} onClick={() => setOutput(!output)}>{output ? '停止控制鼠标' : '启用 · 控制真鼠标'}</button></div>
        {accessBlocked && <p className="emg8-warn" role="alert">{ACCESSIBILITY_HINT}</p>}
        <p className="emg8-fine">{output ? (accessBlocked ? '鼠标还没动：先允许辅助功能，再做动作。' : fresh ? '已启用：识别到的动作会真的点 / 挪鼠标。' : '已启用，等手环重新出数据后才会动鼠标。') : '演练：只显示识别结果，不动鼠标。'}{latency != null ? ` 最近一次从识别到执行 ${latency} ms。` : ''}同一类连续 3 次、置信度 ≥ 0.65 才算一次，回到放松才能做下一次。</p>
      </div> : profile.protocol === 'select' ? <div className="ins-bind">
        <table><tbody>{profile.labels.filter((l) => l !== profile.labels[0]).map((l) => <tr key={l}><td>{LABEL_CN[l] ?? l}</td><td>只认，不挪鼠标</td></tr>)}</tbody></table>
        <p className="emg8-fine">{profile.game === 'tianjie' ? '结印识别到就出招：同一印连续 3 次、置信度 ≥ 0.8 就送游戏，不用先放松；按住按各印冷却再出一次，换印即出。认对测试期间照旧要先放松。' : '同一类连续 3 次、置信度 ≥ 0.65 才记一次，回到放松才能再记。'}不会点击，也不会滚动。</p>
        <ExamPanel exam={exam} ready={!!ready && !validationBusy} onStart={startExam} onStop={() => setExam(null)} />
        {profile.game === 'tianjie' && !exam && <ContinuousValidation bridge={bridge} projectId={projectId} ready={!!ready} donning={donning} labels={profile.labels} onBusy={setValidationBusy} logger={validationLog} />}
        {profile.game === 'tianjie' && gameBridge() && <><button className="emg8-primary" onClick={() => void gameBridge()!.open().then((r) => { if (!r.ok) onError(r.message); })}>打开结印游戏</button>
          <p className="emg8-fine">认到的结印送进「掌中天劫」：道指 → 道指剑，破邪印 → 破邪印，五雷诀 → 五雷诀。游戏只收置信度 ≥ 0.8，冷却和灵力由游戏判定。</p></>}
      </div> : <p className="emg8-fine">食指点按：选择；中指单击：返回；中指双击：唤醒；中指长按：启动器；拇指侧面双击：AI。中指单击会等待 450 ms，排除双击。</p>}
      {profile.protocol === 'select' ? <p className="emg8-warn">{profile.labels.length} 类识别尚未佩戴验收。这一页只显示认到了哪一类。</p> : <p className="emg8-warn">组合动作尚未实测验收。基础分类准确率不能当作双击、长按或音量控制准确率。</p>}</section>
      <fieldset disabled={validationBusy} style={{ border: 0, padding: 0, margin: 0 }}><RecognitionControls thresholdUv={recognition.thresholdUv} setThresholdUv={recognition.setThresholdUv} sensitivity={recognition.sensitivity} setSensitivity={recognition.setSensitivity} pred={st?.wl8?.live?.last ?? null} /></fieldset>
      <aside className="emg8-card"><h3>本次实际识别记录</h3>{events.length ? <EventTape events={events} /> : <p className="emg8-fine">还没有识别到指令。</p>}<p className="emg8-fine">低置信、误触、丢帧或断流都会取消当前动作；{profile.game === 'tianjie' ? '恢复后摆稳就出。' : '恢复后先放松。'}{profile.protocol === 'mouse' ? (output ? '「开始用手势」已经打开真鼠标，点「停止控制鼠标」就只演练。' : '只有点了「启用」才会操作真鼠标。') : profile.protocol === 'select' ? '只把类名记下来，不发鼠标。' : '试用不会改变系统音量或鼠标。'}</p></aside></div>
  </div>;
}

/** 认对测试面板：进行中显示提示，做完显示每类认对 / 漏认 / 认成别类 */
function ExamPanel({ exam, ready, onStart, onStop }: { exam: { plan: string[]; i: number; phase: 'rest' | 'do' | 'done'; trials: ExamTrial[] } | null; ready: boolean; onStart: () => void; onStop: () => void }) {
  if (!exam) return <p><button className="emg8-primary" disabled={!ready} title={grayTitle(!ready && '先开始识别')} onClick={onStart}>认对测试 · 21 题 · 约 2.5 分钟</button></p>;
  if (exam.phase !== 'done') {
    const name = LABEL_CN[exam.plan[exam.i]] ?? exam.plan[exam.i];
    return <div className="ins-live"><h2 role="status">{exam.phase === 'rest' ? '放松' : `做：${name}`}</h2><span className="ins-cap">第 {exam.i + 1} / {exam.plan.length} 题 · 测试期间不送游戏</span><button onClick={onStop}>停止测试</button></div>;
  }
  const sc = examScore(exam.trials);
  return <div>
    <h3>认对 {sc.ok} / {sc.n}{sc.n ? `（${Math.round(100 * sc.ok / sc.n)}%）` : ''}</h3>
    <table><thead><tr><th>提示</th><th>认对</th><th>漏认</th><th>认成别类</th></tr></thead><tbody>{Object.entries(sc.per).map(([l, r]) => <tr key={l}><td>{LABEL_CN[l] ?? l}</td><td>{r.ok} / {r.n}</td><td>{r.miss}</td><td>{Object.entries(r.wrong).map(([w, k]) => `${LABEL_CN[w] ?? w} ${k}`).join('，') || '—'}</td></tr>)}</tbody></table>
    <p className="emg8-fine">放松段误出招 {sc.restFires} 次{sc.paused ? ` · 信号检查暂停 ${sc.paused} 题，不计分` : ''}</p>
    <button onClick={onStart}>再测一次</button> <button onClick={onStop}>关闭</button>
  </div>;
}
