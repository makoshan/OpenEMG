'use client';
// 光标控制。阶段一（主方案 8.1 P0）：只用 IMU 移动光标。阶段二（P1）：捏住保持 = 按下左键，松开 = 松开左键，中间转手腕就是拖拽。
// 控制器在采集服务里（firmware/wl8_cursor.Controller），这里只发白名单动作、显示状态。默认演练（只算不发）；「启用」才动真光标；
// 停止按钮常驻，Esc 也停，停之前服务端先补松开左键。
// 验收（拟定目标）：静止 10 s 漂移 ≤ 10 点；10 个目标 ≥ 8 个进入 30 点半径并停 1 s；拖拽每次恰好一按一松。
import { motion } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import type { CursorMode, CursorOpts, CursorState, CursorTick, Emg8Bridge, Hand } from './contract';
import { GUIDE, HandGuide, PINCH_GUIDE, PINCH_STEP, type GuideStep } from './hand';
import { grayTitle } from './gray-title';

const VMAX = 2500, TARGETS = 10, RADIUS = 30, HOLD_MS = 1000, TIMEOUT_MS = 12000;
export const CURSOR_MODE_CN: Record<CursorMode, string> = { off: '只读 · 不会操作鼠标', calibrating: '校准中 · 不动光标', log: '演练 · 只计算不动光标', move: '移动光标 · 不点击', drag: '捏合 · 会点击和按下左键' };

const OPTS: [keyof CursorOpts, string, string][] = [
  ['adaptive', '快动作少平滑', '慢动作照样去抖，快动作不再晚 60 ms'],
  ['soft', '软死区', '比死区慢的动作按比例缩小，不再整段截掉'],
  ['rezero', '静止时修正零点', '前臂停稳 1 秒后慢慢校正陀螺零点；有意的慢移不会被当成静止'],
  ['click', '短捏 = 单击', '捏一下松开就点（拖拽模式里，前臂要先停住）；捏住保持仍是拖拽'],
];

type Test = { targets: { x: number; y: number }[]; i: number; hold: number; t0: number; hits: boolean[]; mode: CursorMode; done: boolean };

