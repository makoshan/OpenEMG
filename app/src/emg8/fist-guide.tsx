'use client';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { Hand } from './contract';
import { sameFingerNote } from './readout';
import type { GuideMode } from './thumb-guide';
import { grayTitle } from './gray-title';

// 手势示范：OpenEMG 自绘 400×400 白线透明底几何动图（public/images/emg8-meta/*.webp，经 CSS invert 转为深色细线）。
// 播放规则：准备 / 暂停 = 停在首帧静图；预览 = 循环播；录制「做！」= 从头播一遍后停回首帧，不让动图无限循环带偏采集。
// 方向口径：上 / 下 = 沿食指（朝指尖 = 上，两只手一样）；左 / 右 = 拇指横越食指朝**你的左 / 右边**拨（空间方向，和 Meta 一致）。
// 动图画的是**右手**（Mako 2026-10-08 指出）；左手整体镜像后左右会反，所以左手把左右两段片子对调再镜像（Mako 2026-10-08 发现「左滑动画往右」）。
export const ANIM: Record<string, { file: string; ms: number; loop?: [number, number]; go?: number }> = {
  mouse_rest: { file: 'thumb_swipe_up', ms: 0 },                 // 放松没有独立动图：用握拳首帧静图
  mouse_up: { file: 'thumb_swipe_up', ms: 1480 }, mouse_down: { file: 'thumb_swipe_down', ms: 1620 },
  mouse_left: { file: 'thumb_swipe_left', ms: 2040 }, mouse_right: { file: 'thumb_swipe_right', ms: 1660 },
  mouse_side: { file: 'thumb_click', ms: 1700 }, mouse_index: { file: 'index_pinch', ms: 1370 }, mouse_middle: { file: 'middle_pinch', ms: 1410 },
  mouse_swipe: { file: 'thumb_swipe_up', ms: 1480 },            // 拇指拨动（上 / 下 / 左合成一类，2026-10-10）：示范只放一个方向，口令里说明别的方向也行
  // 结印（2026-10-16 codex 按 Mako 的实拍重画，脚本 app/scripts/seal-anim/）：从松握拳摆出手印并停在手印上；放松用破邪印的首帧
  seal_rest: { file: 'seal_poxie', ms: 0 },
  // loop：结印动图在准备 / 录制 / 暂停时都一直循环放（Mako 2026-10-16「这个演示动画，要一直放」）；[a, b] = 起手结束、摆印结束占一遍的比例，
  // 不录制时步骤高亮按它走；录制时高亮跟口令走，go = 「做！」后摆印那段的时长
  seal_poxie: { file: 'seal_poxie', ms: 2600, loop: [.23, .54], go: 480 }, seal_daozhi: { file: 'seal_daozhi', ms: 2600, loop: [.23, .54], go: 480 }, seal_wulei: { file: 'seal_wulei', ms: 2600, loop: [.23, .54], go: 480 },
  // EgoEMG 六手势（2026-10-16）：codex 生图、按 EgoEMG 动捕核过的静图（app/scripts/egoemg-guide/），唤起借中指捏合首帧；没有动图，连续动作靠口令说节奏
  ego_rest: { file: 'ego_rest', ms: 0 }, ego_pinch_middle: { file: 'middle_pinch', ms: 0 }, ego_thumb_slide: { file: 'ego_thumb_slide', ms: 0 },
  ego_index_bow: { file: 'ego_index_bow', ms: 0 }, ego_ring_thumb: { file: 'ego_ring_thumb', ms: 0 }, ego_claw5: { file: 'ego_claw5', ms: 0 },
};
/** 静止示范（放松类）：没有动画，停在首帧 */
const still = (label: string) => !(ANIM[asMouse(label)]?.ms > 0);
// 相对路径：App 用 file:// 打开 dist/index.html，绝对路径 /images 会找不到（2026-10-14 发现原力手环 App 示范图一直是空的）
const BASE = './images/emg8-meta/';
const SWAP: Record<string, string> = { mouse_left: 'mouse_right', mouse_right: 'mouse_left' };
/** AI 选择和鼠标组共用示范片子。唤起 = 中指尖碰拇指。 */
export const asMouse = (label: string) => label === 'ai_summon' ? 'mouse_middle' : label.startsWith('ai_') ? `mouse_${label.slice(3)}` : label;
/** 左手：镜像会把横向方向反过来，左滑用右滑的片子（镜像后拇指才往左走） */
export const clipLabel = (label: string, hand: Hand) => (hand === 'left' ? SWAP[label] ?? label : label);
/** 此刻该显示哪张：静图（首帧）还是动图；playing = 录制里这一遍还没播完 */
export const guideSrc = (label: string, mode: GuideMode, playing: boolean, hand: Hand = 'right') => {
  const a = ANIM[clipLabel(asMouse(label), hand)] ?? ANIM.mouse_rest;
  const anim = a.ms > 0 && (!!a.loop || mode === 'preview' || (mode === 'record' && playing));
  return BASE + a.file + (anim ? '.webp' : '-first.png');
};
/** 三步里当前高亮哪一步：0 起手、1 做动作、2 复位 */
export const guideStep = (label: string, mode: GuideMode, seconds: number, hand: Hand = 'right') => {
  if (label.startsWith('ego_')) return label !== 'ego_rest' && mode === 'record' ? 1 : 0;   // 静图：录制时高亮「做」，其余停在起手
  const mouse = asMouse(label);
  const a = ANIM[clipLabel(mouse, hand)];
  if (a?.loop && mode === 'prepare') return 0;
  if (a?.loop && mode === 'record') return seconds * 1000 < (a.go ?? 500) ? 1 : 2;              // 「做！」后：摆印 → 保持
  if (a?.loop) { const f = ((seconds * 1000) % a.ms) / a.ms; return f < a.loop[0] ? 0 : f < a.loop[1] ? 1 : 2; }   // 不录制：循环示范
  if (still(label) || !(mode === 'preview' || mode === 'record')) return 0;
  const ms = a?.ms ?? 1500, s = mode === 'preview' ? (seconds * 1000) % (ms + 600) : seconds * 1000;
  return s < ms * .15 ? 0 : s < ms * .75 ? 1 : 2;
};

