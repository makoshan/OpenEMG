// 八通道肌电工作室的 IPC（main.cjs 只加一行：registerEmg8({ ipcMain, guarded, getWin: () => win })）。
// 页面只能调白名单里的动作；端口、路径、请求头（X-Mako-Collector / X-Mako-Project）都不出主进程。
// 桌面通过工程设备服务启动 emg8-server.py，复用手表采集器；端口由主进程分配。
// 实时数据：主进程订阅 /api/emg/stream8（SSE），每 50 ms 把 EMG / IMU / 识别结果打包成一条 pt:emg8:event 推给窗口。
const http = require('node:http');

const HOST = '127.0.0.1';
const PORT = Number(process.env.PT_EMG8_PORT || 8767);
const GESTURE_ACTIONS = new Set(['left_click', 'right_click', 'move', 'scroll']);
const ACCESS_HINT = '到系统设置 → 隐私与安全性 → 辅助功能里允许 OpenEMG。';
function printThingsTrusted(prompt) {
  const { systemPreferences } = require('electron');
  return systemPreferences.isTrustedAccessibilityClient(!!prompt) === true;
}
const MAX_STEP = 400;
function postGesture(action, dx, dy) {
  const electron = require('electron');
  if (typeof electron.postGesture === 'function') return electron.postGesture(action, dx, dy);
  return require('./emg8-mouse.cjs').post(action, dx, dy);
}
const AB_ACTIONS = new Set(['start', 'pause', 'resume', 'stop', 'void', 'conditions']);
const CURSOR_ACTIONS = new Set(['calibrate', 'calibrate_pinch', 'log', 'enable', 'stop', 'drift', 'config', 'flip']);
const profiles = require('./emg8-profiles.json');
const { studioRoute, STUDIO_EVENTS } = require('./emg8-studio-routes.cjs');
const { shell } = require('electron');
const LABELS = new Set(['rest', 'left', 'right', 'click', 'pinch', 'rub', 'fist', 'loose', ...Object.values(profiles).flatMap((p) => p.captureLabels ?? p.labels)]);

function request(method, path, projectId, body, port = PORT) {
  return new Promise((resolve, reject) => {
    const data = body === undefined ? null : Buffer.from(JSON.stringify(body));
    const headers = { 'X-Mako-Collector': '1', 'X-Mako-Project': projectId || '' };
    if (data) Object.assign(headers, { 'Content-Type': 'application/json', 'Content-Length': data.length });
    const req = http.request({ host: HOST, port, method, path, headers, timeout: 20000 }, (res) => {
      let buf = '';
      res.setEncoding('utf8'); res.on('data', (c) => { buf += c; });
      res.on('end', () => {
        // 回的不是 JSON（别的程序占了这个端口，比如 python -m http.server 的 404 网页）：不把原文贴给页面（2026-10-12 截图里整页 HTML）
        let json = null; try { json = buf ? JSON.parse(buf) : {}; } catch { json = null; }
        if (json === null || typeof json !== 'object') { const e = new Error(`采集服务端口 ${port} 上回的不是采集服务（${res.statusCode}，不是 JSON），请重新连接`); e.code = 'not-collector'; reject(e); return; }
        if (res.statusCode >= 400) { const e = new Error(json?.error || `采集服务返回 ${res.statusCode}`); e.code = `http-${res.statusCode}`; reject(e); }
        else resolve(json);
      });
    });
    req.on('timeout', () => { req.destroy(new Error('采集服务没有响应')); });
    req.on('error', (err) => { const e = new Error(err.code === 'ECONNREFUSED' ? '采集服务没开：先启动 emg_web.py --wl8' : err.message); e.code = 'offline'; reject(e); });
    if (data) req.write(data);
    req.end();
  });
}

