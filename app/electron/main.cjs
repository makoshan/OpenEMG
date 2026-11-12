// OpenEMG 单机 App：一个窗口 + 一个本机采集服务。八通道 emg8-server.py → host/emg_web.py --wl8；单通道（Cheez）emg1-server.py → host/emg_web.py。
// 页面和 PrintThings 的肌电工作室同一套；这里只做三件事：建本机工程、起采集服务、把 emg8-ipc 接上。
const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { registerEmg8 } = require('./emg8-ipc.cjs');
const { registerEmg1 } = require('./emg8-single-ipc.cjs');
const { createCloud } = require('./cloud.cjs');
const { registerGame } = require('./game.cjs');
// 云端平台地址；自检时可指到本机 vibe-hw platform/server.mjs
const PLATFORM = process.env.YUANLI_PLATFORM ?? '';

// 打包后用 Resources 里自带的 Python 和 host/（scripts/bundle-python.sh）；开发时用 Mako 本机训练环境和本仓 host/
const RES = app.isPackaged ? process.resourcesPath : null;
const PY = process.env.YUANLI_PY ?? (RES ? path.join(RES, 'python', 'bin', 'python3') : (fs.existsSync(path.resolve(__dirname, '..', '..', '.venv', 'bin', 'python')) ? path.resolve(__dirname, '..', '..', '.venv', 'bin', 'python') : 'python3'));
const HOST_DIR = process.env.YUANLI_HOST ?? (RES ? path.join(RES, 'host') : path.resolve(__dirname, '..', '..', 'host'));
const DEV_URL = process.env.YUANLI_DEV_URL;           // 开发时指向 vite（npm run dev），否则读 dist/
// YUANLI_FAKE=1：合成台架；emg_web 不许假台架写工程：八通道会停在连接步，只看报错链路；单通道不带 --project、数据写 userData/fake-single（只给自检用）；YUANLI_REPLAY=<录音.npz>：按原速回放推流，能连能看不能录；YUANLI_USERDATA：自检用临时数据目录
// 2026-10-16 改名 OpenEMG：数据目录仍用旧名，已录工程、模型、云端令牌和页面设置原地可用，不搬家
app.setPath('userData', path.join(app.getPath('appData'), '原力手环'));
if (process.env.YUANLI_USERDATA) app.setPath('userData', process.env.YUANLI_USERDATA);

// 本机唯一工程：emg_web.py 只认 printthings-project 格式，数据和模型都落在这个目录里
function ensureProject() {
  const dir = path.join(app.getPath('userData'), 'project');
  const file = path.join(dir, 'project.json');
  if (!fs.existsSync(file)) {
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(file, JSON.stringify({ format: 'printthings-project', projectId: randomUUID(), name: 'OpenEMG' }, null, 2));
  }
  return { dir, id: JSON.parse(fs.readFileSync(file, 'utf8')).projectId };
}

const freePort = () => new Promise((resolve, reject) => {
  const s = net.createServer(); s.unref(); s.on('error', reject);
  s.listen(0, '127.0.0.1', () => { const { port } = s.address(); s.close(() => resolve(port)); });
});

// 采集服务只起一个（串口独占）；页面连手环时才起。kind：'wl8' 八通道 / 'emg' 单通道，换设备先收掉旧的再起新的
let collector = null;
let serialPort = '';      // 经典 5 步里手选的手环数据串口；空 = 按 VID 自动找
// gone：上一个服务的进程彻底退出（或根本没起）才兑现。新服务排在它后面，快速 八→单→八 也不会两个进程同时开串口
let gone = Promise.resolve();
const ENTRY = { wl8: 'emg8-server.py', emg: 'emg1-server.py' };
function startCollector(project, kind = 'wl8') {
  if (collector?.kind === kind) return collector.ready;
  collector?.child?.kill();
  const before = gone;
  let release;
  gone = new Promise((r) => { release = r; });
  // self：旧服务的 exit 晚到时只清自己，不能把新起的那个从 collector 上摘掉（否则两路抢同一串口）
  const self = collector = { kind, child: null, ready: null };
  self.ready = (async () => {
    await before;
    if (!fs.existsSync(PY)) throw Object.assign(new Error(`没找到 Python：${PY}`), { code: 'toolchain' });
    const port = await freePort();
    // 排队期间又换了设备：不再起这一个
    if (collector !== self) throw Object.assign(new Error('已切换到另一种设备'), { code: 'superseded' });
    // YUANLI_DEVICE=wl18：八通道入口改连唯理 18 通道腕带（emg_web 的 --device 优先于 --wl8）；页面还按 8 路画，先只给开发自测录制
    // -I：不读用户机器上的 PYTHONPATH / 用户 site-packages，只用自带的库；-u：日志不缓冲，才能及时看到就绪行
    const fake1 = kind === 'emg' && process.env.YUANLI_FAKE;
    const where = fake1 ? ['--fake', '--data', path.join(app.getPath('userData'), 'fake-single')] : ['--project', project.dir];
    const child = spawn(PY, ['-I', '-B', '-u', path.join(__dirname, ENTRY[kind]), '--firmware-root', HOST_DIR, '--port', String(port), ...where, ...(kind === 'wl8' && process.env.YUANLI_FAKE ? ['--fake'] : []), ...(kind === 'wl8' && serialPort ? ['--serial', serialPort] : []), ...(kind === 'wl8' && process.env.YUANLI_REPLAY ? ['--replay', process.env.YUANLI_REPLAY] : []), ...(kind === 'wl8' && process.env.YUANLI_DEVICE ? ['--device', process.env.YUANLI_DEVICE] : [])],
      { cwd: HOST_DIR, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] });
    self.child = child;
    child.once('exit', release); child.once('error', release);   // 起不来时只有 error 没有 exit
    await new Promise((resolve, reject) => {
      let out = '';
      // 平时约 7 秒；装好后第一次打开，macOS 要逐个扫描几百个库文件，实测可到 30 秒
      const timer = setTimeout(() => reject(new Error(`采集服务 60 秒没起来：${out.trim().split('\n').pop() ?? ''}`)), 60000);
      const feed = (d) => { out += d; process.stdout.write(d); if (out.includes('MAKO emg collector: http://127.0.0.1:')) { clearTimeout(timer); resolve(); } };
      child.stdout.on('data', feed); child.stderr.on('data', feed);
      child.on('error', (e) => { clearTimeout(timer); if (collector === self) collector = null; reject(e); });
      child.on('exit', (code) => { clearTimeout(timer); if (collector === self) collector = null; reject(new Error(`采集服务退出了（${code}）：${out.trim().split('\n').pop() ?? ''}`)); });
    });
    return { url: `http://127.0.0.1:${port}` };
  })();
  // 没起出进程（排队被换掉、找不到 Python 等）时 exit 永远不来，在这里放行后面的服务
  self.ready.catch(() => { if (self.child) self.child.kill(); else release(); if (collector === self) collector = null; });
  return self.ready;
}

