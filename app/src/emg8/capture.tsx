'use client';
// 采集：ab-control-v1 引导步骤（视觉稿 firmware/research/2026-09-30-ab-control-ui-mock.html，Mako 已确认；条件检查只提醒）
// + 手势卡片快速采集（Teachable Machine 式：每个手势一张卡，显示样本数，点一下连录几条）。
import { AnimatePresence, motion } from 'motion/react';
import { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { AbState, Conditions, Emg8Bridge, Hand, ServiceState } from './contract';
import { LABEL_CN, LABEL_ICON } from './contract';
import { NumberTicker } from './effects';
import type { Profile } from './profiles';
import { MetaCapture } from './meta-capture';
import { CalibrationCapture } from './calibration-capture';
import { linkLine } from './link';
import { ThumbCapture } from './thumb-capture';
import { grayTitle } from './gray-title';
import { EnrollRun } from './enroll-run';

export type CaptureProps = {
  profile: Profile; projectId: string; bridge: Emg8Bridge; st: ServiceState | null; ab: AbState | null;
  hand: Hand; donning: number; setDonning: (n: number) => void; placement: string; setPlacement: (s: string) => void;
  strap: number | null; setStrap: (n: number | null) => void;   // 织带孔位：只记进元数据，不参与识别
  setHand: (h: Hand) => void; onError: (m: string) => void;
  envelope?: () => number;                                 // 走纸记录条读最新一批的平均幅度（0–1），studio 提供
  onTrained?: (runId: string, opts?: { armMouse?: boolean }) => void; // 校准组：录满后去识别页；armMouse 为真才操作真鼠标
  rmsAt?: number;                                         // 最后真实EMG批次到达的主机毫秒时间
  onReconnect?: () => void;                                // 引导模式这页没有顶栏「重新连接」，未连上时就地给一个
  onRewear?: () => void;                                   // 摘下重戴后电极转了位置：回「② 戴好」重新检查贴合
  rms?: number[] | null;                                   // 8 路实时 RMS（µV），校准页做底噪提醒
};
/** 戴法（2026-10-21）：线缆朝向、CH1 电极对准哪里。工作室持有，录制时由包过的 bridge.record 带上；只记录，不影响识别。值是 .json 里的英文键。 */
export const CABLE_CN = { elbow: '朝手肘', palm: '朝手掌' } as const;
export const CH0_CN = { ulnar: '尺骨茎突侧', radial: '桡骨侧', palmar: '掌侧', dorsal: '背侧' } as const;
export type CableDir = keyof typeof CABLE_CN; export type Ch0Site = keyof typeof CH0_CN;
export type WearHow = { cable: CableDir | null; ch0: Ch0Site | null; setCable: (v: CableDir | null) => void; setCh0: (v: Ch0Site | null) => void };
export const WearContext = createContext<WearHow | null>(null);
/** 织带孔位：存进每条录音的元数据，以后拿底噪对照松紧；不参与识别。空着 = 这次没记。后面跟两个戴法下拉，所有录制页一起有。 */
export function StrapField({ strap, setStrap, disabled, className }: { strap: number | null; setStrap: (n: number | null) => void; disabled?: boolean; className?: string }) {
  const how = useContext(WearContext);
  return <><label className={className} title="按同一个数法记第几个孔；只记录，不影响识别">织带孔位<input type="number" min={1} max={20} value={strap ?? ''} placeholder="不记" disabled={disabled}
    onChange={(e) => { const n = Math.round(Number(e.target.value)); setStrap(e.target.value === '' || !n ? null : Math.max(1, Math.min(20, n))); }} /></label>
    {how && <><label className={className} title="线缆从腕带往哪边走；只记录，不影响识别">线缆朝向<select value={how.cable ?? ''} disabled={disabled} onChange={(e) => how.setCable((e.target.value || null) as CableDir | null)}>
      <option value="">未记</option>{Object.entries(CABLE_CN).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
    <label className={className} title="左栏 CH1 那颗电极贴在手腕哪一侧；只记录，不影响识别">CH1 电极对准<select value={how.ch0 ?? ''} disabled={disabled} onChange={(e) => how.setCh0((e.target.value || null) as Ch0Site | null)}>
      <option value="">未记</option>{Object.entries(CH0_CN).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label></>}</>;
}
const PHASE_WORD: Record<string, string> = { prepare: '准备', rest: '放松', hold: '捏住', release: '松开', daily: '动一动' };
const PHASE_ICON: Record<string, string> = { prepare: '⏱️', rest: '🖐️', hold: '🤏', release: '🖐️', daily: '🤹' };

/** 口令进度在两次轮询之间按本地时钟往前走，游标才连贯（暂停时不走） */
function useSmoothElapsed(elapsed: number | undefined, key: string, paused: boolean) {
  const [shown, setShown] = useState(0); const base = useRef({ at: 0, el: 0 });
  useEffect(() => { base.current = { at: performance.now(), el: elapsed ?? 0 }; }, [elapsed, key]);
  useEffect(() => {
    let raf = 0;
    const f = () => { const b = base.current; setShown(b.el + (paused ? 0 : (performance.now() - b.at) / 1000)); raf = requestAnimationFrame(f); };
    raf = requestAnimationFrame(f); return () => cancelAnimationFrame(raf);
  }, [paused]);
  return shown;
}

function LegacyCapture({ profile, projectId, bridge, st, ab, hand, donning, setDonning, placement, setPlacement, strap, setStrap, setHand, onError, onTrained }: CaptureProps) {
  const thumb = profile.labels.some((l) => l.startsWith('thumb_'));
  const gestures = profile.captureLabels ?? profile.labels;
  const connected = st?.project?.id === projectId && st?.rig.kind === 'wl8' && !!st.rig.port && st.rig.streaming && profile.labels.every((l) => st.tiers.includes(l));
  const [step, setStep] = useState('rehearsal');
  const [purpose, setPurpose] = useState<'dev' | 'rehearsal' | 'accept'>('rehearsal');
  const [cond, setCond] = useState<Conditions | null>(null);
  const [checking, setChecking] = useState(false);
  const [count, setCount] = useState(5);
  const [split, setSplit] = useState<'train' | 'rewear'>('train');
  const p = ab?.progress ?? {};
  const active = !!ab?.active, busy = !!st?.busy;
  const elapsed = useSmoothElapsed(p.phase_elapsed, `${p.cycle}-${p.phase}`, !!ab?.paused);
  const call = async (r: Promise<{ ok: boolean; message?: string }>) => { const x = await r; if (!x.ok) onError(x.message ?? '失败'); return x; };

  const checkConditions = async () => {
    setChecking(true);
    const r = await bridge.ab(projectId, { action: 'conditions' });
    setChecking(false);
    if (r.ok) setCond(r.value as Conditions); else onError(r.message);
  };
  const start = () => call(bridge.ab(projectId, { action: 'start', step, hand, donning, purpose, placement, conditions: cond, strap_hole: strap ?? undefined }));
  const steps = [...(ab?.steps ?? []), { key: 'rewear', title: '摘下重戴', hint: '完整摘下，酒精擦拭、沾水后重新戴好，进入下一次佩戴' }];

  // 当前循环的时间轴
  const plan = p.cycle_plan ?? [];
  const total = plan.reduce((s, x) => s + x.dur, 0) || 1;
  const before = plan.slice(0, plan.findIndex((x) => x.phase === p.phase)).reduce((s, x) => s + x.dur, 0);
  const head = Math.min(1, (before + Math.min(elapsed, p.phase_dur ?? 0)) / total);
  const left = Math.max(0, Math.ceil((p.phase_dur ?? 0) - elapsed));
  const word = p.phase === 'daily' ? (p.text ?? '') : p.phase === 'prepare' ? `${left || ''}` : PHASE_WORD[p.phase ?? ''] ?? '';
  const c = cond;
  const gp = st?.progress ?? {};

  return <div className="emg8-capture">
    <aside className="emg8-col">
      {thumb ? <section className="emg8-card"><header><h3>拇指四向 · 采集步骤</h3></header>
        <ol><li>前臂有支撑，手腕和食指保持不动。</li><li>静止和四个方向分别录；看到「做！」再滑一次。</li><li>滑完抬起拇指复位，避免反向滑回混进样本。</li><li>训练每类至少 5 条；摘下重戴、增加编号，再录每类至少 3 条验证。</li></ol>
        <p className="emg8-fine">个人数据和模型保存在本工程，本机训练。</p>
      </section> : <section className="emg8-card">
        <header><h3>抓放训练 · 本次佩戴</h3><small>{ab?.protocol ?? 'ab-control-v1'}</small></header>
        <ol className="emg8-steps">{steps.map((s, i) => {
          const d = ab?.done?.[s.key]; const cur = active ? p.step === s.key : step === s.key;
          return <li key={s.key} className={`${cur ? 'cur' : ''} ${d?.files ? 'done' : ''}`}>
            <button onClick={() => { if (active) return; setStep(s.key); setPurpose(s.key === 'rehearsal' ? 'rehearsal' : purpose === 'rehearsal' ? 'dev' : purpose); }} disabled={active || busy} title={grayTitle(active && '这一步正在录，不能换步骤')}>
              <span className="n">{d?.files ? '✓' : i}</span>
              <span><b>{s.title}</b><small>{s.hint}</small></span>
              <small>{d?.files ? `${d.files} 次${d.voided ? ` · 作废 ${d.voided}` : ''}` : ''}</small>
            </button></li>;
        })}</ol>
      </section>}
      <section className="emg8-card">
        <header><h3>会话</h3></header>
        <div className="emg8-form">
          <label>手别<select value={hand} onChange={(e) => setHand(e.target.value as Hand)} disabled={active || busy}><option value="left">左手</option><option value="right">右手</option></select></label>
          <label>第几次佩戴<input type="number" min={1} max={20} value={donning} onChange={(e) => setDonning(Math.min(20, Math.max(1, Number(e.target.value) || 1)))} disabled={active || busy} /></label>
          <label className="wide">佩戴位置 / 条件<input value={placement} onChange={(e) => setPlacement(e.target.value)} disabled={active || busy} placeholder="腕部贴掌根 · 酒精+沾水 · 前臂搁床" /></label>
          <StrapField strap={strap} setStrap={setStrap} disabled={active || busy} />
          {!thumb && <label className="wide">用途<select value={purpose} onChange={(e) => setPurpose(e.target.value as typeof purpose)} disabled={active || busy}>
            {Object.entries(ab?.purposes ?? { dev: '开发数据', rehearsal: '预演（不入训练集）', accept: '独立验收（冻结后）' }).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>}
        </div>
        {thumb ? <button disabled={busy || donning >= 20} title={grayTitle(donning >= 20 && '佩戴次数已经到 20')} onClick={() => { setDonning(donning + 1); setSplit('rewear'); }}>已摘下重戴 → 第 {Math.min(20, donning + 1)} 次佩戴</button> : step === 'rewear' && !active
          ? <button className="emg8-primary" onClick={() => setDonning(donning + 1)}>已重新戴好 → 第 {donning + 1} 次佩戴</button>
          : <div className="emg8-row">
            {!active ? <button className="emg8-primary" onClick={start} disabled={busy || !!st?.rig.replay} title={grayTitle(!!st?.rig.replay && '正在回放，不能新录')}>开始这一步</button>
              : ab?.paused ? <button className="emg8-primary" onClick={() => call(bridge.ab(projectId, { action: 'resume' }))}>继续</button>
                : <button onClick={() => call(bridge.ab(projectId, { action: 'pause' }))}>暂停</button>}
            <button onClick={() => call(bridge.ab(projectId, { action: 'void' }))} disabled={!active} title={grayTitle(!active && '还没开始这一步')}>作废上一条</button>
            <button className="emg8-stop" onClick={() => call(bridge.ab(projectId, { action: 'stop' }))} disabled={!active} title={grayTitle(!active && '还没开始这一步')}>停止</button>
          </div>}
        {st?.rig.replay && <p className="emg8-warn">回放模式不能录制训练数据</p>}
        <p className="emg8-fine">不舒服或累了就停，不为凑条数强录。作废只做标记，原始文件保留。</p>
      </section>
    </aside>

    <div className="emg8-col">
      <section className="emg8-card">
        <header><h3>采集条件</h3><button onClick={checkConditions} disabled={checking || busy}>{checking ? '测量中… 5 秒' : '测一下（5 秒）'}</button></header>
        <div className="emg8-checks">
          <div className={c?.mains_mv != null && c.mains_mv > 2 ? 'warn' : ''}><small>工频 50 Hz</small><b>{c?.mains_mv != null ? `${c.mains_mv} mV` : '—'}</b><small>建议 ≤ 2 mV</small></div>
          <div className={c?.noise_uv != null && c.noise_uv > 150 ? 'warn' : ''}><small>放松底噪（中位）</small><b>{c?.noise_uv != null ? `${c.noise_uv} µV` : '—'}</b><small>手放松时测</small></div>
          <div className={c?.acc_g != null && (c.acc_g < 8.5 || c.acc_g > 11) ? 'warn' : ''}><small>IMU</small><b>{c?.acc_g != null ? `|a| ${c.acc_g}` : '—'}</b><small>静止约 9.8</small></div>
          <div className={c?.power === 'ac' ? 'warn' : ''}><small>供电</small><b>{c?.power === 'battery' ? '电池' : c?.power === 'ac' ? '充电器' : '—'}</b><small>应当用电池</small></div>
        </div>
        {!!c?.warnings.length && <ul className="emg8-warnlist">{c.warnings.map((w) => <li key={w}>⚠️ {w}</li>)}</ul>}
        {c && !c.warnings.length && <p className="emg8-ok">条件良好，可以开始。</p>}
      </section>

      {thumb && <section className={`emg8-card emg8-cue ${busy && gp.label ? 'on' : ''}`} aria-live="polite">
        <div className="emg8-cue-top">
          <div><div className="emg8-cue-title">{gp.label ? LABEL_CN[gp.label] : '选择下方手势开始采集'}</div>
            <div className="emg8-cue-hint">{gp.label ? profile.gestures?.[gp.label]?.cue : '看到「做！」时，完成一次滑动。静止类保持放松。'}</div></div>
          <div className={`emg8-cue-big ${gp.phase === 'NOW' ? 'go' : ''}`}>{gp.label ? gp.phase === 'NOW' ? '做！' : gp.phase : '—'}</div>
        </div>
        {gp.label && <p className="emg8-fine">第 {gp.take} / {gp.count} 条 · {split === 'train' ? '训练集' : '重戴验证集'}</p>}
      </section>}

      {!thumb && <section className={`emg8-card emg8-cue ${active ? 'on emg8-beam' : ''}`} aria-live="polite">
        {active ? <>
          <div className="emg8-cue-top">
            <div className="emg8-cue-icon">{PHASE_ICON[p.phase ?? ''] ?? '•'}</div>
            <div><div className="emg8-cue-title">{p.text}</div>
              <div className="emg8-cue-hint">{p.title}{p.cycles ? ` · 第 ${p.cycle} / ${p.cycles} 次` : ''}{p.force ? ` · ${p.force === 'light' ? '轻力' : '中等力'}` : ''}{ab?.paused ? ' · 已暂停' : ''}</div></div>
            <div className={`emg8-cue-big ${p.phase === 'hold' ? 'go' : ''}`}><AnimatePresence mode="popLayout" initial={false}>
              <motion.span key={word} style={{ display: 'inline-block' }} initial={{ opacity: 0, scale: 1.6, filter: 'blur(6px)' }} animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
                exit={{ opacity: 0, scale: .6 }} transition={{ type: 'spring', stiffness: 420, damping: 24 }}>{word}</motion.span></AnimatePresence></div>
          </div>
          {plan.length > 0 && <div className="emg8-timeline">
            {plan.map((x, i) => <span key={i} className={`t-${x.phase}`} style={{ flex: x.dur }}>{PHASE_WORD[x.phase]} {x.dur} s</span>)}
            <i className="emg8-playhead" style={{ left: `${head * 100}%` }} />
          </div>}
          <div className="emg8-cue-meta"><span>已完成 {p.completed ?? 0}{p.voided?.length ? ` · 作废 ${p.voided.join('、')}` : ''}</span><span>本步剩余约 {Math.round(p.step_remaining ?? 0)} 秒</span></div>
        </> : <div className="emg8-cue-idle">
          <b>{steps.find((s) => s.key === step)?.title}</b>
          <span>{steps.find((s) => s.key === step)?.hint}</span>
          {ab?.last_saved && <small>上一步已保存：{ab.last_saved.step} · {ab.last_saved.completed} 次 · {(ab.last_saved.emg_samples / 2000).toFixed(0)} 秒{ab.last_saved.stopped ? ' · 中途停止' : ''}{ab.last_saved.dropped ? ` · 丢包 ${ab.last_saved.dropped}` : ''}</small>}
        </div>}
      </section>}

      <section className="emg8-card">
        <header><h3>手势卡片 · 快速采集</h3>
          <div className="emg8-row tight">
            <select value={split} onChange={(e) => setSplit(e.target.value as 'train' | 'rewear')}><option value="train">训练集</option><option value="rewear">重戴验证集</option></select>
            <select value={count} onChange={(e) => setCount(Number(e.target.value))}>{[3, 5, 10].map((n) => <option key={n} value={n}>每次 {n} 条</option>)}</select>
          </div></header>
        <div className="emg8-gcards">{gestures.map((g) => {
          const n = st?.counts?.[split]?.wl8?.[g] ?? 0; const rec = st?.busy && gp.label === g;
          return <button key={g} className={`emg8-gcard ${rec ? 'rec' : ''}`} disabled={!connected || busy || active || !!st?.rig.replay} title={grayTitle(!connected && '还没连上这条腕带', active && '引导步骤还在录', !!st?.rig.replay && '正在回放，不能新录')}
            onClick={() => call(bridge.record(projectId, { label: g, count, set: split, donning, session: `${hand === 'left' ? '左手' : '右手'} · ${placement}`, countdown: 3, strap_hole: strap ?? undefined }))}>
            <span className="i">{LABEL_ICON[g]}</span><b>{LABEL_CN[g]}</b>
            <span className="n"><NumberTicker value={n} /><small> 条</small></span>
            <span className="bar"><i style={{ width: `${Math.min(100, (n / 15) * 100)}%` }} /></span>
            <small>{rec ? `录制中 ${gp.take}/${gp.count} · ${gp.phase === 'NOW' ? '做！' : gp.phase ?? ''}` : '点一下，连录'}</small>
            {profile.gestures?.[g] && <small>{profile.gestures[g].cue}</small>}
          </button>;
        })}</div>
        {(!connected || st?.rig.link === 'no-receiver' || st?.rig.link === 'waiting-band' || st?.rig.link === 'dropped') && <p className="emg8-fine" role="status">{linkLine(st?.rig.link, st?.rig.link_detail)}</p>}
        {!!st?.log.length && <p className="emg8-fine" role="status">{st.log.at(-1)}</p>}
        <p className="emg8-fine">{thumb ? '每条 2 秒：静止类保持放松；方向类滑一次后抬起复位。重戴验证要摘下再戴，并使用新的佩戴编号。' : '每条 2 秒：先放松 → 做一次 → 松开。训练集和重戴验证集分开录；重戴要真的摘下来再戴。'}</p>
      </section>
      <EnrollRun profile={profile} projectId={projectId} bridge={bridge} st={st} hand={hand} donning={donning} placement={placement} strap={strap} count={count} split={split} connected={connected} onError={onError} onTrained={onTrained} />
    </div>
  </div>;
}

// 拇指组使用动作引导；旧抓放协议保留原来的采集流程。
export function Capture(props: CaptureProps) {
  return props.profile.calibrate ? <CalibrationCapture {...props} /> : props.profile.protocol ? <MetaCapture {...props} /> : props.profile.gestures && props.profile.layout !== 'cards' ? <ThumbCapture {...props} /> : <LegacyCapture {...props} />;
}
