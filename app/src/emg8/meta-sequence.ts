// 组合动作按时间判定；低置信、换指、断流都取消待触发动作，先放松再恢复。
export type MetaCommand = '选择' | '返回' | '唤醒／熄屏' | '打开／关闭启动器' | '启动／退出 AI';
export class MetaSequence {
  private previous = 0;
  private restFrames = 0;
  private candidate = '';
  private candidateFrames = 0;
  private contact = '';
  private down = 0;
  private long = false;
  private pending: { label: string; at: number } | null = null;
  private armed = false;
  held = false;
  reset() { this.previous = 0; this.restFrames = 0; this.candidate = ''; this.candidateFrames = 0; this.contact = ''; this.down = 0; this.long = false; this.pending = null; this.armed = false; this.held = false; }
  expire(now: number): MetaCommand[] {
    if (this.previous && now - this.previous > 300) { this.reset(); return []; }
    if (this.pending && this.contact !== this.pending.label && now - this.pending.at > 450) {
      const p = this.pending; this.pending = null;
      return p.label === 'meta_middle' ? ['返回'] : [];
    }
    return [];
  }
  push(label: string, confidence: number, now: number): MetaCommand[] {
    if (!Number.isFinite(now) || !Number.isFinite(confidence) || confidence < .65 || ['meta_other', 'motion_other'].includes(label)) { this.reset(); return []; }
    if (this.previous && (now <= this.previous || now - this.previous > 300)) this.reset();
    if (this.pending && !['meta_rest', 'motion_rest', this.pending.label].includes(label)) this.pending = null;
    const out = this.expire(now); this.previous = now;
    const rest = label === 'meta_rest' || label === 'motion_rest';
    // 松开运动门立即关；点按事件的两帧去抖不能让复位动作继续调节。
    if (rest) this.held = false;
    if (label === this.candidate) this.candidateFrames++; else { this.candidate = label; this.candidateFrames = 1; }
    if (this.candidateFrames < 2) return out;
    if (rest) {
      this.restFrames++;
      if (this.contact) {
        const duration = now - this.down, old = this.contact; this.contact = ''; this.held = false;
        if (!this.long && duration >= 70 && duration < 650) {
          if (old === 'meta_index') out.push('选择');
          else if (old === 'meta_middle' || old === 'meta_side') {
            if (this.pending?.label === old && this.down - this.pending.at <= 450) {
              out.push(old === 'meta_middle' ? '唤醒／熄屏' : '启动／退出 AI'); this.pending = null;
            } else this.pending = { label: old, at: now };
          }
        }
      }
      if (this.restFrames >= 2) this.armed = true;
      return out;
    }
    if (!['meta_index', 'meta_middle', 'meta_side', 'motion_hold'].includes(label)) { this.reset(); return []; }
    if (this.contact && this.contact !== label) { this.reset(); return []; }
    if (!this.contact && this.armed) {
      this.contact = label; this.down = now; this.long = false; this.restFrames = 0;
    }
    this.held = this.contact === 'motion_hold';
    if (this.contact && !this.long && now - this.down >= 650) {
      this.long = true; this.pending = null;
      if (label === 'meta_middle') out.push('打开／关闭启动器');
    }
    return out;
  }
}
export type MotionCalibration = { status: string; reason: string; donning?: number; bias?: number[]; vectors?: Record<string, number[]> };
// 仅把校准过的角速度映射到页内试用；不能从惯性数据推断稳定的直线位移。
export function motionDirection(gyro: number[], cal: MotionCalibration, mode: 'knob' | 'scroll'): { label: string; speed: number } | null {
  if (cal.status !== 'calibrated' || !cal.bias || !cal.vectors || gyro.length < 3 || !gyro.slice(0, 3).every(Number.isFinite)) return null;
  const g = gyro.slice(0, 3).map((v, i) => v * .0012 - cal.bias![i]);
  const norm = Math.hypot(...g); if (norm < .2 || norm > 8) return null;
  const names = mode === 'knob' ? ['motion_cw', 'motion_ccw'] : ['motion_up', 'motion_down', 'motion_left', 'motion_right'];
  const scores = names.map((label) => ({ label, speed: g.reduce((s, v, i) => s + v * cal.vectors![label]?.[i], 0) })).sort((a, b) => b.speed - a.speed);
  return scores[0].speed / norm >= .8 ? scores[0] : null;
}
