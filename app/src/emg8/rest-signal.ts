// 肌电幅度不能证明电极接触。只在明确提示放松的阶段检查信号，动作期不更新底噪。
export const REST_SETTLE_MS = 600; // 显示 RMS 是 0.5 秒窗，先等上一个动作退出窗口。
export const REST_STABLE_MS = 1200;
export const SIGNAL_VALID_MS = 10000; // 默认定时复查；结印会话仅在断开超过 BREAK_MS 或显式重置后重查。
/** 数据断开超过这么久才撤销放松检查。丢帧、渲染卡顿这类短暂不连续只取消当次动作：电极接触不会因为丢一个包而变。
 *  2026-10-15 一局丢帧 33 次，每次都整套重查；重查要 8 路同时静 1.2 s，打着游戏回放中位要等 66 s。 */
export const BREAK_MS = 2000;
export const LANE_HOLD_MS = 3000; // 一路要在放松检查里连续过线这么久才算坏路（复核 P1：短暂发力不能换来屏蔽）
/** 坏路计时只在「其余路都安静」时进行：过线 ≤2 路、其余路 ≤ 70% 红线（150 µV → 105 µV）。
 *  肌肉发力会让多路一起升；2026-10-15 握印时最强的第 1、2 路被当成没贴好屏蔽（校准时这两路放松 45 µV、动作 1000+ µV）。
 *  .55 → .7（2026-10-16 回放，evidence/2026-10-16-contact-quiet-replay）：那段握印 .55–.7 都不误屏蔽、.75 起误屏蔽 14 s；已知坏路早 23–129 s 判出。 */
export const CONTACT_QUIET = .7;
export type SignalCheck = { allowed: boolean; high: number[]; over: number[]; stuck: number[]; text: string };   // over：最近一次放松检查里过线的路（含已屏蔽的）；stuck：其中连续过线 ≥ LANE_HOLD_MS 的路

/** 放松检查里 1–2 路过线：屏蔽这几路继续认（服务端删掉这几路的特征），缺这几路的同次佩戴留一估计低于 minScore 就不屏蔽、照旧拦。
 *  ≥3 路一起过线多半是前臂在用力（或整条没戴好），不屏蔽。laneDrop[k] = 训练时屏蔽第 k+1 路的留一认对率（旧模型没有 → 估计未知，仍屏蔽）。 */
export const MASK_MIN_SCORE = .6;
export function lanePlan(over: number[], laneDrop: number[] | null | undefined, minScore = MASK_MIN_SCORE): { mask: number[]; estimate: number | null } {
  if (!over.length || over.length > 2) return { mask: [], estimate: null };
  const est = laneDrop?.length === 8 ? Math.min(...over.map((l) => laneDrop[l - 1])) : null;
  return est != null && est < minScore ? { mask: [], estimate: est } : { mask: [...over], estimate: est };
}

