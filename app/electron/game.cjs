// 结印小游戏窗口：掌中天劫的构建产物（app/game/tianjie/）；源码在本仓 game/tianjie/，`npm run app` 重新构建并拷过来。
// 主进程只做两件事：开游戏窗口；把识别页认到的手印送进游戏（游戏自己校验冷却、灵力和置信度 0.8–1）。
const path = require('node:path');
const { BrowserWindow, session } = require('electron');

// 只放行游戏认识的三个手印名，避免拼进 executeJavaScript 的内容被页面以外的东西左右
const GESTURES = new Set(['sword', 'guard', 'thunder']);

function registerGame({ ipcMain, guarded }) {
  let gameWin = null, blocked = 0;
  ipcMain.handle('yuanli:game:open', guarded(() => {
    if (gameWin && !gameWin.isDestroyed()) { gameWin.focus(); return true; }
    // 游戏页不需要任何 Node / 预加载能力：开沙箱、隔离上下文
    // 独立会话分区，拦掉所有外网请求：游戏完全离线（它的样式会去 Google 拉字体，拦掉后用系统字体，不外发本机 IP）
    const ses = session.fromPartition('yuanli-game');
    ses.webRequest.onBeforeRequest({ urls: ['http://*/*', 'https://*/*', 'ws://*/*', 'wss://*/*'] }, (d, cb) => { blocked++; cb({ cancel: true }); });
    gameWin = new BrowserWindow({ width: 1280, height: 800, title: '掌天诀 · 结印', webPreferences: { contextIsolation: true, sandbox: true, session: ses } });
    // 只许停在本地游戏页：不开新窗口、不跳走
    gameWin.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
    gameWin.webContents.on('will-navigate', (e) => e.preventDefault());
    gameWin.on('closed', () => { gameWin = null; });
    gameWin.loadFile(path.join(__dirname, '..', 'game', 'tianjie', 'index.html'));
    return true;
  }));
  // 返回明确的接受状态和原因，界面与实际判定一致。
  ipcMain.handle('yuanli:game:gesture', guarded(async (gesture, confidence) => {
    if (!GESTURES.has(gesture) || !Number.isFinite(confidence)) throw Object.assign(new Error('手印名或置信度不合法'), { code: 'bad-input' });
    if (!gameWin || gameWin.isDestroyed()) return { accepted: false, code: 'closed', message: '游戏未打开，请先打开结印游戏' };
    const detail = JSON.stringify({ gesture, confidence: Math.max(0, Math.min(1, confidence)) });
    return await gameWin.webContents.executeJavaScript(`window.TianjieGame?.inputResult ? window.TianjieGame.inputResult(${detail}) : ({accepted:false,code:'loading',message:'游戏尚未就绪或版本不匹配，请重新打开游戏'})`);
  }));
  // 手环实时状态（识别页约 100 ms 一次）：只挑已知字段重新拼，游戏那边 parseBand 再校验一遍
  const STATES = new Set(['off', 'link', 'live', 'paused']), POSES = new Set(['', ...GESTURES]);
  ipcMain.handle('yuanli:game:band', guarded(async (s) => {
    if (!s || !STATES.has(s.state) || typeof s.text !== 'string' || !POSES.has(s.pose ?? '')) throw Object.assign(new Error('手环状态不合法'), { code: 'bad-input' });
    if (!gameWin || gameWin.isDestroyed()) return 'closed';
    const acc = Array.isArray(s.acc) && s.acc.length === 3 && s.acc.every(Number.isFinite) ? s.acc : null;
    // 面板字段可选：2/8/16 路状态只许 ok / mask / bad / ''，两句文字截 40 字；不合法就不带，游戏照旧只显示一行
    const lanes = Array.isArray(s.lanes) && s.lanes.length >= 2 && s.lanes.length <= 16 && s.lanes.every((x) => ['ok', 'mask', 'bad', ''].includes(x)) ? s.lanes : undefined;
    const str = (v) => (typeof v === 'string' ? v.slice(0, 40) : undefined);
    const detail = JSON.stringify({ state: s.state, text: s.text.slice(0, 40), pose: s.pose ?? '', acc, lanes, signal: str(s.signal), rec: str(s.rec) });
    return Boolean(await gameWin.webContents.executeJavaScript(`window.TianjieGame?.band ? window.TianjieGame.band(${detail}) : false`));
  }));
  // close：主窗口关掉时一并关游戏窗口，不留一个还在放音乐的孤窗（Mako 2026-10-17）
  return { blockedRequests: () => blocked, close: () => { if (gameWin && !gameWin.isDestroyed()) gameWin.close(); } };   // blockedRequests 冒烟检查用
}

module.exports = { registerGame };
