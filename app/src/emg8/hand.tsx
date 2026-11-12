'use client';
// 校准动画手：教人怎么动。rest = 手掌朝下放平别动；lr = 俯视，像雨刷一样左右挥手（先往右）；ud = 侧视，手肘当支点整条前臂上下抬（先往上）。
// 手环戴在前臂上只感知前臂转动：只弯手腕测不到（2026-09-30 真腕带实测上下不动），所以 ud 画的是整条前臂动、手腕不弯。
// 用 SVG 自带的 animateTransform 绕手腕转：不依赖 CSS transform-origin 在 SVG 里的各种坑。左手时俯视图镜像（拇指在右）。
import type { Hand } from './contract';

export type GuideStep = 'rest' | 'lr' | 'ud' | 'free' | 'pinch' | 'release';
/** 捏合校准的步骤（服务端 PINCH_PLAN 的 key → 动画） */
export const PINCH_STEP: Record<string, GuideStep> = { rest: 'rest', move: 'free', pinch: 'pinch', gap: 'release' };
export const PINCH_GUIDE: { key: GuideStep; title: string; hint: string }[] = [
  { key: 'rest', title: '放松别动', hint: '4 秒' },
  { key: 'free', title: '不捏，随便动', hint: '前臂左右上下动，手指放松，5 秒' },
  { key: 'pinch', title: '捏住保持', hint: '拇指食指捏紧 5 秒，松开 4 秒，做 3 次' },
];
export const GUIDE: { key: GuideStep; title: string; hint: string }[] = [
  { key: 'rest', title: '放平别动', hint: '手掌朝下搁稳，5 秒' },
  { key: 'lr', title: '左右挥手', hint: '像雨刷，先往右，5 秒' },
  { key: 'ud', title: '前臂上下抬', hint: '手肘不动、手腕别弯，先往上，5 秒' },
];

const SPLINES = '.45 0 .55 1;.45 0 .55 1;.45 0 .55 1;.45 0 .55 1';
const swing = (a: number, x: number, y: number, dur: number) =>
  <animateTransform attributeName="transform" type="rotate" dur={`${dur}s`} repeatCount="indefinite" calcMode="spline" keyTimes="0;.25;.5;.75;1" keySplines={SPLINES}
    values={`0 ${x} ${y};${a} ${x} ${y};0 ${x} ${y};${-a} ${x} ${y};0 ${x} ${y}`} />;

/** 俯视的手（手掌朝下，手指朝上），手腕在 (130,150) */
function TopHand({ thumbRight }: { thumbRight: boolean }) {
  const fingers = [[104, 44], [118, 54], [132, 52], [146, 42]] as const;
  return <g className="hg-hand">
    {fingers.map(([x, h]) => <rect key={x} x={x - 1} y={84 - h} width={12} height={h + 8} rx={6} />)}
    <rect x={100} y={80} width={60} height={72} rx={18} />
    <rect x={thumbRight ? 150 : 84} y={100} width={26} height={12} rx={6} transform={`rotate(${thumbRight ? -35 : 35} ${thumbRight ? 152 : 108} 106)`} />
    <line x1={112} y1={128} x2={148} y2={128} className="hg-knuckle" />
  </g>;
}

/** 侧视的手（手指朝右、手背朝上），手腕在 (120,110) */
function SideHand() {
  return <g className="hg-hand">
    <rect x={120} y={94} width={62} height={32} rx={14} />
    <rect x={176} y={98} width={56} height={22} rx={11} />
    <rect x={150} y={84} width={34} height={12} rx={6} transform="rotate(-12 150 90)" />
  </g>;
}

/** 从拇指一侧看的整只手：拇指和食指捏到一起，中指、无名指、小指自然弯在后面（浅色）。
 *  每根手指是从指根 (px,py) 往外的圆角条，绕指根转；animate 时 张开 → 捏住保持 → 张开 循环，和服务端「捏住 5 秒」无关，只演示动作。 */
function Finger({ px, py, len, h, open, shut, animate, back }: { px: number; py: number; len: number; h: number; open: number; shut: number; animate: boolean; back?: boolean }) {
  return <g transform={animate ? undefined : `rotate(${open} ${px} ${py})`}>
    {animate && <animateTransform attributeName="transform" type="rotate" dur="2.6s" repeatCount="indefinite" keyTimes="0;.25;.75;1"
      values={`${open} ${px} ${py};${shut} ${px} ${py};${shut} ${px} ${py};${open} ${px} ${py}`} />}
    <rect x={px - 6} y={py - h / 2} width={len + 6} height={h} rx={h / 2} className={back ? 'hg-finger-back' : undefined} />
  </g>;
}
function PinchFingers({ animate }: { animate: boolean }) {
  return <g className="hg-hand">
    <Finger px={130} py={92} len={40} h={11} open={50} shut={58} animate={animate} back />
    <Finger px={133} py={97} len={48} h={12} open={42} shut={50} animate={animate} back />
    <Finger px={136} py={102} len={54} h={13} open={34} shut={44} animate={animate} back />
    <rect x={64} y={90} width={78} height={76} rx={22} />
    <Finger px={136} py={108} len={52} h={14} open={8} shut={34} animate={animate} />
    <Finger px={126} py={158} len={54} h={15} open={14} shut={-20} animate={animate} />
    {animate && <circle cx={176} cy={138} r={9} className="hg-spark">
      <animate attributeName="opacity" dur="2.6s" repeatCount="indefinite" keyTimes="0;.24;.3;.72;.76;1" values="0;0;1;1;0;0" /></circle>}
  </g>;
}

