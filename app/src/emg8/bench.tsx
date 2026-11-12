'use client';
// 基准测试：鼠标 / 触控板 / 手环用同一个页面、同一批条件各做一遍，才有可比的数。
// T1 环形指向（ISO 9241-9）：测「指向 + 选择」，吞吐按实际点击位置算，失败试次保留（见 bench-math.ts）。
// T2 打字 + 点击：打一个词回车 → 点目标 → 回到键盘，量整条链的时间；打错重打、点错重点都算在总时间里。
// 目标辅助（最近目标）对所有设备同样可开，算法只看目标几何、不知道哪个是正确目标；辅助成绩单独记。
// 成绩存在本机浏览器存储里（emg8:bench），可导出 JSON。
import { useEffect, useRef, useState } from 'react';
import { grayTitle } from './gray-title';
import { nearestTarget, ringOrder, ringTargets, rng, sequenceResult, shuffled, type Pt, type SeqResult, type Trial } from './bench-math';
import type { CursorMode } from './contract';

type Device = 'mouse' | 'trackpad' | 'band';
const DEVICE_CN: Record<Device, string> = { mouse: '鼠标', trackpad: '触控板', band: '手环' };
const SEED = 20261003, PAD_H = 640;
const CONDITIONS = shuffled([220, 380, 540].flatMap((d) => [24, 44, 72].map((w) => ({ d, w }))), SEED);   // 所有设备同一顺序
const WORDS = shuffled(['hand', 'wrist', 'pinch', 'cursor', 'signal', 'muscle', 'target', 'finger', 'motion', 'screen', 'window', 'button', 'scroll', 'select',
  'drag', 'click', 'point', 'track', 'speed', 'power', 'light', 'sound', 'touch', 'space', 'paper', 'water', 'green', 'house', 'plant', 'chair'], SEED).slice(0, 20);

export type BenchRun = {
  id: string; test: 'T1' | 'T2'; device: Device; assist: boolean; donning: number; time: string; modes: string[];
  tp?: number; mt?: number; err?: number; seqs?: Omit<SeqResult, 'trials'>[]; trials?: Trial[][];
  total?: number; acquire?: number; back?: number; misses?: number; backspaces?: number; rounds?: T2Round[];
};
type T2Round = { word: string; typed: number; enter: number; firstMove: number | null; click: number; misses: number; backspaces: number; back: number | null };

const KEY = 'emg8:bench';
const loadRuns = (): BenchRun[] => { try { return JSON.parse(localStorage.getItem(KEY) || '[]') as BenchRun[]; } catch { return []; } };
const saveRun = (r: BenchRun) => { try { localStorage.setItem(KEY, JSON.stringify([...loadRuns(), r])); } catch { /* 存不下就只在本次页面里看 */ } };
const mean = (xs: number[]) => (xs.length ? xs.reduce((s, v) => s + v, 0) / xs.length : 0);
const stamp = () => new Date().toISOString().slice(0, 19);

