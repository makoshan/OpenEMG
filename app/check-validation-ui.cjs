// 只运行独立测试窗口，媒体由页面夹具替代，绝不触碰已安装 App。
const {app, BrowserWindow} = require('electron');
app.setPath('userData', process.env.VALIDATION_TEST_USERDATA);
app.whenReady().then(() => {
  const w = new BrowserWindow({show: false, width:1100, height:900, webPreferences: {nodeIntegration: false, contextIsolation: true, backgroundThrottling: false}});
  w.webContents.on('console-message', (_e, _level, message) => {
    if (message === 'CAMERA_PREVIEW_SCREEN' && process.env.VALIDATION_TEST_SCREEN) void w.webContents.capturePage().then(image => require('node:fs').writeFileSync(process.env.VALIDATION_TEST_SCREEN, image.toPNG()));
    if (message.includes('PASS') || message.includes('FAIL')) console.log(message);
    if (message.includes('VALIDATION_UI_PASS')) app.exit(0);
    if (message.includes('VALIDATION_UI_FAIL')) app.exit(1);
  });
  w.loadFile(process.env.VALIDATION_TEST_HTML);
  setTimeout(() => {console.error('VALIDATION_UI_FAIL 超时'); app.exit(1);}, 45000);
});
