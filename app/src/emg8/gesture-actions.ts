// 手势 → 动作（鼠标组）：识别结果是每 50 ms 一个类别，这里把它变成「一次动作只触发一次」。
// 执行在采集服务（原力手环 host/wl8_actions.py：左键、右键、相对移动、滚动，服务端另有 250 ms 冷却）。
export type ActionKind = 'left_click' | 'right_click' | 'move' | 'scroll' | 'none';
export type GestureAction = { kind: ActionKind; dx?: number; dy?: number; text: string };

export const MIN_CONF = .65;   // 和 Meta 组合动作同一个置信门槛
export const HOLD = 3;         // 同一类连续 3 次（约 150 ms）才算做了
export const REARM = 2;        // 回到放松连续 2 次才允许下一次（鼠标组）
/** 结印游戏按住不放的重发间隔（毫秒）：对齐游戏各印冷却（game/tianjie/src/combat.mjs：剑 .42 s、印 1.45 s、雷 3.2 s），
 *  这样游戏不会收到「尚在冷却」的重复（复核 M1）。Mako 2026-10-16「只要识别到就可以攻击，保持游戏体验」。 */
export const REPEAT_MS: Record<string, number> = { seal_daozhi: 650, seal_poxie: 1700, seal_wulei: 3500 };   // 留 0.2–0.3 s 余量：游戏卡顿时游戏时钟走得比墙钟慢（main.mjs dt≤.05），余量太薄还会撞冷却（复核二轮）
export const REPEAT_DEFAULT_MS = 650;
export const SCROLL_LINES = 3; // 拇指拨一下翻几行（服务端夹在 ±10）

/** Mako 2026-10-06 选定：食指捏 = 左键，中指捏 = 右键；拇指侧面暂不绑定。
 *  2026-10-11：光标移动不走右滑，在「控制」页用手腕角速度。右滑这一类只认，kind 仍是 move 但识别页不发。
 *  Mako 2026-10-10 定：上 / 下 / 左三向八路电极分不开（三类内部留一 0.47–0.67），合成一类「拇指拨动」= 往下翻 SCROLL_LINES 行；
 *  旧的上 / 下 / 左三条保留给老模型，训练类别里已拿掉（desktop/emg8-profiles.json meta-mouse.labels）。 */
export function mousePreset(step = 120): Record<string, GestureAction> {
  return {
    mouse_index: { kind: 'left_click', text: '左键单击' },
    mouse_middle: { kind: 'right_click', text: '右键单击' },
    mouse_swipe: { kind: 'scroll', dx: 0, dy: SCROLL_LINES, text: `往下翻 ${SCROLL_LINES} 行` },
    mouse_right: { kind: 'move', dx: step, dy: 0, text: `光标右移 ${step}` },
    mouse_left: { kind: 'move', dx: -step, dy: 0, text: `光标左移 ${step}` },
    mouse_up: { kind: 'move', dx: 0, dy: -step, text: `光标上移 ${step}` },
    mouse_down: { kind: 'move', dx: 0, dy: step, text: `光标下移 ${step}` },
    mouse_side: { kind: 'none', text: '未绑定' },
  };
}

/** 采集服务查到没辅助功能权限时要说的那句。trusted 为 null 是查不到，不误拦。 */
export const ACCESSIBILITY_HINT = '到系统设置 → 隐私与安全性 → 辅助功能里允许 OpenEMG。';

export function accessibilityBlocks(trusted: boolean | null | undefined): boolean {
  return trusted === false;
}

/** 采集服务或 App 任一明确未授权就拦住。两边都还没查到是 null，不误拦。 */
export function gestureTrust(pythonTrusted: boolean | null | undefined, appTrusted: boolean | null | undefined): boolean | null {
  if (pythonTrusted === false || appTrusted === false) return false;
  if (pythonTrusted === true || appTrusted === true) return true;
  return null;
}

/** 真鼠标只在「识别在线、开关打开、辅助功能已允许」时动。 */
export const mouseOutputOn = (ready: boolean, output: boolean, trusted?: boolean | null) => ready && output && !accessibilityBlocks(trusted);

/** 串口开着不等于手环在发帧。有 link 时只认 streaming；旧服务没有 link 才退回 streaming 标志。 */
export function signalReady(streaming: boolean, link?: string): boolean {
  if (link) return link === 'streaming';
  return streaming;
}

