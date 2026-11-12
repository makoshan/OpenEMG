// 戴好页的佩戴提醒。来源分两类：SENIAM 通用规则（电极用骨性标志定位、每次一样；双极沿肌纤维方向；皮肤酒精清洁晾干；
// 弹性带固定、线不拉扯；参考点放电惰性组织）和唯理 WL8 卖家佩戴图（手腕贴掌根、主机在手背侧、开关朝小指朝手肘）。
// SENIAM 的 30 块肌肉里没有前臂肌，手环 8 对电极的具体位置不是 SENIAM 推荐，是本项目实测口径（原力手环 host/research/2026-10-10-seniam-placement-to-mako.md）。
import type { Hand } from './contract';

export type WearStep = { k: string; t: string; d: string };

/** 戴好页逐条提醒。文案只说怎么做；「为什么」在研究笔记里。kind 与 link.ts 的 BandLink 相同，默认 USB 版。 */
export const wearSteps = (hand: Hand, kind: 'usb' | 'ble' = 'usb'): WearStep[] => [
  { k: 'where', t: '位置', d: '像戴手表：表带靠手那侧的边离腕横纹约一指宽，别压在腕骨凸起上。量一次、下次戴一样远。' },
  { k: 'turn', t: '方向', d: `主机在${hand === 'left' ? '左' : '右'}手背正中，开关和灯朝小指、朝手肘。转过角度等于换了电极，就得重新校准。` },
  { k: 'skin', t: '皮肤', d: '酒精擦一遍手腕一圈，等它干；8 根金属棒略沾一点水再贴上。' },
  { k: 'tight', t: '松紧', d: '整圈均匀贴紧、不勒；每根金属棒的两头都压在肉上，不架在骨头或手表印子上。勒太紧，肌肉自己会颤。戴松一格也要重新校准。' },
  { k: 'cable', t: '线', d: '白线悬空或贴身固定，别拖桌面、动作时别扯到；Mac 拔掉电源适配器。' },
  kind === 'ble'
    ? { k: 'receiver', t: '接收器', d: '白色接收器离手环近一些，用延长线离开电脑机箱；离充电器、USB 硬盘和其他蓝牙设备远一些。' }
    : { k: 'receiver', t: '插头', d: '白色 USB 头插紧。手环上的 Type-C 只充电，不传数据。' },
  { k: 'settle', t: '等', d: '戴好先放松 1 分钟再检查，金属电极要一会儿才贴稳（经验值，未实测）。' },
];

/** 「佩戴位置 / 条件」输入框的填法：写成下次能照着戴的样子 */
export const PLACEMENT_HINT = '离腕横纹几 cm · 主机对准哪 · 皮肤怎么处理，例：腕横纹上 2 cm · 主机手背正中 · 酒精+沾水';

/** 什么时候显示提醒：这次佩戴还没检查，或检查出有电极没贴紧 */
export const showWearSteps = (checked: boolean, bad: number) => !checked || bad > 0;

/** 检查完的说法。1–2 路过线才点名某一片；≥3 路一起过线多半是整条没贴好或前臂没放松（evidence/2026-10-15-mains-share：过线不是工频，8 路齐高的批次 20–100 Hz 占 86–99%），
 *  这时服务端的「工频偏大 / Mac 接着充电器」提醒也要露出来——以前只在 8 路全好时才显示（2026-10-16 Mako：0/8 还提示往 CH1 那侧压一格）。 */
export const WHOLE_BAND_BAD = 3;
export type WearVerdict = { headline: string; sub: string; warnings: string[] };
export function wearVerdict(bad: number[], extra: string[]): WearVerdict {
  const ok = 8 - bad.length;
  if (!bad.length) return { headline: '8 路都贴好了', sub: extra.length ? '底噪正常，可以开始录动作；下面的提醒能改就改' : '可以开始录动作', warnings: extra };
  if (bad.length >= WHOLE_BAND_BAD) return {
    headline: bad.length === 8 ? '8 路都偏高' : `${ok} 路贴好了，CH${bad.join('、CH')} 都偏高`,
    sub: '不是哪一片的事：整条摘下重贴，酒精擦手腕、金属棒沾水，整圈压紧、前臂搁稳，放松 1 分钟再检查',
    warnings: extra,
  };
  return { headline: `${ok} 路贴好了，CH${bad.join('、CH')} 还差一点`, sub: `把表带往 CH${bad[0]} 那侧压一格，再检查一次`, warnings: [] };
}
