// 售后录屏里反复问、而界面没写明的几件事。数字对齐原力手环 host/wl8.py（2000 Hz、imu 6 列、两个换算）
// 和 host/take_file.py（recorded_at 在 write() 里取，是停下后写盘的时刻；文件按段，不按 30 秒重叠）。

export const GYRO_SCALE = 0.0012;
export const ACC_SCALE = 0.0005978;

/** 售后里同一根拇指的方向滑会互相认成对方；食指点、中指点不在这句里。
 *  2026-10-10 五类：上 / 下 / 左已合成拇指拨动，不再进训练。右滑仍在，单独一句，不再叫人「别把四个方向放进同一次」。 */
const CONFUSED_THUMB = new Set(['mouse_up', 'mouse_down', 'mouse_left']);

export const SAME_FINGER_NOTE = '拇指的上、下、左用的是同一根手指，很容易互相认错。拨到头停一下，再慢慢抬回来，别弹回去；还是分不开，就不要把这三个方向放进同一次训练。';
export const RIGHT_SWIPE_NOTE = '右滑和拇指拨动用的是同一根手指，只是方向不同：右滑只朝你的右边。拨到头停一下，再慢慢抬回来，别弹回去。';

/** 售后里第二常见的问题。放松类不显示：那一条要保持不动。 */
export const WINDOW_NOTE = '两秒是窗口。看到「做！」再做，做完马上松开，不要把这两秒握满。做晚了，这一下会标进下一个动作。';

/** 换一次戴法就要重录。摘下、转动、戴松都算。 */
export const REDON_NOTE = '摘下、转过角度或戴松一格，都要重新校准。上次的模型不能沿用。';

export function sameFingerNote(label: string): string {
  if (label === 'mouse_right') return RIGHT_SWIPE_NOTE;
  return CONFUSED_THUMB.has(label) ? SAME_FINGER_NOTE : '';
}

/** 设备页和数据页共用。采样率必须来自设备，不许写死。 */
export function dataReadout(fsHz: number): string[] {
  if (!Number.isInteger(fsHz) || fsHz < 1) throw new Error('采样率必须是正整数');
  const ms200 = Math.round((200 / fsHz) * 1000);
  return [
    `肌电是 ${fsHz} Hz。seq 是 0–255 循环的包序号，用来查丢包，不是采样率。`,
    '一段从点「开始录」到点「停」。没有每 30 秒自动切文件，相邻两段不重叠。',
    '头里的 date、time、recorded_at 是这段写盘的时刻（停下之后）。开头 ≈ 这个时刻减去这段的秒数。',
    '没有暂停键。点「停」结束这一段；再点「开始录」是下一段。',
    `惯性在 .h5 的 imu，6 列 int16：前 3 列角速度 ×${GYRO_SCALE} = rad/s，后 3 列加速度 ×${ACC_SCALE} = m/s²。导出的 .txt 只有肌电，没有这 6 列。`,
    `窗口点数 = 采样率 × 秒数。1 秒是 ${fsHz} 点；200 点在这个采样率下只有 ${ms200} 毫秒。`,
    '接到别的程序用导出的 .txt，或在规则页打开 LSL。本程序占着接收器串口时，串口助手打不开同一个口；要看原始串口，先退出本程序，拔插一次接收器，再开串口工具。',
    '识别出的动作从规则页送出（按键或 LSL）。训练得到的模型在运行记录里，不在原始波形文件里。',
  ];
}
