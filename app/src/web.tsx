// 网页版：Chrome / Edge 用 Web Serial 直连唯理腕带的 USB 接收器，看八路波形。
// 不经过 Python 服务；解码与 host/wl8.py 逐帧一致（npm run check）。
// 录制：选动作 → 倒数 3 秒 → 截满 2 秒（4000 帧 EMG）的串口原始字节 → 同意过就立刻传到平台（webcloud.ts）。
import { useEffect, useRef, useState } from 'react';
import { ElectrodeRing } from './emg8/ring';
import { DisplayFilter, Rms } from './emg8/signal';
import { Waveform, type WaveHandle } from './emg8/wave';
import { BAUD, EMG_HZ, FRAME, RECEIVERS, decode, dropped } from './wl8';
import { CONSENT_TITLE, CONSENT_VERSION } from './consent';
import { ConsentText } from './cloud';
import { consent, loadSaved, revoke, uploadTake } from './webcloud';
import './emg8/emg8.css';
import './emg8/instrument.css';

// Web Serial 的类型 TS 自带库里没有，只声明用到的几样
type Port = { addEventListener(t: 'disconnect', f: () => void, o?: { once: boolean }): void; open(o: { baudRate: number; bufferSize?: number }): Promise<void>; close(): Promise<void>; readable: ReadableStream<Uint8Array> | null };
type Serial = { requestPort(o: { filters: object[] }): Promise<Port> };
const serial = (navigator as unknown as { serial?: Serial }).serial;

type Link = { state: 'idle' | 'opening' | 'live' | 'error'; message?: string };
// AI 选择六类（和 App 的 ai-select 动作组同一套标签），每条 2 秒，和 App 的录音一样长
const LABELS: [string, string][] = [['ai_rest', '放松'], ['ai_summon', '唤起'], ['ai_up', '上滑'], ['ai_down', '下滑'], ['ai_left', '左滑'], ['ai_right', '右滑']];
const TAKE_SECONDS = 2;
type Capture = { parts: Uint8Array[]; frames: number; done: (b: Uint8Array | null) => void };

