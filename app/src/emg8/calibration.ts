// 每次佩戴校准的纯逻辑（design/emg-calibration-v1）：轮流录 8 类 × 3 轮，每条按幅度门槛当场重录一次，录满自动训练。
// 界面只负责触发 record / train 和读服务端状态；这里不碰 React，门禁直接测。

export type Verdict = 'ok' | 'weak' | 'lost';
export type Mark = '' | 'now' | 'ok' | 'redo';
export type Cal = {
  plan: string[]; i: number; redone: Record<number, true>; marks: Mark[]; rest: number[];
  phase: 'arm' | 'wait' | 'contact' | 'train' | 'training' | 'done' | 'stopped'; seenBusy: boolean; last: string; runId: string | null; armedAt?: number;
  restDue?: boolean;   // 这一戴底噪偏高过：贴好后还要重录放松。记在进度上，离开这一页再回来还在
  waived?: number[];   // 用户点了「仍然开始」放过的过线路（1 起，最多 2 路）；黄线本来就不拦（calibrationHolds）
};

/** 8 类轮流 × rounds 轮，同一类不连录。给 rand 就每轮重新洗牌（EgoEMG 六手势：避免某类总跟在同一类后面），
 *  跨轮交界处若和上一条同类就把这一类挪到本轮第二位，仍保证不连录；不给 rand 与原来逐字相同。 */
export const calibrationPlan = (labels: string[], rounds: number, rand?: () => number, after?: string) => Array.from({ length: rounds }).reduce<string[]>((plan) => {
  const round = [...labels];
  if (rand) for (let i = round.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [round[i], round[j]] = [round[j], round[i]]; }
  // after：「再补一轮」是新计划，拿上一计划最后录的那条当交界参照
  if (round.length > 1 && round[0] === (plan.at(-1) ?? after)) [round[0], round[1]] = [round[1], round[0]];
  return [...plan, ...round];
}, []);

/** 一条录完的判定：没存下 = lost；动作峰值不到放松的 minRatio 倍 = weak（放松本身、或量不到放松基线时不判） */
export const takeVerdict = (kind: string | undefined, peak: number, rest: number, minRatio: number): Verdict =>
  kind === 'rest' || !(rest > 0) ? 'ok' : peak < rest * minRatio ? 'weak' : 'ok';

/** 进度格第 r 轮里「label」那一格对应计划的第几条（打乱顺序后不能用 r*n+c）；没有返回 -1 */
export const cellIndex = (plan: string[], r: number, n: number, label: string) => { const i = plan.slice(r * n, r * n + n).indexOf(label); return i < 0 ? -1 : r * n + i; };

export const startCalibration = (labels: string[], rounds: number, rand?: () => number, after?: string): Cal =>
  ({ plan: calibrationPlan(labels, rounds, rand, after), i: 0, redone: {}, marks: Array(labels.length * rounds).fill(''), rest: [], phase: 'arm', seenBusy: false, last: '', runId: null });

/** 一条结束后推进：weak / lost 且这一格还没重录过 → 原地重录（黄点）；否则记录并进下一条；录满 → train */
export function advance(c: Cal, v: Verdict, name: string): Cal {
  const marks = [...c.marks];
  if (v !== 'ok' && !c.redone[c.i]) {
    marks[c.i] = 'redo';
    return { ...c, marks, redone: { ...c.redone, [c.i]: true }, phase: 'arm', seenBusy: false, last: `${name}：${v === 'lost' ? '没录上' : '没检测到动作'}，这一条再来一次` };
  }
  if (v === 'lost') {                                            // 重录过还是没存下：这一格留空往前走，训练前再按条数判
    marks[c.i] = 'redo';
    return { ...c, marks, i: c.i + 1, phase: c.i + 1 >= c.plan.length ? 'train' : 'arm', seenBusy: false, last: `${name}：两次都没录上，先跳过；录满后可「再补一轮」` };
  }
  marks[c.i] = marks[c.i] === 'redo' ? 'redo' : 'ok';
  const i = c.i + 1, done = i >= c.plan.length;
  return { ...c, marks, i, phase: done ? 'train' : 'arm', seenBusy: false, last: v === 'ok' ? `✓ ${name}` : `${name}：仍然偏弱，先收下，试一下时再看` };
}

/** 放松底噪判定：按多路实时 RMS（µV）。bad ≥ limit（戴好页同一条红线）；high ≥ 55% limit（2026-10-08 实录：贴好 43–51，贴坏 98–291）。 */
export type Noise = { kind: 'unknown' | 'ok' | 'high' | 'bad'; bad: number[]; high: number[] };
export function noiseVerdict(rms: number[] | null | undefined, limit: number): Noise {
  if (!rms || rms.length < 2 || rms.some((v) => !Number.isFinite(v))) return { kind: 'unknown', bad: [], high: [] };
  const bad = rms.flatMap((v, i) => (v > limit ? [i + 1] : [])), high = rms.flatMap((v, i) => (v >= limit * .55 && v <= limit ? [i + 1] : []));   // 与戴好页同口径：≤ limit 算过
  return { kind: bad.length ? 'bad' : high.length ? 'high' : 'ok', bad, high };
}

