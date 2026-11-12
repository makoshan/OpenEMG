// 连接指引的唯一文案。服务端 rig.link 四态；页面不要再各写一份。
// 串口芯片两套都是 CP2102 / CH343，软件分不出买的是哪套，由页面上的「USB 版 / 蓝牙版」决定文案。
// 默认 USB：Mako 买的是有线版（host/wl8.py：Type-C 只充电，数据走灰白线白色 USB 头，电源开关，绿灯闪 = 连上）。
// 蓝牙版文案照厂商说明书：白色接收器、长按 3 秒、两边灯长亮。
export type RigLink = 'no-receiver' | 'waiting-band' | 'streaming' | 'dropped';

export type BandLink = 'usb' | 'ble';

export type LinkAdvice = { title: string; detail: string; steps: string[] };

export const RECONNECT_COOLDOWN_MS = 3000;

export const DEFAULT_BAND_LINK: BandLink = 'usb';

const BAND_LINK_KEY = 'emg8-band-link';

export function readBandLink(): BandLink {
  if (typeof localStorage === 'undefined') return DEFAULT_BAND_LINK;
  return localStorage.getItem(BAND_LINK_KEY) === 'ble' ? 'ble' : DEFAULT_BAND_LINK;
}

export function writeBandLink(kind: BandLink): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(BAND_LINK_KEY, kind);
}

const USB_ABSENT = ['把灰白线上的白色 USB 头插到电脑', '手环上的 Type-C 只充电，不传数据', '还是没有：退出杀毒软件和银行 U 盾，它们会占着串口'];
const BLE_ABSENT = ['把白色接收器插到电脑 USB 口', '接收器灯会闪', '还是没有：退出杀毒软件和银行 U 盾，它们会占着串口'];
const USB_WAIT = [
  '打开手环电源开关，绿灯闪就是连上了',
  '先充 30 分钟再开，别用快充',
  '不要用串口助手打开同一个口，它会被本程序占用',
];
const BLE_WAIT = [
  '长按手环电源键 3 秒，灯开始闪',
  '等 1–10 秒，两边灯都变长亮',
  '超过 10 秒：拔接收器、长按 2 秒关机，从 ① 重来',
  '不要用串口助手打开同一个口，它会被本程序占用',
];
const UNKNOWN: LinkAdvice = { title: '正在确认连接', detail: '稍等一下。一直这样的话，点「重新连接」。', steps: [] };

function pick(kind: BandLink, usb: string[], ble: string[]): string[] {
  switch (kind) {
    case 'usb':
      return [...usb];
    case 'ble':
      return [...ble];
    default: {
      const unexpected: never = kind;
      void unexpected;
      return [...usb];
    }
  }
}

export function linkAdvice(link: RigLink | undefined, reason = '', kind: BandLink = DEFAULT_BAND_LINK): LinkAdvice {
  switch (link) {
    case 'no-receiver':
      return kind === 'ble'
        ? { title: '没检测到蓝牙接收器', detail: '电脑这边还没看到接收器。', steps: pick(kind, USB_ABSENT, BLE_ABSENT) }
        : { title: '没检测到 USB 线', detail: '电脑这边还没看到这条线。', steps: pick(kind, USB_ABSENT, BLE_ABSENT) };
    case 'waiting-band':
      return kind === 'ble'
        ? { title: '接收器在了，手环还没连上', detail: '接收器灯如果在闪，就是还在等手环。', steps: pick(kind, USB_WAIT, BLE_WAIT) }
        : { title: '线在了，手环还没出数据', detail: '串口已经打开，还没收到一帧。', steps: pick(kind, USB_WAIT, BLE_WAIT) };
    case 'dropped':
      return { title: '连接断了', detail: reason || '读取中断', steps: pick(kind, USB_ABSENT, BLE_ABSENT) };
    case 'streaming':
      return { title: '手环醒了', detail: '', steps: [] };
    case undefined:
      return UNKNOWN;
    default: {
      const unexpected: never = link;
      void unexpected;
      return UNKNOWN;
    }
  }
}

const MARKS = ['①', '②', '③', '④'];

export function linkLine(link: RigLink | undefined, reason = '', kind: BandLink = readBandLink()): string {
  const advice = linkAdvice(link, reason, kind);
  const head = advice.detail ? `${advice.title}。${advice.detail}` : `${advice.title}。`;
  if (!advice.steps.length) return head;
  const steps = advice.steps.map((step, i) => `${MARKS[i] ?? `${i + 1}.`} ${step}`).join(' ');
  return `${head} ${steps}`;
}

export function zeroNote(link: RigLink | undefined, kind: BandLink = readBandLink()): string {
  switch (link) {
    case 'no-receiver':
      return kind === 'ble' ? '接收器被拔了。插上白色接收器，等灯闪，再继续。' : '白线拔了。把白色 USB 头插回去，再继续。';
    case 'dropped':   // 读串口出错也会走这里，不一定是拔线：只说断了，给拔下重插这一步（复核 P3）
      return kind === 'ble' ? '连接断了。拔下白色接收器再插好，等两边灯长亮，再继续。' : '连接断了（线松了或读取出错）。把白色 USB 头拔下再插紧，再继续。';
    case 'waiting-band':
      return kind === 'ble' ? '手环掉线了。长按电源键 3 秒，等两边灯长亮，再继续。' : '手环没出数据。打开电源开关，绿灯闪了再继续。';
    case 'streaming':
    case undefined:
      return '没收到数据。回到「连上」，看现在卡在哪一步。';
    default: {
      const unexpected: never = link;
      void unexpected;
      return '没收到数据。回到「连上」，看现在卡在哪一步。';
    }
  }
}

/** 蓝牙版 waiting-band 超过 10 秒时，高亮「拔掉重来」那一步。USB 版没有这一步，返回 -1。 */
export function hotStep(link: RigLink | undefined, elapsedSec: number, kind: BandLink = DEFAULT_BAND_LINK): number {
  if (kind !== 'ble') return -1;
  return link === 'waiting-band' && elapsedSec >= 10 ? 2 : -1;
}

/** 从「口不在 / 已断开」变成「口在了」才自动重连；3 秒内不连第二次。 */
export function shouldAutoReconnect(prev: string | undefined, next: string | undefined, sinceMs: number): boolean {
  if (sinceMs < RECONNECT_COOLDOWN_MS) return false;
  if (prev !== 'no-receiver' && prev !== 'dropped') return false;
  return next === 'waiting-band' || next === 'streaming';
}
