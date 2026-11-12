'use client';
// 识别页的幅度门槛、灵敏度（经典组再加动作阈值 = 把握度）。服务端用峰峰值和这几个数决定这次认不认；这里只显示读数并送参数。
import { useEffect, useRef, useState } from 'react';
import type { Emg8Bridge, Pred } from './contract';

function stored(key: string, d: number, lo: number, hi: number) {
  try { const v = Number(localStorage.getItem(key)); return localStorage.getItem(key) != null && Number.isInteger(v) && v >= lo && v <= hi ? v : d; } catch { return d; }
}

/** 页面记住的门槛（训练完自动开识别时直接带上，不等识别页再调） */
export const storedGate = (withProb: boolean) => ({ thresholdUv: stored('yuanli.gate.threshold', 0, 0, 5000), sensitivity: stored('yuanli.gate.sensitivity', 5, 1, 10), minProb: withProb ? stored('yuanli.gate.minprob', 70, 0, 99) / 100 : 0,
  ...(withProb ? { thresholdX: stored('yuanli.gate.times10', 0, 0, 100) / 10 } : {}) });

// withProb：经典 5 步才用「动作阈值（把握度）」和「幅度门槛 × 放松底噪」（倍数），其它动作组照旧：把握度发 0、门槛按绝对微伏
export function useRecognitionGate(bridge: Emg8Bridge, projectId: string, on: boolean, onError: (message: string) => void, server?: Pred | null, mask?: number[], withProb = false) {
  // 记住上次的值：重开 App 后滑块回 0 而人以为还是 5000（2026-10-14）。读不到就用默认
  const [thresholdUv, setThresholdUv] = useState(() => stored('yuanli.gate.threshold', 0, 0, 5000));
  const [sensitivity, setSensitivity] = useState(() => stored('yuanli.gate.sensitivity', 5, 1, 10));
  const [probPct, setProbPct] = useState(() => stored('yuanli.gate.minprob', 70, 0, 99));   // 唯理上位机默认 70%
  const minProb = withProb ? probPct / 100 : 0;
  const [times10, setTimes10] = useState(() => stored('yuanli.gate.times10', 0, 0, 100));   // 倍数 × 10 存整数；0 = 不拦
  const timesX = times10 / 10;
  useEffect(() => { try { localStorage.setItem('yuanli.gate.threshold', String(thresholdUv)); localStorage.setItem('yuanli.gate.sensitivity', String(sensitivity)); localStorage.setItem('yuanli.gate.minprob', String(probPct)); localStorage.setItem('yuanli.gate.times10', String(times10)); } catch { /* 存不了就算了 */ } }, [thresholdUv, sensitivity, probPct, times10]);
  const report = useRef(onError);
  useEffect(() => { report.current = onError; }, [onError]);
  // 服务端回报的门槛和滑块不一致就重发：识别会话在服务端重开时门槛会回到 0，而页面的 on 一直是 true（2026-10-14 滑块 5000、服务端 0）
  // mask：要服务端屏蔽的路（不传 = 不管屏蔽）；服务端回报的和它不一致也重发
  const maskKey = mask ? mask.join(',') : null;
  const gate = server?.gate;
  const drift = (!!gate && (gate.threshold_uv !== thresholdUv || gate.sensitivity !== sensitivity || (gate.min_prob ?? 0) !== minProb || (withProb && (gate.threshold_x ?? null) !== timesX))) || (!!server && maskKey != null && (server.mask ?? []).join(',') !== maskKey);
  useEffect(() => {
    if (!on) return;
    const handle = window.setTimeout(() => {
      void bridge.live(projectId, { action: 'tune', thresholdUv, sensitivity, minProb, ...(withProb ? { thresholdX: timesX } : {}), ...(maskKey != null ? { mask: maskKey ? maskKey.split(',').map(Number) : [] } : {}) }).then((r) => { if (!r.ok) report.current(r.message); });
    }, 160);
    return () => window.clearTimeout(handle);
  }, [bridge, on, projectId, sensitivity, thresholdUv, minProb, timesX, withProb, drift, maskKey]);
  return { thresholdUv, setThresholdUv, sensitivity, setSensitivity, minProb, probPct, setProbPct, timesX, setTimesX: (x: number) => setTimes10(Math.round(x * 10)) };
}