/** 校准页的「开始用手势」不传 arm。光标移动在「控制」页，用手腕角速度。只有调用方明确要求、且是鼠标组，才启用真鼠标。 */
export function armFromGestureStart(protocol: string | undefined, arm: boolean): boolean {
  return arm && protocol === 'mouse';
}

/** 边沿触发（鼠标组）：开始前必须先看到放松；触发后要回到放松才能再触发，按住不放不会连发。
 *  continuous（结印游戏）：识别到就出——同一类连续 HOLD 次、置信 ≥ GAME_MIN_CONF 就出招，不等放松；换印连续 HOLD 次就出；
 *  同一印按住按墙钟限速（REPEAT_MS），丢帧重置、置信抖动都绕不过（复核 S1）。 */
export class GestureTrigger {
  private cand = ''; private n = 0; private armed = false; private restN = 0; private lastAt: Record<string, number> = {};   // 每一印上次出招的墙钟
  continuous: boolean;   // 结印游戏开；认对测试期间识别页会关掉，免得重发记成放松段误出招（复核 S3）
  constructor(private rest: string, continuous = false) { this.continuous = continuous; }
  /** 累计放松上膛和当前类别。不确定会中断计数。 */
  private tally(top: string, conf: number) {
    if (conf < MIN_CONF) { this.cand = ''; this.n = 0; this.restN = 0; return; }
    if (top === this.rest) { this.cand = ''; this.n = 0; if (++this.restN >= REARM) this.armed = true; return; }
    this.restN = 0;
    if (top === this.cand) this.n++; else { this.cand = top; this.n = 1; }
  }
  /** 放松检查还没过：照样上膛、记住正在做的印，这一下不出招。 */
  watch(top: string, conf: number) { this.tally(top, conf); }
  /** 已经看到过放松，下一记稳住的印可以出；结印游戏不需要上膛。 */
  primed() { return this.continuous || this.armed; }
  /** now：毫秒时钟，只给 continuous 的按住限速用。 */
  push(top: string, conf: number, now = Date.now()): string | null {
    this.tally(top, conf);
    if (conf < MIN_CONF || top === this.rest || this.n < HOLD) return null;
    if (this.continuous) {
      if (conf < GAME_MIN_CONF) return null;   // 游戏只收 ≥ .8：没到就不占这次出招（复核 S2）
      const last = this.lastAt[top];   // 按每一印各自的冷却限速，换印来回也绕不过；系统时钟往回拨时当作已过
      if (last !== undefined && now >= last && now - last < (REPEAT_MS[top] ?? REPEAT_DEFAULT_MS)) return null;
      this.lastAt[top] = now; return top;
    }
    if (!this.armed) return null;
    this.armed = false; return top;
  }
  /** 丢帧 / 断流 / 暂停后重新积累；按住限速按墙钟，不随之清零 */
  reset() { this.cand = ''; this.n = 0; this.armed = false; this.restN = 0; }
}

/** 结印组 → 掌中天劫（app/game/tianjie）的手印名。游戏只收置信度 0.8–1（它的 README），低于的不送、记下原因。 */
export const SEAL_TO_GAME: Record<string, 'sword' | 'guard' | 'thunder'> = { seal_daozhi: 'sword', seal_poxie: 'guard', seal_wulei: 'thunder' };
export const GAME_MIN_CONF = .8;
export const GAME_NAME: Record<string, string> = { sword: '道指剑', guard: '破邪印', thunder: '五雷诀' };
export function sealToGame(label: string, conf: number): { gesture: 'sword' | 'guard' | 'thunder'; confidence: number } | { skip: string } {
  const gesture = SEAL_TO_GAME[label];
  if (!gesture) return { skip: '不是结印手势' };
  if (!(conf >= GAME_MIN_CONF)) return { skip: `置信 ${conf.toFixed(2)} 低于游戏门槛 ${GAME_MIN_CONF}` };
  return { gesture, confidence: Math.min(1, conf) };
}

