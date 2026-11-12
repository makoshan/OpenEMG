import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { EmgStudio } from './emg8/studio';
import { SingleStudio } from './emg8/single';
import { emg8Bridge } from './emg8/contract';
import { WebCapture } from './web';
import { CloudBar } from './cloud';
import './tokens.css';
import './app.css';

// 单机版只有一个工程；id 由主进程建好后注入（window.pt.projectId），页面原样复用 PrintThings 的肌电工作室
const pt = (window as unknown as { pt?: { projectId?: string } }).pt;

// 设备：八通道（唯理手环）/ 单通道（Cheez + ESP32-S3）。两个工作室同一套外观，选择放进各自顶栏；记住上次的选择
type Device = 'wl8' | 'emg';
const KEY = 'yuanli-device';

function App() {
  const [device, setDevice] = useState<Device>(() => { try { return localStorage.getItem(KEY) === 'emg' ? 'emg' : 'wl8'; } catch { return 'wl8'; } });
  if (!emg8Bridge() || !pt?.projectId) return <WebCapture />;          // 普通浏览器：网页版直连串口
  const pick = (d: Device) => { setDevice(d); try { localStorage.setItem(KEY, d); } catch { /* 无存储 */ } };
  const slot = <select aria-label="设备" value={device} onChange={(e) => pick(e.target.value as Device)}>
    <option value="wl8">八通道 · 唯理肌电手环</option><option value="emg">单通道 · Cheez + ESP32-S3</option></select>;
  // 云端上传目前只传八通道录音，所以只在八通道工作室顶栏出现
  const wl8Slot = <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>{slot}<CloudBar /></span>;
  return device === 'wl8' ? <EmgStudio projectId={pt.projectId} deviceSlot={wl8Slot} /> : <SingleStudio projectId={pt.projectId} deviceSlot={slot} />;
}

createRoot(document.getElementById('root')!).render(<div className="v3"><App /></div>);
