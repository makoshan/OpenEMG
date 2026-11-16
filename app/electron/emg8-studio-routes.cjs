'use strict';
// EMG Studio 新路由白名单（原力手环 host/studio_api.py ROUTES）：页面只给动作名与受限参数，方法、路径、请求体在这里拼。
// 主进程（emg8-ipc.cjs）与浏览器试用台共用这一份；scripts/check-emg8-studio.mjs 逐条核对路径与必失败样本。

const str = (v, max = 200) => (typeof v === 'string' ? v.slice(0, max) : undefined);
const int = (v, lo, hi, d) => (Number.isInteger(v) && v >= lo && v <= hi ? v : d);
const num = (v, lo, hi, d) => (typeof v === 'number' && Number.isFinite(v) && v >= lo && v <= hi ? v : d);
const q = (o) => Object.entries(o).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
const fail = (message, code) => { throw Object.assign(new Error(message), { code }); };
const rel = (v) => { const s = str(v, 240); if (!s || s.startsWith('/') || s.includes('\\') || s.split('/').includes('..')) fail('文件必须是数据目录内的相对路径', 'bad-file'); return s; };
const name = (v) => { const s = str(v, 60); if (!s || !/^[\w\-\u4e00-\u9fff]+$/.test(s)) fail('名字只能用字母、数字、中文、下划线和短横线', 'bad-name'); return s; };
const FEATURE_MODES = new Set(['bands5', 'hudgins', 'combined']);
const featureMode = (v) => {
  if (v == null || v === '') return 'bands5';
  if (typeof v !== 'string' || !FEATURE_MODES.has(v)) fail('特征只能是 bands5、hudgins、combined', 'bad-feature');
  return v;
};
const labelsOf = (v) => {
  if (!Array.isArray(v) || v.length < 2 || v.length > 32) fail('至少要有两类', 'bad-label');
  const out = v.map((l) => name(l));
  if (new Set(out).size !== out.length) fail('标签重复', 'bad-label');
  return out;
};
const kOf = (v) => {
  if (v == null) return 1;
  if (!Number.isInteger(v) || v < 1 || v > 20) fail('k 必须是 1 到 20 的整数', 'bad-k');
  return v;
};

