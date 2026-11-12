// App 顶栏的云端状态：没同意时点开看同意书；同意后显示已传 / 待传，可立即同步或撤回同意（云端全删）。
// 只在 App 里出现（window.pt.cloud）；网页版的上传在 web.tsx 里。
import { useEffect, useState } from 'react';
import { CONSENT_ITEMS, CONSENT_TITLE, CONSENT_VERSION } from './consent';
import type { Result } from './desktop-bridge';

export type CloudState = { consented: boolean; consentAt: string | null; total: number; uploaded: number; rejected: number; pending: number; syncing: boolean; lastError: string; base: string };
type CloudBridge = { state: () => Promise<Result<CloudState>>; consent: (v: string) => Promise<Result<CloudState>>; revoke: () => Promise<Result<CloudState>>; sync: () => Promise<Result<CloudState>> };
const bridge = () => (window as unknown as { pt?: { cloud?: CloudBridge } }).pt?.cloud;

export function ConsentText() {
  return <dl className="cloud-consent">{CONSENT_ITEMS.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>;
}

export function CloudBar() {
  const b = bridge();
  const [st, setSt] = useState<CloudState | null>(null), [open, setOpen] = useState(false), [busy, setBusy] = useState(false), [err, setErr] = useState('');
  const take = (r: Result<CloudState>) => { if (r.ok) { setSt(r.value); setErr(''); } else setErr(r.message); };
  useEffect(() => {
    if (!b) return;
    const tick = () => void b.state().then(take);
    tick(); const t = setInterval(tick, 15000); return () => clearInterval(t);   // 每次都要在主进程扫一遍录音 json，别太勤
  }, [b]);
  if (!b) return null;
  const run = async (f: () => Promise<Result<CloudState>>) => { setBusy(true); try { take(await f()); } finally { setBusy(false); setTimeout(() => void b.state().then(take), 3000); } };
  const label = !st ? '云端 …' : !st.consented ? '云端：未开启' : st.syncing ? `云端：上传中（待传 ${st.pending}）` : st.lastError ? '云端：上传出错' : st.pending ? `云端：待传 ${st.pending}` : `云端：已传 ${st.uploaded}`;
  return <>
    <button type="button" className={`cloud-chip${st?.lastError ? ' warn' : ''}`} onClick={() => setOpen(true)}>{label}</button>
    {open && <div className="cloud-mask" onClick={() => setOpen(false)}>
      <div className="cloud-panel" role="dialog" aria-label="云端上传" onClick={(e) => e.stopPropagation()}>
        <h3>{CONSENT_TITLE}</h3>
        {st?.consented ? <>
          <p>已在 {st.consentAt ? new Date(st.consentAt).toLocaleDateString('zh-CN') : '—'} 同意。本机八通道录音 {st.total} 条：已传 {st.uploaded}，待传 {st.pending}{st.rejected ? `，被平台拒收 ${st.rejected}` : ''}。</p>
          {st.lastError && <p className="v3-note warn">{st.lastError}</p>}
          <div className="cloud-actions">
            <button type="button" disabled={busy || st.syncing} onClick={() => run(b.sync)}>立即同步</button>
            <button type="button" className="danger" disabled={busy} onClick={() => { if (confirm('撤回同意后，云端的录音和记录会全部删除，不能恢复。本机录音不受影响。确定吗？')) void run(b.revoke); }}>撤回同意并删除云端数据</button>
          </div>
          <details><summary>同意书全文</summary><ConsentText /></details>
        </> : <>
          <ConsentText />
          <div className="cloud-actions">
            <button type="button" className="primary" disabled={busy} onClick={() => run(() => b.consent(CONSENT_VERSION))}>同意并开始上传</button>
            <button type="button" onClick={() => setOpen(false)}>暂不</button>
          </div>
        </>}
        {err && <p className="v3-note warn">{err}</p>}
        <p className="cloud-foot">同意书版本 {CONSENT_VERSION} · 平台 {st?.base}</p>
      </div>
    </div>}
  </>;
}