/** 放过之后的判定：放过的红路不算，黄色偏高清空；没放过的路过线照旧 bad。显示仍用原判定，不把红的画成绿的。
 *  2026-10-15 别人试戴第 1、2 路 228/372 µV 压不下来，整页卡死开始不了；1–2 路坏让留一分说话，≥3 路照旧拦。 */
export function waiveNoise(n: Noise, waived: number[] | null | undefined): Noise {
  if (!waived || n.kind === 'unknown') return n;
  const bad = n.bad.filter((l) => !waived.includes(l));
  return { kind: bad.length ? 'bad' : 'ok', bad, high: [] };
}
/** 校准页拦不拦：只看红线。黄线（≥55% 红线）只提醒、照常录（Mako 2026-10-15）：
 *  第 5 次佩戴底噪 62–81 µV，三分之二放松段碰黄线、0 过红线；10-09 第 7 次 60–85 µV 照样训出 0.705。 */
export const calibrationHolds = (n: Noise) => n.kind === 'bad';
/** 放过过线的路（累计去重）。同时清 restDue：完成页放过后不再逼着重录放松，按留一分给按钮（2026-10-16 截图 100% 卡在灰按钮） */
export const waiveCal = (c: Cal, bad: number[]): Cal => ({ ...c, waived: [...new Set([...(c.waived ?? []), ...bad])].sort((a, b) => a - b), restDue: false });
/** 完成页是否只给「重录放松」：现在过线（扣掉放过的路），或这一戴过线过、还没放过 */
export const askRestFor = (c: Cal | null | undefined, holds: boolean) => c?.phase === 'done' && (holds || !!c.restDue);
/** 能不能「仍然开始」：现在过线，且已放过的路加上现在过线的路合计不超过上限（2 通道最多放过 1 路，8/16 通道最多 2 路） */
export const canWaive = (n: Noise, waived: number[] | null | undefined, totalCh = 8) => {
  const maxWaive = Math.min(2, Math.max(1, totalCh - 1));
  return calibrationHolds(n) && new Set([...(waived ?? []), ...n.bad]).size <= maxWaive;
};

/** 用手势页要不要暂停出招：1–2 路过线 = 电极没贴好，立刻停；多路过线可能是在用力，持续 WIDE_LOOSE_MS 才算整条松了（底噪取近 4 s 最低值，从开始过线算实际约 14 s）。
 *  wideSince = 多路连续过线的起点（0 = 现在没有）。2026-10-14 一局 6 路 >150 µV 持续 2.5 分钟没停，才加持续判定。 */
export const WIDE_LOOSE_MS = 10000;
export function contactPause(n: Noise, wideSince: number, now: number, totalCh = 8): boolean {
  if (n.kind !== 'bad') return false;
  const maxBad = Math.min(2, Math.max(1, totalCh - 1));
  return n.bad.length <= maxBad || (wideSince > 0 && now - wideSince >= WIDE_LOOSE_MS);
}

/** 底噪 = 最近 windowMs 内每路 RMS 的最低值：动作时数值升高是肌肉信号，不该报红；放松那一截才是底噪（Mako 2026-10-08）。 */
export function noiseFloor(history: { t: number; rms: number[] }[], now: number, windowMs = 4000): number[] | null {
  const valid = history.filter((h) => now - h.t <= windowMs && h.rms.length >= 2);
  if (!valid.length) return null;
  const nCh = valid[valid.length - 1].rms.length;
  const recent = valid.filter((h) => h.rms.length === nCh);
  return Array.from({ length: nCh }, (_, c) => Math.min(...recent.map((h) => h.rms[c])));
}

/** 开始整轮校准时该用几号佩戴：上一次校准完成的编号 = 现在的编号 → 这是新戴上的，自动 +1（上限 20）；否则照用。
 *  2026-10-08 Mako 三轮校准编号都停在 6，坏数据混训，才加这条；「佩戴与信号」里仍可手改。 */
export const nextDonning = (current: number, lastCalibrated: number | null) => (lastCalibrated != null && lastCalibrated >= current ? Math.min(20, lastCalibrated + 1) : current);

/** 校准完成后的同次佩戴留一分怎么说（2026-10-09 走查：24% 也写「模型好了，可以开始用手势」，用户会直接去用）。
 *  n 类随机猜约 1/n；< 55% 当「认不准」，主按钮改成再补一轮；< 75% 一般；其余可以用。 */
