'use client';
// 引导模式前两步：① 连上（表针扫秒，收到数据后 8 路 LED 依次点亮）② 戴好（5 秒信号检查，逐路比放松底噪上限）。
// 数据：studio 的 flow / rms（每 500 ms）和服务端 conditions（firmware/wl8_ab.py）。
import { useEffect, useRef, useState } from 'react';
import type { Conditions, Emg8Bridge, Hand, ServiceState } from './contract';
import { Dial, Led, NOISE_LIMIT_UV } from './instrument';
import { hotStep, linkAdvice, readBandLink, writeBandLink, type BandLink } from './link';
import { showWearSteps, wearSteps, wearVerdict } from './placement';
import { grayTitle } from './gray-title';

const CONNECT_TIMEOUT_S = 15;                                   // 和 desktop/device-service.cjs 等服务起来的上限一致

export type WearCheck = { donning: number; perChannel: number[]; warnings: string[] };

export function SetupView({ sub, online, hz, dropped, rms, range, hand, donning, since, st, projectId, bridge, wear, busy, onWear, onReconnect, onNext, onError, bandLink, stale }: {
  stale?: boolean;   // 检查过了，但现在实时底噪又超线：勾作废，要重新检查
  sub: 0 | 1; online: boolean; hz: number; dropped: number; rms: number[] | null; range: number; hand: Hand; donning: number; since: number;
  st: ServiceState | null; projectId: string; bridge: Emg8Bridge; wear: WearCheck | null; busy: boolean;
  onWear: (w: WearCheck) => void; onReconnect: () => void; onNext: () => void; onError: (m: string) => void;
  bandLink?: BandLink;
}) {
  const [now, setNow] = useState(() => performance.now());
  const [checking, setChecking] = useState<number | null>(null);   // 检查开始时刻
  const [kind, setKind] = useState<BandLink>(() => bandLink ?? readBandLink());
  const choose = (next: BandLink) => { setKind(next); writeBandLink(next); };
  const link = st?.rig.link;
  const waitOrigin = useRef<number | null>(null);
  useEffect(() => {
    if (online && checking == null) return;
    // 表针要逐帧动。没有明确的连接状态时，15 秒后停表。等手环时继续走，好让「超过 10 秒」那一步亮起来。
    let raf = 0;
    const tick = () => {
      const t = performance.now();
      setNow(t);
      if (checking != null || link === 'waiting-band' || t - since < CONNECT_TIMEOUT_S * 1000 + 100) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [online, checking, since, link]);
  const elapsed = Math.max(0, (now - since) / 1000);
  const advice = linkAdvice(link, st?.rig.link_detail, kind);
  const guidedLink = link === 'no-receiver' || link === 'waiting-band' || link === 'dropped';
  const timedOut = !online && !guidedLink && elapsed >= CONNECT_TIMEOUT_S;
  if (link === 'waiting-band') { if (waitOrigin.current == null) waitOrigin.current = performance.now(); }
  else waitOrigin.current = null;
  const hot = hotStep(link, waitOrigin.current == null ? 0 : (performance.now() - waitOrigin.current) / 1000, kind);
  const kindSwitch = <div className="ins-link-kind" role="group" aria-label="手环接法">
    <button type="button" aria-pressed={kind === 'usb'} onClick={() => choose('usb')}>USB 版</button>
    <button type="button" aria-pressed={kind === 'ble'} onClick={() => choose('ble')}>蓝牙版</button>
  </div>;
  const serviceError = st?.rig.error || (st?.rig.banner?.startsWith('断开') ? st.rig.banner : '');
  const chCount = Math.max(2, st?.rig.n_channels ?? rms?.length ?? 8);
  const mine = wear?.donning === donning && wear.perChannel.length === chCount ? wear : null;
  const checks = mine ? mine.perChannel.map((v) => (v <= NOISE_LIMIT_UV ? 'ok' : 'bad') as 'ok' | 'bad') : null;
  const bad = checks?.map((c, i) => (c === 'bad' ? i + 1 : 0)).filter(Boolean) ?? [];
  const sweep = checking == null ? null : Math.min(1, (now - checking) / 5000);

  const check = async () => {
    setChecking(performance.now());
    try {
      const r = await bridge.ab(projectId, { action: 'conditions' });
      if (!r.ok) { onError(r.message); return; }
      const c = r.value as Conditions;
      onWear({ donning, perChannel: c.noise_per_channel?.length === chCount ? c.noise_per_channel : Array(chCount).fill(c.noise_uv ?? Infinity), warnings: c.warnings });
    } finally { setChecking(null); }
  };

  if (sub === 0) {
    const big = online ? `${chCount} / ${chCount}` : timedOut ? '15.0 s' : `${elapsed.toFixed(1)} s`;
    return <section className="emg8-card ins-stage">
      <div className="ins-corner"><span className="ins-cap">步骤 1 · 连接</span><span className="ins-cap"><Led state={online ? 'on' : timedOut ? 'warn' : 'off'} /> {online ? '在线' : timedOut ? '没有数据' : '启动中'}</span></div>
      <div className={timedOut ? 'ins-shake' : ''}><Dial values={rms} max={range} online={online} hand={hand} channels={chCount} needle={online ? null : Math.min(elapsed, CONNECT_TIMEOUT_S)} big={big} small={online ? `${Math.round(hz)} Hz` : '启动采集服务'} /></div>
      {kindSwitch}
      <h2 className="ins-headline">{online ? '手环醒了' : guidedLink ? advice.title : timedOut ? '15 秒没收到数据' : '正在唤醒手环'}</h2>
      <p className="ins-sub">{online ? `${chCount} 路都在出数据 · 丢帧 ${dropped}` : guidedLink ? advice.detail : serviceError || (timedOut ? '点「重新连接」再试一次' : '正在确认电脑有没有看到手环')}</p>
      {guidedLink && !!advice.steps.length && <ol className="ins-checklist">{advice.steps.map((step, i) => <li key={step} className={i === hot ? 'ins-now' : undefined}>{step}</li>)}</ol>}
      <div className="ins-actions">{online ? <button className="emg8-primary ins-next" onClick={onNext}>去戴好它 →</button> : <button className={timedOut ? 'emg8-primary' : ''} disabled={busy} onClick={onReconnect}>重新连接</button>}</div>
      <p className="ins-honest">每路的灯只在收到该路数据后才亮；VU 条长度 = 该路实时幅度（±{range} µV 满格）</p>
    </section>;
  }
  // N 路都贴好就算过；「Mac 接着充电器」这类条件只提醒，不拦（2026-10-09 走查：8/8 贴好却被挡住，同一句还显示了两遍）
  const passed = !!mine && bad.length === 0 && !stale;
  const verdict = wearVerdict(bad, mine?.warnings ?? [], chCount);   // 文案和「露不露服务端提醒」都在 placement.ts，check-wear-hint.mjs 不开 Electron 就能自检
  return <section className="emg8-card ins-stage">
    <div className="ins-corner"><span className="ins-cap">步骤 2 · 佩戴 · 第 {donning} 次</span><span className="ins-cap"><Led state={online ? 'on' : 'off'} /> {online ? `在线 · ${Math.round(hz)} Hz` : '未连接'}</span></div>
    <Dial values={rms} max={range} online={online} hand={hand} channels={chCount} checks={checking == null ? checks : null} limit={NOISE_LIMIT_UV} sweep={sweep}
      big={checking != null ? `${Math.min(chCount, Math.floor((sweep ?? 0) * chCount))} / ${chCount}` : mine ? `${chCount - bad.length} / ${chCount}` : '—'} small={checking != null ? '正在听每一路' : stale ? '底噪又高了' : mine ? bad.length ? `CH${bad.join('、CH')} 噪声高` : '全部贴好' : '还没检查'} />
    {kindSwitch}
    <h2 className="ins-headline">{checking != null ? '别动，正在听每一路…' : !mine ? '像戴手表那样戴在手腕' : stale ? '刚才贴好了，现在底噪又高了' : verdict.headline}</h2>
    <p className="ins-sub">{checking != null ? '手放松，前臂搁稳' : stale ? '电极可能被碰松了：沾水压紧，再检查一次' : !mine ? '照下面几条戴好，再检查一遍' : verdict.sub}</p>
    {mine && verdict.warnings.map((w) => <p key={w} className="emg8-warn">{w}</p>)}
    {checking == null && showWearSteps(!!mine, bad.length) && <ol className="ins-wearlist" aria-label="佩戴提醒">{wearSteps(hand, kind, chCount).map((s) => <li key={s.k}><b>{s.t}</b>{s.d}</li>)}</ol>}
    <div className="ins-actions">
      {passed ? <button className="emg8-primary ins-next" onClick={onNext}>开始录动作 →</button>
        : <button className="emg8-primary" disabled={!online || busy || checking != null} title={grayTitle(!online && '腕带还没连上')} onClick={check}>{mine ? '再检查一次' : '检查贴合 · 5 秒'}</button>}
      {mine && !passed && <button onClick={onNext}>先这样录</button>}
    </div>
    <p className="ins-honest">红刻度 = 放松底噪上限 {NOISE_LIMIT_UV} µV；低于它才亮绿灯。绿灯只说明能录，不说明识别会准</p>
  </section>;
}
