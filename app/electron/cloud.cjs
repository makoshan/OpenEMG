// 可选云端同步模块：仅当显式配置自建平台地址（YUANLI_PLATFORM）且用户主动同意后才上传 npz；默认留空不联网。
// 不依赖 electron，check-cloud.mjs 直接拿它对真平台跑端到端。
// 只传 npz（EMG/IMU/包序号）；同名 json 里有串口路径（带接收器序列号），只在本机读标签、佩戴次数和时长，不上传。
// 本地状态 cloud.json（权限 600）：匿名令牌、同意版本、每条录音固定的上传 id 和是否已传完。
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const CONSENT_VERSION = '2026-10-14';                       // 与 src/consent.ts 和平台 CONSENT_VERSIONS 同步改
const SETS = ['emg-wl8-data', 'emg-wl8-data-rewear'];       // emg_web 的八通道训练集 / 重戴集

function createCloud({ stateFile, dataRoot, base, fetch = globalThis.fetch }) {
  const load = () => { try { return JSON.parse(fs.readFileSync(stateFile, 'utf8')); } catch { return { takes: {} }; } };
  const save = (s) => { fs.mkdirSync(path.dirname(stateFile), { recursive: true }); fs.writeFileSync(stateFile, JSON.stringify(s, null, 1), { mode: 0o600 }); };
  let st = load(), syncing = null, revoking = false, lastError = '';

  // 工程里所有八通道录音：相对路径 → 本机元数据（读不出 json 的跳过，不猜标签）
  function scan() {
    const out = [];
    for (const set of SETS) {
      const root = path.join(dataRoot, set);
      let labels = []; try { labels = fs.readdirSync(root, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name); } catch { continue; }
      for (const label of labels) for (const f of fs.readdirSync(path.join(root, label)).filter((f) => f.endsWith('.npz'))) {
        const rel = path.join(set, label, f);
        let meta; try { meta = JSON.parse(fs.readFileSync(path.join(dataRoot, rel.replace(/\.npz$/, '.json')), 'utf8')); } catch { continue; }
        out.push({ rel, label: meta.label ?? label, donning: meta.donning, session: meta.session, seconds: meta.seconds });
      }
    }
    return out;
  }

  const status = () => {
    const all = scan(), done = all.filter((t) => st.takes[t.rel]?.done).length, rejected = all.filter((t) => st.takes[t.rel]?.rejected).length;
    return { consented: !!st.token, consentVersion: st.consent_version ?? null, consentAt: st.consent_at ?? null, subjectId: st.subject_id ?? null,
      total: all.length, uploaded: done, rejected, pending: all.length - done - rejected, syncing: !!syncing, lastError, base };
  };

  async function call(method, p, { body, headers = {} } = {}) {
    const r = await fetch(base + p, { method, body, headers: { ...headers, ...(st.token ? { 'x-subject-token': st.token } : {}) }, signal: AbortSignal.timeout(30000) });
    let j = null; try { j = await r.json(); } catch { /* 非 JSON */ }
    return { status: r.status, body: j };
  }

  async function consent(version) {
    if (version !== CONSENT_VERSION) throw Object.assign(new Error('同意书版本不对，请刷新后重新阅读'), { code: 'consent' });
    if (st.token) return status();
    const r = await call('POST', '/v1/wl8/subjects', { body: JSON.stringify({ consent_version: version }), headers: { 'content-type': 'application/json' } });
    if (r.status !== 201) throw Object.assign(new Error(r.body?.error ?? `平台返回 ${r.status}`), { code: 'platform' });
    st = { ...st, token: r.body.token, subject_id: r.body.subject_id, consent_version: version, consent_at: new Date().toISOString() }; save(st);
    return status();
  }

  // 请平台删光；平台确认（200，或 401 = 早已删完）才清本地令牌。删失败就留着令牌，用户能再点一次
  async function finishDelete() {
    const r = await call('DELETE', '/v1/wl8/me');
    if (r.status !== 200 && r.status !== 401) return r;
    st = { takes: {} }; save(st); lastError = '';
    return null;
  }
  // 撤回同意：先等正在跑的那轮同步结束、期间不开新同步，免得撤回后还有不带令牌的上传报误导性的错
  async function revoke() {
    if (!st.token) return status();
    revoking = true;
    try {
      await syncing?.catch(() => {});
      const bad = await finishDelete();
      if (bad) throw Object.assign(new Error(bad.body?.error ?? `平台返回 ${bad.status}`), { code: 'platform' });
    } finally { revoking = false; }
    return status();
  }

  // 传一轮：每条第一次尝试时固定一个 uuid 并先落盘，之后重传都用它（平台按 id 幂等）。断网就停在这一条，下次接着传
  async function syncOnce() {
    if (!st.token) return status();
    lastError = '';
    for (const t of scan()) {
      if (!st.token) break;
      const rec = st.takes[t.rel] ?? (st.takes[t.rel] = { id: crypto.randomUUID() });
      if (rec.done || rec.rejected) continue;
      save(st);
      const q = new URLSearchParams({ label: t.label, donning: String(t.donning), source: 'app', format: 'npz', ...(t.seconds ? { seconds: String(t.seconds) } : {}) });
      // 会话说明（如「左手 · 腕部贴掌根」）是自填文字，走请求头，不进 URL 访问日志
      const headers = { 'content-type': 'application/octet-stream', ...(t.session ? { 'x-take-session': encodeURIComponent(String(t.session).slice(0, 120)) } : {}) };
      let r;
      try { r = await call('PUT', `/v1/wl8/takes/${rec.id}?${q}`, { body: fs.readFileSync(path.join(dataRoot, t.rel)), headers }); }
      catch (e) { lastError = `连不上平台：${e.message}`; return status(); }
      if (r.status === 201 || r.status === 200) rec.done = true;
      else if (r.status === 401) {
        // 令牌失效：多半是撤回做到一半（平台已打删除标记）。补发一次删除，平台确认删完才清本地，否则留着令牌让用户再点撤回
        const bad = await finishDelete().catch((e) => ({ status: 0, body: { error: e.message } }));
        lastError = bad ? '云端删除还没做完，请再点一次「撤回同意并删除云端数据」' : '云端数据已删除，本机已退出上传；要继续上传请重新同意';
        return status();
      }
      else if (r.status === 409) { rec.id = crypto.randomUUID(); lastError = `${t.rel} 与已传内容冲突，换 id 下轮重传`; }   // 本机文件被改过
      else if ([400, 413, 422].includes(r.status)) { lastError = `${t.rel}：${r.body?.error ?? r.status}`; rec.rejected = r.body?.error ?? String(r.status); }   // 这条本身不合格，别每轮重试
      else { lastError = `平台暂时收不了（${r.status}${r.body?.error ? '：' + r.body.error : ''}），稍后重试`; save(st); return status(); }   // 404（平台还没上线这组接口）、429、5xx：整轮停下，下轮再试
      save(st);
    }
    return status();
  }
  const sync = () => (revoking ? Promise.resolve(status()) : syncing ?? (syncing = syncOnce().finally(() => { syncing = null; })));

  return { status, consent, revoke, sync, CONSENT_VERSION };
}

module.exports = { createCloud, CONSENT_VERSION };
