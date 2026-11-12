// 鼠标事件必须在 App 进程里发。采集用的 Python 没有 Quartz，勾选它也移动不了光标。
function addon() {
  if (process.platform !== 'darwin') throw Object.assign(new Error('手势鼠标目前只在 macOS 上发事件'), { code: 'mouse-platform' });
  try { return require('./emg8-mouse.node'); }
  catch { throw Object.assign(new Error('鼠标模块没有装进 OpenEMG'), { code: 'mouse-module' }); }
}

function post(action, dx, dy) {
  addon().post(action, dx, dy);
}

module.exports = { post, where: () => addon().where() };