/** 认对测试：每个非放松类各 per 题、打乱。每题先放松 EXAM_REST_MS，再按提示做 EXAM_DO_MS；记做题窗口里第一次触发（就是游戏会收到的那一下）。 */
export const EXAM_REST_MS = 2500, EXAM_DO_MS = 4000;
export type ExamTrial = { target: string; got: string | null; restFires: number; paused: boolean };
export function examPlan(labels: string[], per: number, rnd: () => number = Math.random): string[] {
  const plan = labels.flatMap((l) => Array(per).fill(l) as string[]);
  for (let i = plan.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [plan[i], plan[j]] = [plan[j], plan[i]]; }
  return plan;
}
/** 电极没贴好而暂停过的题不计分；没触发算漏认；放松段的触发算误出招 */
export function examScore(trials: ExamTrial[]) {
  const used = trials.filter((t) => !t.paused);
  const per: Record<string, { n: number; ok: number; miss: number; wrong: Record<string, number> }> = {};
  for (const t of used) {
    const r = (per[t.target] ??= { n: 0, ok: 0, miss: 0, wrong: {} });
    r.n++;
    if (t.got === t.target) r.ok++; else if (t.got == null) r.miss++; else r.wrong[t.got] = (r.wrong[t.got] ?? 0) + 1;
  }
  return { n: used.length, ok: used.reduce((s, t) => s + (t.got === t.target ? 1 : 0), 0), paused: trials.length - used.length, restFires: used.reduce((s, t) => s + t.restFires, 0), per };
}

/** 推给游戏左下角的手环状态（electron/game.cjs → TianjieGame.band）：只显示和让画面里的手跟着摆，不出招。 */
export type BandStatus = { state: 'off' | 'link' | 'live' | 'paused'; text: string; pose: '' | 'sword' | 'guard' | 'thunder'; acc: number[] | null;
  lanes?: Lane[]; signal?: string; rec?: string };   // 识别中才带：8 路状态、信号结论、识别 / 出招结果（游戏左下角面板）
export type Lane = 'ok' | 'mask' | 'bad' | '';
/** 游戏面板里的肌电一栏：最近一次放松检查的 8 路状态 + 一句结论。mask / high 都是 1 起的路号 */
export function bandSignal(check: { allowed: boolean; high: number[]; over: number[]; text: string }, mask: number[], rmsFresh: boolean): { lanes: Lane[]; signal: string } {
  const lanes = Array.from({ length: 8 }, (_, i): Lane => mask.includes(i + 1) ? 'mask' : check.high.includes(i + 1) || check.over.includes(i + 1) ? 'bad' : rmsFresh ? 'ok' : '');
  const signal = !rmsFresh ? '没收到肌电数据' : !check.allowed ? check.text : mask.length ? `第 ${mask.join('、')} 路接触差 · 已屏蔽，用 ${8 - mask.length} 路识别` : '信号正常';
  return { lanes, signal };
}
/** 没在识别时：没数据 = off（游戏用按键）；有数据但没开识别 / 在回放 = link */
export function bandIdle(fresh: boolean, on: boolean, replay: boolean, linkTitle: string): BandStatus {
  const text = !fresh ? (linkTitle ? `${linkTitle} · 按键模拟` : '手环未连接 · 按键模拟') : replay ? '正在回放 · 按键模拟' : on ? '手环已连接 · 识别准备中' : '手环已连接 · 未开始识别';
  return { state: fresh ? 'link' : 'off', text, pose: '', acc: null };
}
/** 识别中：置信 ≥ MIN_CONF 才让手摆成认到的印；放松、不确定、别组的类都是不摆。acc = 这一批加速度均值 */
export function bandLive(top: string, conf: number, name: string, acc: number[] | null): BandStatus {
  const sure = conf >= MIN_CONF;
  return { state: 'live', text: `识别中 · ${sure ? `${name} ${conf.toFixed(2)}` : '不确定'}`, pose: sure ? SEAL_TO_GAME[top] ?? '' : '', acc };
}
/** 放松检查还没过：照样报当前类别、手型跟着摆，不出招。state 必须是 live，游戏只在 live 时摆手。 */
export function gatedWatch(top: string, conf: number, name: string, acc: number[] | null, amplitudeBlocked: boolean): { live: string; band: BandStatus } {
  if (amplitudeBlocked) return { live: '幅度不够 · 当放松', band: { state: 'live', text: '识别中 · 放松', pose: '', acc } };
  const band = bandLive(top, conf, name, acc);
  return { live: `${name} ${conf.toFixed(2)}${conf < MIN_CONF ? ' · 不确定' : ''} · 等放松后再出招`, band };
}

/** 跨佩戴用旧模型（2026-10-16 道指剑认成破邪印）：模型练完之后手环又重新出过数据——拔线重插、采集服务重启、断流 ≥ 30 秒后恢复（host/wl8.py link_since）——
 *  就提醒先重新校准。只提醒不拦截；本次佩戴练出新模型后 created 晚于 link_since，自动消失。缺任一边（旧服务没有 link_since / 还没选模型）不提醒、不误报。 */