export function Control({ projectId, bridge, cs, tick, hand, onError }: { projectId: string; bridge: Emg8Bridge; cs: CursorState | null; tick: CursorTick | null; hand: Hand; onError: (m: string) => void }) {
  const mode = cs?.mode ?? 'off';
  const act = async (a: Parameters<Emg8Bridge['cursor']>[1]) => { const r = await bridge.cursor(projectId, a); if (!r.ok) onError(r.message); };
  const [gain, setGain] = useState<number | null>(null), [dead, setDead] = useState<number | null>(null), [accel, setAccel] = useState<number | null>(null);

  // Esc 停止：移动中随时可按（不用空格，免得和游戏快捷键撞）
  useEffect(() => {
    if (mode !== 'move' && mode !== 'drag') return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') void bridge.cursor(projectId, { action: 'log' }); };
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h);
  }, [mode, bridge, projectId]);

  const live = mode === 'move' || mode === 'drag';
  const canEnable = !!cs?.cal && !cs.replay && cs.trusted !== false && !live && mode !== 'calibrating';
  const why = !cs ? '采集服务未响应' : cs.replay ? '回放数据只能演练，不能动真光标' : cs.trusted === false ? '采集服务的宿主没有辅助功能权限：系统设置 → 隐私与安全性 → 辅助功能' : !cs.cal ? '先校准（每次戴上做一次，15 秒）' : mode === 'calibrating' ? '校准还在进行' : live ? '先停下光标，再启用' : '';
  const c = cs?.calib;
  const v = tick && mode !== 'off' ? [tick.vx, tick.vy] : [0, 0];

  return <div className="emg8-control">
    <section className="emg8-card emg8-control-head">
      <div><h3>光标控制</h3><small>移动光标用手腕角速度。捏住保持 = 按下左键，转手腕 = 拖拽，松开 = 松开左键；短捏不点击。</small></div>
      <div className="emg8-row tight">
        <button onClick={() => act({ action: 'calibrate' })} disabled={mode === 'calibrating' || live} title={grayTitle(mode === 'calibrating' && '校准还在进行', live && '先停下光标，再重新校准')}>{cs?.cal ? '重新校准' : '校准 15 秒'}</button>
        <button onClick={() => act({ action: 'calibrate_pinch' })} disabled={mode === 'calibrating' || live} title={grayTitle(mode === 'calibrating' && '校准还在进行', live && '先停下光标，再重新校准')}>{cs?.pcal ? '重做捏合校准' : '捏合校准 32 秒'}</button>
        <button onClick={() => act({ action: 'log' })} disabled={!cs?.cal || mode === 'log'} title={grayTitle(!cs?.cal && '先校准，才能演练', mode === 'log' && '已经在演练')}>演练</button>
        <button className="emg8-primary" onClick={() => act({ action: 'enable', stage: 'move' })} disabled={!canEnable} title={why}>启用 · 移动</button>
        <button className="emg8-primary" onClick={() => act({ action: 'enable', stage: 'drag' })} disabled={!canEnable || !cs?.pcal} title={cs?.pcal ? why : '先做捏合校准'}>启用 · 捏住拖拽</button>
        <button className="emg8-stop emg8-bigstop" onClick={() => act({ action: live && cs?.cal ? 'log' : 'stop' })} disabled={mode === 'off'} title={grayTitle(mode === 'off' && '光标没在动')}>■ 停止（Esc）</button>
      </div>
    </section>
    <div className={`emg8-modebar m-${mode}`} role="status"><b>{CURSOR_MODE_CN[mode]}</b><span>{cs?.note || why}</span>
      <span>IMU {cs?.imu_age_ms != null ? `${cs.imu_age_ms} ms` : '—'} · 肌电 {cs?.emg_age_ms != null ? `${cs.emg_age_ms} ms` : '—'} · 权限 {cs?.trusted == null ? '—' : cs.trusted ? '已授权' : '未授权'}{cs?.cal ? ` · 校准于 ${cs.cal.created.slice(11, 16)}` : ''}</span></div>

    <div className="emg8-control-grid">
      <div className="emg8-col">
        <section className={`emg8-card emg8-cue ${c ? 'on emg8-beam' : ''}`} aria-live="polite">
          {c ? <>
            <div className="emg8-cue-top emg8-cue-hand">
              <HandGuide step={(c.kind === 'pinch' ? PINCH_STEP[c.plan[c.step]?.key] ?? 'rest' : c.plan[c.step]?.key ?? 'rest') as GuideStep} hand={hand} size={200} />
              <div><div className="emg8-cue-title">{c.step < 0 ? (c.kind === 'pinch' ? '准备：手放松' : '准备：手掌朝下放平') : c.text}</div>
                <div className="emg8-cue-hint">{c.kind === 'pinch' ? '捏合校准' : '移动校准'} · 第 {Math.max(1, c.step + 1)} / {c.plan.length} 步 · 跟着动画做{c.kind === 'pinch' ? '；不捏那段手指放松' : '；慢一两秒没关系'}</div></div>
              <div className="emg8-cue-big">{Math.max(0, Math.ceil(c.total - Math.max(0, c.t)))}</div>
            </div>
            <div className="emg8-timeline">
              {c.plan.map((p) => <span key={p.start} className={p.key === 'pinch' || p.key === 'lr' || p.key === 'ud' ? 't-hold' : 't-rest'} style={{ flex: p.dur }}>{p.text.split('，')[0]}</span>)}
              <i className="emg8-playhead" style={{ left: `${Math.min(100, Math.max(0, c.t / c.total) * 100)}%` }} />
            </div>
          </> : <div className="emg8-cue-idle">
            <b>{cs?.cal ? '已校准' : '怎么校准 · 15 秒三步'}</b>
            <div className="emg8-guide">{GUIDE.map((g, i) => <figure key={g.key}><HandGuide step={g.key} hand={hand} size={150} />
              <figcaption><b>{i + 1}. {g.title}</b><small>{g.hint}</small></figcaption></figure>)}</div>
            <span>点「校准 15 秒」后照着做，页面和语音会提示每一步。换手、摘下重戴都要重做。</span>
            {cs?.cal && <small>左右用陀螺第 {cs.cal.x_axis} 轴（{cs.cal.x_sign > 0 ? '+' : '−'}），上下用第 {cs.cal.y_axis} 轴（{cs.cal.y_sign > 0 ? '+' : '−'}）</small>}
            {cs?.cal && <div className="emg8-row tight"><small>方向不对？</small>
              <button onClick={() => act({ action: 'flip', axis: 'x' })}>⇆ 左右反了</button><button onClick={() => act({ action: 'flip', axis: 'y' })}>⇅ 上下反了</button></div>}
          </div>}
        </section>

        <section className="emg8-card">
          <header><h3>手感（硬件要调）</h3><small>改完立即生效</small></header>
          <label className="emg8-knob">灵敏度 <b>{Math.round(gain ?? cs?.gain ?? 700)}</b> 点/秒 每 rad/s
            <input type="range" min={200} max={1500} step={50} value={gain ?? cs?.gain ?? 700} onChange={(e) => setGain(Number(e.target.value))} onPointerUp={() => gain && act({ action: 'config', gain })} /></label>
          <label className="emg8-knob">死区 <b>{(dead ?? cs?.deadzone ?? .12).toFixed(2)}</b> rad/s（手在抖光标不动就调大）
            <input type="range" min={.04} max={.3} step={.01} value={dead ?? cs?.deadzone ?? .12} onChange={(e) => setDead(Number(e.target.value))} onPointerUp={() => dead && act({ action: 'config', deadzone: dead })} /></label>
          <label className="emg8-knob">加速 <b>{(accel ?? cs?.accel ?? 1).toFixed(1)}</b>（0 = 线性；越大：慢动作越准、快动作走得越远）
            <input type="range" min={0} max={3} step={.1} value={accel ?? cs?.accel ?? 1} onChange={(e) => setAccel(Number(e.target.value))} onPointerUp={() => accel != null && act({ action: 'config', accel })} /></label>
        </section>

        <section className="emg8-card">
          <header><h3>跟手与单击</h3><small>逐项开关，做对照</small></header>
          {OPTS.map(([k, label, hint]) => <label key={k} className="emg8-opt">
            <input type="checkbox" checked={cs?.opts?.[k] ?? true} disabled={!cs?.opts} onChange={(e) => act({ action: 'config', [k]: e.target.checked })} />
            <span><b>{label}</b><small>{hint}</small></span></label>)}
          {cs?.update_ms?.n ? <p className="emg8-fine">数据更新间隔 中位 {cs.update_ms.p50} ms · p95 {cs.update_ms.p95} ms · 最长 {cs.update_ms.max} ms
            {cs.update_ms.long ? ` · 超过 100 ms ${cs.update_ms.long} 次` : ''} · 处理 p95 {cs.update_ms.proc_p95} ms
            {cs.bias_shift ? ` · 零点已修正 ${cs.bias_shift} rad/s` : ''}{cs.clicks ? ` · 单击 ${cs.clicks} 次` : ''}</p>
            : <p className="emg8-fine">校准后在演练或移动状态下显示数据更新间隔。</p>}
        </section>
      </div>

      <div className="emg8-col">
        <section className="emg8-card emg8-joy-card">
          <header><h3>瞄准速度</h3><small>{live ? '真光标正在按这个速度走' : '演练：只画在这里'}</small></header>
          <Joystick v={v} />
          <p className="emg8-fine">{Math.round(Math.hypot(v[0], v[1]))} 点/秒 · 满圈 = {VMAX}</p>
        </section>
        <section className="emg8-card">
          <header><h3>漂移测试</h3>
            <button onClick={() => act({ action: 'drift' })} disabled={mode !== 'log' && !live} title={grayTitle(mode !== 'log' && !live && '先进入演练或移动，再测漂移')}>手放稳，测 10 秒</button></header>
          {cs?.drift ? <p className={cs.drift.done ? (cs.drift.max_px <= 10 ? 'emg8-ok' : 'emg8-warnline') : ''}>
            {cs.drift.wait_s ? `准备… ${Math.ceil(cs.drift.wait_s)} 秒后开始，手放稳别动`
              : cs.drift.done ? `最大漂移 ${cs.drift.max_px} 点（拟定目标 ≤ 10）${cs.drift.moved ? ` · 测量期间前臂有动作（最大 ${cs.drift.peak_w} rad/s，超过死区），这不是零点漂移，手放稳重测` : ''}`
              : `测量中… 还剩 ${cs.drift.left_s} 秒 · 当前 ${cs.drift.max_px} 点`}</p>
            : <p className="emg8-fine">点了以后先倒数 3 秒再测 10 秒，统计控制器要让光标走的距离；演练和移动状态都能测。</p>}
        </section>
      </div>
    </div>
    <PinchPanel cs={cs} tick={tick} hand={hand} />
    <TargetTest mode={mode} />
    <DragTest mode={mode} />
  </div>;
}

