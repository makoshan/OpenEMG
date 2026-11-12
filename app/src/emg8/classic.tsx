'use client';
// 经典 5 步：唯理上位机 EMGband_flex_ctrl_2k.exe 的流程搬进引导模式（稿 docs/design/classic-5step，方向 A，2026-10-15 Mako 定）。
// ① 连上页多一张串口卡（手环数据串口 / 控制串口 / 数据导出）；③ 录动作页换成动作 1–16 卡片 + 次数时长；⑤ 识别页多控制串口输出。
import { useEffect, useRef, useState } from 'react';
import type { CtrlState, Emg8Bridge, ServiceState } from './contract';
import { LABEL_CN } from './contract';
import type { CaptureProps } from './capture';
import { StrapField } from './capture';
import { enrollSequence } from './enroll-run';
import { grayTitle } from './gray-title';
import { CLASSIC_MOVE, CLASSIC_REST, classicLabel, type ClassicPick, type Profile } from './profiles';

const COUNTS = [3, 5, 7, 9];
const SECONDS = [2, 3, 4];
const MOVE_TAKE_S = 3;   // 随意动手按 3 秒一条、不倒数连续录：1 分钟 = 20 条（IPC 每批最多 50 条，2 分钟 40 条）
type Spec = { count: number; seconds: number; countdown: number };

/** 改过的名字写进 LABEL_CN：训练页、识别页、录制提示都按 LABEL_CN 显示。ponytail: 全局表就地改，经典组以外的标签不碰 */
export function applyClassicNames(base: Profile, pick: ClassicPick) {
  for (const [l, g] of Object.entries(base.gestures ?? {})) LABEL_CN[l] = pick.names[l]?.trim() || g.name;
}

