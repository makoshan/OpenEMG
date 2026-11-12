// 单通道（Cheez + ESP32-S3）工作室的 IPC：和八通道 emg8-ipc.cjs 同一套做法——页面只调白名单动作，端口和请求头不出主进程。
// 后端是 host/emg_web.py（不带 --wl8）：/api/emg/state、record（task=gestures）、gesture-train、live1、stream。
// 实时流：订阅 /api/emg/stream（每行 `S t 贴合数 v×10`，1 kHz 原始 ADC；`CUE {json}` 录制提示；`P {json}` 识别结果），每 50 ms 打包推一条 pt:emg1:event。
// 文件名带 emg8- 前缀：原力手环是源头，vibe-hw 用 sync-emg8.mjs 同步过去，两个 App 共用。
const http = require('node:http');
const { request } = require('./emg8-ipc.cjs');

const HOST = '127.0.0.1';
const GESTURES = ['rest', 'pinch', 'rub', 'snap', 'fist'];
// 动作组：'five' = 单通道原五类；其余和八通道同一份清单（emg8-profiles.json）。训练类别 = labels，录制可用 captureLabels
const profiles = require('./emg8-profiles.json');
const groupOf = (g) => {
  if (g == null || g === 'five') return { group: 'five', labels: GESTURES, capture: GESTURES };
  const p = Object.hasOwn(profiles, g) ? profiles[g] : null;
  if (!p) throw Object.assign(new Error('未知动作组'), { code: 'bad-group' });
  return { group: g, labels: p.labels, capture: p.captureLabels ?? p.labels };
};
const groupBody = (g) => (g.group === 'five' ? {} : { group: g.group, labels: g.labels });
const SPLITS = new Set(['train', 'validation', 'test']);
const MODELS = new Set(['lda', 'svm']);           // 打包 App 不带 torch：只放经典模型