/** 侧视的整条前臂 + 手（手腕不弯），手肘在 (40,150)；手环画在靠手腕的前臂上 */
function Forearm() {
  return <g>
    <rect x={30} y={137} width={112} height={26} rx={12} className="hg-armmove" />
    <rect x={106} y={133} width={20} height={34} rx={5} className="hg-band" />
    <g transform="translate(16 39)"><SideHand /></g>
  </g>;
}

export function HandGuide({ step, hand = 'left', size = 220, active = true }: { step: GuideStep; hand?: Hand; size?: number; active?: boolean }) {
  const thumbRight = hand === 'left';                          // 左手手掌朝下，拇指在右边
  return <svg className={`emg8-hg ${active ? 'on' : ''}`} viewBox="0 0 260 210" width={size} height={size * 210 / 260} aria-label={GUIDE.find((g) => g.key === step)?.title}>
    <defs>
      <marker id="hg-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" className="hg-arrowhead" /></marker>
    </defs>
    {step === 'rest' && <>
      <rect x={60} y={176} width={140} height={10} rx={5} className="hg-table" />
      <circle cx={130} cy={112} r={70} className="hg-pulse"><animate attributeName="r" values="58;78;58" dur="2.4s" repeatCount="indefinite" /><animate attributeName="opacity" values=".5;0;.5" dur="2.4s" repeatCount="indefinite" /></circle>
      <rect x={108} y={150} width={44} height={40} rx={10} className="hg-arm" />
      <TopHand thumbRight={thumbRight} />
      <text x={130} y={24} className="hg-label">别动 · 放松</text>
    </>}
    {step === 'lr' && <>
      <path d="M 70 58 A 90 90 0 0 1 190 58" className="hg-path" markerStart="url(#hg-arrow)" markerEnd="url(#hg-arrow)" />
      <g className="hg-ghost" transform="rotate(28 130 150)"><TopHand thumbRight={thumbRight} /></g>
      <g className="hg-ghost" transform="rotate(-28 130 150)"><TopHand thumbRight={thumbRight} /></g>
      <rect x={108} y={150} width={44} height={50} rx={10} className="hg-arm" />
      <g>{swing(28, 130, 150, 2.4)}<TopHand thumbRight={thumbRight} /></g>
      <circle cx={130} cy={150} r={5} className="hg-pivot" />
      <text x={214} y={50} className="hg-label hg-first">先往右 →</text>
    </>}
    {step === 'ud' && <>
      <rect x={6} y={164} width={110} height={8} rx={4} className="hg-table" />
      <path d="M 236 98 A 205 205 0 0 1 236 202" className="hg-path" markerStart="url(#hg-arrow)" markerEnd="url(#hg-arrow)" />
      <g className="hg-ghost" transform="rotate(-15 40 150)"><Forearm /></g>
      <g className="hg-ghost" transform="rotate(15 40 150)"><Forearm /></g>
      <g>{swing(-15, 40, 150, 2.6)}<Forearm /></g>
      <circle cx={40} cy={150} r={6} className="hg-pivot" />
      <text x={196} y={40} className="hg-label hg-first">↑ 先往上</text>
      <text x={110} y={198} className="hg-sub">手肘当支点 · 手腕别弯</text>
    </>}
    {step === 'free' && <>
      <path d="M 70 58 A 90 90 0 0 1 190 58" className="hg-path" markerStart="url(#hg-arrow)" markerEnd="url(#hg-arrow)" />
      <rect x={108} y={150} width={44} height={50} rx={10} className="hg-arm" />
      <g>{swing(20, 130, 150, 1.6)}<TopHand thumbRight={thumbRight} /></g>
      <text x={130} y={24} className="hg-label">不捏 · 随便动</text>
    </>}
    {(step === 'pinch' || step === 'release') && <>
      <rect x={14} y={112} width={56} height={36} rx={12} className="hg-arm" />
      <rect x={40} y={108} width={18} height={44} rx={5} className="hg-band" />
      <PinchFingers animate={step === 'pinch'} />
      <text x={130} y={24} className={`hg-label ${step === 'pinch' ? 'hg-first' : ''}`}>{step === 'pinch' ? '捏住 · 保持' : '松开 · 手指放松'}</text>
    </>}
  </svg>;
}
