// 只运行独立测试窗口，媒体由页面夹具替代，绝不触碰已安装 App。
const {app, BrowserWindow} = require('electron');
app.setPath('userData', process.env.FILTER_TEST_USERDATA);
app.whenReady().then(() => {
  const w = new BrowserWindow({show: false, webPreferences: {nodeIntegration: false, contextIsolation: true, backgroundThrottling: false}});
  w.webContents.on('console-message', (_e, _level, message) => {
    if (message.includes('PASS') || message.includes('FAIL')) console.log(message);
    if (message.includes('FILTER_UI_PASS')) { w.webContents.capturePage().then(image => { if (process.env.FILTER_TEST_SCREEN) require('node:fs').writeFileSync(process.env.FILTER_TEST_SCREEN, image.toPNG()); app.exit(0); }); }
    if (message.includes('FILTER_UI_FAIL')) app.exit(1);
  });
  w.loadFile(process.env.FILTER_TEST_HTML);
  setTimeout(() => {console.error('FILTER_UI_FAIL 超时'); app.exit(1);}, 25000);
});