/** 阶段二：捏合分数条（按下线 / 松开线 / 动前臂区）+ 左键灯 + 按下松开是否成对 */
function PinchPanel({ cs, tick, hand }: { cs: CursorState | null; tick: CursorTick | null; hand: Hand }) {
  const p = cs?.pcal, score = tick?.score ?? cs?.score ?? 0, btn = tick?.button ?? cs?.button ?? 'up', ev = cs?.events;
  const MAX = 1.4, at = (x: number) => `${Math.min(100, Math.max(0, (x / MAX) * 100))}%`;
  return <section className="emg8-card emg8-pinch">
    <header><h3>捏住拖拽 · 阶段二</h3>
      <small>{p ? `捏合校准于 ${p.created.slice(11, 16)} · 用 CH${p.channels.map((c) => c + 1).join('、')} · 用法：停住 → 捏 → 拖 → 停住 → 松` : '先做捏合校准（32 秒）：放松 → 不捏随便动 → 捏住保持 ×3。电极先沾湿、前臂搁稳'}</small></header>
    {!p && <div className="emg8-guide">{PINCH_GUIDE.map((g, i) => <figure key={g.key}><HandGuide step={g.key} hand={hand} size={150} />
      <figcaption><b>{i + 1}. {g.title}</b><small>{g.hint}</small></figcaption></figure>)}</div>}
    {p && <div className="emg8-pinch-live">
      <div className={`emg8-lamp b-${btn}`}><i /><b>{btn === 'down' ? '按下' : btn === 'pending' ? '准备…' : '松开'}</b><small>左键</small></div>
      <div className="emg8-meter">
        <div className="track">
          <span className="zone" style={{ width: at(p.rest_p95) }} title="放松（含两次捏之间）时的水平" />
          <motion.i className={btn} animate={{ width: at(score) }} transition={{ type: 'spring', stiffness: 400, damping: 30 }} />
          <span className="mk off" style={{ left: at(p.off) }}>松开线</span><span className="mk on" style={{ left: at(p.on) }}>按下线</span>
        </div>
        <small>捏合分数 {score.toFixed(2)} · 放松时最高 {p.rest_p95} · 捏住时最低 {p.pinch_p25}{p.move_p90 != null ? ` · 动前臂时 ${p.move_p90}（比捏住还大，所以动的时候不许按下）` : ''}</small>
        <small className={cs?.still ? 'emg8-ok' : 'emg8-warnline'}>{cs?.still ? '● 前臂静止：可以捏下去' : '○ 前臂在动：先停住再捏（按住之后可以动，就是拖拽）'}{cs?.artifacts ? ` · 电极伪迹 ${cs.artifacts} 拍` : ''}</small>
      </div>
      <div className="emg8-evt"><b>{ev?.down ?? 0} 按 / {ev?.up ?? 0} 松</b>
        <small className={ev && !ev.paired ? 'emg8-warnline' : 'emg8-ok'}>{ev && !ev.paired ? '⚠ 按下 / 松开没成对' : '成对 ✓'}</small></div>
    </div>}
  </section>;
}