export function FistGuide({ label, kind, name, icon, cue, hand, mode, takeKey, onPreview }: {
  label: string; kind?: string; name: string; icon: string; cue: string; hand: Hand; mode: GuideMode; takeKey: string; onPreview: () => void;
}) {
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const bump = useRef(0);                                           // 鼠标组：每次重新进入 record 换一次 key，<img> 才会从第 0 帧重播
  // layout effect：在绘制前切到「正在播」，「做！」那一刻不会先闪一帧首帧静图
  useLayoutEffect(() => {
    const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (mode !== 'record' || reduced) { setPlaying(false); return; }
    bump.current++; setPlaying(true);
    const clip = ANIM[clipLabel(asMouse(label), hand)];
    const id = setTimeout(() => setPlaying(false), (clip?.go ?? clip?.ms ?? 1500) + 80);   // 播一遍就停回首帧（左手左右对调后按实际片子的时长）
    return () => clearTimeout(id);
  }, [label, mode, takeKey, hand]);
  const loop = !!ANIM[asMouse(label)]?.loop;
  useEffect(() => {
    if (mode === 'paused' && !loop) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let raf = 0; const start = performance.now();
    const tick = () => { setT(reduced ? 0 : (performance.now() - start) / 1000); if (!reduced && (loop || mode === 'preview' || mode === 'record') && !still(label)) raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [label, mode, takeKey, loop]);
  const step = guideStep(label, mode, t, hand);
  const src = guideSrc(label, mode, playing, hand);
  const mouse = asMouse(label);
  const along = mouse === 'mouse_up' || mouse === 'mouse_down', any = mouse === 'mouse_swipe';
  const pinch = mouse === 'mouse_index' || mouse === 'mouse_middle';
  const seal = label.startsWith('seal_');                        // 结印：摆好后保持，不是做一下就松
  // 结印三印另放 Mako 的实拍（2026-10-16 拍的是左手，存成水平翻转的右手，和白线示范同一口径：左手佩戴时再镜像回来）；放松没有实拍
  const photo = seal && !still(label) ? `${BASE}${label}-photo.jpg` : '';
  const ego = label.startsWith('ego_');
  const steps = ego ? kind === 'rest' ? ['手自然放松，手指微弯不碰', '保持放松，不施力', '继续放松']
      : kind === 'cont' ? ['手放松', `看到“做！”后连续做${name}，约每 1–1.5 秒一次`, '一直做到提示结束']
      : ['手放松', `看到“做！”后摆出${name}`, '保持住，直到提示结束']
    : still(label) ? ['松握拳，拇指搭在食指上', '保持放松，不施力', '继续放松']
    : seal ? ['松握拳，手放松', `看到“做！”后摆出${name}`, '保持住，直到提示结束']
    : mouse === 'mouse_side' ? ['松握拳，拇指悬在食指上方', '看到“做！”后轻点一下', '抬起，回到悬空']
    : pinch ? ['松握拳，手放松', `看到“做！”后${mouse === 'mouse_index' ? '食指' : '中指'}尖碰拇指尖一下`, '分开，回到松握拳']
    : ['松握拳，拇指搭在食指侧面', `看到“做！”后${any ? '朝指尖、指根或你的左边' : along ? '沿着食指' : '横越食指朝' + (mouse === 'mouse_left' ? '左' : '右')}拨一下`, '拨到头停一下，再慢慢抬回来，别弹回去。'];
  return <div className="emg8-demo-body">
    <figure className={`emg8-thumb-picture emg8-meta-anim${photo ? ' with-photo' : ''}`}>
      <small>{hand === 'left' ? '左手' : '右手'} · {photo ? '示范 · 实拍' : ego ? '示范' : '松握拳'}</small>
      <div className="emg8-meta-anim-frame" data-mode={mode} data-playing={playing ? 'on' : undefined}>
        <img key={`${src}:${loop ? 0 : bump.current}`} src={src} alt={`${name}动作示范`} style={{ transform: hand === 'left' ? 'scaleX(-1)' : undefined }} draggable={false} />
        {!ego && <span className="emg8-meta-anim-icon">{icon}</span>}   {/* EgoEMG 示范图细节多，图标不压在手上 */}
      </div>
      {photo ? <img className="emg8-meta-photo" src={photo} alt={`${name}实拍`} style={{ transform: hand === 'left' ? 'scaleX(-1)' : undefined }} draggable={false} /> : null}
      <figcaption>{ego ? kind === 'rest' ? '手指微弯不碰，保持放松' : kind === 'cont' ? '来回做，不停，到提示结束' : '摆好后保持，别松开' : still(label) ? '拇指轻搭食指，保持放松' : seal ? '摆好后保持，别松开' : mouse === 'mouse_side' ? '点一下，不要滑' : pinch ? '轻碰一下就分开' : `${any ? '朝指尖、指根或你的左边都行，别朝右，' : along ? (mouse === 'mouse_up' ? '朝指尖' : '朝指根') : (mouse === 'mouse_left' ? '横越食指朝你的左边' : '横越食指朝你的右边')}拨一下，拨到头停一下再慢慢抬回来`}</figcaption>
    </figure>
    <div className="emg8-thumb-instructions">
      <h3>{icon} {ego ? name : name.replace('拇指', '')}</h3>   {/* 「拇指滑」「无名指碰拇指」不去掉拇指 */}<p>{cue}</p><small>{ego ? '前臂有支撑，手腕不动；照图摆准就行，不用使劲。' : seal ? '前臂有支撑，手腕不动；手印摆准就行，不用使劲攥。' : '前臂有支撑，手腕不动；手不用攥紧。上下沿食指，左右按你自己看的左右。'}</small>
      {sameFingerNote(label) ? <p className="emg8-warn">{sameFingerNote(label)}</p> : null}
      <ol className="emg8-thumb-sequence">{steps.map((text, i) => <li key={i} className={step === i ? 'current' : ''}><b>{i + 1}</b>{text}</li>)}</ol>
      {loop ? <div className="emg8-preview-controls"><small>{mode === 'record' || mode === 'prepare' ? `跟随口令 · ${['等「做！」', '结印', '保持'][step]}` : `循环示范 · ${['起手', '结印', '保持'][step]}`}</small></div> : <div className="emg8-preview-controls"><button onClick={onPreview} disabled={mode === 'prepare' || mode === 'record'} title={grayTitle((mode === 'prepare' || mode === 'record') && '正在录，示范跟着口令走')}>{mode === 'paused' ? '播放示范' : '暂停示范'}</button><small>{mode === 'record' || mode === 'prepare' ? '跟随真实录制口令' : ego ? kind === 'rest' ? '静止示范 · 不施力' : '静图示范 · 未录制' : still(label) ? '静止示范 · 不施力' : mode === 'paused' ? '示范已暂停' : (seal ? ['起手', '结印', '保持'] : ['起手', '做动作', '复位'])[step] + ' · 未录制'}</small></div>}
    </div>
  </div>;
}
