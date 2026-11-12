'use client';

import { useState } from 'react';
import type { Hand } from './contract';
import './gesture-library.css';

type Gesture = {
  id: number;
  name: string;
  slug: string;
};

const GESTURES: Gesture[] = [
  { id: 1, name: '全手屈伸', slug: 'full-hand' },
  { id: 2, name: '大拇指屈伸', slug: 'thumb' },
  { id: 3, name: '食指屈伸', slug: 'index' },
  { id: 4, name: '中指屈伸', slug: 'middle' },
  { id: 5, name: '小指伸屈', slug: 'little' },
  { id: 6, name: '食中伸屈', slug: 'index-middle' },
  { id: 7, name: '食小伸屈', slug: 'index-little' },
  { id: 8, name: '大食中伸屈', slug: 'thumb-index-middle' },
  { id: 9, name: '中无名小伸屈', slug: 'middle-ring-little' },
  { id: 10, name: '食中无名小伸屈', slug: 'four-fingers' },
  { id: 11, name: '捏食指', slug: 'pinch-index' },
  { id: 12, name: '捏中指', slug: 'pinch-middle' },
  { id: 13, name: '捏无名指', slug: 'pinch-ring' },
  { id: 14, name: '捏小指', slug: 'pinch-little' },
  { id: 15, name: '中无名屈伸', slug: 'middle-ring-flex' },
  { id: 16, name: '食中无名屈伸', slug: 'index-middle-ring-flex' },
];

// 相对路径：App 从 file://…/dist/index.html 打开，开头带 / 会解析到磁盘根目录（10-22 实测整页裂图）；素材在 public/gesture-library，构建时复制进 dist
const asset = (hand: Hand, gesture: Gesture, extension: 'jpg' | 'mp4') =>
  `gesture-library/${hand}/${gesture.id.toString().padStart(2, '0')}-${gesture.slug}.${extension}`;

export function GestureLibrary({
  hand,
  onHandChange,
}: {
  hand: Hand;
  onHandChange: (hand: Hand) => void;
}) {
  const [selectedId, setSelectedId] = useState(11);
  const selected = GESTURES.find((gesture) => gesture.id === selectedId) ?? GESTURES[10];

  return (
    <section className="emg8-gesture-library" aria-labelledby="gesture-library-title">
      <header className="emg8-card emg8-gesture-library-head">
        <div>
          <h3 id="gesture-library-title">16 个动作参考</h3>
          <p>选择左右手，再点一个动作查看完整循环。自然完成动作，不要刻意绷紧。</p>
        </div>
        <div className="emg8-gesture-hand" role="group" aria-label="演示手">
          <button aria-pressed={hand === 'left'} onClick={() => onHandChange('left')}>左手</button>
          <button aria-pressed={hand === 'right'} onClick={() => onHandChange('right')}>右手</button>
        </div>
      </header>

      <div className="emg8-gesture-layout">
        <article className="emg8-card emg8-gesture-player">
          <div className="emg8-gesture-player-title">
            <span>{selected.id.toString().padStart(2, '0')}</span>
            <div><h3>{selected.name}</h3><small>{hand === 'left' ? '左手' : '右手'} · 跟随一轮后放松</small></div>
          </div>
          <video
            key={`${hand}:${selected.id}`}
            autoPlay
            controls
            loop
            muted
            playsInline
            poster={asset(hand, selected, 'jpg')}
            aria-label={`${hand === 'left' ? '左手' : '右手'}${selected.name}动作演示`}
          >
            <source src={asset(hand, selected, 'mp4')} type="video/mp4" />
          </video>
          <p className="emg8-fine">动作参考库不会修改当前模型，也不会自动开始录制。</p>
        </article>

        <div className="emg8-gesture-grid" aria-label="动作列表">
          {GESTURES.map((gesture) => (
            <button
              className="emg8-gesture-tile"
              key={gesture.id}
              aria-pressed={gesture.id === selected.id}
              onClick={() => setSelectedId(gesture.id)}
            >
              <img src={asset(hand, gesture, 'jpg')} alt="" />
              <span><b>{gesture.id.toString().padStart(2, '0')}</b>{gesture.name}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
