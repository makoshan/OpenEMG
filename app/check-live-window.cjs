const { app, BrowserWindow } = require('electron');
const path = require('node:path');
app.setPath('userData', path.resolve('build/live-check/userdata'));
app.whenReady().then(async () => {
  const win = new BrowserWindow({ width: 1100, height: 900, show: false, webPreferences: { backgroundThrottling: false } });
  await win.loadFile('build/live-dist/build/live-check/index.html');
  for (let i = 0; i < 900; i++) {   // 夹具本身约 40 s；机器忙时 setTimeout 会漂，留足余量
    await new Promise(r => setTimeout(r, 100));
    const result = await win.webContents.executeJavaScript('window.checkResult');
    if (result) {
      console.log(JSON.stringify({ ...result, text: undefined }));
      require('node:fs').writeFileSync('build/live-check/result.json', JSON.stringify(result));
      require('node:fs').writeFileSync('build/live-check/window.png', (await win.capturePage()).toPNG());
      app.exit(result.ok ? 0 : 1); return;
    }
  }
  console.error('真实页面检查超时'); app.exit(1);
}).catch(e => { console.error(e); app.exit(1); });
