'use client';
import { SpecialChecks } from './special-checks';
// 训练剧场：学习曲线逐点生长 → 判别投影散点按录制顺序落点、聚成簇 → 混淆矩阵按行淡入；结果卡在最上，载入 0.6 秒就翻面、数字滚动。
// 所有数字都来自服务端 run.json（firmware/wl8_train.py），前端不重算；跨佩戴分（重戴目录或留一次佩戴）才算数，同次佩戴标"偏乐观"。
import { animate, motion, useMotionValue, useTransform } from 'motion/react';
import { useEffect, useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Conditions, Emg8Bridge, FeatureMode, Hand, Run, RunSummary, ServiceState } from './contract';
import { CLASS_COLORS, LABEL_CN, pct } from './contract';
import { Confetti } from './effects';
import { ElectrodeRing } from './ring';
import { Odometer } from './instrument';
import { matchesProfile, trainingBlock, validationHint, type Profile } from './profiles';
import { grayTitle } from './gray-title';

/** 结果卡大数字：只用跨佩戴分（重戴目录或留一次佩戴）；都没有就是「—」，不拿同次佩戴分顶替 */
export const revealScore = (run: Pick<Run, 'rewear'>) => pct(run.rewear);
/** 跨佩戴分的叫法：没有重戴目录时服务端按佩戴编号留一次佩戴估分，不叫「重戴」；旧 run 没这个字段，只可能来自重戴目录 */
export const rewearName = (source?: Run['rewear_source']) => (source === '留一次佩戴' ? '留一次佩戴' : '重戴');

/** 8 路都是有限数才算测过。测到的 0 留下，没测过是 null，页面写成「—」。 */
export function readoutMedian(xs: number[] | null | undefined): number | null {
  if (!xs || xs.length !== 8 || xs.some((v) => typeof v !== 'number' || !Number.isFinite(v))) return null;
  const s = [...xs].sort((a, b) => a - b);
  return (s[3] + s[4]) / 2;
}
export function readoutLabeled(v: number | null, digits: number, unit: string): string {
  if (v == null || !Number.isFinite(v)) return '—';
  return `${v.toFixed(digits)} ${unit}`;
}
export function channelLine(xs: number[] | null | undefined): string {
  if (readoutMedian(xs) == null || !xs) return '还没测';
  return `8 路 ${xs.map((v) => String(Math.round(v))).join(' ')}`;
}

function Ticker({ value, delay = 0 }: { value: number; delay?: number }) {
  const mv = useMotionValue(0); const text = useTransform(mv, (v) => `${Math.round(v)}%`);
  useEffect(() => { const c = animate(mv, value * 100, { duration: 1.4, delay, ease: [0.16, 1, 0.3, 1] }); return () => c.stop(); }, [mv, value, delay]);
  return <motion.span>{text}</motion.span>;
}

function Scatter({ run, reveal }: { run: Run; reveal: number }) {
  const pts = [...run.projection.train.map((p) => ({ ...p, kind: 'train' as const })), ...run.projection.rewear.map((p) => ({ ...p, kind: 'rewear' as const }))];
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const sx = (x: number) => 20 + ((x - x0) / (x1 - x0 || 1)) * 360, sy = (y: number) => 280 - ((y - y0) / (y1 - y0 || 1)) * 240;   // 顶上留 40px：簇名画在圆心上方 20px，原来 260 会把最上面的类名裁掉一半
  const shown = Math.round(reveal * pts.length);
  return <svg viewBox="0 0 400 300" className="emg8-scatter" aria-label="判别投影散点">
    {pts.slice(0, shown).map((p, i) => <motion.circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={p.kind === 'rewear' ? 5 : 4}
      fill={p.kind === 'rewear' ? 'none' : CLASS_COLORS[p.label] ?? '#888'} stroke={CLASS_COLORS[p.label] ?? '#888'} strokeWidth={p.kind === 'rewear' ? 2 : 0}
      initial={{ opacity: 0, scale: 0 }} animate={{ opacity: .9, scale: 1 }} transition={{ type: 'spring', stiffness: 260, damping: 18 }} />)}
    {reveal >= 1 && run.projection.centroids.map((c) => <g key={c.label}>
      <motion.circle cx={sx(c.x)} cy={sy(c.y)} r={16} fill="none" stroke={CLASS_COLORS[c.label]} strokeWidth={2} pathLength={1} initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 1 }} transition={{ duration: .7, ease: [0.4, 0, 0.2, 1] }} />
      <text x={sx(c.x)} y={sy(c.y) - 20} textAnchor={sx(c.x) < 100 ? 'start' : sx(c.x) > 300 ? 'end' : 'middle'} className="emg8-scatter-l">{LABEL_CN[c.label] ?? c.label}</text></g>)}
  </svg>;
}