export function WebCapture() {
  const [link, setLink] = useState<Link>({ state: 'idle' });
  const [hz, setHz] = useState(0), [lost, setLost] = useState(0), [rms, setRms] = useState<number[] | null>(null);
  const [range, setRange] = useState(500);
  const wave = useRef<WaveHandle>(null);
  const port = useRef<Port | null>(null), reader = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const capture = useRef<Capture | null>(null);
  // 截一段原始字节：从现在起攒串口数据，数满 2 秒的 EMG 帧就交出（头尾可能各带半帧，训练端按帧头重新同步）
  // 断开 / 拔线时交出 null：这条作废，录制按钮不会一直卡在「录制中」
  const grab = () => new Promise<Uint8Array | null>((done) => {
    const c: Capture = { parts: [], frames: 0, done };
    capture.current = c;
    // 兜底：数据流停了却没报错（接收器卡住），超时也作废
    setTimeout(() => { if (capture.current === c) { capture.current = null; done(null); } }, (TAKE_SECONDS + 3) * 1000);
  });

  // 先摘掉 port.current 再 cancel：读循环看到不是当前端口就退出，不会在已关闭的流上反复 getReader 空转
  const stop = async () => {
    const p = port.current, r = reader.current;
    port.current = null; reader.current = null;
    capture.current?.done(null); capture.current = null;
    try { await r?.cancel(); } catch { /* 已断开 */ }
    try { await p?.close(); } catch { /* 已关闭 */ }
  };
  useEffect(() => () => { void stop(); }, []);

  const connect = async () => {
    if (!serial) return;
    let p: Port;
    try { p = await serial.requestPort({ filters: RECEIVERS }); } catch { return; }      // 用户在选择框点了取消
    setLink({ state: 'opening' });
    try { await p.open({ baudRate: BAUD, bufferSize: 1 << 16 }); }
    catch (e) { setLink({ state: 'error', message: `打不开串口：${(e as Error).message}。App 或 PrintThings 的肌电页可能正占着它，先关掉再连。` }); return; }
    port.current = p; setLink({ state: 'live' }); setLost(0);
    const filt = new DisplayFilter(50), acc = new Rms(1000);
    let tail = new Uint8Array(0), prev: number | null = null, n = 0, t0 = performance.now(), lostTotal = 0;
    // 只管这个端口被拔：事件挂在端口上（Web Serial 会冒泡到 navigator.serial，挂全局会被别的串口设备误触发）
    p.addEventListener('disconnect', () => { if (port.current !== p) return; void stop(); setLink({ state: 'error', message: '接收器被拔掉了，插回后重新连接' }); setHz(0); }, { once: true });
    while (p.readable && port.current === p) {
      const r = p.readable.getReader(); reader.current = r;
      try {
        for (;;) {
          const { value, done } = await r.read();
          if (done || !value) return;                                 // 被 stop() 取消：结束，不再开新 reader
          const buf = new Uint8Array(tail.length + value.length); buf.set(tail); buf.set(value, tail.length);
          const d = decode(buf); tail = d.tail;
          if (tail.length > 4096) tail = tail.slice(-(FRAME - 1));   // 一直没帧头（波特率错 / 线上全是垃圾）：尾巴不许无限长
          lostTotal += dropped(d.seq, prev); if (d.seq.length) prev = d.seq[d.seq.length - 1];
          if (d.emg.length) {
            const frames = d.emg.map((f) => filt.process(f));
            frames.forEach((f) => acc.push(f)); wave.current?.push(frames); n += frames.length;
          }
          if (d.imu.length) wave.current?.pushGyro(d.imu);
          const c = capture.current;
          if (c) {
            c.parts.push(value); c.frames += d.emg.length;
            if (c.frames >= EMG_HZ * TAKE_SECONDS) {
              const out = new Uint8Array(c.parts.reduce((a, x) => a + x.length, 0)); let at = 0; for (const x of c.parts) { out.set(x, at); at += x.length; }
              capture.current = null; c.done(out);
            }
          }
          const now = performance.now();
          if (now - t0 >= 1000) { setHz(Math.round((n * 1000) / (now - t0))); setRms(acc.values()); setLost(lostTotal); n = 0; t0 = now; }
        }
      } catch (e) {
        // 缓冲溢出、帧错误等可恢复错误：仍在线，换个 reader 接着读；丢的那段不拼进下一段
        if (port.current === p) {
          console.warn('读串口出错，继续读', e); tail = new Uint8Array(0); prev = null;
          capture.current?.done(null); capture.current = null;       // 正在录的这条跨过了数据缺口：作废，不拼
        }
      } finally { r.releaseLock(); }
    }
    // 致命错误后 readable 变 null 而 disconnect 没来：不能停在「在线」
    if (port.current === p) { void stop(); setLink({ state: 'error', message: '串口读不下去了，请重新连接' }); setHz(0); }
  };

  const disconnect = async () => { await stop(); setLink({ state: 'idle' }); setHz(0); setRms(null); };

  if (!serial) return <div className="emg8"><p className="v3-note warn">这个浏览器不能直连串口。请用电脑上的 Chrome 或 Edge 打开；Safari、Firefox 和手机都不行。</p></div>;
  const live = link.state === 'live';
  return <div className="emg8">
    <header style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
      <b style={{ fontSize: 16 }}>OpenEMG · 网页版</b>
      <span>{live ? `在线 · ${hz} Hz · 丢帧 ${lost}` : link.state === 'opening' ? '正在打开串口…' : '未连接'}</span>
      <span style={{ flex: 1 }} />
      <label>量程 <select value={range} onChange={(e) => setRange(Number(e.target.value))}><option value={500}>±500 µV</option><option value={2000}>±2000 µV</option></select></label>
      {live ? <button onClick={disconnect}>断开</button> : <button onClick={connect} disabled={link.state === 'opening'}>连接腕带</button>}
    </header>
    {link.state === 'error' && <p className="v3-note warn">{link.message}</p>}
    {link.state === 'idle' && <p className="v3-note">插上腕带灰白线的白色 USB 头，点「连接腕带」，在弹窗里选 CP2102 或 CH343 那一项。</p>}
    <section className="emg8-signal"><Waveform ref={wave} rangeUv={range} rms={rms ?? undefined} /><ElectrodeRing values={rms} max={range} label="实时 RMS µV" /></section>
    <Recorder live={live} grab={grab} />
  </div>;
}

