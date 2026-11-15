// 页面只拿到工程 id 和肌电白名单动作（与 PrintThings desktop/preload.cjs 的 emg8 段同一份接口）
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('pt', {
  isDesktop: true,
  projectId: ipcRenderer.sendSync('yuanli:projectId'),
  device: {
    get: () => ipcRenderer.invoke('yuanli:device:get'),
    set: (d) => ipcRenderer.invoke('yuanli:device:set', d),
  },
  // 单通道（Cheez + ESP32-S3）工作室：与 PrintThings desktop/preload.cjs 的 emg1 段同一份接口
  emg1: {
    state: (a) => ipcRenderer.invoke('pt:emg1:state', a),
    record: (id, a) => ipcRenderer.invoke('pt:emg1:record', id, a),
    recordStop: (id) => ipcRenderer.invoke('pt:emg1:recordStop', id),
    train: (id, a) => ipcRenderer.invoke('pt:emg1:train', id, a),
    live: (id, a) => ipcRenderer.invoke('pt:emg1:live', id, a),
    guideUrl: () => ipcRenderer.invoke('pt:emg1:guideUrl'),
    streamStart: (id) => ipcRenderer.invoke('pt:emg1:streamStart', id),
    streamStop: () => ipcRenderer.invoke('pt:emg1:streamStop'),
    onEvent(cb) {
      const h = (_e, ev) => { if (ev && typeof ev === 'object') cb(ev); };
      ipcRenderer.on('pt:emg1:event', h);
      return () => ipcRenderer.removeListener('pt:emg1:event', h);
    },
  },
  // 云端上传（electron/cloud.cjs）：只给状态和四个动作，令牌不出主进程
  cloud: {
    state: () => ipcRenderer.invoke('yuanli:cloud:state'),
    consent: (v) => ipcRenderer.invoke('yuanli:cloud:consent', v),
    revoke: () => ipcRenderer.invoke('yuanli:cloud:revoke'),
    sync: () => ipcRenderer.invoke('yuanli:cloud:sync'),
  },
  // 结印小游戏（electron/game.cjs）：开窗口、送手印；手印名只认 sword / guard / thunder
  game: {
    open: () => ipcRenderer.invoke('yuanli:game:open'),
    gesture: (g, conf) => ipcRenderer.invoke('yuanli:game:gesture', g, conf),
    band: (s) => ipcRenderer.invoke('yuanli:game:band', s),   // 手环状态：连没连、认成什么、倾角；只显示，不出招
  },
  emg8: {
    validation: (id, a) => ipcRenderer.invoke('pt:emg8:validation', id, a),
    state: () => ipcRenderer.invoke('pt:emg8:state'),
    abState: (a) => ipcRenderer.invoke('pt:emg8:abState', a),
    ab: (id, a) => ipcRenderer.invoke('pt:emg8:ab', id, a),
    record: (id, a) => ipcRenderer.invoke('pt:emg8:record', id, a),
    recordStop: (id) => ipcRenderer.invoke('pt:emg8:recordStop', id),
    action: (id, a) => ipcRenderer.invoke('pt:emg8:action', id, a),
    access: (prompt) => ipcRenderer.invoke('pt:emg8:access', prompt === true),
    train: (id, a) => ipcRenderer.invoke('pt:emg8:train', id, a),
    runs: () => ipcRenderer.invoke('pt:emg8:runs'),
    run: (rid) => ipcRenderer.invoke('pt:emg8:run', rid),
    live: (id, a) => ipcRenderer.invoke('pt:emg8:live', id, a),
    cursor: (id, a) => ipcRenderer.invoke('pt:emg8:cursor', id, a),
    streamStart: (id) => ipcRenderer.invoke('pt:emg8:streamStart', id),
    streamStop: () => ipcRenderer.invoke('pt:emg8:streamStop'),
    studio: (id, op, a) => ipcRenderer.invoke('pt:emg8:studio', id, op, a),
    ports: () => ipcRenderer.invoke('pt:emg8:ports'),
    dataPort: (p) => ipcRenderer.invoke('pt:emg8:dataPort', p),
    ctrl: (id, a) => ipcRenderer.invoke('pt:emg8:ctrl', id, a),
    openData: (reveal) => ipcRenderer.invoke('pt:emg8:openData', reveal === true),
    exportClassic: (a) => ipcRenderer.invoke('pt:emg8:exportClassic', a),
    onEvent(cb) {
      const h = (_e, ev) => { if (ev && typeof ev === 'object') cb(ev); };
      ipcRenderer.on('pt:emg8:event', h);
      return () => ipcRenderer.removeListener('pt:emg8:event', h);
    },
  },
});
