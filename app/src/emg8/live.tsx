'use client';
// 实时识别：服务端 LivePredictor 每 100 ms 出一次概率；这里用弹簧把概率条推上推下，最高的一类发光，
// 外圈是它的置信度，换类时爆一圈粒子。
import { MetaLive } from './meta-live';
import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import { EventTape, Flap, Gauge } from './instrument';
import type { Emg8Bridge, Pred, ServiceState } from './contract';
import { CLASS_COLORS, LABEL_CN, LABEL_ICON } from './contract';
import { Burst, ConfidenceRing } from './effects';
import type { Profile } from './profiles';
import { grayTitle } from './gray-title';
import { RecognitionControls, useRecognitionGate } from './recognition-gate';
import { ClassicOut } from './classic';

function BasicLive({ profile, projectId, bridge, st, pred, runId, onError }: { profile: Profile; projectId: string; bridge: Emg8Bridge; st: ServiceState | null; pred: Pred | null; runId: string | null; onError: (m: string) => void }) {
  const on = !!st?.wl8?.live;
  const classic = profile.layout === 'classic';
  const gate = useRecognitionGate(bridge, projectId, on, onError, st?.wl8?.live?.last, undefined, classic);
  const valid = pred && Object.keys(pred.probs).length === profile.labels.length && profile.labels.every((l) => l in pred.probs);
  const probs = on && valid ? pred.probs : {};
  const labels = profile.labels;
  const blocked = on && (!!pred?.gate?.blocked || !!pred?.gate?.unsure);   // unsure：过不了动作阈值（把握度），同样不换牌
  const top = blocked ? undefined : on && valid && profile.labels.includes(pred?.stable ?? '') ? pred?.stable : undefined;                     // 防抖后的类别；被门槛拦住时不换牌
  // 引导组用仪器部件：防抖后的类别一变（且不是放松）就记一条事件
  const guided = !!profile.gestures;
  const [events, setEvents] = useState<{ id: number; t: string; text: string; ok: boolean }[]>([]);
  const t0 = useRef(0);
  useEffect(() => {
    if (!top || top === 'rest' || ['rest', 'other'].includes(profile.gestures?.[top]?.kind ?? '')) return;   // 放松、随意动手（不触发）不记事件
    if (!t0.current) t0.current = performance.now();
    setEvents((xs) => [...xs, { id: performance.now(), t: `${((performance.now() - t0.current) / 1000).toFixed(1)}s`, text: LABEL_CN[top] ?? top, ok: true }].slice(-6));
  }, [top]);
  const toggle = async () => {
    const r = await bridge.live(projectId, on ? { action: 'stop' } : { action: 'start', runId: runId ?? undefined, thresholdUv: gate.thresholdUv, sensitivity: gate.sensitivity, minProb: gate.minProb, ...(classic ? { thresholdX: gate.timesX } : {}) });
    if (!r.ok) onError(r.message);
  };
  return <div className="emg8-live">
    <section className="emg8-card emg8-live-head">
      <div><h3>实时识别</h3><small>{on ? `模型 ${st?.wl8?.live?.run_id} · 每 100 ms 一次 · 窗口 1 秒` : '先在「训练」里训练一个模型，再开始'}</small></div>
      <button className={on ? 'emg8-stop' : 'emg8-primary'} onClick={toggle} disabled={!on && !runId} title={grayTitle(!on && !runId && '先在训练页生成一个模型')}>{on ? '停止识别' : '开始识别'}</button>
    </section>
    <div className="emg8-live-grid">
      <section className="emg8-card emg8-live-big">
        {guided ? <div className="ins-live">
          <Flap text={blocked ? (pred?.gate?.unsure ? '把握不够' : '幅度不够') : top ? LABEL_CN[top] ?? top : on ? '等数据' : '未开始'} dim={!top && !blocked} />
          <Gauge value={top ? probs[top] ?? 0 : 0} />
          <span className="ins-cap">置信度 · 连续 3 次同一类才换牌</span>
        </div> : <div className="emg8-live-stage">
        <ConfidenceRing value={top ? probs[top] ?? 0 : 0} color={top ? CLASS_COLORS[top] : 'transparent'} size={220} />
        <Burst burstKey={top ?? ''} color={top ? CLASS_COLORS[top] : '#fff'} />
        <AnimatePresence mode="wait">
          <motion.div key={top ?? 'none'} className="emg8-live-top" style={{ ['--glow' as string]: top ? CLASS_COLORS[top] : 'transparent' }}
            initial={{ opacity: 0, scale: .8, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: .9 }} transition={{ type: 'spring', stiffness: 380, damping: 26 }}>
            <span className="i">{blocked ? '–' : top ? LABEL_ICON[top] : '…'}</span><b>{blocked ? '幅度不够' : top ? LABEL_CN[top] : on ? '等数据' : '未开始'}</b>
          </motion.div>
        </AnimatePresence>
        </div>}
        <small>{st?.rig.replay ? '回放数据，不是现场' : '现场实时'}</small>
        {guided && <EventTape events={events} />}
      </section>
      <section className="emg8-card">
        <header><h3>各类概率</h3></header>
        <ul className="emg8-bars">{labels.map((l) => <li key={l} className={l === top ? 'top' : ''}>
          <span>{LABEL_ICON[l]} {LABEL_CN[l] ?? l}</span>
          <div className="track"><motion.i style={{ background: CLASS_COLORS[l] ?? 'var(--emg8-accent)' }} animate={{ width: `${Math.round((probs[l] ?? 0) * 100)}%` }} transition={{ type: 'spring', stiffness: 300, damping: 30 }} />
            {gate.minProb > 0 && <em className="emg8-bar-gate" style={{ left: `${gate.minProb * 100}%` }} aria-hidden />}</div>
          <b>{Math.round((probs[l] ?? 0) * 100)}%</b></li>)}</ul>
        {gate.minProb > 0 && <p className="emg8-fine">橙线 = 动作阈值 {gate.probPct}%：没有一类过线就判放松。</p>}
        <p className="emg8-fine">是否经过重戴验证请查看训练结果。手没放松、电极变干时识别可能变乱。此页显示手势，拇指驱动鼠标尚未接入。</p>
      </section>
      <RecognitionControls thresholdUv={gate.thresholdUv} setThresholdUv={gate.setThresholdUv} sensitivity={gate.sensitivity} setSensitivity={gate.setSensitivity} pred={pred}
        {...(classic ? { probPct: gate.probPct, setProbPct: gate.setProbPct, timesX: gate.timesX, setTimesX: gate.setTimesX } : {})} />
      {classic && <ClassicOut bridge={bridge} projectId={projectId} ctrl={st?.wl8?.ctrl} onError={onError} />}
    </div>
  </div>;
}

export function Live(props: Parameters<typeof BasicLive>[0] & { donning?: number; armMouse?: boolean; rms?: number[] | null; rmsAt?: number; onRewear?: () => void }) {
  return props.profile.protocol ? <MetaLive key={props.profile.name} {...props} donning={props.donning ?? 0} /> : <BasicLive {...props} />;   // 换动作组要重挂载：触发器里的放松标签只在挂载时取（复核二轮）
}
