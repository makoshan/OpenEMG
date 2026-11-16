'use client';
// 数据台：EMG Studio 新路由（原力手环 host/studio_api.py）的原生界面，EMG_STUDIO_V2_PLAN F2–F6。
// 设备（描述 / 通道名）→ 录制（会话 = 一次佩戴，段 = .h5）→ 数据（质量门、回放、导出 OpenSignals .txt、统计、激活分析）
// → 训练（按会话分三集的数据集、LDA / CNN、冻结）→ 规则（识别概率 → 事件、LSL 输出）。旧采集页的录制照旧，同时写 .h5。
import { useCallback, useEffect, useRef, useState } from 'react';
import type { Result } from '../desktop-bridge';
import type { BringupDecodeResult, C08bRegState, ChannelStats, DevicePinout, EmgAnalysis, Emg8Bridge, FeatureMode, Hand, Rule, StudioConfig, StudioDataset, StudioDevice, StudioEvent, StudioFile, StudioOp, StudioOps, StudioRun, StudioSession, StudioTake, TrainJob } from './contract';
import { CH_COLORS, pct } from './contract';
import { dataReadout } from './readout';
import { grayTitle } from './gray-title';

export type WorkbenchSub = 'device' | 'record' | 'data' | 'train' | 'rules';
const SUBS: [WorkbenchSub, string][] = [['device', '设备'], ['record', '录制'], ['data', '数据'], ['train', '训练'], ['rules', '规则']];
const WRITES = new Set<StudioOp>(['deviceConfigPut', 'c08bReg', 'sessionStart', 'sessionStop', 'takeStart', 'takeStop', 'datasetSave', 'trainStart', 'trainFreeze', 'gestureGate', 'gestureFewshot', 'gestureDump']);
type Call = <K extends StudioOp>(op: K, a?: StudioOps[K][0]) => Promise<StudioOps[K][1] | null>;

export function Workbench({ projectId, bridge, hand, donning, placement, initialSub = 'record', onSubChange }: {
  projectId: string; bridge: Emg8Bridge | undefined; hand: Hand; donning: number; placement: string;
  initialSub?: WorkbenchSub; onSubChange?: (s: WorkbenchSub) => void;
}) {
  const [sub, setSub] = useState<WorkbenchSub>(initialSub);
  useEffect(() => { setSub(initialSub); }, [initialSub]);
  const pickSub = (next: WorkbenchSub) => { setSub(next); onSubChange?.(next); };
  const [err, setErr] = useState('');
  const [dev, setDev] = useState<StudioDevice | null>(null);
  const [gates, setGates] = useState<StudioEvent[]>([]);
  const [tick, setTick] = useState(0);
  const call: Call = useCallback(async (op, a) => {
    if (!bridge?.studio) { setErr('数据台只在桌面 App 里可用'); return null; }
    const r = await bridge.studio(projectId, op, a) as Result<StudioOps[typeof op][1]>;
    if (!r.ok) { setErr(r.message); return null; }
    setErr('');
    if (WRITES.has(op)) { const d = await bridge.studio(projectId, 'deviceState'); if (d.ok) setDev(d.value); setTick((n) => n + 1); }
    return r.value;
  }, [bridge, projectId]);
  useEffect(() => {
    let live = true;
    const poll = async () => { const d = await call('deviceState'); if (live && d) setDev(d); };
    void poll(); const t = setInterval(() => { void poll(); setTick((n) => n + 1); }, 1500);
    return () => { live = false; clearInterval(t); };
  }, [call]);
  useEffect(() => bridge?.onEvent((e) => {
    if (e.type === 'batch' && e.studio?.length) setGates((g) => [...e.studio!.filter((x) => x.type === 'gate').reverse(), ...g].slice(0, 40));
  }), [bridge]);
  const page = () => {
    switch (sub) {
      case 'device': return <DevicePage call={call} dev={dev} />;
      case 'record': return <RecordPage call={call} dev={dev} gates={gates} hand={hand} donning={donning} placement={placement} />;
      case 'data': return <DataPage call={call} dev={dev} tick={tick} />;
      case 'train': return <TrainPage call={call} tick={tick} />;
      case 'rules': return <RulesPage call={call} />;
      default: { const never: never = sub; return never; }
    }
  };
  return <div className="emg8-control">
    <section className="emg8-card emg8-control-head">
      <div><h3>数据台</h3><small>{dev ? `${dev.name} · ${dev.fs_Hz} Hz × ${dev.n_channels} 路 · ${dev.session ? `会话 ${dev.session}` : '没有进行中的会话'}${dev.recording ? ' · 录制中' : ''}` : '读取设备…'}</small></div>
      <nav className="emg8-tabs" aria-label="数据台页面">{SUBS.map(([k, t]) => <button key={k} aria-pressed={sub === k} onClick={() => pickSub(k)}>{t}</button>)}</nav>
    </section>
    {err && <p className="emg8-warn" role="alert">{err}</p>}
    {page()}
  </div>;
}

const GatePill = ({ ok, why }: { ok: boolean; why?: string }) => <span className={ok ? 'emg8-gate ok' : 'emg8-gate bad'} title={why}>{ok ? '过' : why || '未过'}</span>;

function ReadoutCard({ fsHz }: { fsHz: number | undefined }) {
  if (!fsHz) return null;
  return <section className="emg8-card emg8-span-2"><header><h4>这份数据怎么读</h4></header>
    <ol className="emg8-gates">{dataReadout(fsHz).map((line) => <li key={line}>{line}</li>)}</ol></section>;
}

