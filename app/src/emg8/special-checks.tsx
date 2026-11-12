import type { Run } from './contract';
import type { Profile } from './profiles';
import { MetaSequence, type MetaCommand } from './meta-sequence';
const expected: Record<string, MetaCommand> = { meta_index_tap: '选择', meta_middle_tap: '返回', meta_middle_double: '唤醒／熄屏', meta_middle_long: '打开／关闭启动器', meta_side_double: '启动／退出 AI' };
export function trialCommands(ticks: NonNullable<Run['sequence_trials']>[number]['ticks']) {
  const decoder = new MetaSequence(); const commands: MetaCommand[] = [];
  for (const tick of ticks) commands.push(...decoder.push(tick.top, tick.confidence, tick.ms));
  // 只允许最后真实信号时间的待触发动作自然结束；超过断流阈值不补造信号。
  return commands;
}
export function SpecialChecks({ run, profile }: { run: Run; profile: Profile }) {
  if (profile.protocol === 'mouse' || profile.protocol === 'select') return null;   // 鼠标五类和 AI 六类没有独立组合练习，也没有方向校准
  return <section className="emg8-card"><h3>{profile.protocol === 'motion' ? '运动方向校准' : '组合动作检验 · 独立练习录制'}</h3>
    {profile.protocol === 'motion' ? <p>{run.motion_calibration?.status === 'calibrated' ? `第 ${run.motion_calibration.donning} 次佩戴方向已校准；组合动作尚未实物验收。` : run.motion_calibration?.reason ?? '还没有有效运动校准数据。'}</p> : <table className="emg8-confusion"><thead><tr><th>组合动作</th><th>符合口令／已检验</th><th>采集目标</th></tr></thead><tbody>{Object.keys(expected).map((label) => {
      const trials = (run.sequence_trials ?? []).filter((x) => x.label === label);
      const good = trials.filter((x) => { const commands = trialCommands(x.ticks); return !x.error && commands.length === 1 && commands[0] === expected[label]; }).length;
      return <tr key={label}><th>{profile.gestures?.[label]?.name}</th><td>{good} / {trials.length}</td><td>至少 3 条</td></tr>;
    })}</tbody></table>}
    <p className="emg8-fine">组合练习没有参与基础模型拟合。检验依据录制口令与识别结果，仍需你确认实际动作录对；这里不代表重戴准确率。</p>
  </section>;
}