export function RecognitionControls({ thresholdUv, setThresholdUv, sensitivity, setSensitivity, pred, probPct, setProbPct, timesX, setTimesX }: {
  thresholdUv: number; setThresholdUv: (value: number) => void; sensitivity: number; setSensitivity: (value: number) => void; pred: Pred | null;
  probPct?: number; setProbPct?: (value: number) => void;   // 给了就多一条「动作阈值（把握度）」
  timesX?: number; setTimesX?: (value: number) => void;     // 给了就把「幅度门槛」换成 × 放松底噪
}) {
  const prob = probPct != null && !!setProbPct;
  const rel = timesX != null && !!setTimesX;
  const signal = pred?.signal;
  const gate = pred?.gate;
  const db = signal?.noise_db;
  return <section className="emg8-card emg8-recognition-gate">
    <header><h3>识别门槛</h3><small>{gate?.unsure ? '这一下把握不够，判放松' : gate?.blocked ? '这一下幅度不够，不算动作' : gate && gate.effective_uv > 0 ? `有效门槛 ${gate.effective_uv} µV` : '门槛是 0，幅度再小也交给模型'}</small></header>
    <p className="emg8-fine">基线 {signal ? `${signal.baseline_uv} µV` : '—'} · 时域噪声 Vpp {signal ? `${signal.vpp_uv} µV` : '—'} · 频域噪声 {db == null ? '—' : `${db} dB`}</p>
    <div className="emg8-form">
      {prob && <label><span>动作阈值</span>
        <input type="range" min={0} max={95} step={5} value={probPct} aria-label="动作阈值（把握度）" onChange={(e) => setProbPct(Number(e.target.value))} /><b>{probPct}%</b>
      </label>}
      {rel ? <label><span>幅度门槛</span>
        <input type="range" min={0} max={10} step={0.5} value={timesX} aria-label="幅度门槛（放松底噪的倍数）" onChange={(e) => setTimesX(Number(e.target.value))} /><b>{timesX ? `${timesX}×` : '不拦'}</b>
      </label> : <label><span>幅度门槛</span>
        <input type="range" min={0} max={5000} step={50} value={thresholdUv} aria-label="幅度门槛" onChange={(e) => setThresholdUv(Number(e.target.value))} /><b>{thresholdUv} µV</b>
      </label>}
      <label><span>灵敏度</span>
        <input type="range" min={1} max={10} step={1} value={sensitivity} aria-label="灵敏度" onChange={(e) => setSensitivity(Number(e.target.value))} /><b>{sensitivity}</b>
      </label>
    </div>
    {prob && <p className="emg8-fine">动作阈值：最像的那一类概率要过这条线才算，不过线判放松（唯理默认 70%）。</p>}
    {rel ? <p className="emg8-fine">{!gate ? '开始识别后显示你的放松底噪和实际门槛。' : gate.rest_ref_uv ? `幅度门槛按你自己的放松底噪算：${timesX}× ${gate.rest_ref_uv} µV，再按灵敏度缩放，实际 ${gate.effective_uv} µV；这一窗峰峰值没过就判放松。` : '这个模型没记放松底噪（训练早于这一版），重新训练后倍数门槛才生效；现在不拦。'}底噪取训练时最新一次佩戴的放松条，换人、重戴后重新训练才会更新。灵敏度 6 保持这个数（5 是 1.2 倍），调高放宽、调低收紧。</p>
      : <p className="emg8-fine">幅度门槛是峰峰值要超过多少才识别。灵敏度 6 保持这个数（5 是 1.2 倍），调高就放宽，调低就收紧。和鼠标快慢不是同一个旋钮。</p>}
  </section>;
}
