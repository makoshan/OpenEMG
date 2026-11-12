'use client';
// 勾选动作、设定单次时长，按顺序录完再训练。原来的单类按钮仍是每条 2 秒。
import { useRef, useState } from 'react';
import { grayTitle } from './gray-title';
import type { Emg8Bridge, Hand, ServiceState } from './contract';
import { LABEL_CN } from './contract';
import { trainingBlock, type Profile } from './profiles';

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function EnrollRun(props: {
  profile: Profile; projectId: string; bridge: Emg8Bridge; st: ServiceState | null; hand: Hand; donning: number; placement: string; strap: number | null;
  count: number; split: 'train' | 'rewear'; connected: boolean; onError: (message: string) => void;
  onTrained?: (runId: string, opts?: { armMouse?: boolean }) => void;
}) {
  return <EnrollBody key={props.profile.name} {...props} />;
}

function EnrollBody({ profile, projectId, bridge, st, hand, donning, placement, strap, count, split, connected, onError, onTrained }: {
  profile: Profile; projectId: string; bridge: Emg8Bridge; st: ServiceState | null; hand: Hand; donning: number; placement: string; strap: number | null;
  count: number; split: 'train' | 'rewear'; connected: boolean; onError: (message: string) => void;
  onTrained?: (runId: string, opts?: { armMouse?: boolean }) => void;
}) {
  const [picked, setPicked] = useState(profile.labels);
  const [seconds, setSeconds] = useState(2);
  const [running, setRunning] = useState(false);
  const [note, setNote] = useState('');
  const stop = useRef(false);
  const toggle = (label: string) => setPicked((xs) => {
    const next = xs.includes(label) ? xs.filter((item) => item !== label) : [...xs, label];
    return profile.labels.filter((item) => next.includes(item));
  });
  const halt = () => { stop.current = true; void bridge.recordStop(projectId); };
  const run = async () => {
    stop.current = false;
    setRunning(true);
    try {
      await enrollSequence({ labels: picked, profile, projectId, bridge, st, count, seconds, split, donning, strap, session: `${hand === 'left' ? '左手' : '右手'} · ${placement}`, stopped: () => stop.current, setNote, onError, onTrained });
    } finally {
      setRunning(false);
    }
  };
  const blocked = running || !!st?.busy || !!st?.rig.replay || !!st?.wl8?.replay;
  return <section className="emg8-card">
    <header><h3>录完就识别</h3><small>{note || '勾选的动作按顺序录；整组都勾上时录完训练并打开识别'}</small></header>
    <div className="emg8-enroll-picks">{profile.labels.map((label) => <label key={label}><input type="checkbox" checked={picked.includes(label)} disabled={running} onChange={() => toggle(label)} />{LABEL_CN[label] ?? label}</label>)}</div>
    <div className="emg8-row">
      <label>单次时长 <select aria-label="单次时长" value={seconds} disabled={running} onChange={(e) => setSeconds(Number(e.target.value))}>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} 秒</option>)}</select></label>
      <button className="emg8-primary" disabled={!connected || blocked || !picked.length} title={grayTitle(!connected && '还没连上这条腕带', running && '正在录', !!st?.busy && !running && '采集服务正忙', !!(st?.rig.replay || st?.wl8?.replay) && '正在回放，不能新录', !picked.length && '先勾选要录的动作')} onClick={() => void run()}>{running ? note || '进行中' : `按顺序各录 ${count} 条`}</button>
      {running && <button onClick={halt}>停下</button>}
    </div>
    <p className="emg8-fine">单类按钮仍是每条 2 秒。这里的时长只作用于这一条短路径。训练集录完且每类够数才会训练；验证集只录不训练。</p>
  </section>;
}

/** 按顺序把 labels 各录 count 条，录全整组且是训练集就训练，训练完回调 onTrained。经典 5 步和「录完就识别」共用。 */
export async function enrollSequence({ labels, profile, projectId, bridge, st, count, seconds, split, donning, strap = null, session, stopped, setNote, onError, onTrained, plan }: {
  labels: string[]; profile: Profile; projectId: string; bridge: Emg8Bridge; st: ServiceState | null; count: number; seconds: number; split: 'train' | 'rewear';
  donning: number; strap?: number | null; session: string; stopped: () => boolean; setNote: (note: string) => void; onError: (message: string) => void;
  onTrained?: (runId: string, opts?: { armMouse?: boolean }) => void;
  plan?: (label: string) => { count: number; seconds: number; countdown: number } | undefined;   // 某类单独的次数 / 时长 / 倒数（经典组的随意动手连续录）
}) {
  if (!labels.length) { onError('先勾选要录的动作'); return; }
  if (st?.rig.replay || st?.wl8?.replay) { onError('回放不能录训练数据'); return; }
  for (const label of labels) {
    if (stopped()) return;
    setNote(`正在录 ${LABEL_CN[label] ?? label}`);
    const p = plan?.(label) ?? { count, seconds, countdown: 3 };
    const recorded = await bridge.record(projectId, { label, count: p.count, set: split, donning, seconds: p.seconds, countdown: p.countdown, session, strap_hole: strap ?? undefined });
    if (!recorded.ok) { onError(recorded.message); return; }
    const started = Date.now();
    const deadline = started + p.count * (p.countdown + p.seconds + 8) * 1000 + 5000;
    let sawBusy = false;
    while (Date.now() < deadline) {
      if (stopped()) return;
      const state = await bridge.state();
      if (!state.ok) { onError(state.message); return; }
      if (state.value.busy) sawBusy = true;
      else if (sawBusy || Date.now() - started > 800) break;
      await sleep(250);
    }
    if (Date.now() >= deadline) { onError(`${LABEL_CN[label] ?? label} 这一批超时`); return; }
  }
  if (stopped() || split !== 'train') { setNote(split === 'train' ? '已停下' : '验证集已按顺序录完'); return; }
  // 识别页要整组模型（概率里的类别要和整组一致），只勾了一部分就只录不训，免得跳过去一直「等数据」
  if (labels.length < profile.labels.length) { setNote(`已录完勾选的 ${labels.length} 类；识别要整组模型，勾全 ${profile.labels.length} 类再训练`); return; }
  const fresh = await bridge.state();
  if (!fresh.ok) { onError(fresh.message); return; }
  const why = trainingBlock(fresh.value, profile, projectId);
  if (why) { onError(why); return; }
  setNote('正在训练');
  const trained = await bridge.train(projectId, { labels: profile.labels });
  if (!trained.ok) { onError(trained.message); return; }
  const trainDeadline = Date.now() + 180000;
  while (Date.now() < trainDeadline) {
    const state = await bridge.state();
    if (!state.ok) { onError(state.message); return; }
    const job = state.value.wl8?.train;
    if (job?.error) { onError(job.error); return; }
    if (!job?.running && job?.run_id) { setNote('训练完成'); onTrained?.(job.run_id); return; }
    await sleep(400);
  }
  onError('训练超时');
}