export function Bench({ mode, donning }: { mode: CursorMode; donning: number }) {
  const [device, setDevice] = useState<Device>('mouse');
  const [assist, setAssist] = useState(false);
  const [runs, setRuns] = useState<BenchRun[]>(() => loadRuns());
  const done = (r: BenchRun) => { saveRun(r); setRuns(loadRuns()); };
  const bandOn = mode === 'move' || mode === 'drag';
  const mismatch = device === 'band' ? !bandOn : bandOn;
  const exportJson = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(loadRuns(), null, 1)], { type: 'application/json' }));
    a.download = `emg8-bench-${stamp().replace(/[:T]/g, '')}.json`; a.click(); URL.revokeObjectURL(a.href);
  };
  return <div className="emg8-control">
    <section className="emg8-card emg8-control-head">
      <div><h3>基准测试 · 和鼠标比</h3><small>同一个页面、同一批条件，每种设备先练 1 轮再测 2 轮；设备顺序交错着做。</small></div>
      <div className="emg8-row tight">
        <label className="emg8-inline">设备 <select value={device} onChange={(e) => setDevice(e.target.value as Device)}>{(Object.keys(DEVICE_CN) as Device[]).map((d) => <option key={d} value={d}>{DEVICE_CN[d]}</option>)}</select></label>
        <label className="emg8-inline"><input type="checkbox" checked={assist} onChange={(e) => setAssist(e.target.checked)} /> 目标辅助（选最近的目标）</label>
        <button onClick={exportJson} disabled={!runs.length} title={grayTitle(!runs.length && '还没有成绩可导出')}>导出成绩</button>
      </div>
    </section>
    {mismatch && <p className="emg8-warn">{device === 'band' ? '选的是「手环」，但手环现在没在控制光标：先到「④ 控制」启用，否则这轮成绩会被标记。' : `选的是「${DEVICE_CN[device]}」，但手环正在控制光标：先停掉手环，否则这轮成绩会被标记。`}</p>}
    <RingTest key={`t1-${device}-${assist}`} device={device} assist={assist} mode={mode} donning={donning} onDone={done} />
    <TypeClickTest key={`t2-${device}-${assist}`} device={device} assist={assist} mode={mode} donning={donning} onDone={done} />
    <Results runs={runs} onClear={() => { try { localStorage.removeItem(KEY); } catch { /* 忽略 */ } setRuns([]); }} />
  </div>;
}

