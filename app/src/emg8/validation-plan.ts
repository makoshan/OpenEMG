// 提示只是计划；实际动作起止必须之后从手部视频核对。
export type ValidationCue = { label: string; text: string; seconds: number };
export function validationPlan(labels: string[], names: Record<string, string>, random = Math.random): ValidationCue[] {
  const actions = labels.slice(1).flatMap(l => Array(7).fill(l) as string[]);
  for (let i = actions.length - 1; i > 0; i--) { const j = Math.floor(random() * (i + 1)); [actions[i], actions[j]] = [actions[j], actions[i]]; }
  return [{ label: 'prepare', text: '准备开始，请保持手部入镜', seconds: 5 },
    { label: labels[0], text: '自然放松，手臂有支撑', seconds: 30 },
    ...actions.flatMap(l => [{ label: l, text: `做：${names[l] ?? l}`, seconds: 3 }, { label: labels[0], text: '松开，回到放松', seconds: 4 }]),
    { label: 'non_target_movement', text: '随意动手、转腕，但不要做目标手势', seconds: 60 }];
}