let win = null, baseUrl = '';
const guarded = (fn) => async (e, ...args) => {
  if (!String(e.senderFrame?.url ?? '').startsWith(baseUrl)) return { ok: false, code: 'forbidden', message: '发送方不是本机页面' };
  try { return { ok: true, value: await fn(...args) }; }
  catch (err) { return { ok: false, code: err.code ?? 'error', message: String(err.message ?? err) }; }
};

app.whenReady().then(() => {
  const project = ensureProject();
  // 关于窗口可核对安装来源；旧开发包没有清单时如实显示开发版。
  const buildFile = path.join(process.resourcesPath, 'build-info.json');
  const revision = app.isPackaged && fs.existsSync(buildFile) ? JSON.parse(fs.readFileSync(buildFile, 'utf8')).commit.slice(0, 7) : '开发版';
  app.setAboutPanelOptions({ applicationName: 'OpenEMG', applicationVersion: app.getVersion() + ' · ' + revision });
  // 预加载脚本拿工程 id 用（同步，只此一个值）
  ipcMain.on('yuanli:projectId', (e) => { e.returnValue = project.id; });
  // 设备服务：op 'open8' 起八通道（emg8-ipc），'open' 起单通道（emg8-single-ipc）；同 PrintThings device-service 的约定
  const deviceService = {
    emg: (id, op) => { if (id !== project.id) throw Object.assign(new Error('不是本机工程'), { code: 'wrong-project' }); return startCollector(project, op === 'open' ? 'emg' : 'wl8'); },
    dir: project.dir,
    serial: () => serialPort,
    // 换数据串口：记下来并收掉正在跑的八通道服务，下次 open8 带 --serial 重起
    setSerial: (p) => { serialPort = p; if (collector?.kind === 'wl8') { collector.child?.kill(); collector = null; } },
  };
  registerEmg8({ ipcMain, guarded, getWin: () => win, deviceService });
  registerEmg1({ ipcMain, guarded, getWin: () => win, deviceService });
  const game = registerGame({ ipcMain, guarded });   // 结印小游戏窗口（electron/game.cjs）
  // 云端上传：令牌在 userData/cloud.json，不进页面；同意后每分钟扫一次新录音
  const cloud = createCloud({ stateFile: path.join(app.getPath('userData'), 'cloud.json'), dataRoot: path.join(project.dir, 'data', 'emg'), base: PLATFORM });
  ipcMain.handle('yuanli:cloud:state', guarded(() => cloud.status()));
  ipcMain.handle('yuanli:cloud:consent', guarded(async (v) => { await cloud.consent(v); void cloud.sync(); return cloud.status(); }));   // 第一轮放后台传，按钮不用等
  ipcMain.handle('yuanli:cloud:revoke', guarded(() => cloud.revoke()));
  ipcMain.handle('yuanli:cloud:sync', guarded(() => cloud.sync()));
  setInterval(() => { if (cloud.status().consented) void cloud.sync(); }, 60000).unref();
  win = new BrowserWindow({ width: 1400, height: 900, title: 'OpenEMG',
    // 游戏在前台时，识别页仍需按时处理50ms预测，不能按后台页面节流。
    webPreferences: { backgroundThrottling: false, preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, sandbox: false } });
  baseUrl = DEV_URL ? new URL(DEV_URL).origin + '/' : pathToFileURL(path.resolve(__dirname, '..', 'dist')).href + '/';   // 中文路径会被转义，比较前统一成 URL 形式
  if (DEV_URL) win.loadURL(DEV_URL); else win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  win.on('closed', () => game.close());   // 关主窗口连带关游戏窗口，App 随之退出
});

app.on('window-all-closed', () => app.quit());
app.on('will-quit', () => { collector?.child?.kill(); });