/** T1：13 个目标一圈，3 种距离 × 3 种大小；每点一下（不管中没中）就换到对面的下一个 */
function RingTest({ device, assist, mode, donning, onDone }: { device: Device; assist: boolean; mode: CursorMode; donning: number; onDone: (r: BenchRun) => void }) {
  const pad = useRef<HTMLDivElement>(null);
  const run = useRef<{ ci: number; k: number; t: number; trials: Trial[]; seqs: SeqResult[]; firstEnter: number | null; entries: number; inside: boolean } | null>(null);
  const modeRef = useRef(mode); useEffect(() => { modeRef.current = mode; }, [mode]);
  const [view, setView] = useState<{ ci: number; k: number; w: number; h: number } | null>(null);
  const [result, setResult] = useState<BenchRun | null>(null);
  const order = ringOrder();
  const targetsFor = (ci: number, w: number, h: number) => ringTargets(w / 2, h / 2, CONDITIONS[ci].d);
  const start = () => {
    pad.current!.scrollIntoView({ block: 'center' });                          // 整圈目标都要在窗口里
    const r = pad.current!.getBoundingClientRect();
    run.current = { ci: 0, k: 0, t: 0, trials: [], seqs: [], firstEnter: null, entries: 0, inside: false };
    setResult(null); setView({ ci: 0, k: 0, w: r.width, h: r.height });
  };
  const local = (e: React.PointerEvent): Pt => { const r = pad.current!.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  const move = (e: React.PointerEvent) => {
    const s = run.current; if (!s || !view || s.k === 0) return;
    const ts = targetsFor(s.ci, view.w, view.h), p = local(e), to = ts[order[s.k]];
    const inside = Math.hypot(p.x - to.x, p.y - to.y) <= CONDITIONS[s.ci].w / 2;
    if (inside && !s.inside) { s.entries++; if (s.firstEnter == null) s.firstEnter = performance.now() - s.t; }
    s.inside = inside;
  };
  const down = (e: React.PointerEvent) => {
    const s = run.current; if (!s || !view) return;
    const ts = targetsFor(s.ci, view.w, view.h), p = local(e), now = performance.now(), c = CONDITIONS[s.ci];
    const toIdx = order[s.k], to = ts[toIdx];
    const hit = assist ? nearestTarget(ts, p) === toIdx : Math.hypot(p.x - to.x, p.y - to.y) <= c.w / 2;
    if (s.k === 0) { if (!hit) return; }                                    // 每组第一个目标只用来起表，必须点中
    else s.trials.push({ from: ts[order[s.k - 1]], to, click: p, mt: now - s.t, hit, firstEnter: s.firstEnter, entries: s.entries, mode: modeRef.current });
    s.t = now; s.firstEnter = null; s.entries = 0; s.inside = false; s.k++;
    if (s.k > 13) {                                                         // 这一组 13 次做完
      s.seqs.push(sequenceResult(c.d, c.w, s.trials)); s.trials = []; s.k = 0; s.ci++;
      if (s.ci >= CONDITIONS.length) {
        const all = s.seqs.flatMap((q) => q.trials);
        const r: BenchRun = { id: `T1-${Date.now()}`, test: 'T1', device, assist, donning, time: stamp(), modes: [...new Set(all.map((t) => t.mode ?? ''))],
          tp: mean(s.seqs.map((q) => q.tp)), mt: mean(all.map((t) => t.mt)) / 1000, err: all.filter((t) => !t.hit).length / all.length,
          seqs: s.seqs.map(({ trials: _t, ...q }) => q), trials: s.seqs.map((q) => q.trials) };
        run.current = null; setView(null); setResult(r); onDone(r); return;
      }
    }
    setView({ ...view, ci: s.ci, k: s.k });
  };
  const c = view ? CONDITIONS[view.ci] : null, ts = view ? targetsFor(view.ci, view.w, view.h) : [];
  return <section className="emg8-card">
    <header><h3>T1 环形指向 · {CONDITIONS.length} 组 × 13 次</h3>
      <div className="emg8-row tight">{view && <b>第 {view.ci + 1} / {CONDITIONS.length} 组 · {view.k === 0 ? '点亮着的目标开始' : `${view.k} / 13`}</b>}<button onClick={start}>{view || result ? '重新开始' : '开始'}</button></div></header>
    <div ref={pad} className="emg8-pad emg8-benchpad" style={{ height: PAD_H }} onPointerDown={down} onPointerMove={move}>
      {view && c && ts.map((t, i) => <i key={i} className={`emg8-ringt ${i === order[view.k] ? 'on' : ''}`} style={{ left: t.x - c.w / 2, top: t.y - c.w / 2, width: c.w, height: c.w }} />)}
      {result && <div className="emg8-pad-result"><b>{result.tp!.toFixed(2)} 比特/秒</b>
        <span>{DEVICE_CN[result.device]}{result.assist ? ' · 目标辅助' : ''} · 平均每次 {result.mt!.toFixed(2)} 秒 · 点错 {(result.err! * 100).toFixed(0)}%</span>
        <small>{flag(result) || '已保存到下面的成绩表'}</small></div>}
      {!view && !result && <p className="emg8-pad-hint">点「开始」，依次点亮着的圆。点不中也会换到下一个（算一次点错）。共 {CONDITIONS.length * 13} 次，手环大约 5 分钟。</p>}
    </div>
    <p className="emg8-fine">吞吐按实际点击位置算（有效宽度 = 4.133 × 点击偏差的标准差），失败试次照算；时间从上一次点击到这一次点击，捏合识别的等待也在里面。</p>
  </section>;
}

/** T2：打一个词回车 → 点目标（旁边有 5 个干扰目标）→ 下一轮的第一个按键。点错、打错都重来，时间照算。 */
function TypeClickTest({ device, assist, mode, donning, onDone }: { device: Device; assist: boolean; mode: CursorMode; donning: number; onDone: (r: BenchRun) => void }) {
  const pad = useRef<HTMLDivElement>(null), input = useRef<HTMLInputElement>(null);
  const modeRef = useRef(mode); useEffect(() => { modeRef.current = mode; }, [mode]);
  const st = useRef<{ t0: number; rounds: T2Round[]; cur: Partial<T2Round> & { shown: number }; modes: Set<string>; lastClick: number | null } | null>(null);
  const [view, setView] = useState<{ i: number; phase: 'type' | 'click'; pts: Pt[]; bad: boolean } | null>(null);
  const [text, setText] = useState('');
  const [result, setResult] = useState<BenchRun | null>(null);
  const R = 24;
  const layout = (i: number): Pt[] => {                                     // 第 0 个是正确目标，后 5 个是干扰；固定种子，各设备相同
    const r = pad.current!.getBoundingClientRect(), g = rng(SEED + i * 97), pts: Pt[] = [];
    while (pts.length < 6) {
      const p = { x: 60 + g() * (r.width - 120), y: 110 + g() * (r.height - 170) };
      if (pts.every((q) => Math.hypot(p.x - q.x, p.y - q.y) > 3 * R)) pts.push(p);
    }
    return pts;
  };
  const begin = (i: number) => { st.current!.cur = { shown: performance.now(), misses: 0, backspaces: 0, firstMove: null }; setText(''); setView({ i, phase: 'type', pts: layout(i), bad: false }); setTimeout(() => input.current?.focus(), 0); };
  const start = () => { pad.current!.scrollIntoView({ block: 'center' }); st.current = { t0: performance.now(), rounds: [], cur: { shown: 0 }, modes: new Set(), lastClick: null }; setResult(null); begin(0); };
  const key = (e: React.KeyboardEvent<HTMLInputElement>) => {
    const s = st.current; if (!s || !view || view.phase !== 'type') return;
    const now = performance.now();
    if (s.cur.typed == null) { s.cur.typed = now - s.cur.shown; if (s.lastClick != null && s.rounds.length) s.rounds[s.rounds.length - 1].back = now - s.lastClick; }
    if (e.key === 'Backspace') s.cur.backspaces = (s.cur.backspaces ?? 0) + 1;
    if (e.key === 'Enter') {
      if (text.trim() === WORDS[view.i]) { s.cur.enter = now - s.cur.shown; setView({ ...view, phase: 'click', bad: false }); }
      else setView({ ...view, bad: true });                                  // 打错：留在原地重打，时间照算
    }
  };
  const moved = () => { const s = st.current; if (s && view?.phase === 'click' && s.cur.firstMove == null) s.cur.firstMove = performance.now() - s.cur.shown; };
  const down = (e: React.PointerEvent) => {
    const s = st.current; if (!s || !view || view.phase !== 'click') return;
    const r = pad.current!.getBoundingClientRect(), p = { x: e.clientX - r.left, y: e.clientY - r.top }, now = performance.now();
    s.modes.add(modeRef.current);
    const ok = assist ? nearestTarget(view.pts, p) === 0 : Math.hypot(p.x - view.pts[0].x, p.y - view.pts[0].y) <= R;
    if (!ok) { s.cur.misses = (s.cur.misses ?? 0) + 1; return; }             // 点错：重点，时间照算
    s.rounds.push({ word: WORDS[view.i], typed: s.cur.typed ?? 0, enter: s.cur.enter ?? 0, firstMove: s.cur.firstMove ?? null, click: now - s.cur.shown, misses: s.cur.misses ?? 0, backspaces: s.cur.backspaces ?? 0, back: null });
    s.lastClick = now;
    if (view.i + 1 >= WORDS.length) {
      const rs = s.rounds, backs = rs.map((x) => x.back).filter((x): x is number => x != null);
      const res: BenchRun = { id: `T2-${Date.now()}`, test: 'T2', device, assist, donning, time: stamp(), modes: [...s.modes], total: (now - s.t0) / 1000,
        acquire: mean(rs.map((x) => x.click - x.enter)) / 1000, back: mean(backs) / 1000, misses: rs.reduce((a, x) => a + x.misses, 0), backspaces: rs.reduce((a, x) => a + x.backspaces, 0), rounds: rs };
      st.current = null; setView(null); setResult(res); onDone(res); return;
    }
    begin(view.i + 1);
  };
  return <section className="emg8-card">
    <header><h3>T2 打字 + 点击 · {WORDS.length} 轮</h3>
      <div className="emg8-row tight">{view && <b>第 {view.i + 1} / {WORDS.length} 轮 · {view.phase === 'type' ? '打字，回车' : '点绿色目标'}</b>}<button onClick={start}>{view || result ? '重新开始' : '开始'}</button></div></header>
    <div ref={pad} className="emg8-pad emg8-benchpad" style={{ height: 460 }} onPointerDown={down} onPointerMove={moved}>
      {view && <div className={`emg8-t2word ${view.bad ? 'bad' : ''}`}><b>{WORDS[view.i]}</b>
        <input ref={input} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={key} disabled={view.phase !== 'type'} autoCapitalize="off" autoCorrect="off" spellCheck={false} aria-label="照着打这个词，回车" /></div>}
      {view?.phase === 'click' && view.pts.map((p, i) => <i key={i} className={`emg8-ringt ${i === 0 ? 'on' : 'distract'}`} style={{ left: p.x - R, top: p.y - R, width: 2 * R, height: 2 * R }} />)}
      {result && <div className="emg8-pad-result"><b>{result.total!.toFixed(1)} 秒</b>
        <span>{DEVICE_CN[result.device]}{result.assist ? ' · 目标辅助' : ''} · 回车到点中 {result.acquire!.toFixed(2)} 秒 · 点中到下一个按键 {result.back!.toFixed(2)} 秒</span>
        <small>{flag(result) || `点错 ${result.misses} 次 · 退格 ${result.backspaces} 次 · 已保存`}</small></div>}
      {!view && !result && <p className="emg8-pad-hint">点「开始」：照着打出单词按回车，再点绿色圆（灰色是干扰），然后直接打下一个词。打错重打、点错重点，时间都算。</p>}
    </div>
    <p className="emg8-fine">总时间从「开始」到最后一次点中。「点中到下一个按键」就是回到键盘的时间：鼠标要挪手，手环不用——这一项差多少要看实测。</p>
  </section>;
}

/** 这轮成绩能不能算：选了手环但中途不是手环在控制（或反过来）就标出来 */
function flag(r: BenchRun): string {
  const band = r.modes.some((m) => m === 'move' || m === 'drag'), other = r.modes.some((m) => m !== 'move' && m !== 'drag');
  if (r.device === 'band' && other) return '⚠ 部分点击时手环没在控制光标，这轮不算手环成绩';
  if (r.device !== 'band' && band) return '⚠ 部分点击时手环在控制光标，这轮不算' + DEVICE_CN[r.device] + '成绩';
  return '';
}

function Results({ runs, onClear }: { runs: BenchRun[]; onClear: () => void }) {
  const rows = runs.slice(-12).reverse();
  return <section className="emg8-card">
    <header><h3>成绩表（最近 12 次）</h3><button onClick={() => { if (window.confirm('清空本机保存的全部基准成绩？先导出再清。')) onClear(); }} disabled={!runs.length} title={grayTitle(!runs.length && '还没有成绩可清空')}>清空</button></header>
    {rows.length ? <table className="emg8-confusion emg8-benchtable"><thead><tr><th>时间</th><th>测试</th><th>设备</th><th>辅助</th><th>佩戴</th><th>成绩</th><th>细项</th><th>备注</th></tr></thead>
      <tbody>{rows.map((r) => <tr key={r.id}><td>{r.time.slice(5, 16).replace('T', ' ')}</td><td>{r.test}</td><td>{DEVICE_CN[r.device]}</td><td>{r.assist ? '开' : '关'}</td><td>{r.donning}</td>
        <td><b>{r.test === 'T1' ? `${r.tp!.toFixed(2)} 比特/秒` : `${r.total!.toFixed(1)} 秒`}</b></td>
        <td>{r.test === 'T1' ? `每次 ${r.mt!.toFixed(2)} 秒 · 点错 ${(r.err! * 100).toFixed(0)}%` : `指向 ${r.acquire!.toFixed(2)} 秒 · 回键盘 ${r.back!.toFixed(2)} 秒 · 点错 ${r.misses}`}</td>
        <td>{flag(r)}</td></tr>)}</tbody></table>
      : <p className="emg8-fine">还没有成绩。先用鼠标和触控板各做一遍当基准。</p>}
  </section>;
}