const STUDIO = {
  deviceState: () => ['GET', '/api/device/state'],
  deviceConfig: () => ['GET', '/api/device/config'],
  deviceConfigPut: (a) => {
    const body = {};
    if (a?.fsHz !== undefined) {
      if (!Number.isInteger(a.fsHz) || ![500, 1000, 2000].includes(a.fsHz)) fail('采样率只能是 500、1000 或 2000 Hz', 'bad-fs');
      body.fs_Hz = a.fsHz;
    }
    if (Array.isArray(a?.channels)) {
      body.channels = a.channels.slice(0, 64).map((c) => ({ index: int(c?.index, 0, 63, -1), label: str(c?.label, 24), enabled: typeof c?.enabled === 'boolean' ? c.enabled : undefined }));
    }
    return ['PUT', '/api/device/config', body];
  },
  devicePinout: (a) => ['GET', `/api/device/pinout${a?.deviceId ? `?${q({ device_id: name(a.deviceId) })}` : ''}`],
  c08bReg: (a) => {
    const op = typeof a?.op === 'string' ? a.op.trim().toLowerCase() : 'state';
    if (!['state', 'rreg', 'wreg', 'clro'].includes(op)) fail('未知寄存器操作（仅限 state / rreg / wreg / clro）', 'bad-reg-op');
    if (op === 'state' || op === 'clro') return ['POST', '/api/device/c08b_reg', { op }];
    const chip = typeof a?.chip === 'string' ? a.chip.trim().toLowerCase() : 'both';
    if (!['u1', 'u2', 'both'].includes(chip)) fail('芯片选择只能是 u1、u2 或 both', 'bad-chip');
    let addr = a?.addr;
    if (typeof addr === 'string') {
      const s = addr.trim();
      if (!/^(0x[0-9a-fA-F]{1,2}|\d{1,2}|[A-Za-z0-9_]{2,16})$/.test(s)) fail('寄存器地址格式无效', 'bad-addr');
      addr = s;
    } else if (!Number.isInteger(addr) || addr < 0 || addr > 0x19) {
      fail('寄存器地址必须在 0x00 到 0x19 之间', 'bad-addr');
    }
    if (op === 'rreg') return ['POST', '/api/device/c08b_reg', { op, chip, addr }];
    let val = a?.val;
    if (typeof val === 'string') {
      const vs = val.trim();
      if (!/^(0x[0-9a-fA-F]{1,2}|\d{1,3})$/.test(vs)) fail('寄存器写入值必须是 0x00..0xFF 十六进制或 0..255 整数', 'bad-val');
      val = Number.parseInt(vs, vs.toLowerCase().startsWith('0x') ? 16 : 10);
    }
    if (!Number.isInteger(val) || val < 0 || val > 0xFF) fail('寄存器写入值超出 0x00..0xFF', 'bad-val');
    return ['POST', '/api/device/c08b_reg', { op, chip, addr, val }];
  },
  bringupDecode: (a) => {
    const sample = a?.sample == null || a.sample === '' ? undefined : name(a.sample);
    const hex = a?.hex == null ? '' : str(a.hex, 512).trim();
    if (!sample && (!hex || !/^[0-9a-fA-F\s:xX\-]+$/.test(hex))) fail('自检报文只能包含十六进制字符', 'bad-hex');
    return ['POST', '/api/device/bringup_decode', sample ? { sample } : { hex }];
  },
  sessionStart: (a) => ['POST', '/api/session/start', { subject: str(a?.subject, 40) || 'S', donning: int(a?.donning, 1, 99, 1), hand: a?.hand === 'right' ? 'right' : 'left', placement: str(a?.placement, 80) || '', notes: str(a?.notes, 200) || '' }],
  sessionStop: () => ['POST', '/api/session/stop', {}],
  takeStart: (a) => ['POST', '/api/take/start', { label: name(a?.label), seconds: a?.seconds == null ? null : num(a.seconds, 0.2, 600, 2) }],
  takeStop: () => ['POST', '/api/take/stop', {}],
  takeMark: (a) => ['POST', '/api/take/mark', { label: str(a?.label, 40) || 'mark', source: 'app' }],
  files: (a) => ['GET', `/api/files/list${a?.session ? `?${q({ session: name(a.session) })}` : ''}`],
  fileOpen: (a) => ['GET', `/api/files/open?${q({ file: rel(a?.file), from: int(a?.from, 0, 1e9, 0), decim: int(a?.decim, 1, 1000, 1), ...(Number.isInteger(a?.to) ? { to: int(a.to, 1, 1e9, 1) } : {}) })}`],
  exportTxt: (a) => ['POST', '/api/files/export_txt', { file: rel(a?.file), converted: a?.converted !== false }],
  datasets: () => ['GET', '/api/dataset/list'],
  datasetSave: (a) => ['PUT', '/api/dataset/save', { name: name(a?.name), label_map: a?.labelMap && typeof a.labelMap === 'object' ? Object.fromEntries(Object.entries(a.labelMap).slice(0, 64).map(([k, v]) => [str(k, 40), v === null ? null : str(v, 40)])) : {} }],
  trainStart: (a) => {
    const dataset = name(a?.dataset);
    const mode = featureMode(a?.featureMode);
    if (mode !== 'bands5' && a?.trainer === 'cnn') fail('CNN 只用原始窗', 'bad-feature');
    const body = { dataset, trainer: a?.trainer === 'cnn' ? 'cnn' : 'lda', seed: int(a?.seed, 0, 1e6, 0), epochs: int(a?.epochs, 1, 400, 40) };
    if (a?.featureMode) body.feature_mode = mode;
    return ['POST', '/api/train/start', body];
  },
  trainRuns: () => ['GET', '/api/train/runs'],
  trainFreeze: (a) => ['POST', '/api/train/freeze', { run_id: name(a?.runId) }],
  stats: (a) => ['GET', `/api/plugin/stats?${q({ window_s: num(a?.windowS, 0.1, 5, 1) })}`],
  emgAnalysis: (a) => ['POST', '/api/plugin/emg_analysis', { file: rel(a?.file) }],
  rules: () => ['GET', '/api/rules'],
  rulesPut: (a) => ['PUT', '/api/rules', { rules: Array.isArray(a?.rules) ? a.rules.slice(0, 32) : [] }],
  lsl: (a) => ['PUT', '/api/lsl', { enabled: a?.enabled === true }],
  gestureState: () => ['GET', '/api/gesture/state'],
  gestureGate: (a) => {
    const uv = a?.minRmsUv;
    if (typeof uv !== 'number' || !Number.isFinite(uv) || uv < 0 || uv > 5000) fail('能量门必须是 0 到 5000', 'bad-gate');
    const rest = a?.restLabel == null || a.restLabel === '' ? undefined : name(a.restLabel);
    return ['PUT', '/api/gesture/gate', { min_rms_uv: uv, ...(rest ? { rest_label: rest } : {}) }];
  },
  gestureFewshot: (a) => {
    const body = { feature_mode: featureMode(a?.featureMode), k: kOf(a?.k) };
    if (typeof a?.dataset === 'string' && a.dataset) body.dataset = name(a.dataset);
    else body.labels = labelsOf(a?.labels);
    return ['POST', '/api/gesture/fewshot', body];
  },
  gestureDump: () => ['POST', '/api/gesture/blackbox/dump', {}],
};

/** 动作名 → [方法, 路径, 请求体]；未知动作与越界参数直接抛错，不发请求 */
const studioRoute = (op, a) => {
  if (typeof op !== 'string' || !Object.hasOwn(STUDIO, op)) fail('未知操作', 'bad-action');
  return STUDIO[op](a);
};

// 服务端 SSE 里属于数据台的命名事件；其余未知事件丢弃，不当 EMG 帧解析
const STUDIO_EVENTS = new Set(['gate', 'take', 'train', 'rule', 'lsl']);

module.exports = { STUDIO, STUDIO_EVENTS, studioRoute };