export class RestSignalGate {
  private started = 0;
  private last = 0;
  private lowSince: number | null = null;
  private until = 0;
  private high: number[] = [];
  private over: number[] = [];
  private ignore: number[] = [];
  private forced: number[] = [];
  private overSince = new Map<number, number>();   // 路 → 这一段连续过线从哪个批次开始；数据不连续就清掉，有效期到期重检时保留
  private seen = 0;   // 上一个批次时刻。reset 不清它：外部 reset 会把 last 清零，靠它才认得出断流（复核 #55 P1）
  private alive = 0;  // 最近一次收到数据批次（心跳）。丢帧后显示 RMS 要约 1.5 s 才重新稳定，这期间数据仍在流，不算断流
  private held(l: number) { const t = this.overSince.get(l); return t != null && this.seen - t >= LANE_HOLD_MS; }
  constructor(private limit = 150, private policy: 'periodic' | 'session' = 'periodic') {}
  /** 已屏蔽的路不挡放松检查（仍记进 over，贴好了下一次检查会看到它恢复） */
  setIgnore(lanes: number[]) { this.ignore = [...lanes]; }
  /** 用户手动屏蔽的路：不用等连续过线 3 秒，直接不挡放松检查。放松时其余路也常在 75–150 µV 之间跳，自动判坏路要等几分钟（2026-10-16 回放） */
  force(lanes: number[]) { this.forced = [...lanes]; }
  reset(now: number) {
    this.started = now; this.last = 0; this.lowSince = null; this.until = 0; this.high = [];
  }
  /** 每收到一个数据批次调用一次：数据在流就不算断流，哪怕显示 RMS 还在稳定、暂时为空。 */
  heartbeat(at: number) {
    // 断流超过 BREAK_MS 后的第一批：这里先撤销放行，不靠 status 定时器（睡眠唤醒时定时器和数据的先后说不准，复核 #85）
    if (this.until && at - Math.max(this.last, this.alive) > BREAK_MS) this.reset(at);
    if (at > this.alive) this.alive = at;
  }
  observe(rms: number[] | null | undefined, at: number, now: number) {
    // 没有 RMS（丢帧或断开后显示滤波还在稳定）：这一批不计，不能当放松，也不撤销已有放行；断流由心跳按 BREAK_MS 判断。
    if (!rms) return;
    if (rms.length !== 8 || rms.some(v => !Number.isFinite(v) || v < 0)) {
      this.reset(now); this.overSince.clear(); this.seen = 0; return;
    }
    // 过期、未来、乱序、重复的批次这一批不计，不撤销通过：重画同一批不能累积放松时间；断开太久由下面和 status 按 BREAK_MS 撤销。
    if (!(at > 0) || at > now || now - at > 1000 || at <= this.last) return;
    const prev = Math.max(this.last, this.alive);
    if (prev && at - prev > BREAK_MS) this.reset(now);
    else if (this.last && at - this.last > 300) this.lowSince = null;   // 短暂不连续：已通过的保留，没通过的「连续安静」重新起算
    // 断流 / 乱序：坏路重新计时。已通过时不清：清了 stuck 会变空、已屏蔽的坏路被放开，放行却还在（复核 #85 P1）
    if (this.seen && this.until <= now && (at < this.seen || at - this.seen > 300)) this.overSince.clear();
    this.seen = at;
    if (!this.started || (this.until && now >= this.until)) this.reset(now);
    this.last = at;
    if (this.until > now) return; // 已通过时的动作幅度绝不改写放松结论。
    this.over = rms.flatMap((v, i) => v > this.limit ? [i + 1] : []);
    for (const l of [...this.overSince.keys()]) if (!this.over.includes(l)) this.overSince.delete(l);
    const quiet = this.over.length <= 2 && rms.every((v, i) => this.over.includes(i + 1) || v <= this.limit * CONTACT_QUIET);
    for (const l of this.over) {
      if (!this.overSince.has(l)) { if (quiet) this.overSince.set(l, at); }   // 其余路不安静 = 在发力，不开始坏路计时
      else if (!quiet && !this.held(l)) this.overSince.delete(l);              // 没满 3 秒就有别的路跟着升：是起印，不是接触；已满的坏路做动作时保持
    }
    this.high = this.over.filter((l) => !this.forced.includes(l) && !(this.ignore.includes(l) && this.held(l)));   // 只放过已屏蔽且自己满 3 秒的路；回落后重新起算的不放过（复核 #55 P2）
    if (now - this.started < REST_SETTLE_MS || this.high.length) { this.lowSince = null; return; }
    this.lowSince ??= at;
    if (at - this.lowSince >= REST_STABLE_MS) {
      // 结印动作期不定时要求放松；数据新鲜度仍由 status 和 observe 检查。
      this.until = this.policy === 'session' ? Infinity : now + SIGNAL_VALID_MS; this.high = [];
    }
  }
  status(now: number): SignalCheck {
    if (this.until && (now >= this.until || now - Math.max(this.last, this.alive) > BREAK_MS)) this.reset(now);
    const allowed = this.until > now;
    const stuck = this.over.filter((l) => this.held(l));
    return { allowed, high: [...this.high], over: [...this.over], stuck, text: allowed ? '放松检查通过 · 动作幅度不判接触' : this.high.length
      // 多路一起高是前臂发力（2026-10-15 实录 3–8 路偏高时 60–250 Hz 占六成多、6 路同涨），不是电极问题；不带路号，游戏面板只截 40 字
      ? this.high.length >= 3 ? '手还在用力：完全松开 2 秒，暂不出招'
        // 1–2 路连续过线满 LANE_HOLD_MS 才说接触；刚过线可能是握着手印，照旧请放松（复核 #69）
        : this.high.every((l) => stuck.includes(l)) ? `第 ${this.high.join('、')} 路电极没贴好：压一下那片，暂不出招`
        : `请放松：第 ${this.high.join('、')} 路偏高，暂不出招`
      : this.quietText(now) };
  }
  /** 手已经松开：先等半秒窗里的上一个动作出去，再倒数还要保持的安静。 */
  private quietText(now: number): string {
    const since = this.started ? now - this.started : 0;
    if (since < REST_SETTLE_MS) return `松开，再等 ${((REST_SETTLE_MS + REST_STABLE_MS - since) / 1000).toFixed(1)} 秒`;
    const held = this.lowSince == null ? 0 : Math.max(0, now - this.lowSince);
    const left = REST_STABLE_MS - held;
    return left > 0 ? `已松开，再保持 ${(left / 1000).toFixed(1)} 秒` : '已松开，马上继续';
  }
}