/** 拖拽测试：把方块拖进圆圈。每次应当恰好一次按下、一次松开（主方案 8.1 P1）。用页面收到的真实鼠标事件判，和手腕还是鼠标无关，所以记下状态。 */
const TRIALS = 10, BOX = 56, GOAL_R = 44;
type Pt = { x: number; y: number };
type Drag = { i: number; box: Pt; goal: Pt; grab: Pt | null; downs: number; ups: number; results: { ok: boolean; clean: boolean }[]; mode: CursorMode; done: boolean };

function DragTest({ mode }: { mode: CursorMode }) {
  const pad = useRef<HTMLDivElement>(null);
  const [d, setD] = useState<Drag | null>(null);
  const place = () => {
    const r = pad.current!.getBoundingClientRect(), m = 60, rnd = () => ({ x: m + Math.random() * (r.width - 2 * m), y: m + Math.random() * (r.height - 2 * m) });
    const box = rnd(); let goal = rnd();
    for (let k = 0; k < 20 && Math.hypot(box.x - goal.x, box.y - goal.y) < 180; k++) goal = rnd();
    return { box, goal };
  };
  const local = (e: React.PointerEvent) => { const r = pad.current!.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  const start = () => setD({ i: 0, ...place(), grab: null, downs: 0, ups: 0, results: [], mode: 'drag', done: false });   // 只看每次按下时的模式，点「开始」那一刻不算
  const down = (e: React.PointerEvent) => {
    if (!d || d.done) return;
    const q = local(e), hit = Math.abs(q.x - d.box.x) <= BOX / 2 && Math.abs(q.y - d.box.y) <= BOX / 2;
    e.currentTarget.setPointerCapture(e.pointerId);
    setD({ ...d, downs: d.downs + 1, grab: hit ? { x: d.box.x - q.x, y: d.box.y - q.y } : null, mode: mode === 'drag' ? d.mode : mode });
  };
  const move = (e: React.PointerEvent) => { if (!d?.grab) return; const q = local(e); setD({ ...d, box: { x: q.x + d.grab.x, y: q.y + d.grab.y } }); };
  const up = () => {
    if (!d || d.done) return;
    if (!d.grab) { setD({ ...d, ups: d.ups + 1 }); return; }
    const ok = Math.hypot(d.box.x - d.goal.x, d.box.y - d.goal.y) <= GOAL_R, i = d.i + 1;
    const results = [...d.results, { ok, clean: d.downs === 1 && d.ups === 0 }];
    setD({ ...d, ...(i < TRIALS ? place() : {}), i, grab: null, downs: 0, ups: 0, results, done: i >= TRIALS });
  };
  const n = d?.results.filter((r) => r.ok).length ?? 0, clean = d?.results.filter((r) => r.clean).length ?? 0;
  return <section className="emg8-card">
    <header><h3>拖拽测试 · 把方块拖进圆圈 · {TRIALS} 次</h3>
      <div className="emg8-row tight">{d && <b>{n} / {d.results.length} 拖进 · 一按一松 {clean} / {d.results.length}</b>}<button onClick={start}>{d ? '重新开始' : '开始'}</button></div></header>
    <div ref={pad} className="emg8-pad emg8-dragpad" onPointerDown={down} onPointerMove={move} onPointerUp={up}>
      {d && !d.done && <>
        <motion.div key={`g${d.i}`} className="emg8-goal" style={{ left: d.goal.x - GOAL_R, top: d.goal.y - GOAL_R, width: GOAL_R * 2, height: GOAL_R * 2 }}
          initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 300, damping: 18 }}><span>{d.i + 1}</span></motion.div>
        <div className={`emg8-box ${d.grab ? 'grab' : ''}`} style={{ left: d.box.x - BOX / 2, top: d.box.y - BOX / 2, width: BOX, height: BOX }}>✋</div>
      </>}
      {d?.done && <div className="emg8-pad-result"><b>{n} / {TRIALS}</b><span>拖进圆圈 · 一按一松 {clean} / {TRIALS}</span>
        <small>{d.mode === 'drag' ? '全程在「捏住拖拽」状态：这是手环控制的成绩' : `测试时状态是「${CURSOR_MODE_CN[d.mode]}」：用的不是手环，不算验收`}</small></div>}
      {!d && <p className="emg8-pad-hint">启用「捏住拖拽」后点「开始」：光标移到方块上，捏住 → 转前臂拖进圆圈 → 松开。</p>}
    </div>
  </section>;
}

