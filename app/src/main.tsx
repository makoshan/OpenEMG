import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { EmgStudio } from './emg8/studio';
import { SingleStudio } from './emg8/single';
import { emg8Bridge } from './emg8/contract';
import { WebCapture } from './web';
import { CloudBar } from './cloud';
import './tokens.css';
import './app.css';

// 单机版只有一个工程；id 与初始设备档位由主进程同步注入，消除冷启动双起 Python 采集进程
type InitialDeviceInfo = { device: string; forced?: boolean; persisted?: boolean };
type DeviceBridge = { get: () => Promise<{ ok: boolean; value?: { device: string } }>; set: (device: string) => Promise<{ ok: boolean; value?: { device: string } }> };
const pt = (window as unknown as { pt?: { projectId?: string; initialDevice?: InitialDeviceInfo; device?: DeviceBridge } }).pt;

// 设备档位：16 通道（双 ADS1298）/ 8 通道（唯理手环或单 ADS1298）/ 2 通道（ADS1292）/ 单通道（Cheez + ESP32-S3）；命令行指定 YUANLI_DEVICE=wl18 时同步挂载 18 通道档
type Device = 'c08b-16ch' | 'wl8' | 'c08b-8ch' | 'c08b-2ch' | 'wl18' | 'emg';
const DEVICES: { id: Device; label: string }[] = [
  { id: 'c08b-16ch', label: '16 通道 · OpenEMG 双 ADS1298' },
  { id: 'wl8', label: '8 通道 · 唯理肌电手环' },
  { id: 'c08b-8ch', label: '8 通道 · OpenEMG 单 ADS1298' },
  { id: 'c08b-2ch', label: '2 通道 · OpenEMG ADS1292' },
  ...(pt?.initialDevice?.device === 'wl18' ? [{ id: 'wl18' as const, label: '18 通道 · 唯理肌电手环' }] : []),
  { id: 'emg', label: '单通道 · Cheez + ESP32-S3' },
];
const VALID_DEVICES = new Set<string>(DEVICES.map((d) => d.id));
const KEY = 'yuanli-device';

function resolveStartupDevice(): { device: Device; needsSync: boolean } {
  const init = pt?.initialDevice;
  if (init?.forced && VALID_DEVICES.has(init.device)) {
    return { device: init.device as Device, needsSync: false };
  }
  if (init?.persisted && VALID_DEVICES.has(init.device)) {
    try { localStorage.setItem(KEY, init.device); } catch { /* 无存储 */ }
    return { device: init.device as Device, needsSync: false };
  }
  try {
    const saved = localStorage.getItem(KEY);
    if (saved && VALID_DEVICES.has(saved)) {
      return { device: saved as Device, needsSync: saved !== (init?.device ?? 'wl8') };
    }
  } catch { /* 无存储 */ }
  const fallback = init?.device && VALID_DEVICES.has(init.device) ? (init.device as Device) : 'wl8';
  return { device: fallback, needsSync: false };
}

function App() {
  const [startup] = useState(resolveStartupDevice);
  const [device, setDevice] = useState<Device>(startup.device);
  const [switching, setSwitching] = useState(false);
  useEffect(() => {
    if (!pt?.device || !startup.needsSync) return;
    void pt.device.set(device);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!emg8Bridge() || !pt?.projectId) return <WebCapture />;          // 普通浏览器：网页版直连串口
  const pick = (d: Device) => {
    if (d === device) return;
    setDevice(d);
    try { localStorage.setItem(KEY, d); } catch { /* 无存储 */ }
    if (pt?.device) {
      setSwitching(true);
      void pt.device.set(d).finally(() => { setTimeout(() => setSwitching(false), 260); });
    }
  };
  const slot = <select className="yuanli-device-select" aria-label="设备" value={device} onChange={(e) => pick(e.target.value as Device)}>
    {DEVICES.map((d) => <option key={d.id} value={d.id}>{d.label}</option>)}
  </select>;
  // 云端上传目前只传多通道手环录音，单通道不显示
  const multiSlot = <span className="yuanli-top-slot">{slot}{switching && <span className="emg8-spec-badge">切换档位中…</span>}<CloudBar /></span>;
  return device !== 'emg'
    ? <EmgStudio projectId={pt.projectId} deviceTier={device} deviceSlot={multiSlot} />
    : <SingleStudio projectId={pt.projectId} deviceSlot={slot} />;
}

createRoot(document.getElementById('root')!).render(<div className="v3"><App /></div>);
