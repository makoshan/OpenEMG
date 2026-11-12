// 网页版的云端上传：和 App 的 electron/cloud.cjs 同一组平台接口（/v1/wl8），只是令牌存在浏览器里。
// ponytail: 令牌放 localStorage——清浏览器数据就丢，丢了没法再删云端数据；要找回得做账号，等真有用户再说
const BASE = (import.meta as unknown as { env?: { VITE_PLATFORM?: string } }).env?.VITE_PLATFORM ?? '';
const KEY = 'yuanli-cloud';

type Saved = { token: string; subjectId: string; consentVersion: string; consentAt: string };
export const loadSaved = (): Saved | null => { try { return JSON.parse(localStorage.getItem(KEY) ?? 'null'); } catch { return null; } };
const store = (s: Saved | null) => { try { if (s) localStorage.setItem(KEY, JSON.stringify(s)); else localStorage.removeItem(KEY); } catch { /* 无存储：只在这一页有效 */ } };

async function call(method: string, path: string, init: { token?: string; body?: BodyInit; headers?: Record<string, string> } = {}) {
  const r = await fetch(BASE + path, { method, body: init.body, headers: { ...(init.headers ?? {}), ...(init.token ? { 'x-subject-token': init.token } : {}) } });
  let body: { error?: string; [k: string]: unknown } | null = null; try { body = await r.json(); } catch { /* 非 JSON */ }
  return { status: r.status, body };
}

export async function consent(version: string): Promise<Saved> {
  const r = await call('POST', '/v1/wl8/subjects', { body: JSON.stringify({ consent_version: version }), headers: { 'content-type': 'application/json' } });
  if (r.status !== 201) throw new Error(r.body?.error ?? `平台返回 ${r.status}`);
  const s = { token: String(r.body!.token), subjectId: String(r.body!.subject_id), consentVersion: version, consentAt: new Date().toISOString() };
  store(s); return s;
}

export async function revoke(s: Saved) {
  const r = await call('DELETE', '/v1/wl8/me', { token: s.token });
  if (r.status !== 200 && r.status !== 401) throw new Error(r.body?.error ?? `平台返回 ${r.status}`);
  store(null);
}

/** 传一条录音（串口原始字节）。返回 'ok' / 'retry'（网络、404、429、5xx，可以再点）/ 'rejected'（这条本身不合格） */
export async function uploadTake(s: Saved, t: { id: string; label: string; donning: number; seconds: number; bytes: Uint8Array }): Promise<{ result: 'ok' | 'retry' | 'rejected'; message?: string }> {
  const q = new URLSearchParams({ label: t.label, donning: String(t.donning), source: 'web', format: 'wl8raw', seconds: String(t.seconds) });
  let r;
  try { r = await call('PUT', `/v1/wl8/takes/${t.id}?${q}`, { token: s.token, body: t.bytes as BodyInit, headers: { 'content-type': 'application/octet-stream' } }); }
  catch (e) { return { result: 'retry', message: `连不上平台：${(e as Error).message}` }; }
  if (r.status === 201 || r.status === 200) return { result: 'ok' };
  if (r.status === 401) {
    // 令牌失效多半是撤回做到一半：补发一次删除，平台确认删完才清本地，否则留着令牌让用户再点撤回
    const d = await call('DELETE', '/v1/wl8/me', { token: s.token }).catch(() => ({ status: 0, body: null }));
    if (d.status === 200 || d.status === 401) { store(null); return { result: 'retry', message: '云端数据已删除；要继续上传请重新同意' }; }
    return { result: 'retry', message: '云端删除还没做完，请再点一次「撤回同意并删除云端数据」' };
  }
  if ([400, 409, 413, 422].includes(r.status)) return { result: 'rejected', message: r.body?.error ?? String(r.status) };
  return { result: 'retry', message: `平台暂时收不了（${r.status}）` };
}