function Joystick({ v }: { v: number[] }) {
  const R = 100, s = (x: number) => (x / VMAX) * R;
  return <svg className="emg8-joy" viewBox="-120 -120 240 240" aria-label="瞄准速度">
    {[1, .5].map((k) => <circle key={k} r={R * k} className="ring" />)}
    <line x1={-R} y1={0} x2={R} y2={0} className="axis" /><line x1={0} y1={-R} x2={0} y2={R} className="axis" />
    <motion.line x1={0} y1={0} animate={{ x2: s(v[0]), y2: s(v[1]) }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} className="vec" />
    <motion.circle r={10} animate={{ cx: s(v[0]), cy: s(v[1]) }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} className="dot" />
  </svg>;
}

/** 目标测试：光标（手腕控制时就是真光标）进入目标 30 点内并停 1 秒算命中，12 秒没中算失败。坐标用页面 CSS 像素 ≈ 逻辑点。 */
function TargetTest({ mode }: { mode: CursorMode }) {
  const pad = useRef<HTMLDivElement>(null), pos = useRef<{ x: number; y: number } | null>(null);
  const [test, setTest] = useState<Test | null>(null);
  const start = () => {
    const r = pad.current!.getBoundingClientRect(), m = 50;
    const targets = Array.from({ length: TARGETS }, () => ({ x: m + Math.random() * (r.width - 2 * m), y: m + Math.random() * (r.height - 2 * m) }));
    setTest({ targets, i: 0, hold: 0, t0: performance.now(), hits: [], mode: 'move', done: false });   // 只记测试过程中的模式：点「开始」时还在演练不算（2026-10-02 误标）
  };
  useEffect(() => {
    if (!test || test.done) return;
    const id = setInterval(() => setTest((t) => {
      if (!t || t.done) return t;
      const now = performance.now(), g = t.targets[t.i], p = pos.current;
      const inside = !!p && Math.hypot(p.x - g.x, p.y - g.y) <= RADIUS, hold = inside ? t.hold + 50 : 0;
      const hit = hold >= HOLD_MS, timeout = now - t.t0 > TIMEOUT_MS;
      if (!hit && !timeout) return { ...t, hold, mode: mode === 'move' || mode === 'drag' ? t.mode : mode };   // 测试中途离开移动状态要记下来
      const hits = [...t.hits, hit], i = t.i + 1;
      return { ...t, hits, i, hold: 0, t0: now, done: i >= TARGETS };
    }), 50);
    return () => clearInterval(id);
  }, [test?.done, !!test, mode]); // eslint-disable-line react-hooks/exhaustive-deps
  const n = test?.hits.filter(Boolean).length ?? 0, cur = test && !test.done ? test.targets[test.i] : null;
  return <section className="emg8-card">
    <header><h3>目标测试 · {TARGETS} 个目标</h3>
      <div className="emg8-row tight">{test && <b>{n} / {test.hits.length} 命中</b>}<button onClick={start}>{test ? '重新开始' : '开始'}</button></div></header>
    <div ref={pad} className="emg8-pad" onPointerMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); pos.current = { x: e.clientX - r.left, y: e.clientY - r.top }; }}
      onPointerLeave={() => { pos.current = null; }}>
      {cur && <motion.div key={test!.i} className="emg8-target" style={{ left: cur.x - RADIUS, top: cur.y - RADIUS, width: RADIUS * 2, height: RADIUS * 2 }}
        initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 400, damping: 20 }}>
        <svg viewBox="0 0 60 60"><circle cx={30} cy={30} r={27} className="t-ring" /><circle cx={30} cy={30} r={27} className="t-hold" style={{ strokeDashoffset: 170 * (1 - (test!.hold / HOLD_MS)) }} /></svg>
        <span>{test!.i + 1}</span></motion.div>}
      {test?.done && <div className="emg8-pad-result"><b>{n} / {TARGETS}</b><span>{n >= 8 ? '达到拟定目标（≥ 8）' : '未达拟定目标（≥ 8）'}</span>
        <small>{test.mode === 'move' ? '全程在「移动光标」状态：这是手腕控制的成绩' : `测试时状态是「${CURSOR_MODE_CN[test.mode]}」：用的不是手腕，不算验收`}</small></div>}
      {!test && <p className="emg8-pad-hint">启用移动光标后点「开始」，用手腕把光标移进圆圈并停 1 秒。</p>}
    </div>
  </section>;
}