function registerEmg8({ ipcMain, guarded, getWin, deviceService }) {
  // 有设备服务时端口只来自它分配的那一个（streamStart 绑定）；绑定前不碰默认 8767——那里可能是别的程序（2026-10-12 被 http.server 占用）
  let port = deviceService ? null : PORT, boundProject = '', bindError = '';   // bindError：设备服务没起来的真实原因，绑定前报错时带上，别只说「会自动接上」
  const requestBound = (method, path, id, body) => {
    if (id && boundProject && id !== boundProject) throw Object.assign(new Error('采集服务绑定的是另一个工程，请重新连接'), { code: 'wrong-project' });
    if (!port) throw Object.assign(new Error(bindError ? `采集服务没起来：${bindError}` : '采集服务还在启动：连上手环后会自动接上'), { code: 'not-bound' });
    return request(method, path, id, body, port);
  };
  const validateLabels = (labels) => {
    if (labels === undefined) return undefined;
    if (!Array.isArray(labels) || !labels.length || labels.some((l) => !LABELS.has(l)) || new Set(labels).size !== labels.length) throw Object.assign(new Error('未知或重复训练类别'), { code: 'bad-label' });
    return labels;
  };
  const send = (ev) => { const w = getWin(); if (w && !w.isDestroyed()) w.webContents.send('pt:emg8:event', ev); };
  const str = (v, max = 200) => (typeof v === 'string' ? v.slice(0, max) : undefined);
  const int = (v, lo, hi, d) => (Number.isInteger(v) && v >= lo && v <= hi ? v : d);
  // 织带孔位只进元数据（底噪对照松紧用），不参与识别；不填返回 undefined，不传
  const strapHole = (v) => {
    if (v == null) return undefined;
    if (!Number.isInteger(v) || v < 1 || v > 20) throw Object.assign(new Error('织带孔位必须是 1 到 20 的整数'), { code: 'bad-strap' });
    return v;
  };
  // 戴法（线缆朝向、CH1 电极位置）同样只进元数据；不填不传，非固定选项报 bad-wear
  const wearPick = (v, allowed) => {
    if (v == null) return undefined;
    if (!allowed.includes(v)) throw Object.assign(new Error(`戴法只能是 ${allowed.join(' / ')}`), { code: 'bad-wear' });
    return v;
  };
  const q = (o) => Object.entries(o).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');

  ipcMain.handle('pt:emg8:validation', guarded((id, a) => {
    if (!['start','status','clock','stop','events','video','finish'].includes(a?.action)) throw Error('未知连续验证操作');
    // 视频只经本机采集服务写入validation-local；不经过云端上传。
    const body = { ...a };
    if (a.action === 'video') {
      if (!(a.bytes instanceof Uint8Array) || a.bytes.byteLength > 8000000) throw Error('视频分片无效');
      body.base64 = Buffer.from(a.bytes).toString('base64'); delete body.bytes;
    }
    return requestBound('POST', '/api/emg/wl8/validation', str(id), body);
  }));
  ipcMain.handle('pt:emg8:state', guarded(async () => {
    const st = await requestBound('GET', '/api/emg/state?view=capture');
    // 原采集器按当前设备返回扁平计数，工作室契约按设备分层。
    const kind = st.rig?.kind || 'wl8';
    st.counts = Object.fromEntries(Object.entries(st.counts || {}).map(([split, counts]) => [split,
      counts[kind] && typeof counts[kind] === 'object' ? counts : { [kind]: counts }]));
    return st;
  }));
  ipcMain.handle('pt:emg8:abState', guarded((a) => requestBound('GET', `/api/emg/ab?${q({ hand: a?.hand === 'right' ? 'right' : 'left', donning: int(a?.donning, 1, 20, 1) })}`)));
  ipcMain.handle('pt:emg8:ab', guarded((id, a) => {
    if (!AB_ACTIONS.has(a?.action)) throw Object.assign(new Error('未知操作'), { code: 'bad-action' });
    const body = { action: a.action };
    if (a.action === 'start') Object.assign(body, { step: str(a.step, 20), hand: a.hand === 'right' ? 'right' : 'left', donning: int(a.donning, 1, 20, 1),
      purpose: ['dev', 'rehearsal', 'accept'].includes(a.purpose) ? a.purpose : 'dev', placement: str(a.placement), conditions: a.conditions && typeof a.conditions === 'object' ? a.conditions : null, strap_hole: strapHole(a.strap_hole) });
    if (a.action === 'conditions') body.seconds = 5;
    return requestBound('POST', '/api/emg/ab', str(id), body);
  }));
  ipcMain.handle('pt:emg8:record', guarded((id, a) => {
    if (!LABELS.has(a?.label)) throw Object.assign(new Error('未知手势'), { code: 'bad-label' });
    const body = { label: a.label, count: int(a.count, 1, 50, 5), set: a.set === 'rewear' ? 'rewear' : 'train',
      session: str(a.session) || '', donning: int(a.donning, 1, 20, 1), countdown: int(a.countdown, 0, 5, 3), calibration: a.calibration === true };
    if (a?.seconds != null) {
      if (typeof a.seconds !== 'number' || !Number.isInteger(a.seconds) || a.seconds < 1 || a.seconds > 5) throw Object.assign(new Error('单次时长必须是 1 到 5 秒'), { code: 'bad-seconds' });
      body.seconds = a.seconds;
    }
    if (a?.strap_hole != null) body.strap_hole = strapHole(a.strap_hole);
    if (a?.cable_dir != null) body.cable_dir = wearPick(a.cable_dir, ['elbow', 'palm']);
    if (a?.ch0_site != null) body.ch0_site = wearPick(a.ch0_site, ['ulnar', 'radial', 'palmar', 'dorsal']);
    return requestBound('POST', '/api/emg/record', str(id), body);
  }));
  // 手势 → 系统鼠标：只放行四个动作，位移 / 行数是有限数字（服务端再夹到 ±400 px / ±10 行并限频；滚动由 emg8-mouse.node 再夹 ±10 行）
  ipcMain.handle('pt:emg8:access', guarded((prompt) => ({ trusted: printThingsTrusted(prompt === true) })));
  ipcMain.handle('pt:emg8:action', guarded(async (id, a) => {
    if (!GESTURE_ACTIONS.has(a?.action)) throw Object.assign(new Error('未知动作'), { code: 'bad-action' });
    if (!printThingsTrusted(false)) throw Object.assign(new Error(ACCESS_HINT), { code: 'accessibility' });
    const px = (v) => {
      const n = typeof v === 'number' && Number.isFinite(v) ? v : 0;
      return Math.max(-MAX_STEP, Math.min(MAX_STEP, n));
    };
    const dx = px(a.dx), dy = px(a.dy);
    const result = await requestBound('POST', '/api/emg/wl8/action', str(id), { action: a.action, dx, dy, deliver: 'app' });
    if (result?.ok) postGesture(a.action, dx, dy);
    return result;
  }));
  // 停下当前这一批：服务端在倒数中或下一条开始前停，已收下的保留
  ipcMain.handle('pt:emg8:recordStop', guarded((id) => requestBound('POST', '/api/emg/record', str(id), { action: 'stop' })));
  ipcMain.handle('pt:emg8:train', guarded((id, a) => requestBound('POST', '/api/emg/wl8/train', str(id), { labels: validateLabels(a?.labels) })));
  ipcMain.handle('pt:emg8:runs', guarded(() => requestBound('GET', '/api/emg/wl8/runs')));
  ipcMain.handle('pt:emg8:run', guarded((rid) => requestBound('GET', `/api/emg/wl8/run?${q({ id: str(rid, 40) || '' })}`)));
  ipcMain.handle('pt:emg8:live', guarded((id, a) => {
    const action = a?.action === 'stop' ? 'stop' : a?.action === 'tune' ? 'tune' : 'start';
    const body = { action, run_id: str(a?.runId, 40) };
    if (action !== 'stop') {
      const threshold = typeof a?.thresholdUv === 'number' && Number.isFinite(a.thresholdUv) ? a.thresholdUv : undefined;
      const sensitivity = typeof a?.sensitivity === 'number' && Number.isFinite(a.sensitivity) ? a.sensitivity : undefined;
      if (a?.thresholdUv != null && (threshold == null || threshold < 0 || threshold > 5000)) throw Object.assign(new Error('幅度门槛必须在 0 到 5000'), { code: 'bad-gate' });
      if (a?.sensitivity != null && (sensitivity == null || !Number.isInteger(sensitivity) || sensitivity < 1 || sensitivity > 10)) throw Object.assign(new Error('灵敏度必须是 1 到 10 的整数'), { code: 'bad-gate' });
      if (a?.minProb != null) {   // 动作阈值（把握度）0–0.99
        if (typeof a.minProb !== 'number' || !Number.isFinite(a.minProb) || a.minProb < 0 || a.minProb >= 1) throw Object.assign(new Error('动作阈值必须在 0% 到 99%'), { code: 'bad-gate' });
        body.min_prob = Math.round(a.minProb * 100) / 100;
      }
      if (a?.thresholdX !== undefined) {   // 幅度门槛 × 放松底噪：0–20 倍，null = 回到绝对微伏
        if (a.thresholdX !== null && (typeof a.thresholdX !== 'number' || !Number.isFinite(a.thresholdX) || a.thresholdX < 0 || a.thresholdX > 20)) throw Object.assign(new Error('幅度门槛倍数必须在 0 到 20'), { code: 'bad-gate' });
        body.threshold_x = a.thresholdX === null ? null : Math.round(a.thresholdX * 100) / 100;
      }
      if (threshold != null) body.threshold_uv = threshold;
      if (sensitivity != null) body.sensitivity = sensitivity;
      if (a?.mask != null) {   // 屏蔽坏路：1–8 的整数，最多 7 路
        if (!Array.isArray(a.mask) || a.mask.length > 7 || a.mask.some((l) => !Number.isInteger(l) || l < 1 || l > 8)) throw Object.assign(new Error('屏蔽的路必须是 1 到 8 的整数'), { code: 'bad-gate' });
        body.mask = [...new Set(a.mask)].sort((x, y) => x - y);
      }
    }
    return requestBound('POST', '/api/emg/wl8/live', str(id), body);
  }));

  // 经典 5 步（唯理上位机流程）：列串口、换手环数据串口、控制串口、导出这一组数据
  const SERIAL = /^\/dev\/(cu\.|tty\.|ttys)[\w.-]+$/;
  // selected：主进程当前手选的数据串口（'' = 自动），页面重挂载后下拉框按它显示
  ipcMain.handle('pt:emg8:ports', guarded(() => ({ list: require('node:fs').readdirSync('/dev').filter((n) => n.startsWith('cu.')).sort().map((n) => `/dev/${n}`), selected: deviceService?.serial?.() ?? '' })));
  ipcMain.handle('pt:emg8:dataPort', guarded((p) => {
    if (p !== '' && !(typeof p === 'string' && SERIAL.test(p))) throw Object.assign(new Error('串口路径不对'), { code: 'bad-port' });
    if (!deviceService?.setSerial) throw Object.assign(new Error('这个版本不能手选串口'), { code: 'unsupported' });
    stop(); deviceService.setSerial(p); return true;      // 收掉旧服务；页面随后「重新连接」用新串口起
  }));
  ipcMain.handle('pt:emg8:ctrl', guarded((id, a) => {
    const action = ['open', 'close', 'test'].includes(a?.action) ? a.action : null;
    if (!action) throw Object.assign(new Error('未知控制串口操作'), { code: 'bad-action' });
    const body = { action };
    if (action === 'open') {
      if (!(typeof a.port === 'string' && SERIAL.test(a.port))) throw Object.assign(new Error('串口路径不对'), { code: 'bad-port' });
      body.port = a.port; body.baud = a.baud === 9600 ? 9600 : 115200;
    }
    return requestBound('POST', '/api/emg/wl8/ctrl', str(id), body);
  }));
  // reveal=false 只回路径（连上页显示数据存在哪），true 再在访达里打开
  ipcMain.handle('pt:emg8:openData', guarded(async (reveal) => {
    if (!deviceService?.dir) throw Object.assign(new Error('没有本机工程'), { code: 'unsupported' });
    const dir = require('node:path').join(deviceService.dir, 'data', 'emg');
    if (reveal !== true) return dir;
    require('node:fs').mkdirSync(dir, { recursive: true });
    const err = await shell.openPath(dir); if (err) throw new Error(err); return dir;
  }));
  ipcMain.handle('pt:emg8:exportClassic', guarded(async (a) => {
    if (!deviceService?.dir) throw Object.assign(new Error('没有本机工程'), { code: 'unsupported' });
    const labels = validateLabels(a?.labels) ?? [];
    const runId = a?.runId == null ? '' : str(a.runId, 40);
    if (runId && (!/^[\w.-]+$/.test(runId) || /^\.+$/.test(runId))) throw Object.assign(new Error('模型编号不对'), { code: 'bad-run' });
    const { dialog } = require('electron'), fs = require('node:fs'), path = require('node:path');
    const opts = { title: '导出到目录', properties: ['openDirectory', 'createDirectory'] }, w = getWin();
    const pick = w ? await dialog.showOpenDialog(w, opts) : await dialog.showOpenDialog(opts);
    if (pick.canceled || !pick.filePaths[0]) return { canceled: true };
    const d = new Date(), two = (n) => String(n).padStart(2, '0');   // 本地时间，不用 UTC
    const stamp = `${d.getFullYear()}${two(d.getMonth() + 1)}${two(d.getDate())}-${two(d.getHours())}${two(d.getMinutes())}${two(d.getSeconds())}`;
    const out = path.join(pick.filePaths[0], `OpenEMG-经典16-${stamp}`);
    const data = path.join(deviceService.dir, 'data', 'emg');
    let files = 0;
    const copy = (from, to) => { if (!fs.existsSync(from)) return; fs.cpSync(from, to, { recursive: true }); files += fs.readdirSync(to).length; };
    for (const split of ['emg-wl8-data', 'emg-wl8-data-rewear']) for (const l of labels) copy(path.join(data, split, l), path.join(out, split, l));
    if (runId) copy(path.join(deviceService.dir, 'models', 'emg', 'wl8', runId), path.join(out, 'model', runId));
    if (!files) throw Object.assign(new Error('这一组还没有录音或模型可导出'), { code: 'empty' });
    shell.showItemInFolder(out);
    return { path: out, files };
  }));

  // 数据台：动作名 → 白名单路由（emg8-studio-routes.cjs）
  ipcMain.handle('pt:emg8:studio', guarded(async (id, op, a) => {
    const [method, path, body] = studioRoute(op, a);
    const r = await requestBound(method, path, str(id), body);
    // 导出写在工程 data/emg/exports；页面只拿文件名，主进程在访达里定位。
    if (op === 'exportTxt' && r?.path) { shell?.showItemInFolder?.(r.path); return { name: r.path.split('/').pop() }; }
    if (op === 'gestureDump' && r?.path) { shell?.showItemInFolder?.(r.path); return { name: String(r.path).split('/').pop(), samples: r.samples }; }
    if (op === 'gestureFewshot' && r?.artifact) r.artifact = String(r.artifact).split('/').pop();
    if (op === 'emgAnalysis' && r?.csv) r.csv = r.csv.split('/').pop();
    return r;
  }));

  // 光标：服务端移动中 3 秒没人读状态就回演练。心跳放主进程（窗口被挡住时页面定时器会被节流），App 退出时主动退回演练。
  let beat = null, cursorProject = '';
  const heartbeat = (mode) => {
    const live = mode === 'move' || mode === 'drag';                 // 拖拽模式同样要心跳，否则 3 秒后被看门狗松开
    if (live && !beat) beat = setInterval(() => requestBound('GET', '/api/emg/wl8/cursor').then((st) => { if (st.mode !== 'move' && st.mode !== 'drag') heartbeat(st.mode); }).catch(() => {}), 1000);
    if (!live && beat) { clearInterval(beat); beat = null; }
  };
  ipcMain.handle('pt:emg8:cursor', guarded(async (id, a) => {
    if (!CURSOR_ACTIONS.has(a?.action)) throw Object.assign(new Error('未知操作'), { code: 'bad-action' });
    const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : undefined);        // 范围由服务端夹住
    const bool = (v) => (typeof v === 'boolean' ? v : undefined);                             // 没给的开关不发，服务端保持原值
    cursorProject = str(id) || '';
    const st = await requestBound('POST', '/api/emg/wl8/cursor', cursorProject, { action: a.action, gain: num(a.gain), deadzone: num(a.deadzone), accel: num(a.accel), adaptive: bool(a.adaptive), soft: bool(a.soft), rezero: bool(a.rezero), click: bool(a.click), axis: a.axis === 'x' ? 'x' : 'y', stage: a.stage === 'drag' ? 'drag' : 'move' });
    heartbeat(st.mode); return st;
  }));
  // requestBound 会同步抛（换过工程 → wrong-project）：包进 Promise，退出时不留未捕获异常（复核 P2）
  require('electron').app.on('before-quit', () => { if (beat) Promise.resolve().then(() => requestBound('POST', '/api/emg/wl8/cursor', cursorProject, { action: 'log' })).catch(() => {}); heartbeat('off'); });

  // 实时流：同一时间只开一路
  let stream = null, generation = 0;
  const stop = () => { generation++; if (stream) { stream.req.destroy(); clearInterval(stream.timer); stream = null; } };
  ipcMain.handle('pt:emg8:streamStart', guarded(async (id) => {
    stop();
    const current = generation;
    // 工程服务分配端口；页面不提供任意地址或路径。
    if (deviceService) {
      let entry;
      try { entry = await deviceService.emg(id, 'open8'); } catch (e) { bindError = String(e?.message ?? e).slice(0, 200); throw e; }
      if (current !== generation) return true; // 离开页面时，不恢复已取消的数据流。
      port = Number(new URL(entry.url).port); boundProject = id; bindError = '';
    }
    const s = { emg: [], imu: [], preds: [], studio: [], cursor: null, idx: null, segment: null, dropped: 0, req: null, timer: null };
    const fail = (message) => {
      if (current !== generation) return;
      s.emg = []; s.imu = []; s.preds = []; s.studio = []; s.cursor = null;
      clearInterval(s.timer); send({ type: 'error', message });
    };
    s.req = http.get({ host: HOST, port, path: `/api/emg/stream8?${q({ project: str(id, 60) || '' })}` }, (res) => {
      // 主动重连会销毁旧请求；旧流的回调不能污染新连接的状态。
      if (current !== generation) { res.resume(); return; }
      if (res.statusCode !== 200) {
        let body = '';
        res.setEncoding('utf8');
        res.on('data', (c) => { body += c; });
        res.on('end', () => {
          if (current !== generation) return;
          let parsed = null;
          try { parsed = JSON.parse(body); } catch { parsed = null; }
          const code = parsed && typeof parsed.code === 'string' ? parsed.code : undefined;
          send({ type: 'error', code, message: (parsed && parsed.error) || `数据流被拒绝（${res.statusCode}）：工程或设备不匹配` });
        });
        return;
      }
      res.setEncoding('utf8'); let buf = '', kind = 'emg';
      res.on('data', (chunk) => {
        if (current !== generation) return;
        buf += chunk; let i;
        while ((i = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, i); buf = buf.slice(i + 1);
          if (line.startsWith('event:')) kind = line.slice(6).trim();
          else if (line.startsWith('data:')) {
            try {
              const p = JSON.parse(line.slice(5));
              if (kind === 'boundary') {
                s.emg = []; s.imu = []; s.preds = []; s.cursor = null; s.idx = null; s.segment = p.segment;
                send({ type: 'boundary' });
              }
              else if (kind === 'imu') s.imu.push(...p.samples);
              else if (kind === 'pred') s.preds.push(p);
              else if (kind === 'cursor') s.cursor = { mode: p.mode, vx: p.vx, vy: p.vy, score: p.score, button: p.button };   // 只留最新一条
              else if (STUDIO_EVENTS.has(kind)) s.studio.push(p);
              else if (kind === 'emg') {
                // 一次UI批次不能拼接两个采集段；序号缺口也作为边界。
                if ((s.segment !== null && s.segment !== p.segment) || (s.idx !== null && s.idx !== p.sample_index) || s.dropped !== p.dropped_frames) {
                  s.emg = []; s.imu = []; s.preds = []; s.cursor = null; send({ type: 'boundary' });
                }
                s.segment = p.segment; s.emg.push(...p.samples); s.idx = p.sample_index + p.samples.length; s.dropped = p.dropped_frames;
              }
            } catch { /* 半行，下次再拼 */ }
            kind = 'emg';
          }
        }
      });
      res.on('end', () => fail('采集服务数据流已断开，请重新连接手环'));
      res.on('error', () => fail('采集服务数据流异常，请重新连接手环'));
    });
    s.req.on('error', () => fail('采集服务暂时无法连接，请接好手环后重新连接'));
    s.timer = setInterval(() => {
      if (!s.emg.length && !s.imu.length && !s.preds.length && !s.cursor && !s.studio.length) return;
      send({ type: 'batch', emg: s.emg, imu: s.imu, preds: s.preds, cursor: s.cursor, studio: s.studio, sampleIndex: s.idx, dropped: s.dropped, t: Date.now() });
      s.emg = []; s.imu = []; s.preds = []; s.studio = []; s.cursor = null;
    }, 50);
    stream = s; return true;
  }));
  ipcMain.handle('pt:emg8:streamStop', guarded(() => { stop(); return true; }));
  return { stop };
}

module.exports = { registerEmg8, request };
