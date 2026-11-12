'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import { NOISE_LIMIT_UV, TakeDeck, useAcceptBead, zeroStopped } from './instrument';
import type { CaptureProps } from './capture';
import { StrapField } from './capture';
import type { Hand } from './contract';
import type { GuideMode } from './thumb-guide';
import { FistGuide } from './fist-guide';
import { advance, askRestFor, calibrationHolds, canWaive, cellIndex, doneActions, nextDonning, noiseAdvice, noiseFloor, noiseVerdict, pauseHistory, contactGate, scoreVerdict, startCalibration, stopForRelaxationNoise, takeVerdict, waiveCal, waiveNoise, type Cal } from './calibration';
import { linkLine, zeroNote } from './link';
import { ElectrodeRing } from './ring';
import { PLACEMENT_HINT } from './placement';
import { REDON_NOTE, WINDOW_NOTE } from './readout';
import { grayTitle } from './gray-title';

// 每次佩戴校准页（design/emg-calibration-v1）：戴好 → 5 类轮流 × 5 轮（约 6 分钟）→ 自动训练 → 去识别。
// 只用这次佩戴的数据（服务端按佩戴编号过滤）；每条录完按幅度门槛判一次，弱 / 没录上就原地再录一次。
// 校准进度放在模块级：切到别的步骤再回来，组件重挂也接着显示（2026-10-09 走查：去「用手势」看一眼回来，进度和「模型好了」全没了，像白录）
const calStore = new Map<string, Cal | null>();
export function CalibrationCapture({ profile, projectId, bridge, st, hand, donning, setDonning, placement, setPlacement, strap, setStrap, setHand, onError, envelope, onTrained, onReconnect, onRewear, rms, rmsAt = 0 }: CaptureProps) {
  const cfg = profile.calibrate!;
  const storeKey = `${projectId}:${profile.name}`;
  // 重挂时若上次停在录制 / 训练中途，计数基线等 ref 已归零，接着判会错：先置「已停下」，用户点「继续校准」接着录
  const restore = (c: Cal | null | undefined): Cal | null => c && ['arm', 'wait', 'contact', 'train', 'training'].includes(c.phase) ? { ...c, phase: 'stopped', seenBusy: false, last: '刚才离开了这一页，已停下；点「继续校准」接着录' } : c ?? null;
  const [cal, setCal] = useState<Cal | null>(() => restore(calStore.get(storeKey)));
  useEffect(() => { setCal(restore(calStore.get(storeKey))); }, [storeKey]);           // 换工程 / 手势组但组件没重挂
  useEffect(() => { calStore.set(storeKey, cal); }, [storeKey, cal]);
  const [note, setNote] = useState('');                      // 自动改佩戴编号的说明：整轮里一直显示，不被每条的判定顶掉
  const [selected, setSelected] = useState(profile.labels[4] ?? profile.labels[0]);
  const [preview, setPreview] = useState(true);
  const [pending, setPending] = useState(false);
  const connected = st?.project?.id === projectId && st.rig.kind === 'wl8' && !!st.rig.port && st.rig.streaming && profile.labels.every((l) => st.tiers.includes(l));
  const replay = !!st?.rig.replay || !!st?.wl8?.replay;
  const gp = st?.progress;
  const recording = !!st?.busy && !!gp?.label && profile.labels.includes(gp.label);
  const running = !!cal && !['done', 'stopped'].includes(cal.phase);
  const waitingContact = cal?.phase === 'contact';
  const current = cal && (cal.phase === 'arm' || cal.phase === 'wait' || cal.phase === 'contact') ? cal.plan[cal.i] : null;
  const label = recording ? gp!.label! : current ?? selected;
  const gesture = profile.gestures![label];
  const mode: GuideMode = recording ? gp?.phase === 'NOW' ? 'record' : 'prepare' : pending || cal?.phase === 'arm' ? 'prepare' : preview ? 'preview' : 'paused';
  const counts = st?.project?.id === projectId ? st.counts.train?.wl8 ?? {} : {};
  const deck = useRef<HTMLDivElement>(null);
  useAcceptBead(counts, (l) => profile.gestures?.[l]?.color ?? '#163F35', deck, recording ? label : null);
  const zero = zeroStopped(st);
  const job = st?.wl8?.train;
  const score = job?.events?.find((e): e is Extract<typeof e, { stage: 'done' }> => e.stage === 'done')?.same_wear;
  // 底噪样本只收两种时段：① 没在跑校准（含暂停等贴合）的空闲段——和戴好页同口径，开始前能看、能拦、贴好能自动继续；
  // ② 录制里明确要求放松的倒数段（跳过前 0.6 s 避开上一动作尾巴）。动作 NOW 段永远不收：Mako 2026-10-08「我捏的时候底噪肯定会很高」。
  const hist = useRef<{ t: number; rms: number[] }[]>([]);
  const relaxingSince = useRef(0);
  const relaxing = !!cal && cal.phase === 'wait' && recording && gp?.label === cal.plan[cal.i] && /^[1-9]$/.test(gp?.phase ?? '');
  const idle = !recording && (!cal || cal.phase === 'stopped' || cal.phase === 'done' || cal.phase === 'contact' || cal.phase === 'arm');
  const now = Date.now();
  const signalFresh = rmsAt > 0 && now - rmsAt >= 0 && now - rmsAt < 500;
  if (relaxing) relaxingSince.current ||= now; else relaxingSince.current = 0;
  if ((idle || (relaxing && rmsAt - relaxingSince.current >= 600)) && signalFresh && rms?.length === 8 && rms.every(Number.isFinite) && hist.current.at(-1)?.t !== rmsAt) {
    hist.current.push({ t: rmsAt, rms }); hist.current = hist.current.filter(h => now - h.t <= 4000);
  }
  if (!connected || !signalFresh || !rms) { hist.current = []; relaxingSince.current = 0; }
  // 动作段保留刚才放松测量的基线，供幅度比较；不把新动作幅度添进去（4 s 窗按最后一个样本的时间算）。
  const floor = noiseFloor(hist.current, hist.current.at(-1)?.t ?? now);
  const noise = noiseVerdict(floor, NOISE_LIMIT_UV);   // 开始前拦、放松倒数里拦（2026-10-08 第 6 次佩戴底噪 158 µV 训出 50%，门槛才加）
  const gate = waiveNoise(noise, cal?.waived);          // 拦不拦按 gate（扣掉「仍然开始」放过的路）；电极环、柱子仍按原判定画
  const noiseText = recording && gp?.phase === 'NOW' ? '动作录制中 · 底噪检查已暂停'
    : cal?.waived && gate.kind === 'ok' && noise.kind !== 'ok' ? `已放过：${noiseAdvice(noise, NOISE_LIMIT_UV)}；这几路先不拦，分数低再回来压紧` : noiseAdvice(noise, NOISE_LIMIT_UV);
  const tape = useMemo(() => ({ uv: () => { const f = noiseFloor(hist.current, hist.current.at(-1)?.t ?? Date.now()); return f ? Math.max(...f) : NaN; }, limit: NOISE_LIMIT_UV }), []);   // 走纸条画 8 路最高的放松底噪

  // 幅度：录制的 NOW 阶段记 8 路 RMS（µV，不封顶）的最高值；基线 = 放松底噪最低值里最高的一路。
  // 之前读走纸条 envelope（0–1，125 µV 就满格），动作再大也算不到 3 倍，2026-10-08 第 7 次佩戴 24 条全被判弱（离线实为 5–21 倍）。
  const amp = useRef({ peak: 0, phase: '' });
  const nowKey = recording && gp?.phase === 'NOW' ? `${gp.take}` : '';
  if (nowKey && amp.current.phase !== nowKey) amp.current = { peak: 0, phase: nowKey };
  if (nowKey && rms && rms.length >= 8) amp.current.peak = Math.max(amp.current.peak, ...rms);

  // 状态机：arm 发一条录制 → wait 等服务端忙完 → 判定推进 → 录满 train → training 等模型 → done
  const [tick, setTick] = useState(0);                       // wait 阶段没见到 busy 时每秒自检一次超时
  useEffect(() => { if (!(cal?.phase === 'wait' && !cal.seenBusy) && cal?.phase !== 'contact') return; const t = setInterval(() => setTick((x) => x + 1), 1000); return () => clearInterval(t); }, [cal?.phase, cal?.seenBusy]);
  const okSince = useRef(0);
  const before = useRef(0), startRun = useRef<string | null | undefined>(undefined), fresh = useRef(false);   // fresh：train 返回后见过一次新任务快照（running 或 error 清空），之后的 error 才算这次的
  useEffect(() => {
    if (!cal) return;
    if (cal.phase === 'arm') {
      if (st?.busy || pending || !connected || replay || !signalFresh || !rms || gate.kind === 'unknown') return;
      if (calibrationHolds(gate)) { void pauseForContact(); return; }   // 只有过红线才不开录；黄线照常录，只提醒（Mako 2026-10-15）
      hist.current = []; relaxingSince.current = 0; amp.current = { peak: 0, phase: '' };   // 每条重新测放松，上一动作和旧基线不参与暂停判定
      const l = cal.plan[cal.i]; before.current = counts[l] ?? 0; setPending(true);
      void bridge.record(projectId, { label: l, count: 1, set: 'train', donning, session: `${hand === 'left' ? '左手' : '右手'} · ${placement} · 校准${cal.waived ? ` · 仍然开始（第${cal.waived.join('、')}路过线）` : ''}`, countdown: 3, calibration: true, strap_hole: strap ?? undefined })
        .then((r) => { if (r.ok) setCal((c) => c && c.phase === 'arm' ? { ...c, phase: 'wait', seenBusy: false, armedAt: Date.now() } : c); else { onError(r.message); setCal((c) => c && { ...c, phase: 'stopped', last: r.message }); } })
        .finally(() => setPending(false));
    } else if (cal.phase === 'wait') {
      if (relaxing && !signalFresh) { void stop('放松测量时信号已中断；检查连接后点「继续校准」'); return; }
      if (relaxing && stopForRelaxationNoise(hist.current, Date.now(), gp?.phase, NOISE_LIMIT_UV, cal.waived)) { void pauseForContact(); return; }   // 只看放松倒数段、连续 ≥1.2 s 超线才停；捏合再大也不算（Mako 2026-10-08）
      if (st?.busy) { if (!cal.seenBusy) setCal({ ...cal, seenBusy: true }); return; }
      if (pending) return;
      if (!cal.seenBusy) {                                        // 服务端线程秒失败时看不到 busy：6 s 内计数没变就按「没录上」
        const l = cal.plan[cal.i];
        if ((counts[l] ?? 0) > before.current) setCal({ ...cal, seenBusy: true });
        else if (Date.now() - (cal.armedAt ?? Date.now()) > 6000) setCal(advance(cal, 'lost', profile.gestures![l].name.split(' · ')[0]));
        return;
      }
      const l = cal.plan[cal.i], g = profile.gestures![l], a = amp.current;
      const saved = (counts[l] ?? 0) > before.current;
      const base = floor ? Math.max(...floor) : 0;
      const measured = a.phase !== '';                        // 轮询没赶上 NOW 阶段就没量到幅度：不能拿 0 当「没检测到动作」
      const v = saved ? measured ? takeVerdict(g.kind, a.peak, base, cfg.minRatio) : 'ok' : 'lost';
      const next = advance(cal, v, g.name.split(' · ')[0]);
      setCal(saved && g.kind !== 'rest' && base > 0 ? { ...next, last: `${next.last}（${measured ? `峰值 ${(a.peak / base).toFixed(1)} 倍放松` : '没量到幅度，先收下'}）` } : next);
    } else if (cal.phase === 'contact') {                       // 等电极贴好：底噪连续 1.5 s 回到非差（最低值一个好样本就会掉下来，所以要等稳），自动回 arm 重录这一格
      const g = contactGate(hist.current, Date.now(), NOISE_LIMIT_UV, cal.waived);   // 只看最近 0.5 s，一条好样本不能顶 4 s
      if (calibrationHolds(g) || g.kind === 'unknown') { okSince.current = 0; return; }
      okSince.current ||= Date.now();
      if (Date.now() - okSince.current >= 1500) { okSince.current = 0; setCal({ ...cal, phase: 'arm', seenBusy: false, last: '贴好了，接着录' }); }
      else setTimeout(() => setTick((x) => x + 1), 500);
    } else if (cal.phase === 'train') {
      if (st?.busy || pending) return;
      startRun.current = job?.run_id; fresh.current = false; setPending(true);
      void bridge.train(projectId, { labels: profile.labels }).then((r) => { if (r.ok) setCal((c) => c && { ...c, phase: 'training', last: '正在用这次的样本训练…' }); else { onError(r.message); setCal((c) => c && { ...c, phase: 'stopped', last: r.message }); } }).finally(() => setPending(false));
    } else if (cal.phase === 'training') {
      if (job?.running || job?.error == null) fresh.current = true;    // 服务端起新任务时同步把 error 置空
      if (job && !job.running && job.run_id && job.run_id !== startRun.current) { try { localStorage.setItem(calKey, JSON.stringify(donning)); } catch { /* 预览里可能不可用 */ } setCal({ ...cal, phase: 'done', runId: job.run_id, last: `第 ${donning} 次佩戴的模型好了` }); }
      else if (fresh.current && job?.error) setCal({ ...cal, phase: 'stopped', last: `训练失败：${job.error}。缺的那类用「再补一轮」补上` });
    }
  }, [cal, st?.busy, pending, connected, replay, counts, job?.running, job?.run_id, job?.error, tick, gate.kind, rmsAt, gp?.phase]); // eslint-disable-line react-hooks/exhaustive-deps

  const calKey = `emg8:${projectId}:calibratedDonning`;
  const start = (rounds: number, waived = cal?.waived) => {   // 补一轮沿用这一戴已放过的路；从头开始只有点「仍然开始」才带
    hist.current = []; relaxingSince.current = 0;
    let note = '';
    if (rounds === cfg.rounds) {                                 // 整轮校准 = 新戴上：上次校准完成的编号和现在一样就自动 +1（补录不算）
      let last: number | null = null; try { last = JSON.parse(localStorage.getItem(calKey) ?? 'null'); } catch { /* 预览里可能不可用 */ }
      const n = nextDonning(donning, typeof last === 'number' ? last : null);
      if (n !== donning) { setDonning(n); note = `已自动记为第 ${n} 次佩戴（上一次校准是第 ${donning} 次）；不是新戴的就在「佩戴与信号」改回去`; }
    }
    setNote(note);
    setCal({ ...startCalibration(profile.labels, rounds, cfg.shuffle ? Math.random : undefined, cfg.shuffle ? cal?.plan[cal.i - 1] : undefined), waived });   // shuffle：每轮随机顺序（EgoEMG 六手势）；补一轮不和刚录的那条同类
  };
  // 底噪过线时不进手势：先沾水压紧，只重录放松，再按这次佩戴重算留一。不改佩戴编号。
  const rerecordRest = () => {
    hist.current = []; relaxingSince.current = 0;
    setNote('');
    const rest = profile.labels.find((l) => profile.gestures?.[l]?.kind === 'rest') ?? profile.labels[0];
    setCal({ ...startCalibration([rest], 1), waived: cal?.waived });
  };
  const stop = async (why = '已停下，可以继续') => { setCal((c) => c && { ...c, phase: 'stopped', last: why }); const r = await bridge.recordStop(projectId); if (!r.ok) onError(r.message); };
  // 进等贴合时把底噪历史裁到最近 2 s：停录判的就是这 2 s，电极环和恢复判定也只看它，免得早段好样本把红盖掉（复核 P1）
  const pauseForContact = async () => { hist.current = pauseHistory(hist.current, Date.now()); setCal((c) => c && { ...c, phase: 'contact', seenBusy: false, last: noiseText }); relaxingSince.current = 0; const r = await bridge.recordStop(projectId); if (!r.ok) onError(r.message); };
  // 1–2 路怎么压都下不去：放过现在过线的路接着录（≥3 路 canWaive 为假，按钮不出现）
  // 完成页放过后用手势页：结印组（select）会屏蔽坏路，别的组照旧被放松门拦
  const waive = () => setCal((c) => c && waiveCal(c, noise.bad));
  const waiveLabel = `第 ${noise.bad.join('、')} 路先不管`;   // canWaive 只在有过线路时为真
  const resume = () => { hist.current = []; relaxingSince.current = 0; okSince.current = 0; setCal((c) => c && { ...c, phase: c.i >= c.plan.length ? 'train' : 'arm', seenBusy: false }); };
  const rewear = () => { calStore.set(storeKey, null); setDonning(Math.min(20, donning + 1)); setCal(null); setNote(''); onRewear?.(); };   // 重戴后先回「戴好」查贴合，再校准；直接清 Map：切页会让本组件先卸载，effect 来不及写（复核 P1）
  const verdict = scoreVerdict(score, profile.labels.length);
  const noiseHolds = calibrationHolds(gate);
  const alarm = waitingContact || (connected && gate.kind === 'bad');   // 报警框只出一处：页面其余地方不再重复同一句（2026-10-12 截图里同一句出现 4 次）
  const calWhy = (opts?: { replay?: boolean; noise?: boolean }) => grayTitle(
    !connected && '还没连上这条腕带',
    !signalFresh && '半秒内没有新的肌电',
    opts?.replay && replay && '正在回放，不能新录',
    opts?.noise && noiseHolds && '底噪过线，先沾水压紧再重录放松',
  );
  useEffect(() => {
    if (cal?.phase === 'done' && noiseHolds && !cal.restDue) setCal({ ...cal, restDue: true });
  }, [cal, noiseHolds]);
  const askRest = askRestFor(cal, noiseHolds);
  const doneKind = doneActions(verdict.kind, askRest);
  const noisyLanes = gate.bad.join('、');
  const total = cal?.plan.length ?? profile.labels.length * cfg.rounds;
  const seconds = Math.round(total * 14);
  const names = profile.labels.map((l) => ({ mouse_rest: '松', mouse_index: '食', mouse_middle: '中', mouse_swipe: '拨', mouse_side: '侧', mouse_up: '上', mouse_down: '下', mouse_left: '左', mouse_right: '右' } as Record<string, string>)[l] ?? profile.gestures![l].icon);
  return <div className="emg8-thumb-capture emg8-meta-capture emg8-calibration">
    <div className="emg8-thumb-workgrid">
      <section className="emg8-card emg8-thumb-action">
        <header><h3>动作示范</h3><div className="emg8-thumb-session"><label>佩戴手 <select aria-label="佩戴手" value={hand} disabled={running} onChange={(e) => setHand(e.target.value as Hand)}><option value="left">左手</option><option value="right">右手</option></select></label><small>第 {donning} 次佩戴 · 校准</small></div></header>
        {alarm && <div className="ins-alert emg8-contact" role="alert"><ElectrodeRing values={floor} max={NOISE_LIMIT_UV * 1.6} hand={hand} size={132} label="放松底噪 µV" hot={(v) => v > NOISE_LIMIT_UV} onlyHot /><div><b>{waitingContact ? (noise.kind === 'unknown' ? '已暂停，等信号' : '已暂停，等电极贴好') : '电极没贴紧'}</b><span>{noiseText}</span><small>红的那片就是要压的位置；肌肉发力会让多路一起升，只有一两路高是接触问题</small></div></div>}
        {zero && <div className="ins-alert ins-zero" role="alert"><b>没收到数据 · 0 帧</b><span>这一条已停下。{zeroNote(st?.rig.link)}</span></div>}
        {/* 底噪报警时示范收成一行：报警框已占半屏，示范图被挤到下面看不全；贴好后自动展开（2026-10-12） */}
        {alarm ? <p className="emg8-guide-folded">示范：{gesture.name.split(' · ')[0]} · 电极贴好后展开</p> : <>
        {/* hold（结印）是摆好保持，不是做一下就松：不给「做完马上松开」的窗口提示 */}
        {/* cont（EgoEMG 连续动作）整个两秒都在来回做，同样不给「做完马上松开」 */}
        {gesture.kind !== 'rest' && gesture.kind !== 'hold' && gesture.kind !== 'cont' && <p className="emg8-readfirst">{WINDOW_NOTE}</p>}
        <div className={running ? 'ins-take-row' : 'ins-take-row ins-take-solo'}>
          <FistGuide key={`${label}:${hand}`} label={label} kind={gesture.kind} name={gesture.name} icon={gesture.icon} cue={gesture.cue} hand={hand} mode={mode} takeKey={`${gp?.take ?? ''}:${gp?.phase ?? ''}`} onPreview={() => setPreview(!preview)} />
          {running && <TakeDeck deckRef={deck} phase={gp?.phase} take={gp?.take} count={gp?.count} recording={recording} zero={zero} envelope={envelope} noise={tape} />}
        </div></>}
        <div className={`emg8-thumb-cue ${recording && gp?.phase === 'NOW' ? 'go' : ''}`} role="status"><div><strong>{recording ? gp?.phase === 'NOW' ? gesture.kind === 'rest' ? '保持放松' : gesture.kind === 'hold' ? '摆好，保持住' : gesture.kind === 'cont' ? '做！连续来回做，到提示结束' : '做！只做一次' : '准备，先不要动' : waitingContact ? '压一下亮红的电极，稳了自动继续' : cal?.phase === 'arm' ? '下一条马上开始' : cal?.phase === 'training' ? '正在训练…' : cal?.phase === 'done' ? verdict.title : cal?.phase === 'stopped' ? '已停下' : '先看动作，再开始校准'}</strong><small>{running && cal ? `第 ${Math.min(cal.i + 1, total)} / ${total} 次 · ${gesture.name.split(' · ')[0]}` : cal?.phase === 'stopped' ? `停在第 ${Math.min(cal.i + 1, total)} / ${total} 次 · 「继续校准」接着录，或「放弃这轮」` : cal?.phase === 'done' ? `${total} 次录完 · 第 ${donning} 次佩戴的模型，分数和建议看右栏` : `先听口令放松、3 秒倒数，再录动作；${profile.labels.length} 类轮流，同一类不连录。`}</small></div></div>
        <footer className="emg8-thumb-actionbar">
          {!cal && <button className="emg8-primary" disabled={!connected || !signalFresh || !!st?.busy || replay || noiseHolds} title={calWhy({ replay: true, noise: true })} onClick={() => start(cfg.rounds)}>{`开始校准 · ${total} 次 · 约 ${Math.round(seconds / 60)} 分钟`}</button>}
          {!cal && connected && canWaive(noise, null) && <button disabled={!signalFresh || !!st?.busy || replay} title={calWhy({ replay: true })} onClick={() => start(cfg.rounds, noise.bad)}>仍然开始 · {waiveLabel}</button>}
          {waitingContact && canWaive(noise, cal?.waived) && <button onClick={waive}>{waiveLabel}，接着录</button>}
          {running && <button onClick={() => stop()}>停下</button>}
          {cal?.phase === 'stopped' && <><button className="emg8-primary" disabled={!connected || !signalFresh || !!st?.busy || replay || noiseHolds} title={calWhy({ replay: true, noise: true })} onClick={resume}>{noiseHolds ? `第 ${noisyLanes} 路底噪过线 · 先沾水压紧` : '继续校准'}</button>{noiseHolds && canWaive(noise, cal.waived) && <button disabled={!connected || !signalFresh || !!st?.busy || replay} title={calWhy({ replay: true })} onClick={() => { waive(); resume(); }}>仍然继续 · {waiveLabel}</button>}<button disabled={!connected || !signalFresh || !!st?.busy || replay || noiseHolds} title={calWhy({ replay: true, noise: true })} onClick={() => start(1)}>再补一轮 · {profile.labels.length} 次</button><button onClick={() => setCal(null)}>放弃这轮</button></>}
          {cal?.phase === 'done' && doneKind === 'rest' && <><button className="emg8-primary" disabled={!connected || !signalFresh || !!st?.busy || replay || noiseHolds} title={calWhy({ replay: true, noise: true })} onClick={rerecordRest}>{noiseHolds ? `第 ${noisyLanes} 路底噪过线 · 先沾水压紧` : '沾水压紧后重录放松'}</button>{noiseHolds && canWaive(noise, cal.waived) && <button onClick={waive}>仍然用 · {waiveLabel}</button>}<button disabled={!connected || !signalFresh || !!st?.busy || noiseHolds} title={calWhy({ noise: true })} onClick={() => start(1)}>再补一轮 · {profile.labels.length} 次</button></>}
          {cal?.phase === 'done' && doneKind === 'retry' && <><button className="emg8-primary" disabled={!connected || !signalFresh || !!st?.busy} title={calWhy()} onClick={() => start(1)}>再补一轮 · {profile.labels.length} 次</button><button onClick={() => cal.runId && onTrained?.(cal.runId)}>先试试看 →</button></>}
          {cal?.phase === 'done' && doneKind === 'look' && <><button className="emg8-primary" onClick={() => cal.runId && onTrained?.(cal.runId)}>看认到哪一类</button><button disabled={!connected || !signalFresh || !!st?.busy} title={calWhy()} onClick={() => start(1)}>再补一轮 · {profile.labels.length} 次</button></>}
          <label>示范 <select aria-label="示范动作" value={selected} disabled={running} onChange={(e) => setSelected(e.target.value)}>{profile.labels.map((l) => <option key={l} value={l}>{profile.gestures![l].name.split(' · ')[0]}</option>)}</select></label>
        </footer>
        {(!connected || st?.rig.link === 'no-receiver' || st?.rig.link === 'waiting-band' || st?.rig.link === 'dropped') && <p className="emg8-fine emg8-thumb-validation" role="status">{linkLine(st?.rig.link, st?.rig.link_detail)}{!connected && <> <button type="button" onClick={onReconnect} disabled={!onReconnect} title={grayTitle(!onReconnect && '这一页没有重连')}>重新连接</button></>}</p>}
        {connected && noise.kind === 'high' && <p className={`emg8-fine emg8-thumb-validation emg8-noise-${noise.kind}`} role="alert">{noiseText}</p>}
      </section>
      <aside className="emg8-card emg8-thumb-gestures"><header><h3>校准这次佩戴</h3><small>第 {donning} 次</small></header>
        <div className="emg8-cal-body">
          {cal?.phase === 'done' ? <><div className={`big emg8-score-${verdict.kind}`}>{score != null ? `${Math.round(score * 100)}%` : '模型好了'}</div><p className="emg8-fine">{noiseHolds ? '底噪还高。先沾水压紧，重录放松，再看这个数。' : verdict.hint}</p><p className="emg8-fine">这次佩戴的留一估计。摘下或转一下，这个数作废。</p><p className="emg8-fine">光标移动在「控制」页，用手腕角速度。</p></>
            : !cal && connected && noise.kind === 'bad' ? <><div className="big">先降底噪</div><p className="emg8-fine">8 路放松底噪最好都低于 {NOISE_LIMIT_UV} µV。红的那几路先沾水压紧；只有 1–2 路压不下来，可以点「仍然开始」，看录完的分数再定；3 路及以上要重新戴。</p></>
            : <><div className="big">{running && cal ? `${Math.min(cal.i + 1, total)} / ${total}` : `${total} 次动作`}</div><p className="emg8-fine">{REDON_NOTE}每个手势做 {cfg.rounds} 次，{profile.labels.length} 个手势轮流来；只用这次佩戴的数据训练。</p></>}
          <div className="emg8-cal-last" role="status">{cal?.last ?? ''}</div>
          {note && cal && <p className="emg8-fine emg8-cal-note" role="status">{note}</p>}
          <div className={`emg8-noise emg8-noise-${noise.kind}`} aria-label="放松底噪">{gate.kind !== 'bad' && <small>{noiseText}{noise.kind !== 'unknown' ? ` · 红线 ${NOISE_LIMIT_UV} µV` : ''}</small>}
            <div className="bars">{Array.from({ length: 8 }, (_, i) => { const v = floor?.[i]; const h = Number.isFinite(v as number) ? Math.min(100, (v as number) / (NOISE_LIMIT_UV * 1.6) * 100) : 0; return <i key={i} className={!Number.isFinite(v as number) ? '' : (v as number) > NOISE_LIMIT_UV ? 'bad' : (v as number) >= NOISE_LIMIT_UV * .55 ? 'high' : 'ok'} style={{ height: `${Math.max(4, h)}%` }} title={`第 ${i + 1} 路放松底噪 ${Number.isFinite(v as number) ? Math.round(v as number) : '—'} µV`} />; })}</div>{noise.kind === 'ok' && <small>这里只看本条倒数时的放松测量；动作段不检查底噪。校准口令由 Mac 本地播报。</small>}</div>
          <label className="emg8-cal-place">佩戴位置<input value={placement} disabled={running} onChange={(e) => setPlacement(e.target.value)} placeholder={PLACEMENT_HINT} title={PLACEMENT_HINT} /></label>
          <StrapField className="emg8-cal-place" strap={strap} setStrap={setStrap} disabled={running} />
          {!!st?.log.length && <p className="emg8-fine" role="status">采集服务：{st.log.at(-1)}</p>}
        </div>
        <div className="emg8-cal-beads" style={{ gridTemplateColumns: `auto repeat(${profile.labels.length}, minmax(0, 1fr))` }} aria-label="校准进度">
          <span /> {names.map((n) => <small key={n}>{n}</small>)}
          {Array.from({ length: cal ? Math.ceil(cal.plan.length / profile.labels.length) : cfg.rounds }, (_, r) => <Row key={r} r={r} labels={profile.labels} cal={cal} />)}
        </div>
        <footer><small>本工程累计</small><b>{profile.labels.reduce((s, l) => s + (counts[l] ?? 0), 0)} 条</b></footer>
      </aside>
    </div>
    <details className="emg8-thumb-details"><summary>佩戴与信号</summary><div className="emg8-thumb-details-body">
      <div className="emg8-form"><label>第几次佩戴<input type="number" min={1} max={20} value={donning} disabled={running} onChange={(e) => setDonning(Math.max(1, Math.min(20, Number(e.target.value) || 1)))} /></label><label>佩戴位置 / 条件<input value={placement} disabled={running} onChange={(e) => setPlacement(e.target.value)} placeholder={PLACEMENT_HINT} title={PLACEMENT_HINT} /></label></div>
      <p className="emg8-fine">佩戴位置写成下次能照着戴的样子：{PLACEMENT_HINT}。这一行会存进每条样本的会话名。</p>
      <button disabled={running || donning >= 20} title={grayTitle(donning >= 20 && '佩戴次数已经到 20')} onClick={rewear}>已实际摘下重戴 → 第 {Math.min(20, donning + 1)} 次，先检查贴合再校准</button>
      <p className="emg8-fine">动作太弱（峰值不到放松的 {cfg.minRatio} 倍）或没录上的那一条会当场再录一次（黄点）；第二次仍弱就先收下。</p>
      {!!st?.log.length && <p className="emg8-fine" role="status">采集服务最近一条：{st.log.at(-1)}</p>}
    </div></details>
    {/* 不放「录完就识别」：它绕过校准的语音口令和「太弱当场重录」，校准页自己的流程已经是录完就训练 */}
  </div>;
}

export function Row({ r, labels, cal }: { r: number; labels: string[]; cal: Cal | null }) {
  return <>
    <small>第{r + 1}轮</small>
    {/* 列 = 手势（列头按 labels）；打乱顺序时按计划找这一轮里该手势是第几条，黄点 / 当前格才落在对的列 */}
    {labels.map((l, c) => { const k = cal ? cellIndex(cal.plan, r, labels.length, l) : -1; const m = cal?.marks[k] ?? ''; const now = !!cal && (cal.phase === 'arm' || cal.phase === 'wait') && cal.i === k; return <i key={c} className={`${m}${now ? ' now' : ''}`.trim()} />; })}
  </>;
}