export function Train({ profile, projectId, bridge, st, hand, onError, onLive }: { profile: Profile; projectId: string; bridge: Emg8Bridge; st: ServiceState | null; hand: Hand; onError: (m: string) => void; onLive: (runId: string) => void }) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [reveal, setReveal] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [pipeMode, setPipeMode] = useState<FeatureMode>('bands5');
  const [gateUv, setGateUv] = useState(0);
  const [pipeNote, setPipeNote] = useState('');
  const [cond, setCond] = useState<Conditions | null>(null);
  const [checking, setChecking] = useState(false);
  const job = st?.wl8?.train;
  const running = !!job?.running;
  const loadRuns = async (pick?: string) => {
    const r = await bridge.runs(); if (!r.ok) return onError(r.message);
    const matching = r.value.filter((r) => matchesProfile(r, profile));
    setRuns(matching); const id = matching.find((r) => r.id === pick)?.id ?? matching[0]?.id; if (!id) { setRun(null); return; }
    const one = await bridge.run(id); if (one.ok) { setRun(one.value); setReveal(0); setFlipped(false); }
  };
  // 采集服务起好并绑定工程后再读模型；恢复训练页时不能只请求一次旧端口。
  useEffect(() => { if (st?.project?.id === projectId) void loadRuns(); }, [st?.project?.id, projectId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (job?.run_id && !running && job.run_id !== run?.id) void loadRuns(job.run_id); }, [job?.run_id, running]); // eslint-disable-line react-hooks/exhaustive-deps
  // 播放：散点逐个落下；结果卡在最上面，不等散点播完，0.6 秒后就翻
  useEffect(() => {
    if (!run) return;                                        // 归零在 loadRuns 里做（事件里设状态，不在副作用里同步设）
    const c = animate(0, 1, { duration: 3.2, ease: 'easeInOut', onUpdate: setReveal });
    const t = window.setTimeout(() => setFlipped(true), 600);
    return () => { c.stop(); window.clearTimeout(t); };
  }, [run]);
  const live = (job?.events ?? []).filter((e) => e.stage === 'curve') as { n: number; mean: number; std: number }[];
  const curve = running ? live : run?.learning_curve.points ?? [];
  const counts = useMemo(() => {
    const t = st?.counts?.train?.wl8 ?? {}, r = st?.counts?.rewear?.wl8 ?? {};
    return profile.labels.map((l) => ({ l, t: t[l] ?? 0, r: r[l] ?? 0 }));
  }, [st, profile]);
  const start = async () => { const r = await bridge.train(projectId, { labels: profile.labels }); if (!r.ok) onError(r.message); };
  const measure = async () => {
    setChecking(true);
    const r = await bridge.ab(projectId, { action: 'conditions' });
    setChecking(false);
    if (r.ok) setCond(r.value as Conditions); else onError(r.message);
  };
  const restLabel = profile.labels.find((l) => l.includes('rest')) ?? 'rest';
  const pipe = async (op: 'gestureGate' | 'gestureFewshot' | 'gestureDump') => {
    if (op === 'gestureGate') {
      const r = await bridge.studio(projectId, op, { minRmsUv: gateUv, restLabel });
      if (!r.ok) return onError(r.message);
      onError('');
      setPipeNote(r.value.min_rms_uv > 0 ? `能量门 ${r.value.min_rms_uv} µV，低于此值改判 ${r.value.rest_label}` : '能量门关闭');
      return;
    }
    if (op === 'gestureFewshot') {
      const r = await bridge.studio(projectId, op, { featureMode: pipeMode, k: 1, labels: profile.labels });
      if (!r.ok) return onError(r.message);
      onError('');
      setPipeNote(`少样本 ${r.value.id}`);
      return;
    }
    const r = await bridge.studio(projectId, op);
    if (!r.ok) return onError(r.message);
    onError('');
    setPipeNote(`已导出 ${r.value.name} · ${r.value.samples} 点`);
  };
  const chance = run ? 1 / run.labels.length : 1 / profile.labels.length;
  const blocked = trainingBlock(st, profile, projectId);
  const canMeasure = st?.project?.id === projectId && !!st.rig.streaming && !st.busy && !st.rig.replay && !st.wl8?.replay && !running;

  return <div className="emg8-train">{profile.protocol && <p className="emg8-warn">基础分类采用 200 ms 短窗。下方分数只衡量接触状态，组合动作需在“识别”页实际试用；运动方向需六类各 3 条校准样本。</p>}
    <section className="emg8-card emg8-train-head">
      <div><h3>{profile.name} · 个人训练</h3><small>当前手势组训练数据齐全即可生成基础模型。重戴验证需实际摘下重戴，使用与训练集不同的佩戴编号。</small></div>
      <div className="emg8-counts">{counts.map(({ l, t, r }) => <span key={l}><b style={{ color: CLASS_COLORS[l] }}>{LABEL_CN[l]}</b> 训练 {t} · 重戴 {r}</span>)}</div>
      <div className="emg8-row tight">
        <select value={run?.id ?? ''} onChange={(e) => void loadRuns(e.target.value)} disabled={running}>
          {runs.map((r) => <option key={r.id} value={r.id}>{r.id} · {rewearName(r.rewear_source)} {pct(r.rewear)}</option>)}</select>
        <button className="emg8-primary" onClick={start} disabled={running || !!st?.busy || !!blocked} title={grayTitle(blocked)}>{running ? '训练中…' : '开始训练'}</button>
      </div>
      <div className="emg8-row tight">
        <select value={pipeMode} aria-label="特征" onChange={(e) => setPipeMode(e.target.value as FeatureMode)}>
          <option value="bands5">5 频段（默认）</option><option value="hudgins">时域 48 维</option><option value="combined">组合 88 维</option></select>
        <input type="number" min={0} max={5000} value={gateUv} aria-label="能量门微伏" onChange={(e) => setGateUv(Number(e.target.value))} />
        <button onClick={() => void pipe('gestureGate')}>设置能量门</button>
        <button onClick={() => void pipe('gestureFewshot')}>少样本校准</button>
        <button onClick={() => void pipe('gestureDump')}>导出 30 秒</button>
      </div>
      {pipeNote && <p className="emg8-fine">{pipeNote}。上面的「开始训练」仍用原来的模型。0 µV 不改识别。</p>}
    </section>

    <section className="emg8-card">
      <header><h3>训练前看一眼信号</h3><button onClick={() => void measure()} disabled={!canMeasure || checking} title={grayTitle(st?.project?.id !== projectId && '先连上这个工程的采集', !st?.rig.streaming && '腕带还没在出数据', (!!st?.rig.replay || !!st?.wl8?.replay) && '正在回放，不能测')}>{checking ? '测量中… 5 秒' : '测一下（5 秒）'}</button></header>
      <div className="emg8-checks" aria-label="训练前信号">
        <div><small>基线</small><b>{readoutLabeled(readoutMedian(cond?.baseline_uv), 1, 'µV')}</b><small>{channelLine(cond?.baseline_uv)}</small></div>
        <div><small>时域噪声 Vpp</small><b>{readoutLabeled(readoutMedian(cond?.vpp_uv), 1, 'µV')}</b><small>{channelLine(cond?.vpp_uv)}</small></div>
        <div><small>频域噪声</small><b>{readoutLabeled(readoutMedian(cond?.spectral_db), 1, 'dB')}</b><small>{channelLine(cond?.spectral_db)}</small></div>
      </div>
      <p className="emg8-fine">手放松时测。基线是这 5 秒的中位；时域噪声 Vpp 是 20 Hz 高通后的峰峰值（最大减最小）；频域是 20–450 Hz、去掉 50 Hz 倍频之后，相对 1 µV 的分贝。这不是唯理软件里的柱子。没测过显示「—」，不挡开始训练。</p>
    </section>

    {blocked && <p className="emg8-fine" role="status">{blocked}</p>}
    {!blocked && !running && !run && <p className="emg8-fine" role="status">{validationHint(st, profile)}</p>}
    {run && !running && run.rewear == null && <p className="emg8-warn" role="status">{run.note ?? '基础模型已生成，未完成重戴验证。'}</p>}
    {job?.error && <p className="emg8-warn">训练失败：{job.error}</p>}
    {running && <section className="emg8-card"><ul className="emg8-events">{(job?.events ?? []).slice(-6).map((e, i) => <li key={i}>
      {e.stage === 'data' ? e.message : e.stage === 'same_wear' ? `同次佩戴留一法：${pct(e.value)}` : e.stage === 'rewear' ? `${rewearName(e.source)}测试：${pct(e.value)}（打乱对照 ${pct(e.shuffled)}）` : e.stage === 'curve' ? `学习曲线：每类 ${e.n} 条 → ${pct(e.mean)}` : '完成'}</li>)}</ul></section>}

    {/* 结果卡放在图表前面：先看跨佩戴认对率，再看曲线和矩阵（D5 T3） */}
    {run && <div className="emg8-reveal-wrap">
      {!profile.gestures && <Confetti fire={flipped && (run.rewear ?? 0) >= 0.8 ? 1 : 0} />}{/* 只有跨佩戴分（重戴或留一次佩戴，都是没见过的那次佩戴）过 80% 才放礼花，不给差结果撒花 */}
      <motion.div className="emg8-reveal" animate={{ rotateY: flipped ? 180 : 0 }} transition={{ duration: .9, ease: [0.16, 1, 0.3, 1] }}>
        <div className="emg8-reveal-face front"><b>{run.rewear_source === '留一次佩戴' ? '换一次佩戴还认得出吗？' : '摘下重戴后还认得出吗？'}</b><span>翻开看结果</span></div>
        <div className="emg8-reveal-face back emg8-beam">
          <div className="big">{profile.gestures ? <Odometer text={flipped ? revealScore(run) : '00%'} /> : flipped && run.rewear != null ? <Ticker value={run.rewear} /> : pct(run.rewear)}</div>
          <div className="sub">{run.rewear == null ? '基础模型 · 重戴未验证' : run.rewear_source === '留一次佩戴' ? '留一次佩戴估计' : '摘下重戴'} · {run.labels.map((l) => LABEL_CN[l]).join(' / ')}</div>
          <div className="emg8-compare">
            <span><b>{pct(run.same_wear)}</b>同次佩戴（偏乐观）</span>
            <span><b>{pct(run.shuffled)}</b>打乱标签对照</span>
            <span><b>{pct(run.per_channel ? Math.max(...run.per_channel) : null)}</b>只用最好的一路</span>
          </div>
          <button className="emg8-primary" onClick={() => onLive(run.id)}>用这个模型实时识别 →</button>
        </div>
      </motion.div>
      <p className="emg8-fine">{run.excluded.files.length ? `训练前排除 ${run.excluded.files.length} 条：${run.excluded.rule}。` : ''}{run.note ?? ''} 训练于 {run.created}。</p>
    </div>}
    {profile.protocol && run && <SpecialChecks run={run} profile={profile} />}
    <div className="emg8-train-grid">
      <section className="emg8-card">
        <header><h3>学习曲线</h3><small>{run?.learning_curve.tested_on ?? ''} · 每点 10 次随机抽样</small></header>
        <div style={{ height: 240 }}><ResponsiveContainer>
          <LineChart data={curve.map((p) => ({ n: p.n, acc: Math.round(p.mean * 100), lo: Math.round((p.mean - p.std) * 100) }))} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--emg8-grid)" />
            <XAxis dataKey="n" tick={{ fontSize: 11 }} label={{ value: '每类训练条数', position: 'insideBottom', offset: -2, fontSize: 11 }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
            <ReferenceLine y={Math.round(chance * 100)} stroke="var(--emg8-dim)" strokeDasharray="4 4" label={{ value: '瞎猜', fontSize: 10, position: 'right' }} />
            <Tooltip formatter={(v) => `${String(v)}%`} />
            <Line type="monotone" dataKey="acc" stroke="var(--emg8-accent)" strokeWidth={3} dot={{ r: 4 }} isAnimationActive animationDuration={900} />
          </LineChart></ResponsiveContainer></div>
      </section>
      <section className="emg8-card">
        <header><h3>特征空间</h3><small>判别投影 · 实心 = 训练{run?.projection.rewear.length ? '，空心 = 重戴' : ''}</small></header>
        {run ? <Scatter run={run} reveal={reveal} /> : <p className="emg8-fine">还没有训练记录。</p>}
      </section>
      <section className="emg8-card">
        <header><h3>混淆矩阵（{rewearName(run?.rewear_source)}）</h3><small>行 = 真实，列 = 判定</small></header>
        {run?.confusion ? <table className="emg8-confusion"><thead><tr><th aria-label="真实（行）· 判定（列）">真\判</th>{run.confusion.rows.map((c) => <th key={c}>{LABEL_CN[c] ?? c}</th>)}</tr></thead>
          <tbody>{run.confusion.matrix.map((row, i) => { const n = row.reduce((a, b) => a + b, 0) || 1; return <motion.tr key={i} initial={{ opacity: 0, x: -12 }} animate={{ opacity: reveal >= 1 ? 1 : 0, x: 0 }} transition={{ delay: i * .25 }}>
            <th>{LABEL_CN[run.confusion!.rows[i]]}</th>{row.map((v, j) => <td key={j} style={{ background: i === j ? `rgba(34,197,94,${v / n})` : `rgba(239,68,68,${(v / n) * .8})` }}>{v}</td>)}</motion.tr>; })}</tbody></table>
          : <p className="emg8-fine">重戴未验证，暂不计算混淆矩阵。</p>}
      </section>
      <section className="emg8-card">
        <header><h3>电极贡献</h3><small>每一路单独用时的{rewearName(run?.rewear_source)}准确率</small></header>
        <ElectrodeRing values={run?.per_channel ?? null} max={1} hand={hand} format={(v) => `${Math.round(v * 100)}`} label="单路准确率 %" />
      </section>
    </div>
  </div>;
}