type Take = { id: string; label: string; donning: number; bytes: Uint8Array; state: 'uploading' | 'ok' | 'retry' | 'rejected' | 'local'; message?: string };

function Recorder({ live, grab }: { live: boolean; grab: () => Promise<Uint8Array | null> }) {
  const [saved, setSaved] = useState(loadSaved), [label, setLabel] = useState(LABELS[0][0]), [donning, setDonning] = useState(1);
  const liveRef = useRef(live); liveRef.current = live;
  const [count, setCount] = useState(0), [busy, setBusy] = useState(false), [takes, setTakes] = useState<Take[]>([]), [err, setErr] = useState('');
  const patch = (id: string, t: Partial<Take>) => setTakes((all) => all.map((x) => (x.id === id ? { ...x, ...t } : x)));
  const send = async (t: Take) => {
    const s = loadSaved(); if (!s) { patch(t.id, { state: 'local' }); return; }
    patch(t.id, { state: 'uploading', message: undefined });
    const r = await uploadTake(s, { ...t, seconds: TAKE_SECONDS });
    patch(t.id, { state: r.result, message: r.message }); if (!loadSaved()) setSaved(null);
  };
  const record = async () => {
    setBusy(true); setErr('');
    for (let k = 3; k > 0; k--) { setCount(k); await new Promise((ok) => setTimeout(ok, 1000)); }
    setCount(0);
    if (!liveRef.current) { setBusy(false); setErr('倒数时腕带断开了，没录'); return; }
    const bytes = await grab();
    if (!bytes) { setBusy(false); setErr('录到一半腕带断开或数据中断，这条作废'); return; }
    const t: Take = { id: crypto.randomUUID(), label, donning, bytes, state: 'local' };
    setTakes((all) => [t, ...all]); setBusy(false); void send(t);
  };
  const agree = async () => { try { setSaved(await consent(CONSENT_VERSION)); } catch (e) { setErr((e as Error).message); } };
  const withdraw = async () => {
    if (!saved || !confirm('撤回同意后，云端的录音和记录会全部删除，不能恢复。确定吗？')) return;
    try { await revoke(saved); setSaved(null); setTakes((all) => all.map((t) => ({ ...t, state: 'local' }))); } catch (e) { setErr((e as Error).message); }
  };
  const done = (l: string) => takes.filter((t) => t.label === l && t.state === 'ok').length;
  const stateCn = { uploading: '上传中', ok: '已上传', retry: '没传上', rejected: '被拒', local: '只在本页' } as const;
  return <section className="web-rec">
    <h3>录动作{saved ? '并上传' : ''}</h3>
    {!saved && <details className="web-consent" open><summary>{CONSENT_TITLE}（不同意也能录，录音只留在这一页，关掉就没了）</summary>
      <ConsentText /><button type="button" className="primary" onClick={agree}>同意并开始上传</button></details>}
    <div className="web-rec-row">
      <label>动作 <select value={label} onChange={(e) => setLabel(e.target.value)}>{LABELS.map(([v, n]) => <option key={v} value={v}>{n}（已传 {done(v)}）</option>)}</select></label>
      <label>第几次佩戴 <input type="number" min={1} max={999} value={donning} onChange={(e) => setDonning(Math.max(1, Math.min(999, Number(e.target.value) || 1)))} /></label>
      <button type="button" className="primary" disabled={!live || busy} onClick={record}>{count ? `${count}…` : busy ? '录制中…' : `录一条 · ${TAKE_SECONDS} 秒`}</button>
      {saved && <button type="button" className="danger" onClick={withdraw}>撤回同意并删除云端数据</button>}
    </div>
    {!live && <p className="v3-note">先连接腕带再录。</p>}
    {err && <p className="v3-note warn">{err}</p>}
    {takes.length > 0 && <ol className="web-takes">{takes.map((t) => <li key={t.id} data-state={t.state}>
      {LABELS.find(([v]) => v === t.label)?.[1]} · 第 {t.donning} 次佩戴 · {(t.bytes.length / 1024).toFixed(0)} KB · {stateCn[t.state]}{t.message ? `：${t.message}` : ''}
      {t.state === 'retry' && <button type="button" onClick={() => send(t)}>重试</button>}
    </li>)}</ol>}
  </section>;
}
