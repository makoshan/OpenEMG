import definitions from '../../electron/emg8-profiles.json';
import type { RunSummary, ServiceState } from './contract';

export type ProfileId = keyof typeof definitions;
export type Profile = { name: string; labels: string[]; captureLabels?: string[]; windowMs?: number; protocol?: string; game?: string; /* 'tianjie'：识别页可把触发送进掌中天劫 */ layout?: string; /* 'cards'：按卡片排（手指十六类）；JSON 导入推不出字面量类型 */ calibrate?: { rounds: number; minRatio: number; minTrain?: number; shuffle?: boolean }; minTrain: number; minRewear: number; gestures?: Record<string, { name: string; icon: string; color: string; cue: string; kind?: string }> };
export const PROFILES: Record<ProfileId, Profile> = definitions;
/** 类别中文名：基础类 + 各动作组 gestures 的 name（后面的组同名覆盖前面的）。contract.ts 转出给页面用 */
export const LABEL_CN: Record<string, string> = { rest: '放松', pinch: '捏合', rub: '搓动', fist: '握拳', left: '左滑 · 屈腕', right: '右滑 · 伸腕', click: '单击 · 捏合', loose: '松脱', ...Object.fromEntries(Object.values(PROFILES).flatMap((p) => Object.entries(p.gestures ?? {}).map(([k, v]) => [k, v.name]))) };
const labelName = (profile: Profile, l: string) => profile.gestures?.[l]?.name ?? LABEL_CN[l] ?? l;
export const profileId = (value: unknown): ProfileId => typeof value === 'string' && Object.hasOwn(definitions, value) ? value as ProfileId : 'thumb-four';
// 必须完整匹配类别：旧屈腕模型和缺方向的模型不能冒充四向模型。
export const matchesProfile = (run: Pick<RunSummary, 'labels'>, profile: Profile) =>
  run.labels.length === profile.labels.length && profile.labels.every((l) => run.labels.includes(l));
export function trainingBlock(st: ServiceState | null, profile: Profile, projectId: string): string {
  const ch = st?.rig.n_channels ?? 8;
  if (!st || st.project?.id !== projectId || st.rig.kind !== 'wl8') return ch === 8 ? '先连接本工程的八通道采集服务' : `先连接本工程的 ${ch} 通道采集服务`;
  if (st.rig.replay || st.wl8?.replay) return '回放不能训练现场模型';
  if (!profile.labels.every((l) => st.tiers.includes(l))) return '采集服务版本过旧，请重新连接';
  const need = profile.calibrate?.minTrain ?? profile.minTrain;          // 每次佩戴校准每类 3 次就够（服务端同一口径）
  const missing = profile.labels.filter((l) => (st.counts.train?.wl8?.[l] ?? 0) < need);
  if (missing.length) return `每类至少 ${need} 条训练数据，还缺 ${missing.map((l) => labelName(profile, l)).join('、')}`;
  // 旧屈腕训练仍由原服务校验完整验证集，避免放开后在旧后端报错。
  if (!profile.protocol && profile.layout !== 'classic' && !profile.labels.some((l) => l.startsWith('thumb_'))) {   // 经典组后补动作时不该被旧动作的重戴集拦住
    const rewear = st.counts.rewear?.wl8 ?? {};
    if (profile.labels.some((l) => rewear[l] > 0) && profile.labels.some((l) => (rewear[l] ?? 0) < profile.minRewear)) return '重戴验证数据尚未齐全';
  }
  return '';
}
// 重戴验证是单独的验收项，不阻止已有完整训练集生成基础模型。
export function validationHint(st: ServiceState | null, profile: Profile): string {
  const rewear = st?.counts.rewear?.wl8 ?? {};
  const incomplete = profile.labels.filter((l) => (rewear[l] ?? 0) < profile.minRewear);
  if (incomplete.length) return `可以先训练基础模型。重戴验证每类至少 ${profile.minRewear} 条，还缺 ${incomplete.map((l) => labelName(profile, l)).join('、')}`;
  return '';
}

// 经典 5 步（唯理流程）：动作 1–16 里勾几个就是几类，放松固定第 0 类。工作室把「勾了哪些 + 改的名字」折成一个只含这些类的动作组，
// 往下传给录制、训练门槛、模型匹配和识别页，它们就不用各自认识「经典」。
export type ClassicPick = { picked: number[]; names: Record<string, string> };
export const CLASSIC_REST = 'classic_rest';
export const CLASSIC_MOVE = 'classic_move';   // 随意动手 / 不触发：识别成它等于没动作（2026-10-15 Mako：用的时候手肯定在动）
export const classicLabel = (n: number) => `classic_${n}`;
export function classicView(base: Profile, pick: ClassicPick): Profile {
  const nums = [...new Set(pick.picked)].filter((n) => Number.isInteger(n) && n >= 1 && n <= 16).sort((a, b) => a - b);
  const labels = [CLASSIC_REST, CLASSIC_MOVE, ...nums.map(classicLabel)];
  const gestures = Object.fromEntries(labels.map((l) => {
    const g = base.gestures?.[l] ?? { name: l, icon: '', color: '#888', cue: '' };
    const name = pick.names[l]?.trim() || g.name;
    return [l, { ...g, name, cue: l === CLASSIC_REST || l === CLASSIC_MOVE ? g.cue : `看到「做！」后做「${name}」，保持到提示结束。` }];
  }));
  return { ...base, labels, gestures };
}
