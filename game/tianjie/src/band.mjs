// 手环实时状态（OpenEMG App 识别页约每 100 ms 推一次）：连没连、认成什么、手腕倾角。
// 只做显示和手部跟随，不出招；出招仍只走 TianjieGame.input。
export const STALE_MS = 1500;   // 超过这么久没收到，当手环断了（App 换页、识别停了都会这样）
const STATES = new Set(['off', 'link', 'live', 'paused']);
const POSES = new Set(['', 'sword', 'guard', 'thunder']);
const LANES = new Set(['ok', 'mask', 'bad', '']);

/** 不合法就返回 null。acc = 这一批 IMU 加速度均值（原始计数，只用方向） */
export function parseBand(s) {
  if (!s || !STATES.has(s.state) || typeof s.text !== 'string' || !POSES.has(s.pose ?? '')) return null;
  const acc = Array.isArray(s.acc) && s.acc.length === 3 && s.acc.every(Number.isFinite) && Math.hypot(...s.acc) > 0 ? s.acc : null;
  // 面板（识别中才有）：8 路状态、信号结论、识别 / 出招结果；任一项不合法就当没有
  const lanes = Array.isArray(s.lanes) && s.lanes.length === 8 && s.lanes.every((x) => LANES.has(x)) ? [...s.lanes] : null;
  const str = (v) => (typeof v === 'string' ? v.slice(0, 40) : '');
  return { state: s.state, text: s.text.slice(0, 40), pose: s.pose || '', acc, lanes, signal: str(s.signal), rec: str(s.rec) };
}

const unit = (v) => { const n = Math.hypot(...v); return v.map((x) => x / n); };

// ponytail: 手环坐标轴到画面手的对应关系没在真腕带上标过，先假设 X 轴沿前臂。
// 戴上发现俯仰、侧倾反了或互换，只改这里：pitch / roll 各取旋转向量的哪一轴、乘几
export const AXES = { pitch: [1, 1], roll: [0, -1] };
const LIMIT = .7;   // 画面里手最多倾 40°，免得转出画面

/** 以开始跟踪那一刻的重力方向为零点，返回当前相对它的俯仰 / 侧倾（弧度）。
 *  旋转向量 ≈ 零点 × 当前（单位向量叉积，模长 = sin 夹角），只看重力所以绕竖轴转不出来。 */
export function tilt(neutral, acc) {
  const n = unit(neutral), g = unit(acc);
  const c = [n[1] * g[2] - n[2] * g[1], n[2] * g[0] - n[0] * g[2], n[0] * g[1] - n[1] * g[0]];
  const clamp = (x) => Math.max(-LIMIT, Math.min(LIMIT, x));
  return { pitch: clamp(Math.asin(Math.max(-1, Math.min(1, c[AXES.pitch[0]]))) * AXES.pitch[1]), roll: clamp(Math.asin(Math.max(-1, Math.min(1, c[AXES.roll[0]]))) * AXES.roll[1]) };
}