export type ScoreVerdict = { kind: 'unknown' | 'bad' | 'fair' | 'good'; title: string; hint: string };
export function scoreVerdict(score: number | null | undefined, n: number): ScoreVerdict {
  if (score == null || !Number.isFinite(score)) return { kind: 'unknown', title: '模型好了', hint: '没拿到估计分，先试一下再说' };
  const p = `${Math.round(score * 100)}%`;
  if (score < .55) return { kind: 'bad', title: `练好了，但只认对 ${p}`, hint: `接近乱猜（${n} 类随机约 ${Math.round(100 / n)}%）：多半是电极没贴紧或动作太轻。先「再补一轮」，不行就回「戴好」重新检查贴合` };
  if (score < .75) return { kind: 'fair', title: `模型好了 · 认对 ${p}`, hint: '一般。可以先试，不准的手势用「再补一轮」补' };
  return { kind: 'good', title: `模型好了 · 认对 ${p}`, hint: '不准的手势用「再补一轮」补。光标移动在「控制」页，用手腕角速度。' };
}

/** 录完之后主按钮：底噪过线过就只能重录放松；分数太低才「先试试看」；其余去看认到哪一类。 */
export function doneActions(kind: ScoreVerdict['kind'], askRest: boolean): 'rest' | 'retry' | 'look' {
  if (askRest) return 'rest';
  if (kind === 'bad') return 'retry';
  return 'look';
}

/** 把底噪判定翻成人话：只有 1–2 路高、其余正常 = 那几片电极没贴紧（接触噪声，不是肌肉——肌肉会让多路一起升）；多路高 = 整体戴法 / 沾水问题。 */
export function noiseAdvice(n: Noise, limit: number, totalCh = 8): string {
  if (n.kind === 'unknown') return '等信号';
  if (n.kind === 'ok') return '底噪正常';
  if (n.kind === 'high') return `底噪偏高：第 ${n.high.join('、')} 路，建议沾水压紧再录`;
  const maxBad = Math.min(2, Math.max(1, totalCh - 1));
  return n.bad.length <= maxBad ? `第 ${n.bad.join('、')} 路电极没贴紧（≥ ${limit} µV，其余 ${Math.max(0, totalCh - n.bad.length)} 路正常）：压一下亮红的那片，稳了自动继续`
    : `整体底噪太高：${n.bad.length} 路 ≥ ${limit} µV，摘下沾水重新戴紧`;
}

/** 停录后留下的底噪样本：和 stopForRelaxationNoise 同一个时间基准（现在往前 2 s）。
 *  原来按最后一个样本往前 2 s 裁，多留下约 0.1 s 前的一条好样本；底噪取最低值，这一条就把红盖掉，
 *  等贴合 1.5 s 后自动恢复、再录再停（2026-10-15 夹具复现）。 */
export const pauseHistory = <T extends { t: number }>(history: T[], now: number) => history.filter((h) => h.t <= now && now - h.t <= 2000);

/** 等贴合恢复用的判定：只看最近 0.5 s（约 5 条 RMS）的最低值。原来用 4 s 最低值，一条好样本能管 4 s，
 *  「连续 1.5 s 不过线」等于没查，接触忽好忽坏时录了停、停了录（复核 #76）。 */
export const RECOVER_WINDOW_MS = 500;
export function contactGate(history: { t: number; rms: number[] }[], now: number, limit: number, waived?: number[]): Noise {
  const recent = history.filter((h) => h.t <= now && now - h.t <= RECOVER_WINDOW_MS);
  return waiveNoise(noiseVerdict(noiseFloor(recent, now, RECOVER_WINDOW_MS), limit), waived);
}

/** 仅显式放松倒数可以拦录制。连续有效放松样本不足 1.2 s 或已过期时不下结论。
 * 动作窗无论多大都不参与；放松测量开始后的前 0.6 s 由页面跳过，避开上一动作尾巴。 */
export function stopForRelaxationNoise(history: { t: number; rms: number[] }[], now: number, phase: string | undefined, limit: number, waived?: number[]): boolean {
  if (!phase || !/^[1-9]$/.test(phase)) return false;
  const valid = pauseHistory(history, now).filter(h => h.rms.length >= 2 && h.rms.every(Number.isFinite));
  if (valid.length < 2) return false;
  const nCh = valid[valid.length - 1].rms.length;
  const recent = valid.filter(h => h.rms.length === nCh);
  if (recent.length < 2 || now - recent.at(-1)!.t > 500 || recent.at(-1)!.t - recent[0].t < 1200) return false;
  return waiveNoise(noiseVerdict(noiseFloor(recent, now, 2000), limit), waived).kind === 'bad';
}
