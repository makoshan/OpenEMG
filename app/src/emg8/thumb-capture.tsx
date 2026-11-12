'use client';
import { useRef, useState } from 'react';
import { TakeDeck, useAcceptBead, Wells, zeroStopped } from './instrument';
import type { CaptureProps } from './capture';
import { StrapField } from './capture';
import type { Conditions, Hand } from './contract';
import { linkLine, zeroNote } from './link';
import { ThumbGuide, type GuideMode } from './thumb-guide';
import { grayTitle } from './gray-title';
import { EnrollRun } from './enroll-run';

export function ThumbCapture({ profile, projectId, bridge, st, ab, hand, donning, setDonning, placement, setPlacement, strap, setStrap, setHand, onError, envelope, onTrained }: CaptureProps) {
  const [selected, setSelected] = useState('thumb_up');
  const [split, setSplit] = useState<'train' | 'rewear'>('train');
  const [count, setCount] = useState(5);
  const [preview, setPreview] = useState(true);
  const [pending, setPending] = useState(false);
  const [cond, setCond] = useState<Conditions | null>(null);
  const [checking, setChecking] = useState(false);
  const connected = st?.project?.id === projectId && st.rig.kind === 'wl8' && !!st.rig.port && st.rig.streaming && profile.labels.every((l) => st.tiers.includes(l));
  const busy = !!st?.busy || !!ab?.active || pending || checking;
  const gp = st?.progress;
  const recording = !!st?.busy && !!gp?.label && profile.labels.includes(gp.label);
  const label = recording ? gp!.label! : selected;
  const gesture = profile.gestures![label];
  const mode: GuideMode = recording ? gp?.phase === 'NOW' ? 'record' : 'prepare' : pending ? 'prepare' : preview ? 'preview' : 'paused';
  const target = split === 'train' ? profile.minTrain : profile.minRewear;
  const counts = st?.project?.id === projectId ? st.counts[split]?.wl8 ?? {} : {};
  const total = profile.labels.reduce((sum, l) => sum + (counts[l] ?? 0), 0);
  const deck = useRef<HTMLDivElement>(null);
  useAcceptBead(counts, (l) => profile.gestures?.[l]?.color ?? '#163F35', deck, recording ? label : null);
  const zero = zeroStopped(st);                                    // 服务端 0 帧停下：从页底灰字提到台面红框
  const stop = async () => { const r = await bridge.recordStop(projectId); if (!r.ok) onError(r.message); };
  const callRecord = async () => {
    if (!connected || busy || st?.rig.replay || st?.wl8?.replay) return;
    setPending(true);
    try {
      const r = await bridge.record(projectId, { label: selected, count, set: split, donning, session: `${hand === 'left' ? '左手' : '右手'} · ${placement}`, countdown: 3, strap_hole: strap ?? undefined });
      if (!r.ok) onError(r.message);
    } finally { setPending(false); }
  };
  const conditions = async () => {
    setChecking(true);
    try { const r = await bridge.ab(projectId, { action: 'conditions' }); if (r.ok) setCond(r.value as Conditions); else onError(r.message); }
    finally { setChecking(false); }
  };
  return <div className="emg8-thumb-capture">
    <div className="emg8-thumb-phases"><span className={split === 'train' ? 'active' : ''}>1　采集训练集</span><span>2　训练与试用</span><span className={split === 'rewear' ? 'active' : ''}>3　重戴验证（可稍后）</span></div>
    <div className="emg8-thumb-workgrid">
      <section className="emg8-card emg8-thumb-action">
        <header><h3>动作示范</h3><div className="emg8-thumb-session"><label>佩戴手 <select aria-label="佩戴手" value={hand} disabled={busy} onChange={(e) => setHand(e.target.value as Hand)}><option value="left">左手</option><option value="right">右手</option></select></label><small>第 {donning} 次佩戴 · {split === 'train' ? '训练集' : '重戴验证集'}</small></div></header>
        <div className="ins-take-row">
        <ThumbGuide key={`${label}:${hand}`} label={label} name={gesture.name} icon={gesture.icon} cue={gesture.cue} hand={hand} mode={mode} takeKey={`${gp?.take ?? ''}:${gp?.phase ?? ''}`} onPreview={() => setPreview(!preview)} />
          <TakeDeck deckRef={deck} phase={gp?.phase} take={gp?.take} count={gp?.count} recording={recording} zero={zero} envelope={envelope} />
        </div>
        <div className={`emg8-thumb-cue ${recording && gp?.phase === 'NOW' ? 'go' : ''}`} role="status"><div><strong>{recording ? gp?.phase === 'NOW' ? label === 'thumb_rest' ? '保持放松' : '做！滑一次' : gp?.phase === '准备录制' ? '等待设备，先不要滑' : '准备，先不要滑' : pending ? '正在开始录制…' : '先看动作，再开始录制'}</strong><small>{recording ? `第 ${gp?.take} / ${gp?.count} 条 · ${split === 'train' ? '训练集' : '重戴验证集'}` : '上滑朝指尖，下滑朝指根；左右按你的视角。'}</small></div></div>
        {zero && <div className="ins-alert ins-zero" role="alert"><b>没收到数据 · 0 帧</b><span>这一批已停下，前面收下的保留。{zeroNote(st?.rig.link)}</span></div>}
        <footer className="emg8-thumb-actionbar"><label>数据集 <select aria-label="数据集" value={split} disabled={busy} onChange={(e) => setSplit(e.target.value as 'train' | 'rewear')}><option value="train">训练集</option><option value="rewear">重戴验证集</option></select></label><label>每批 <select aria-label="每批" value={count} disabled={busy} onChange={(e) => setCount(Number(e.target.value))}>{[5, 3, 10].map((n) => <option key={n} value={n}>{n} 条</option>)}</select></label><button className="emg8-primary" disabled={!connected || busy || !!st?.rig.replay || !!st?.wl8?.replay} title={grayTitle(!connected && '还没连上这条腕带', (!!st?.rig.replay || !!st?.wl8?.replay) && '正在回放，不能新录')} onClick={callRecord}>{recording ? `录制中 ${gp?.take}/${gp?.count}` : pending ? '正在开始…' : `开始${gesture.name.replace('拇指', '')}录制 · ${count} 条`}</button>{recording && <button onClick={stop}>停下这一批</button>}</footer>
        {split === 'rewear' && <p className="emg8-fine emg8-thumb-validation">请实际摘下重戴，再在下方更新佩戴编号。相同编号的数据会保留，但不能作为重戴验证；已有训练数据可先生成基础模型。</p>}
        {(!connected || st?.rig.link === 'no-receiver' || st?.rig.link === 'waiting-band' || st?.rig.link === 'dropped') && <p className="emg8-fine emg8-thumb-validation">{linkLine(st?.rig.link, st?.rig.link_detail)}</p>}
      </section>
      <aside className="emg8-card emg8-thumb-gestures"><header><h3>选择动作</h3><small>每类目标 {target} 条</small></header><div role="group" aria-label="选择采集动作">{profile.labels.map((l) => { const g = profile.gestures![l]; return <button key={l} data-label={l} className="emg8-thumb-gesture" aria-pressed={label === l} disabled={busy} onClick={() => setSelected(l)}><span>{g.icon}</span><span>{g.name.replace('拇指', '')}<small>{label === l ? '当前动作' : '点击看示范'}</small></span><Wells n={counts[l] ?? 0} target={target} color={g.color} /></button>; })}</div><footer><small>{split === 'train' ? '训练集' : '重戴验证集'}</small><b>{total} 条</b></footer></aside>
    </div>
    <details className="emg8-thumb-details"><summary>佩戴与信号检查 · {checking ? '测量中…' : cond ? cond.warnings.length ? '需要检查' : '已测量' : '尚未测量'}</summary><div className="emg8-thumb-details-body">
      <div className="emg8-form"><label>第几次佩戴<input type="number" min={1} max={20} value={donning} disabled={busy} onChange={(e) => setDonning(Math.max(1, Math.min(20, Number(e.target.value) || 1)))} /></label><label>佩戴位置 / 条件<input value={placement} disabled={busy} onChange={(e) => setPlacement(e.target.value)} /></label><StrapField strap={strap} setStrap={setStrap} disabled={busy} /></div>
      <button disabled={busy || donning >= 20} title={grayTitle(donning >= 20 && '佩戴次数已经到 20')} onClick={() => { setDonning(donning + 1); setSplit('rewear'); }}>已实际摘下重戴 → 第 {Math.min(20, donning + 1)} 次验证</button>
      <button disabled={!connected || busy || !!st?.rig.replay || !!st?.wl8?.replay} title={grayTitle(!connected && '还没连上这条腕带', (!!st?.rig.replay || !!st?.wl8?.replay) && '正在回放，不能测量')} onClick={conditions}>{checking ? '测量中…' : '检查信号条件 · 5 秒'}</button>
      {cond && <div className="emg8-checks"><div><small>工频 50 Hz</small><b>{cond.mains_mv == null ? '—' : `${cond.mains_mv} mV`}</b></div><div><small>放松底噪</small><b>{cond.noise_uv == null ? '—' : `${cond.noise_uv} µV`}</b></div><div><small>IMU</small><b>{cond.acc_g == null ? '—' : `|a| ${cond.acc_g}`}</b></div><div><small>供电</small><b>{cond.power === 'battery' ? '电池' : cond.power === 'ac' ? '充电器' : '—'}</b></div></div>}
      {cond?.warnings.map((w) => <p key={w} className="emg8-warn">{w}</p>)}
      <p className="emg8-fine">连接正常表示收到数据，仍需检查信号与实际动作。每条 3 秒准备、2 秒录制；训练每类至少 {profile.minTrain} 条，重戴验证每类至少 {profile.minRewear} 条。</p>
    </div></details>
    <EnrollRun profile={profile} projectId={projectId} bridge={bridge} st={st} hand={hand} donning={donning} placement={placement} strap={strap} count={count} split={split} connected={connected} onError={onError} onTrained={onTrained} />
    <div className="emg8-thumb-foot"><small>本工程保存 · 本机训练</small><small>拇指鼠标控制尚未接入</small></div>
    {!!st?.log.length && <p className="emg8-fine" role="status">{st.log.at(-1)}</p>}
  </div>;
}