const FS_OPTIONS: (500 | 1000 | 2000)[] = [500, 1000, 2000];

function C08bTuneCard({ call, dev }: { call: Call; dev: StudioDevice }) {
  const [regSt, setRegSt] = useState<C08bRegState | null>(null);
  const [chip, setChip] = useState<'u1' | 'u2' | 'both'>(dev.n_channels === 16 ? 'both' : 'u1');
  const [addr, setAddr] = useState<number>(dev.n_channels === 2 ? 0x04 : 0x05);
  const [valHex, setValHex] = useState('0x00');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const defChip = dev.n_channels === 16 ? 'both' : 'u1';
    const defAddr = dev.n_channels === 2 ? 0x04 : 0x05;
    setChip(defChip);
    setAddr(defAddr);
    void call('c08bReg', { op: 'state' }).then((s) => { if (s) setRegSt(s); });
  }, [call, dev.device_id, dev.n_channels, dev.fs_Hz]);

  const switchFs = async (fs: 500 | 1000 | 2000) => {
    if (fs === dev.fs_Hz || busy) return;
    setBusy(true);
    try {
      await call('deviceConfigPut', { fsHz: fs });
      const s = await call('c08bReg', { op: 'state' });
      if (s) setRegSt(s);
    } finally {
      setBusy(false);
    }
  };

  const doReg = async (op: 'rreg' | 'wreg' | 'clro', overrideVal?: string) => {
    if (busy) return;
    setBusy(true);
    try {
      const v = overrideVal ?? valHex;
      if (overrideVal) setValHex(overrideVal);
      const res = await call('c08bReg', op === 'clro' ? { op } : op === 'rreg' ? { op, chip, addr } : { op, chip, addr, val: v });
      if (res) setRegSt(res);
    } finally {
      setBusy(false);
    }
  };

  const curItem = regSt?.catalog.find((x) => x.addr === addr);
  const isChReg = regSt?.afe === 'ADS1292' ? (addr === 0x04 || addr === 0x05) : (addr >= 0x05 && addr <= 0x0C);
  const lr = regSt?.last_reg;

  return <section className="emg8-card emg8-span-2" aria-label="C08B 采样率与安全寄存器调参">
    <header>
      <div>
        <h4>采样率切换与安全寄存器调参 · c08b-stream</h4>
        <small>{regSt ? `${regSt.afe} · 已生效覆盖 ${regSt.reg_overrides} 项 · ${regSt.shadow_mode ? '合成影子演练（双硬件锁关闭）' : '离体台架模式'}` : '读取寄存器目录…'}</small>
      </div>
      <div className="emg8-row tight" role="group" aria-label="C08B 采样率档位">
        <span className="emg8-fine" style={{ margin: 0 }}>采样率：</span>
        {FS_OPTIONS.map((fs) => (
          <button
            key={fs}
            type="button"
            className={dev.fs_Hz === fs ? 'emg8-primary' : undefined}
            aria-pressed={dev.fs_Hz === fs}
            disabled={busy || !!dev.recording}
            title={grayTitle(!!dev.recording && '录制进行中不能切换采样率')}
            onClick={() => { void switchFs(fs); }}
          >
            {fs} Hz
          </button>
        ))}
      </div>
    </header>

    <div className="emg8-row tight" style={{ flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
      <label className="emg8-inline">芯片{' '}
        <select value={chip} disabled={dev.n_channels !== 16} onChange={(e) => setChip(e.target.value as 'u1' | 'u2' | 'both')}>
          {dev.n_channels === 16 && <option value="both">双片 U1+U2</option>}
          <option value="u1">主片 U1</option>
          {dev.n_channels === 16 && <option value="u2">副片 U2</option>}
        </select>
      </label>
      <label className="emg8-inline">寄存器{' '}
        <select value={addr} onChange={(e) => {
          const nextA = Number(e.target.value);
          setAddr(nextA);
          const found = regSt?.catalog.find((c) => c.addr === nextA);
          if (found) setValHex(found.default_hex);
        }}>
          {(regSt?.catalog ?? []).map((it) => (
            <option key={it.addr} value={it.addr}>
              {it.addr_hex} {it.name}{it.read_only ? ' [只读]' : ` (默认 ${it.default_hex})`}
            </option>
          ))}
        </select>
      </label>
      <label className="emg8-inline">写入值{' '}
        <input
          value={valHex}
          maxLength={6}
          style={{ width: 82 }}
          aria-label="寄存器十六进制值"
          disabled={!!curItem?.read_only}
          onChange={(e) => setValHex(e.target.value)}
        />
      </label>
      <button type="button" disabled={busy} onClick={() => { void doReg('rreg'); }}>读 (RREG)</button>
      <button
        type="button"
        className="emg8-primary"
        disabled={busy || !!dev.recording || !!curItem?.read_only}
        title={grayTitle(!!dev.recording && '录制进行中禁止写寄存器', !!curItem?.read_only && '该地址为只读寄存器')}
        onClick={() => { void doReg('wreg'); }}
      >
        安全写核 (WREG)
      </button>
      <button
        type="button"
        disabled={busy || !!dev.recording || !regSt?.reg_overrides}
        title={grayTitle(!regSt?.reg_overrides && '当前无寄存器覆盖项')}
        onClick={() => { void doReg('clro'); }}
      >
        清空覆盖 (CLRO)
      </button>
    </div>

    {isChReg && <div className="emg8-row tight" style={{ flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
      <span className="emg8-fine" style={{ margin: 0 }}>通道快捷安全预设：</span>
      <button type="button" disabled={busy || !!dev.recording} onClick={() => { void doReg('wreg', '0x00'); }}>PGA=6 正常输入 (0x00)</button>
      <button type="button" disabled={busy || !!dev.recording} onClick={() => { void doReg('wreg', '0x01'); }}>输入内部短接测底噪 (0x01)</button>
      <button type="button" disabled={busy || !!dev.recording} onClick={() => { void doReg('wreg', '0x60'); }}>PGA=12 高增益 (0x60)</button>
    </div>}

    {curItem?.hint && <p className="emg8-fine" style={{ marginTop: 6 }}>规则提示：{curItem.hint}</p>}

    {lr && <div className="emg8-report97-meta" style={{ marginTop: 6 }} aria-label="最近一次寄存器读写回执">
      <span>序号 <b>#{lr.seq}</b></span>
      <span>目标 <b>{lr.chip.toUpperCase()} · {lr.addr_name} ({lr.addr_hex})</b></span>
      <span>U1 读回 <b>{lr.u1_hex}</b></span>
      {dev.n_channels === 16 && <span>U2 读回 <b>{lr.u2_hex}</b></span>}
      {lr.verify_mask_hex && <span>校验掩码 <b>{lr.verify_mask_hex}</b></span>}
      <span>下行帧 <code>{lr.cmd_hex}</code></span>
    </div>}

    {regSt && Object.keys(regSt.overrides).length > 0 && (
      <p className="emg8-fine" style={{ marginTop: 4 }}>
        当前覆盖项：{Object.entries(regSt.overrides).map(([k, v]) => `${k}=${v}`).join(' · ')}
      </p>
    )}
    {regSt?.note && <p className="emg8-fine" style={{ marginTop: 4 }}>{regSt.note}</p>}
  </section>;
}

function DevicePage({ call, dev }: { call: Call; dev: StudioDevice | null }) {
  const [cfg, setCfg] = useState<StudioConfig | null>(null);
  const [names, setNames] = useState<string[]>([]);
  const [editingNames, setEditingNames] = useState(false);
  const [savedToast, setSavedToast] = useState(false);
  const [pinout, setPinout] = useState<DevicePinout | null>(null);
  const [pinFilter, setPinFilter] = useState('');
  const [hexIn, setHexIn] = useState('');
  const [bringup, setBringup] = useState<BringupDecodeResult | null>(null);
  useEffect(() => {
    void call('deviceConfig').then((c) => { if (c) { setCfg(c); setNames(c.channels.map((x) => x.label)); } });
    void call('devicePinout').then((p) => { if (p) setPinout(p); });
  }, [call, dev?.device_id]);
  const save = async () => {
    const c = await call('deviceConfigPut', { channels: names.map((label, index) => ({ index, label })) });
    if (c) { setCfg(c); setSavedToast(true); setTimeout(() => setSavedToast(false), 1800); }
  };
  const runDecode = async (sample?: '16ch' | '8ch' | '2ch' | 'report16') => {
    const r = await call('bringupDecode', sample ? { sample } : { hex: hexIn });
    if (r) { setBringup(r); if (r.input_hex) setHexIn(r.input_hex); }
  };
  const q = pinFilter.trim().toLowerCase();
  const filteredRows = pinout?.rows.filter((r) => !q || `ch${r.ch} ${r.connector} ${r.esd} ${r.filter} ${r.adc_pin} ${r.zone}`.toLowerCase().includes(q)) ?? [];
  return <div className="emg8-control-grid">
    <section className="emg8-card"><header><h4>设备与安全门锁</h4><span className="emg8-fine">{dev?.device_id}</span></header>
      {dev ? <table className="emg8-table"><tbody>
        <tr><td>名称</td><td><b>{dev.name}</b></td></tr>
        <tr><td>连接</td><td>{dev.rig.streaming ? '在线' : dev.state} · {dev.rig.banner.replace(/ @ .*/, '')}</td></tr>
        <tr><td>采样</td><td>{dev.fs_Hz} Hz × {dev.n_channels} 路 · 丢帧 {dev.dropped}</td></tr>
        <tr><td>能力</td><td>{Object.entries(dev.capabilities).filter(([, v]) => v).map(([k]) => k).join(' · ') || '只读预览'}</td></tr>
        <tr><td>安全门锁</td><td><span className={dev.capabilities.record ? 'emg8-gate ok' : 'emg8-gate bad'}>{dev.capabilities.record ? '已开启录制' : '默认锁定（record=false，需离体台架实测后解锁）'}</span></td></tr>
      </tbody></table> : <p className="emg8-fine">读取中…</p>}
      {pinout?.notes && <p className="emg8-fine">{pinout.notes}</p>}
      <div className="emg8-ch-collapse">
        <div className="emg8-row tight" style={{ justifyContent: 'space-between', marginTop: 8 }}>
          <span className="emg8-fine" style={{ margin: 0 }}>通道名（{names.length} 路）：{names.slice(0, 6).join(' · ')}{names.length > 6 ? ` … CH${names.length}` : ''}{savedToast ? ' · 已保存' : ''}</span>
          <div className="emg8-row tight">
            {editingNames && <button className="emg8-primary" onClick={() => { void save(); }} disabled={!cfg} title={grayTitle(!cfg && '通道表还在读')}>保存通道名</button>}
            <button type="button" onClick={() => setEditingNames((v) => !v)}>{editingNames ? '收起通道名' : '展开改名'}</button>
          </div>
        </div>
        {editingNames && <div className="emg8-form emg8-ch-grid" style={{ marginTop: 8 }}>{names.map((n, i) => <label key={i}><span style={{ color: CH_COLORS[i % CH_COLORS.length] }}>CH{i + 1} · {cfg?.channels[i]?.sensor}</span>
          <input value={n} maxLength={24} onChange={(e) => setNames(names.map((x, j) => (j === i ? e.target.value : x)))} /></label>)}</div>}
      </div>
    </section>

    <section className="emg8-card"><header><h4>首板上电自检解码 · c08b-bringup</h4>
      <div className="emg8-row tight">
        <button onClick={() => { void runDecode('16ch'); }}>示例 16CH</button>
        <button onClick={() => { void runDecode('8ch'); }}>示例 8CH</button>
        <button onClick={() => { void runDecode('2ch'); }}>示例 2CH</button>
        <button onClick={() => { void runDecode('report16'); }}>示例 97B 详报</button>
      </div></header>
      <div className="emg8-row tight" style={{ marginBottom: 8 }}>
        <input style={{ flex: 1, minWidth: 200 }} aria-label="上电自检十六进制输入" value={hexIn} placeholder="粘贴 10B / 12B / 31B BLE 0xFFFF 广播或 97B SWD 内存报告 HEX" onChange={(e) => setHexIn(e.target.value)} />
        <button className="emg8-primary" disabled={!hexIn.trim()} onClick={() => { void runDecode(); }}>解码十项自检</button>
        {bringup && <button type="button" onClick={() => { setBringup(null); setHexIn(''); }}>清空</button>}
      </div>
      {bringup ? <>
        <p className={bringup.verdict === 'PASS' && !bringup.safety_alerts?.length ? 'emg8-ok' : 'emg8-warn'} style={{ marginTop: 4 }}>
          <b>{bringup.verdict}</b> · {bringup.afe_mode_label} · {bringup.led_pattern} · done={bringup.done_mask_hex}/{bringup.expected_done_hex} · fail={bringup.fail_mask_hex}
          {bringup.vbat_mv_approx ? ` · VBAT≈${bringup.vbat_mv_approx} mV` : ''}
          {bringup.crc_hex ? ` · CRC=${bringup.crc_hex}` : ''}
        </p>
        {bringup.source === 'l432_report_97B' && <div className="emg8-report97-meta">
          <span>DRDY 实测 <b>{bringup.drdy_rate_hz ?? '—'} Hz</b></span>
          <span>双片失步 <b>{bringup.drdy_desync_frames ?? 0} 帧</b></span>
          <span>状态字错 <b>{bringup.bad_status_frames ?? 0} 帧</b></span>
          {bringup.imu && <span>IMU {bringup.imu.who_am_i_hex} <b>{bringup.imu.norm_g} g</b></span>}
        </div>}
        {bringup.safety_alerts?.map((a) => <p key={a} className="emg8-warn">{a}</p>)}
        {bringup.notes?.map((n) => <p key={n} className="emg8-fine">{n}</p>)}
        <div className="emg8-row tight" style={{ flexWrap: 'wrap', gap: 5, marginTop: 6 }}>{bringup.items.map((it) => <span key={it.name} className={it.state === 'PASS' ? 'emg8-gate ok' : it.state === 'SKIP' ? 'emg8-fine' : 'emg8-gate bad'}>{it.name}:{it.state}</span>)}</div>
        {bringup.channels && bringup.channels.length > 0 && <div className="emg8-report97-grid" aria-label="97B 逐通道方波与短接底噪">
          {bringup.channels.map((ch) => {
            const sigOk = ch.sig_pp_uv >= 500 && ch.sig_pp_uv <= 5000;
            const noiseOk = ch.noise_rms_nv >= 100 && ch.noise_rms_nv < 5000;
            const ok = sigOk && noiseOk;
            return <div key={ch.ch} className={ok ? 'emg8-ch-cell' : 'emg8-ch-cell bad'}>
              <b style={{ color: CH_COLORS[(ch.ch - 1) % CH_COLORS.length] }}>CH{ch.ch}</b>
              <span>{ch.sig_pp_uv} µVpp · {(ch.noise_rms_nv / 1000).toFixed(2)} µVrms</span>
            </div>;
          })}
        </div>}
      </> : <p className="emg8-fine">首板不焊串口也能对表：贴入手机 nRF Connect 扫到的 0xFFFF 广播串或 SWD 读出的 97B `g_report` 即可离线判读 10 项指标。</p>}
    </section>

    {dev?.device_id?.startsWith('c08b-') && <C08bTuneCard call={call} dev={dev} />}

    {pinout && <section className="emg8-card emg8-span-2"><header>
      <div><h4>硬件通道与座子脚位对线表</h4><small>{pinout.board} · {pinout.interlock}</small></div>
      <div className="emg8-row tight" style={{ flexWrap: 'nowrap', flexShrink: 0 }}>
        <input value={pinFilter} aria-label="筛选通道或脚位" placeholder="搜 CH / FPC / ESD / ADC…" onChange={(e) => setPinFilter(e.target.value)} style={{ width: 210 }} />
        <span className="emg8-spec-badge" style={{ whiteSpace: 'nowrap' }}>{filteredRows.length} / {pinout.rows.length} 路</span>
      </div></header>
      <div style={{ maxHeight: 220, overflow: 'auto' }}>
        <table className="emg8-table"><thead><tr><th>通道</th><th>连接器脚位</th><th>ESD 保护</th><th>RC / 阻排</th><th>ADC 引脚</th><th>分区</th></tr></thead><tbody>
          {filteredRows.map((r) => <tr key={r.ch}><td style={{ color: CH_COLORS[(r.ch - 1) % CH_COLORS.length] }}><b>CH{r.ch}</b></td><td>{r.connector}</td><td>{r.esd}</td><td>{r.filter}</td><td>{r.adc_pin}</td><td>{r.zone}</td></tr>)}
          {!filteredRows.length && <tr><td colSpan={6} className="emg8-fine">没有匹配「{pinFilter}」的通道或器件。</td></tr>}
        </tbody></table>
      </div>
      <p className="emg8-fine">{pinout.aux_pins}</p></section>}
    <ReadoutCard fsHz={dev?.fs_Hz} />
  </div>;
}

function RecordPage({ call, dev, gates, hand, donning, placement }: { call: Call; dev: StudioDevice | null; gates: StudioEvent[]; hand: Hand; donning: number; placement: string }) {
  const [subject, setSubject] = useState('S01');
  const [wear, setWear] = useState(donning);
  const [label, setLabel] = useState('rest');
  const [seconds, setSeconds] = useState('2');
  useEffect(() => { setWear(donning); }, [donning]);
  const canRecord = !!dev?.capabilities.record;
  return <div className="emg8-control-grid">
    <section className="emg8-card"><header><h4>会话 · 一次佩戴</h4><span className="emg8-fine">{dev?.session ?? '未开始'}</span></header>
      <div className="emg8-form">
        <label>受试者<input value={subject} maxLength={40} onChange={(e) => setSubject(e.target.value)} /></label>
        <label>第几次佩戴<input type="number" min={1} max={99} value={wear} onChange={(e) => setWear(Number(e.target.value) || 1)} /></label>
        <label className="wide">位置（取自戴好页）<input value={placement} readOnly /></label>
      </div>
      <div className="emg8-row tight">
        <button className="primary" disabled={!canRecord || !!dev?.session} title={grayTitle(!!dev?.session && '会话已经开着', !dev && '设备描述还在读', !canRecord && '这台设备不能录')} onClick={() => { void call('sessionStart', { subject, donning: wear, hand, placement }); }}>开始会话</button>
        <button disabled={!dev?.session} title={grayTitle(!dev?.session && '还没有这次佩戴的会话')} onClick={() => { void call('sessionStop'); }}>结束会话</button>
      </div>
      {!canRecord && dev && <p className="emg8-warn">{dev.device_id} 不能录制（回放或合成协议）。</p>}
      <p className="emg8-fine">摘下重戴 = 结束会话、佩戴号加一再开。数据集按会话分训练 / 验证 / 测试，同一会话不会跨集。</p></section>
    <section className="emg8-card"><header><h4>录一段</h4><span className="emg8-fine">{dev?.recording ? '录制中' : '空闲'}</span></header>
      <div className="emg8-form">
        <label>标签<input value={label} maxLength={40} onChange={(e) => setLabel(e.target.value)} /></label>
        <label>秒数（空 = 手动停）<input type="number" min={0.5} max={600} step={0.5} value={seconds} onChange={(e) => setSeconds(e.target.value)} /></label>
      </div>
      <div className="emg8-row tight">
        <button className="primary" disabled={!dev?.session || dev.recording} title={grayTitle(!dev?.session && '先开始这次佩戴的会话', !!dev?.recording && '这一段还在录')} onClick={() => { void call('takeStart', { label, seconds: seconds ? Number(seconds) : null }); }}>开始录</button>
        <button disabled={!dev?.recording} title={grayTitle(!dev?.recording && '还没开始录这一段')} onClick={() => { void call('takeMark', { label: 'mark' }); }}>打标记</button>
        <button disabled={!dev?.recording} title={grayTitle(!dev?.recording && '还没开始录这一段')} onClick={() => { void call('takeStop'); }}>停</button>
      </div>
      <ol className="emg8-gates">{gates.map((g, i) => <li key={i}>{new Date(g.t * 1000).toLocaleTimeString()} {String(g.take)} <GatePill ok={!!g.ok} why={g.why as string | undefined} />{g.legacy ? <span className="emg8-fine"> 旧采集页同步</span> : null}</li>)}</ol>
      <p className="emg8-fine">点「停」就结束这一段。没有暂停，也没有每 30 秒自动存一段。</p>
    </section>
  </div>;
}

function DataPage({ call, dev, tick }: { call: Call; dev: StudioDevice | null; tick: number }) {
  const [sessions, setSessions] = useState<StudioSession[]>([]);
  const [takes, setTakes] = useState<StudioTake[]>([]);
  const [pick, setPick] = useState('');
  const [open, setOpen] = useState<{ file: string; data: StudioFile } | null>(null);
  const [note, setNote] = useState('');
  const [analysis, setAnalysis] = useState<EmgAnalysis | null>(null);
  const [stats, setStats] = useState<ChannelStats | null>(null);
  useEffect(() => { void call('files', pick ? { session: pick } : undefined).then((f) => { if (f) { setSessions(f.sessions); setTakes(f.takes.slice().reverse()); } }); }, [call, pick, tick]);
  const view = async (t: StudioTake) => {
    const decim = Math.max(1, Math.floor(((dev?.fs_Hz ?? 2000) * (t.seconds || 2)) / 2400));
    const d = await call('fileOpen', { file: t.file, decim }); if (d) { setOpen({ file: t.file, data: d }); setAnalysis(null); }
  };
  return <div className="emg8-col">
    <ReadoutCard fsHz={dev?.fs_Hz} />
    <section className="emg8-card"><header><h4>文件</h4>
      <label className="emg8-inline">会话 <select value={pick} onChange={(e) => setPick(e.target.value)}><option value="">全部（{sessions.length}）</option>{sessions.map((s) => <option key={s.session} value={s.session}>{s.session} · {s.n_takes} 段</option>)}</select></label></header>
      <div style={{ maxHeight: 280, overflow: 'auto' }}><table className="emg8-table"><thead><tr><th>会话</th><th>文件</th><th>标签</th><th>秒</th><th>门</th><th /></tr></thead><tbody>
        {takes.map((t) => <tr key={t.file}><td>{t.session}</td><td>{t.file.split('/').pop()}</td><td>{t.label}</td><td>{t.seconds}</td><td><GatePill ok={t.gate.ok} why={t.gate.why} /></td>
          <td><button onClick={() => { void view(t); }}>看</button> <button onClick={() => { void call('exportTxt', { file: t.file }).then((r) => r && setNote(`已导出 ${r.name}，App 会在访达里选中它`)); }}>导出 .txt</button></td></tr>)}
        {!takes.length && <tr><td colSpan={6} className="emg8-fine">还没有 .h5 段。录制页或旧采集页录一条就会出现。</td></tr>}
      </tbody></table></div>
      {note && <p className="emg8-ok">{note}</p>}</section>
    {open && <section className="emg8-card"><header><h4>回放 · {open.file}</h4>
      <div className="emg8-row tight"><button onClick={() => { void call('emgAnalysis', { file: open.file }).then((r) => r && setAnalysis(r)); }}>激活分析</button></div></header>
      <Plot rows={open.data.uv} events={open.data.events} fs={(open.data.header['sampling rate'] || 2000) / open.data.decim} labels={open.data.header.label} />
      {analysis && <table className="emg8-table"><thead><tr><th>通道</th><th>激活段</th><th>阈值 µV</th><th>各段起止 s</th></tr></thead><tbody>
        {analysis.channels.map((c) => <tr key={c.label}><td>{c.label}</td><td>{c.n_activations}</td><td>{c.threshold_uv.toFixed(1)}</td><td>{c.activations.map((a) => `${a.start_s}–${a.end_s}`).join('，') || '—'}</td></tr>)}</tbody></table>}
      {analysis && <p className="emg8-fine">阈值 = 本段包络峰值的固定百分比（无 MVC 文件时）；CSV 已写到导出目录：{analysis.csv}。</p>}</section>}
    <section className="emg8-card"><header><h4>实时统计 · 最近 1 秒</h4><button onClick={() => { void call('stats', { windowS: 1 }).then((s) => s && setStats(s)); }}>刷新</button></header>
      {stats ? <table className="emg8-table"><thead><tr><th>通道</th><th>RMS</th><th>均值</th><th>中位</th><th>最小</th><th>最大</th></tr></thead><tbody>
        {stats.channels.map((c, i) => <tr key={i}><td style={{ color: CH_COLORS[i % CH_COLORS.length] }}>{c.label}</td><td>{c.rms.toFixed(1)}</td><td>{c.mean.toFixed(1)}</td><td>{c.median.toFixed(1)}</td><td>{c.min.toFixed(0)}</td><td>{c.max.toFixed(0)}</td></tr>)}</tbody></table>
        : <p className="emg8-fine">单位 µV，未滤波；点刷新读服务端最近 1 秒缓冲。</p>}</section>
  </div>;
}

function Plot({ rows, events, fs, labels }: { rows: number[][]; events: [number, string, string][]; fs: number; labels?: string[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [range, setRange] = useState(500);
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const dpr = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight; c.width = w * dpr; c.height = h * dpr;
    const g = c.getContext('2d'); if (!g) return; g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
    const ch = rows[0]?.length ?? 0, lane = h / Math.max(ch, 1);
    for (let k = 0; k < ch; k++) {
      const y0 = lane * (k + 0.5), mean = rows.reduce((s, r) => s + r[k], 0) / rows.length;
      g.strokeStyle = CH_COLORS[k % CH_COLORS.length]; g.beginPath();
      rows.forEach((r, i) => { const x = (i / Math.max(rows.length - 1, 1)) * w, y = y0 - Math.max(-1, Math.min(1, (r[k] - mean) / range)) * lane / 2; if (i) g.lineTo(x, y); else g.moveTo(x, y); });
      g.stroke(); g.fillStyle = CH_COLORS[k % CH_COLORS.length]; g.font = '11px sans-serif'; g.fillText(labels?.[k] ?? `CH${k + 1}`, 4, lane * k + 12);
    }
    g.fillStyle = '#EF4444';
    for (const [t, l] of events) { const x = (t * fs / rows.length) * w; g.fillRect(x, 0, 1, h); g.fillText(l, x + 3, h - 4); }
  }, [rows, events, fs, labels, range]);
  return <div><label className="emg8-inline">量程 <select value={range} onChange={(e) => setRange(Number(e.target.value))}>{[100, 500, 2000].map((v) => <option key={v} value={v}>±{v} µV</option>)}</select></label>
    <canvas ref={ref} style={{ width: '100%', height: 280, display: 'block' }} aria-label={`${rows[0]?.length ?? 0} 路回放波形`} /></div>;
}

function TrainPage({ call, tick }: { call: Call; tick: number }) {
  const [datasets, setDatasets] = useState<StudioDataset[]>([]);
  const [name, setName] = useState('studio-v1');
  const [pick, setPick] = useState('');
  const [trainer, setTrainer] = useState<'lda' | 'cnn'>('lda');
  const [mode, setMode] = useState<FeatureMode>('bands5');
  const [gateUv, setGateUv] = useState(0);
  const [pipeNote, setPipeNote] = useState('');
  const [rejected, setRejected] = useState<{ file: string; why: string }[]>([]);
  const [runs, setRuns] = useState<StudioRun[]>([]);
  const [job, setJob] = useState<TrainJob | null>(null);
  const [prod, setProd] = useState<{ run_id: string; frozen: string } | null>(null);
  const loadDs = useCallback(async () => { const d = await call('datasets'); if (d) { setDatasets(d.datasets); setPick((p) => p || d.datasets[0]?.name || ''); } }, [call]);
  useEffect(() => { void loadDs(); }, [loadDs]);
  useEffect(() => { void call('trainRuns').then((r) => { if (r) { setRuns(r.runs.slice().reverse()); setJob(r.job); setProd(r.production); } }); }, [call, tick]);
  const ds = datasets.find((d) => d.name === pick);
  return <div className="emg8-control-grid">
    <section className="emg8-card"><header><h4>数据集 · 按会话分三集</h4></header>
      <div className="emg8-row tight"><input value={name} maxLength={60} onChange={(e) => setName(e.target.value)} aria-label="数据集名" />
        <button onClick={() => { void call('datasetSave', { name }).then((r) => { if (r) { setRejected(r.rejected); setPick(name); void loadDs(); } }); }}>生成 / 覆盖</button></div>
      <label className="emg8-inline" style={{ marginTop: 8 }}>选择 <select value={pick} onChange={(e) => setPick(e.target.value)}>{datasets.map((d) => <option key={d.name}>{d.name}</option>)}</select></label>
      {ds && <table className="emg8-table"><thead><tr><th>集</th><th>会话</th><th>各类段数</th></tr></thead><tbody>
        {(['train', 'validation', 'test'] as const).map((s) => <tr key={s}><td>{{ train: '训练', validation: '验证', test: '测试' }[s]}</td><td>{ds.summary.sessions[s].join('、') || '—'}</td>
          <td>{Object.entries(ds.summary[s]).map(([k, v]) => `${k} ${v}`).join(' · ') || '—'}</td></tr>)}</tbody></table>}
      {ds && !ds.summary.sessions.test.length && <p className="emg8-warn">没有独立测试会话：至少再录一次摘下重戴的会话，测试分数才有意义。</p>}
      {ds && (['validation', 'test'] as const).map((s) => [s, Object.keys(ds.summary.train).filter((k) => !ds.summary[s][k])] as const).filter(([s, miss]) => miss.length && ds.summary.sessions[s].length)
        .map(([s, miss]) => <p key={s} className="emg8-warn">{s === 'test' ? '测试' : '验证'}集缺 {miss.join('、')}：这个会话里每类都录几段，分数才可比。</p>)}
      {!!rejected.length && <p className="emg8-fine">剔除 {rejected.length} 段：{rejected.slice(0, 4).map((r) => r.why).join('；')}</p>}</section>
    <section className="emg8-card"><header><h4>训练</h4><span className="emg8-fine">{job?.state === 'running' ? `训练中 · ${job.trainer} · ${job.dataset}` : job?.state === 'error' ? `出错：${job.error}` : ''}</span></header>
      <div className="emg8-row tight"><select value={trainer} onChange={(e) => setTrainer(e.target.value as 'lda' | 'cnn')} aria-label="训练器"><option value="lda">LDA 基线</option><option value="cnn">CNN</option></select>
        <select value={mode} onChange={(e) => setMode(e.target.value as FeatureMode)} aria-label="特征"><option value="bands5">5 频段（默认）</option><option value="hudgins">时域 48 维</option><option value="combined">组合 88 维</option></select>
        <button className="primary" disabled={!pick || job?.state === 'running' || (trainer === 'cnn' && mode !== 'bands5')} title={grayTitle(!pick && '先选一个数据集', trainer === 'cnn' && mode !== 'bands5' && 'CNN 目前只用 5 频段')} onClick={() => { void call('trainStart', { dataset: pick, trainer, featureMode: mode }); }}>训练</button></div>
      <div className="emg8-row tight">
        <input type="number" min={0} max={5000} value={gateUv} aria-label="能量门微伏" onChange={(e) => setGateUv(Number(e.target.value))} />
        <button onClick={() => { void call('gestureGate', { minRmsUv: gateUv, restLabel: 'rest' }).then((r) => r && setPipeNote(r.min_rms_uv > 0 ? `能量门 ${r.min_rms_uv} µV，低于此值改判 ${r.rest_label}` : '能量门关闭')); }}>设置能量门</button>
        <button disabled={!pick} title={grayTitle(!pick && '先选一个数据集')} onClick={() => { void call('gestureFewshot', { dataset: pick, featureMode: mode, k: 1 }).then((r) => r && setPipeNote(`少样本 ${r.id} · 校准 ${r.n_calib} 条`)); }}>少样本校准</button>
        <button onClick={() => { void call('gestureDump').then((r) => r && setPipeNote(`已导出 ${r.name} · ${r.samples} 点`)); }}>导出 30 秒</button>
      </div>
      {pipeNote && <p className="emg8-fine">{pipeNote}。0 µV 表示不改现有识别。</p>}
      <table className="emg8-table"><thead><tr><th>run</th><th>训练器</th><th>数据集</th><th>训练</th><th>验证</th><th>测试</th><th /></tr></thead><tbody>
        {runs.map((r) => <tr key={r.id}><td>{r.id}{prod?.run_id === r.id ? ' · 生产' : ''}</td><td>{r.trainer}</td><td title={r.dataset.fingerprint}>{r.dataset.name}</td>
          <td>{pct(r.metrics.train)}</td><td>{pct(r.metrics.validation)}</td><td>{r.metrics.test == null ? '无独立测试' : pct(r.metrics.test)}</td>
          <td><button disabled={prod?.run_id === r.id} title={grayTitle(prod?.run_id === r.id && '这一条已经是冻结的生产模型')} onClick={() => { void call('trainFreeze', { runId: r.id }); }}>冻结</button></td></tr>)}
        {!runs.length && <tr><td colSpan={7} className="emg8-fine">还没有训练记录</td></tr>}</tbody></table>
      <p className="emg8-fine">分数是按类平衡准确率。冻结写 models/production.json；「③ 识别」页仍用旧流程模型，切换到新模型待接入。</p></section>
  </div>;
}

function RulesPage({ call }: { call: Call }) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [events, setEvents] = useState<StudioEvent[]>([]);
  const [lsl, setLsl] = useState<{ enabled: boolean; why?: string; stream_name?: string }>({ enabled: false });
  const load = useCallback(async () => { const r = await call('rules'); if (r) { setRules(r.rules); setEvents(r.events.slice().reverse()); } }, [call]);
  useEffect(() => { void load(); const t = setInterval(() => { void load(); }, 2000); return () => clearInterval(t); }, [load]);
  const edit = (i: number, patch: Partial<Rule>) => setRules(rules.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return <div className="emg8-control-grid">
    <section className="emg8-card"><header><h4>规则 · 识别 → 事件</h4>
      <div className="emg8-row tight"><button onClick={() => setRules([...rules, { id: `r${rules.length + 1}`, label: 'pinch', threshold: 0.8, hold_ms: 300, cooldown_ms: 1000, action: { type: 'log' } }])}>加一条</button>
        <button className="primary" onClick={() => { void call('rulesPut', { rules }).then((r) => r && setRules(r.rules)); }}>保存</button></div></header>
      <table className="emg8-table"><thead><tr><th>id</th><th>类别</th><th>概率 ≥</th><th>保持 ms</th><th>冷却 ms</th><th>动作</th><th /></tr></thead><tbody>
        {rules.map((r, i) => <tr key={i}><td><input value={r.id} size={5} onChange={(e) => edit(i, { id: e.target.value })} /></td><td><input value={r.label} size={8} onChange={(e) => edit(i, { label: e.target.value })} /></td>
          <td><input type="number" step={0.05} min={0.05} max={1} value={r.threshold} onChange={(e) => edit(i, { threshold: Number(e.target.value) })} /></td>
          <td><input type="number" min={0} value={r.hold_ms} onChange={(e) => edit(i, { hold_ms: Number(e.target.value) })} /></td>
          <td><input type="number" min={0} value={r.cooldown_ms} onChange={(e) => edit(i, { cooldown_ms: Number(e.target.value) })} /></td>
          <td><select value={r.action.type} onChange={(e) => edit(i, { action: { type: e.target.value as Rule['action']['type'] } })}><option value="log">记录</option><option value="key">按键</option><option value="osc">OSC</option></select></td>
          <td><button onClick={() => setRules(rules.filter((_, j) => j !== i))}>删</button></td></tr>)}
        {!rules.length && <tr><td colSpan={7} className="emg8-fine">没有规则。要先在「③ 识别」页开启实时识别，规则才有输入。</td></tr>}</tbody></table>
      <p className="emg8-fine">引擎只产生事件，不发键盘、不发网络；「按键 / OSC」是给订阅者的标记，执行端待接入。</p></section>
    <section className="emg8-card"><header><h4>事件与输出</h4>
      <label className="emg8-inline"><input type="checkbox" checked={lsl.enabled} onChange={(e) => { void call('lsl', { enabled: e.target.checked }).then((r) => r && setLsl(r)); }} /> LSL 输出</label></header>
      {lsl.why && <p className="emg8-warn">LSL 没开：{lsl.why}</p>}{lsl.stream_name && <p className="emg8-ok">LSL 流 {lsl.stream_name}</p>}
      <ol className="emg8-gates">{events.map((e, i) => <li key={i}>{new Date(e.t * 1000).toLocaleTimeString()} {String(e.rule_id)} · {String(e.label)} · p={String(e.p)}</li>)}</ol>
      {!events.length && <p className="emg8-fine">还没有触发过。</p>}</section>
  </div>;
}