export function ClassicPorts({ bridge, projectId, st, labels, runId, onReconnect, onError }: {
  bridge: Emg8Bridge; projectId: string; st: ServiceState | null; labels: string[]; runId: string | null; onReconnect: () => void; onError: (m: string) => void;
}) {
  const [ports, setPorts] = useState<string[]>([]);
  const [dataPort, setDataPort] = useState('');
  const [baud, setBaud] = useState(115200);
  const [note, setNote] = useState('');
  const [dataDir, setDataDir] = useState('');
  const ctrl: CtrlState | undefined = st?.wl8?.ctrl;
  const current = st?.rig.port ?? '';
  const scan = async () => {
    const r = await bridge.ports?.();
    if (!r) { onError('这个版本不能列串口'); return; }
    if (r.ok) { setPorts(r.value.list); setDataPort(r.value.selected); } else onError(r.message);
  };
  useEffect(() => { void scan(); void bridge.openData?.().then((r) => { if (r?.ok) setDataDir(r.value); }); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const pickData = async (p: string) => {
    setDataPort(p);
    const r = await bridge.dataPort?.(p);
    if (r && !r.ok) { onError(r.message); return; }
    if (ctrl?.open) setNote('换了数据串口，采集服务已重起：控制串口要重新选一次');
    onReconnect();
  };
  const call = async (a: Parameters<NonNullable<Emg8Bridge['ctrl']>>[1]) => {
    const r = await bridge.ctrl?.(projectId, a);
    if (r && !r.ok) onError(r.message);
    return r;
  };
  const pickCtrl = (p: string) => void (p ? call({ action: 'open', port: p, baud }) : call({ action: 'close' }));
  const exportAll = async () => {
    const r = await bridge.exportClassic?.({ labels, runId });
    if (!r) return;
    if (!r.ok) { onError(r.message); return; }
    if (!r.value.canceled) setNote(`已导出 ${r.value.files} 项到 ${r.value.path}`);
  };
  const others = ports.filter((p) => p !== current);
  return <section className="emg8-card emg8-classic-ports">
    <header><h3>串口与数据</h3><small>唯理流程 step 1–2</small></header>
    <div className="emg8-classic-cols">
      <div>
        <b>手环数据串口</b>
        <div className="emg8-row tight">
          <select aria-label="手环数据串口" value={dataPort} disabled={!!st?.busy || !!st?.wl8?.live} title={grayTitle(!!st?.busy && '正在录，换口会打断这一条', !!st?.wl8?.live && '先停下识别再换口')} onChange={(e) => void pickData(e.target.value)}>
            <option value="">自动找（CP210x / CH343）</option>
            {ports.map((p) => <option key={p} value={p}>{p}</option>)}
            {dataPort && !ports.includes(dataPort) && <option value={dataPort}>{dataPort}（已拔出）</option>}
          </select>
          <button onClick={() => void scan()}>检测串口</button>
        </div>
        <p className="emg8-fine">{st?.rig.streaming ? `已打开 ${current} · 921600` : st?.rig.error || '未打开：插好线后点「检测串口」，或在上面手选'}</p>
      </div>
      <div>
        <b>控制串口</b>
        <div className="emg8-row tight">
          <select aria-label="控制串口" value={ctrl?.open || ctrl?.error ? ctrl.port : ''} onChange={(e) => pickCtrl(e.target.value)}>
            <option value="">不使用</option>
            {others.map((p) => <option key={p} value={p}>{p}</option>)}
            {ctrl?.port && !others.includes(ctrl.port) && <option value={ctrl.port}>{ctrl.port}</option>}
          </select>
          <select aria-label="波特率" value={baud} onChange={(e) => { const b = Number(e.target.value); setBaud(b); if (ctrl?.open) void call({ action: 'open', port: ctrl.port, baud: b }); }}>
            <option value={9600}>9600</option><option value={115200}>115200</option>
          </select>
          <button disabled={!ctrl?.open} title={grayTitle(!ctrl?.open && '先选一个控制串口')} onClick={() => void call({ action: 'test' })}>发一条测试</button>
        </div>
        {ctrl?.error ? <p className="emg8-warn">{ctrl.error}。关掉占用它的程序（如串口助手）或插回线，再选一次。</p>
          : <p className="emg8-fine">{ctrl?.open ? `已打开 ${ctrl.port} · ${ctrl.baud} 8N1` : '不使用'} · 认出动作一变就发一行编号，如 <code>3\n</code>；放松和随意动手发 <code>0</code></p>}
      </div>
      <div>
        <b>数据存放</b>
        <div className="emg8-row tight">
          <button onClick={() => void bridge.openData?.(true).then((r) => { if (r && !r.ok) onError(r.message); })}>在访达中打开</button>
          <button onClick={() => void exportAll()}>导出到目录…</button>
        </div>
        {dataDir && <code className="emg8-classic-dir" title={dataDir}>{dataDir}</code>}
        <p className="emg8-fine">{note || '导出：这一组的录音（训练 + 重戴）和最新模型。'}</p>
      </div>
    </div>
  </section>;
}

export function ClassicCapture({ base, pick, setPick, ...props }: CaptureProps & { base: Profile; pick: ClassicPick; setPick: (p: ClassicPick) => void }) {
  const { profile, projectId, bridge, st, hand, donning, placement, strap, setStrap, onError, onTrained } = props;
  const [count, setCount] = useState(5);
  const [seconds, setSeconds] = useState(3);
  const [split, setSplit] = useState<'train' | 'rewear'>('train');
  const [moveMin, setMoveMin] = useState(1);
  const [running, setRunning] = useState(false);
  const [note, setNote] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const stop = useRef(false);
  const connected = st?.project?.id === projectId && st?.rig.kind === 'wl8' && !!st.rig.streaming;
  const gp = st?.progress ?? {};
  const toggle = (n: number) => setPick({ ...pick, picked: pick.picked.includes(n) ? pick.picked.filter((x) => x !== n) : [...pick.picked, n] });
  const rename = (l: string, name: string) => { setEditing(null); setPick({ ...pick, names: { ...pick.names, [l]: name.trim().slice(0, 20) } }); };
  const spec = (l: string): Spec => (l === CLASSIC_MOVE ? { count: (moveMin * 60) / MOVE_TAKE_S, seconds: MOVE_TAKE_S, countdown: 0 } : { count, seconds, countdown: 3 });
  const run = async () => {
    stop.current = false; setRunning(true);
    try {
      await enrollSequence({ labels: profile.labels, profile, projectId, bridge, st, count, seconds, split, donning, strap, session: `${hand === 'left' ? '左手' : '右手'} · ${placement}`, stopped: () => stop.current, setNote, onError, onTrained, plan: spec });
    } finally { setRunning(false); }
  };
  const total = profile.labels.reduce((t, l) => { const p = spec(l); return t + p.count * (p.seconds + p.countdown); }, 0);
  const actions = profile.labels.length - 2;
  const blocked = running || !!st?.busy || !!st?.rig.replay || !!st?.wl8?.replay;
  const card = (l: string, n: number | null) => {
    const on = n == null || pick.picked.includes(n);
    const have = st?.counts?.[split]?.wl8?.[l] ?? 0;
    const rec = !!st?.busy && gp.label === l;
    const fixed = l === CLASSIC_MOVE ? ['必录 · 不触发', '随意动手固定要录：识别成它就是没动作，控制串口发 0'] : ['0 · 必录', '放松固定要录，作为第 0 类'];
    return <div key={l} className={`emg8-classic-act${on ? ' on' : ''}${rec ? ' rec' : ''}${n == null ? ' rest' : ''}`}>
      {editing === l ? <input autoFocus defaultValue={LABEL_CN[l]} aria-label={`给动作${n}改名`} maxLength={20}
        onBlur={(e) => rename(l, e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') rename(l, e.currentTarget.value); if (e.key === 'Escape') setEditing(null); }} />
        : <button aria-pressed={on} disabled={n == null || running} title={n == null ? fixed[1] : '点选；双击改名'}
          onClick={() => n != null && toggle(n)} onDoubleClick={() => n != null && !running && setEditing(l)}>
          <span className="k">{n == null ? fixed[0] : n}</span><b>{LABEL_CN[l]}</b>
          <small>{rec ? `● ${gp.take}/${gp.count} ${gp.phase === 'NOW' ? '做！' : gp.phase ?? ''}` : on ? `${have}/${spec(l).count}` : '—'}</small>
        </button>}
    </div>;
  };
  return <div className="emg8-classic-capture">
    <section className="emg8-card">
      <header><h3>选要录的动作</h3><small>点选；双击改名 · 计数 = 已有/每类要录 · 这次 {actions} 个动作 + 放松 + 随意动手</small></header>
      <div className="emg8-classic-acts">
        {card(CLASSIC_REST, null)}
        {card(CLASSIC_MOVE, null)}
        {Array.from({ length: 16 }, (_, i) => card(classicLabel(i + 1), i + 1))}
      </div>
    </section>
    <section className="emg8-card">
      <header><h3>录入参数</h3></header>
      <div className="emg8-row tight">
        <label>每个动作录 <select aria-label="次数" value={count} disabled={running} onChange={(e) => setCount(Number(e.target.value))}>{COUNTS.map((n) => <option key={n} value={n}>{n} 次</option>)}</select></label>
        <label>每次持续 <select aria-label="时长" value={seconds} disabled={running} onChange={(e) => setSeconds(Number(e.target.value))}>{SECONDS.map((n) => <option key={n} value={n}>{n}.0 s</option>)}</select></label>
        <label>随意动手 <select aria-label="随意动手时长" value={moveMin} disabled={running} onChange={(e) => setMoveMin(Number(e.target.value))}><option value={1}>1 分钟</option><option value={2}>2 分钟</option></select></label>
        <label>用途 <select aria-label="用途" value={split} disabled={running} onChange={(e) => setSplit(e.target.value as 'train' | 'rewear')}><option value="train">训练</option><option value="rewear">重戴验证</option></select></label>
        <StrapField strap={strap} setStrap={setStrap} disabled={running} />
      </div>
      <p className="emg8-fine">放松和 {actions} 个动作各 {count} 次 × {seconds}.0 s，随意动手连续 {moveMin} 分钟（转腕、握拳、拿东西、看手机都行，别做动作 1–16），含倒数约 {Math.ceil(total / 60)} 分钟。{split === 'train' ? '录完自动训练并打开识别。' : '重戴验证要真的摘下再戴，只录不训练。'}</p>
      {st?.busy && gp.label && <ClassicCue gp={gp} spec={spec} labels={profile.labels} />}
      <div className="emg8-row tight">
        <button className="emg8-primary" disabled={!connected || blocked || actions < 1}
          title={grayTitle(!connected && '还没连上手环', running && '正在录', !!st?.busy && !running && '采集服务正忙', !!(st?.rig.replay || st?.wl8?.replay) && '正在回放，不能新录', actions < 1 && '至少选一个动作')}
          onClick={() => void run()}>{running ? note || '进行中' : `确定并开始录（各 ${count} 次 + 随意动手 ${moveMin} 分钟）`}</button>
        {running && <button onClick={() => { stop.current = true; void bridge.recordStop(projectId); }}>停下</button>}
        {note && !running && <span className="emg8-fine" role="status">{note}</span>}
      </div>
    </section>
  </div>;
}

/** 录制中的大字提示：动作名、这一条还剩几秒、整批进度。服务端只报阶段，秒数按收到 NOW 的时刻在页面上倒数。ponytail: 轮询 250 ms，倒数起点最多晚一拍 */
function ClassicCue({ gp, spec, labels }: { gp: ServiceState['progress']; spec: (l: string) => Spec; labels: string[] }) {
  const seconds = spec(gp.label ?? '').seconds;
  const key = `${gp.label}-${gp.take}`;
  const now = gp.phase === 'NOW';
  const [start, setStart] = useState<{ key: string; at: number } | null>(null);
  const [, tick] = useState(0);
  useEffect(() => { if (now) setStart((s) => (s?.key === key ? s : { key, at: Date.now() })); }, [now, key]);
  useEffect(() => { if (!now) return; const h = window.setInterval(() => tick((n) => n + 1), 100); return () => window.clearInterval(h); }, [now]);
  const left = now && start?.key === key ? Math.max(0, seconds - (Date.now() - start.at) / 1000) : seconds;
  const i = labels.indexOf(gp.label ?? '');
  const num = gp.label === CLASSIC_REST ? '0' : gp.label === CLASSIC_MOVE ? '不触发' : /^classic_(\d+)$/.exec(gp.label ?? '')?.[1];   // 别处占着采集服务时 label 不是经典的，就不标编号
  const done = i < 0 ? null : labels.slice(0, i).reduce((n, l) => n + spec(l).count, 0) + (gp.take ?? 0);   // enrollSequence 按 labels 顺序录，随意动手条数不同
  const all = labels.reduce((n, l) => n + spec(l).count, 0);
  return <div className="emg8-classic-cue" aria-live="polite">
    <span className="ins-cap">正在录 · {num != null && (gp.label === CLASSIC_MOVE ? '不触发 · ' : `动作 ${num} · `)}第 {gp.take}/{gp.count} 次</span>
    <b>{LABEL_CN[gp.label ?? ''] ?? gp.label}</b>
    <span className={now ? 'go' : undefined}>{now ? `做！${left.toFixed(1)} s` : /^\d+$/.test(gp.phase ?? '') ? `${gp.phase} 秒后开始` : gp.phase ?? ''}</span>
    {done != null && <small>进度 {done} / {all}</small>}
  </div>;
}

/** 识别页：控制串口这次发了什么 */
export function ClassicOut({ bridge, projectId, ctrl, onError }: { bridge: Emg8Bridge; projectId: string; ctrl: CtrlState | undefined; onError: (m: string) => void }) {
  const reopen = async () => { if (!ctrl?.port) return; const r = await bridge.ctrl?.(projectId, { action: 'open', port: ctrl.port, baud: ctrl.baud }); if (r && !r.ok) onError(r.message); };
  const at = (t: number) => new Date(t * 1000).toLocaleTimeString('zh-CN', { hour12: false }) + '.' + String(Math.floor((t % 1) * 100)).padStart(2, '0');
  return <section className="emg8-card emg8-classic-out">
    <header><h3>控制串口输出</h3><small>{ctrl?.open ? `${ctrl.port} · ${ctrl.baud}` : ctrl?.error ? '已断开' : '没打开：在「① 连上」选控制串口'}</small></header>
    {ctrl?.error && <p className="emg8-warn">{ctrl.error}。识别还在跑，结果没发出去。<button onClick={() => void reopen()}>重连</button></p>}
    {!!ctrl?.log.length && <ol className="emg8-classic-log">{ctrl.log.slice(0, 8).map((x, i) => <li key={`${x.t}-${i}`}><span>{at(x.t)}</span><code>{x.code}\n</code><b>{x.label === 'test' ? '测试' : LABEL_CN[x.label] ?? x.label}</b></li>)}</ol>}
    {!ctrl?.log.length && <p className="emg8-fine">还没发过。认出的动作一变就发一次，同一动作保持不重复发。</p>}
  </section>;
}
