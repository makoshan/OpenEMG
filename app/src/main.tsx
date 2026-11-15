import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { EmgStudio } from './emg8/studio';
import { SingleStudio } from './emg8/single';
import { emg8Bridge } from './emg8/contract';
import { WebCapture } from './web';
import { CloudBar } from './cloud';
import './tokens.css';
import './app.css';

// 单机版只有一个工程；id 由主进程建好后注入（window.pt.projectId），页面原样复用肌电工作室
type DeviceBridge = { get: () => Promise<{ ok: boolean; value?: { device: string } }>; set: (device: string) => Promise<{ ok: boolean; value?: { device: string } }> };
const pt = (window as unknown as { pt?: { projectId?: string; device?: DeviceBridge } }).pt;

// 设备档位：16 通道（双 ADS1298）/ 8 通道（唯理手环或单 ADS1298）/ 2 通道（ADS1292）/ 单通道（Cheez + ESP32-S3）
type Device = 'c08b-16ch' | 'wl8' | 'c08b-8ch' | 'c08b-2ch' | 'emg';
const DEVICES: { id: Device; label: string }[] = [
  { id: 'c08b-16ch', label: '16 通道 · OpenEMG 双 ADS1298' },
  { id: 'wl8', label: '8 通道 · 唯理肌电手环' },
  { id: 'c08b-8ch', label: '8 通道 · OpenEMG 单 ADS1298' },
  { id: 'c08b-2ch', label: '2 通道 · OpenEMG ADS1292' },
  { id: 'emg', label: '单通道 · Cheez + ESP32-S3' },
];
const VALID_DEVICES = new Set<string>(DEVICES.map((d) => d.id));
const KEY = 'yuanli-device';

function App() {
  const [device, setDevice] = useState<Device>(() => {
    try {
      const saved = localStorage.getItem(KEY);
      return saved && VALID_DEVICES.has(saved) ? (saved as Device) : 'wl8';
    } catch { return 'wl8'; }
  });
  useEffect(() => {
    if (!pt?.device || device === 'emg') return;
    void pt.device.set(device);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!emg8Bridge() || !pt?.projectId) return <WebCapture />;          // 普通浏览器：网页版直连串口
  const pick = (d: Device) => {
    setDevice(d);
    try { localStorage.setItem(KEY, d); } catch { /* 无存储 */ }
    if (d !== 'emg' && pt?.device) void pt.device.set(d);
  };
  const slot = <select className="yuanli-device-select" aria-label="设备" value={device} onChange={(e) => pick(e.target.value as Device)}>
    {DEVICES.map((d) => <option key={d.id} value={d.id}>{d.label}</option>)}
  </select>;
  // 云端上传目前只传多通道手环录音，单通道不显示
  const multiSlot = <span className="yuanli-top-slot">{slot}<CloudBar /></span>;
  return device !== 'emg'
    ? <EmgStudio projectId={pt.projectId} deviceTier={device} deviceSlot={multiSlot} />
    : <SingleStudio projectId={pt.projectId} deviceSlot={slot} />;
}

createRoot(document.getElementById('root')!).render(<div className="v3"><App /></div>);