function registerEmg1({ ipcMain, guarded, getWin, deviceService }) {
  // port / header：由 streamStart 绑定。header 是服务端绑定的工程 id；假台架没绑工程就是空串（它只写临时目录）
  let port = null, header = '', bindError = '';
  const bound = (method, path, id, body) => {
    if (!port) throw Object.assign(new Error(bindError ? `单通道采集服务没起来：${bindError}` : '单通道采集服务还在启动：连上板子后会自动接上'), { code: 'not-bound' });
    if (header && id && id !== header) throw Object.assign(new Error('采集服务绑定的是另一个工程，请重新连接'), { code: 'wrong-project' });
    return request(method, path, header, body, port);
  };
  const send = (ev) => { const w = getWin(); if (w && !w.isDestroyed()) w.webContents.send('pt:emg1:event', ev); };
  const int = (v, lo, hi, d) => (Number.isInteger(v) && v >= lo && v <= hi ? v : d);
  const runId = (v) => (typeof v === 'string' && /^[\w-][\w.-]{0,79}$/.test(v) ? v : '');   // 不许以点开头：挡住 '..'

  ipcMain.handle('pt:emg1:state', guarded((a) => {
    const g = groupOf(a?.group);
    // 计数按录制类别（captureLabels ⊇ labels）：多录、不进训练的类也要显示进度
    return bound('GET', g.group === 'five' ? '/api/emg/state' : `/api/emg/state?group=${encodeURIComponent(g.group)}&labels=${encodeURIComponent(g.capture.join(','))}`);
  }));
  ipcMain.handle('pt:emg1:record', guarded((id, a) => {
    const g = groupOf(a?.group);
    if (!g.capture.includes(a?.label)) throw Object.assign(new Error('未知手势'), { code: 'bad-label' });
    if (!SPLITS.has(a?.split)) throw Object.assign(new Error('未知数据集'), { code: 'bad-split' });
    return bound('POST', '/api/emg/record', id, { label: a.label, set: a.split, task: 'gestures', count: int(a.count, 1, 30, 5),
      donning: int(a.donning, 1, 20, 1), countdown: int(a.countdown, 0, 5, 3), session: '', ...(g.group === 'five' ? {} : { group: g.group }) });
  }));
  ipcMain.handle('pt:emg1:recordStop', guarded((id) => bound('POST', '/api/emg/record', id, { action: 'stop' })));
  ipcMain.handle('pt:emg1:train', guarded((id, a) => {
    const action = a?.action === 'evaluate' ? 'evaluate' : 'train';
    const model = MODELS.has(a?.model) ? a.model : 'lda';
    return bound('POST', '/api/emg/gesture-train', id, { action, model, run_id: runId(a?.runId), ...groupBody(groupOf(a?.group)) });
  }));
  ipcMain.handle('pt:emg1:live', guarded((id, a) => bound('POST', '/api/emg/live1', id, { action: a?.action === 'stop' ? 'stop' : 'start', run_id: runId(a?.runId), ...groupBody(groupOf(a?.group)) })));
  // 旧引导页（预演 / 诊断 / 三类对照）的地址：只给本机 http 地址，页面拿来放进 iframe
  ipcMain.handle('pt:emg1:guideUrl', guarded(() => {
    if (!port) throw Object.assign(new Error('单通道采集服务还没起来'), { code: 'not-bound' });
    return `http://${HOST}:${port}/guide?project=${encodeURIComponent(header)}`;
  }));

  let stream = null, generation = 0;
  const stop = () => { generation++; if (stream) { stream.req.destroy(); clearInterval(stream.timer); stream = null; } };
  ipcMain.handle('pt:emg1:streamStart', guarded(async (id) => {
    stop();
    const current = generation;
    let entry;
    try { entry = await deviceService.emg(id, 'open'); } catch (e) { bindError = String(e?.message ?? e).slice(0, 200); port = null; throw e; }
    if (current !== generation) return true;
    port = Number(new URL(entry.url).port); bindError = '';
    const st = await request('GET', '/api/emg/state?view=capture', '', undefined, port);
    if (current !== generation) return true;            // 等待期间页面卸载或换了设备：不再开这一路流
    header = st?.project?.id ?? '';
    if (header && header !== id) { port = null; throw Object.assign(new Error('采集服务绑定的是另一个工程'), { code: 'wrong-project' }); }
    const s = { samples: [], worn: [], cue: null, preds: [], req: null, timer: null };
    s.req = http.get({ host: HOST, port, path: '/api/emg/stream' }, (res) => {
      if (current !== generation) { res.resume(); return; }
      if (res.statusCode !== 200) {
        let body = ''; res.setEncoding('utf8'); res.on('data', (c) => { body += c; });
        res.on('end', () => { if (current !== generation) return; let p = null; try { p = JSON.parse(body); } catch { /* 非 JSON */ }
          send({ type: 'error', message: p?.error || `数据流被拒绝（${res.statusCode}）` }); });
        return;
      }
      res.setEncoding('utf8'); let buf = '';
      res.on('data', (chunk) => {
        if (current !== generation) return;
        buf += chunk; let i;
        while ((i = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, i); buf = buf.slice(i + 1);
          if (!line.startsWith('data: ')) continue;
          const d = line.slice(6);
          if (d.startsWith('S ')) {
            const f = d.trim().split(/\s+/), vals = f.slice(3).map(Number);
            if (vals.length && vals.every(Number.isFinite)) { s.samples.push(...vals); s.worn.push(Number(f[2]) / vals.length); }
          } else if (d.startsWith('CUE ')) { try { s.cue = JSON.parse(d.slice(4)); } catch { /* 半行 */ } }
          else if (d.startsWith('P ')) { try { s.preds.push(JSON.parse(d.slice(2))); } catch { /* 半行 */ } }
        }
      });
      res.on('end', () => { if (current === generation) send({ type: 'error', message: '单通道数据流断开了，请检查 USB 线后重新连接' }); });
    });
    s.req.on('error', () => { if (current === generation) send({ type: 'error', message: '单通道采集服务暂时连不上，请重新连接' }); });
    s.timer = setInterval(() => {
      if (!s.samples.length && !s.cue && !s.preds.length) return;
      const worn = s.worn.length ? s.worn.reduce((a, b) => a + b, 0) / s.worn.length : null;
      send({ type: 'batch', samples: s.samples, worn, cue: s.cue, preds: s.preds, t: Date.now() });
      s.samples = []; s.worn = []; s.cue = null; s.preds = [];
    }, 50);
    stream = s; return true;
  }));
  ipcMain.handle('pt:emg1:streamStop', guarded(() => { stop(); return true; }));
  return { stop };
}

module.exports = { registerEmg1 };