export const REWEAR_HINT = '手环可能已重戴，请先在采集页重新校准再识别';   // 也发给游戏的 signal 字段：electron/game.cjs 截 40 字
const monthDayHm = (ms: number) => { const d = new Date(ms), p = (n: number) => String(n).padStart(2, '0'); return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`; };
export function rewearHint(created: string | null | undefined, linkSince: number | null | undefined): { short: string; detail: string } | null {
  if (!created || !linkSince) return null;
  const t = Date.parse(created);   // run.json 的 created 是本机本地时间 YYYY-MM-DDTHH:MM:SS（没时区，按本地解析）；link_since 是采集服务 time.time()，epoch 秒，同一台电脑同一时钟
  if (!Number.isFinite(t) || t >= linkSince * 1000) return null;
  return { short: REWEAR_HINT, detail: `这个模型 ${monthDayHm(t)} 训练，手环 ${monthDayHm(linkSince * 1000)} 才重新出数据；电极换过位置，旧模型会认错。` };   // 文案通用：鼠标 / AI 选择组也是每次佩戴校准，不只结印
}
/** 录制前问「同一次佩戴还是重新戴了」（2026-10-21，Mako 选 D1）：旧数据第 4 次佩戴跨了 10-14 23:58 → 10-15 17:47，中间空了 10.7 h，
 *  多次佩戴混成一个号。只在编号还等于上一条录音的编号时问（「已实际摘下重戴」或校准自动 +1 已经改过就不问）；
 *  问的条件：App 重启后第一次录、距上一条 ≥ 30 分钟、或上一条之后手环重新出过数据（link_since，断流 ≥ 30 秒 / 拔插 / 服务重启）。没有上一条不问。 */
export const REASK_MS = 30 * 60_000;
export function shouldAskRewear(last: { donning: number; at: number } | null, donning: number, now: number, linkSince: number | null | undefined, askedThisRun: boolean): boolean {
  if (!last || last.donning !== donning) return false;
  return !askedThisRun || now - last.at >= REASK_MS || (!!linkSince && linkSince * 1000 > last.at);
}
type Last = { donning: number; at: number };
/** 所有录制都经过的包装：带上戴法；该问时先弹窗（ask 返回用户选的编号），改号后通知 changed。
 *  批量录制（enrollSequence）开头就定了编号：改号后同一批后面传来的旧号也换成新号（复核 P1）；两条同时到共用一个弹窗（复核 P2）。 */
export function guardRecord<A extends { donning: number }, R extends { ok: boolean }>(record: (id: string, a: A & { cable_dir?: string; ch0_site?: string }) => Promise<R>, io: {
  last: Last | null; ask: (last: Last) => Promise<number>; changed: (n: number) => void; saved: (last: Last) => void;
  extra: () => { cable_dir?: string; ch0_site?: string; linkSince?: number | null }; now?: () => number;
}) {
  let last = io.last, askedThisRun = false, remap: { from: number; to: number } | null = null, asking: Promise<number> | null = null;
  const now = io.now ?? Date.now;
  return async (id: string, a: A): Promise<R> => {
    const { linkSince, ...how } = io.extra();
    if (a.donning === remap?.to) remap = null;                       // 界面已跟上新号：之后用户手动改回旧号就照用，不再偷偷换（复核 P1）
    let n = remap?.from === a.donning ? remap.to : a.donning;
    if (asking || shouldAskRewear(last, n, now(), linkSince, askedThisRun)) {
      const from = n;
      asking ??= io.ask(last!).finally(() => { asking = null; });
      n = await asking;
      if (n !== from) { remap = { from, to: n }; io.changed(n); }
    }
    askedThisRun = true;
    const r = await record(id, { ...a, donning: n, ...how });
    if (r.ok) { last = { donning: n, at: now() }; io.saved(last); }
    return r;
  };
}
/** 游戏载荷：有重戴提醒就写进 signal（未开始识别时也发，「戴上神锁」页「实时肌电状态」那一行显示它；识别中顶掉「信号正常」，Mako 2026-10-16 选 A），没有就原样 */
export function withRewearHint(b: BandStatus, hint: string): BandStatus { return hint ? { ...b, signal: hint } : b; }
