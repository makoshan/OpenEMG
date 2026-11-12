// 魔法特效层（design/emg-console-v4/magic.html）：一块全屏 canvas，画光迹、星点、冲击波、符文圆环、聚拢光点、背景光尘。
// 只在有东西要画时逐帧刷新；系统开了「减少动态效果」就什么都不画。调用方只在真实事件发生时触发（触发绑定、服务端回执、AI 请求）。
export type Rgb = string;   // 'r,g,b'
export const RGB = { sky: '142,197,240', mint: '95,199,159', sakura: '240,128,140', lilac: '160,135,230', gold: '240,190,80', grey: '160,165,160' } as const;

/** 特效进度 0–1：rAF 的本帧时间可能早于创建时刻，夹到 ≥ 0，否则半径会算成负数（2026-10-06 预览台录到） */
export const progress = (now: number, t0: number, dur: number) => Math.min(1, Math.max(0, (now - t0) / dur));

type Particle = { x: number; y: number; vx: number; vy: number; life: number; dec: number; r: number; rot: number; rgb: Rgb; star: boolean; drift?: boolean };
type Comet = { x0: number; y0: number; x1: number; y1: number; mx: number; my: number; rgb: Rgb; t0: number; dur: number; trail: [number, number][] };
type Wave = { x: number; y: number; rgb: Rgb; t0: number; dur: number; max: number };
type Sigil = { x: number; y: number; rgb: Rgb; t0: number; dur: number; r: number };
type Flash = { x: number; y: number; rgb: Rgb; t0: number; dur: number; r: number };

class Magic {
  private cv: HTMLCanvasElement | null = null;
  private cx: CanvasRenderingContext2D | null = null;
  private users = 0; private running = false; private ambient = 0;
  private P: Particle[] = []; private C: Comet[] = []; private W: Wave[] = []; private S: Sigil[] = []; private F: Flash[] = [];
  private reduced = () => typeof window === 'undefined' || window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /** 组件挂载时调用，返回卸载函数；最后一个使用者卸载时移除画布 */
  mount() {
    if (typeof document === 'undefined') return () => {};
    if (!this.cv) {
      const cv = document.createElement('canvas');
      cv.setAttribute('aria-hidden', 'true');
      cv.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:60';
      document.body.appendChild(cv); this.cv = cv; this.cx = cv.getContext('2d'); this.resize();
      addEventListener('resize', this.resize);
    }
    this.users++;
    return () => { if (--this.users > 0 || !this.cv) return; removeEventListener('resize', this.resize); this.cv.remove(); this.cv = this.cx = null; this.clear(); };
  }
  private resize = () => { if (!this.cv || !this.cx) return; const d = devicePixelRatio || 1; this.cv.width = innerWidth * d; this.cv.height = innerHeight * d; this.cx.setTransform(d, 0, 0, d, 0, 0); };
  clear() { this.P.length = this.C.length = this.W.length = this.S.length = this.F.length = 0; this.ambient = 0; }

  spark(x: number, y: number, rgb: Rgb, n = 14, speed = 2.6) {
    if (this.reduced()) return;
    for (let k = 0; k < n; k++) { const a = Math.random() * Math.PI * 2, s = speed * (.4 + Math.random()); this.P.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s - .6, life: 1, dec: .016 + Math.random() * .018, r: 2 + Math.random() * 3.4, rot: Math.random() * 6, rgb, star: Math.random() < .6 }); }
    this.kick();
  }
  /** 上升的金色星点（同意时） */
  rise(x: number, y: number, rgb: Rgb, n = 24) {
    if (this.reduced()) return;
    for (let k = 0; k < n; k++) this.P.push({ x: x + (Math.random() - .5) * 90, y: y + Math.random() * 20, vx: (Math.random() - .5) * .6, vy: -1.2 - Math.random() * 2.2, life: 1, dec: .01 + Math.random() * .012, r: 2 + Math.random() * 3, rot: Math.random() * 6, rgb, star: true, drift: true });
    this.kick();
  }
  /** 光点从四周向 (x,y) 聚拢（召唤 AI 卡） */
  implode(x: number, y: number, rgb: Rgb, n = 26, radius = 160) {
    if (this.reduced()) return;
    for (let k = 0; k < n; k++) { const a = Math.random() * Math.PI * 2, r = radius * (.6 + Math.random() * .6), px = x + Math.cos(a) * r, py = y + Math.sin(a) * r;
      this.P.push({ x: px, y: py, vx: (x - px) / 34, vy: (y - py) / 34, life: 1, dec: .028, r: 1.6 + Math.random() * 2.4, rot: 0, rgb, star: Math.random() < .5 }); }
    this.kick();
  }
  comet(x0: number, y0: number, x1: number, y1: number, rgb: Rgb, dur = 460) {
    if (this.reduced()) return;
    this.C.push({ x0, y0, x1, y1, mx: (x0 + x1) / 2 + (Math.random() - .5) * 60, my: Math.min(y0, y1) - 70 - Math.random() * 30, rgb, t0: performance.now(), dur, trail: [] }); this.kick();
  }
  wave(x: number, y: number, rgb: Rgb, max = 220, dur = 700) { if (this.reduced()) return; this.W.push({ x, y, rgb, t0: performance.now(), dur, max }); this.kick(); }
  /** 旋转的符文圆环：识别成功 / 召唤时出现 */
  sigil(x: number, y: number, rgb: Rgb, r = 34, dur = 900) { if (this.reduced()) return; this.S.push({ x, y, rgb, t0: performance.now(), dur, r }); this.kick(); }
  /** 识别成功那一下：一团柔和光晕亮起再散开 */
  burst(x: number, y: number, rgb: Rgb, size = 1) {
    if (this.reduced()) return;
    this.F.push({ x, y, rgb, t0: performance.now(), dur: 700, r: 70 * size }); this.kick();
  }
  /** 背景光尘：on 时缓慢飘几颗，页面不在前台或减少动效时不画 */
  setAmbient(on: boolean) { this.ambient = on && !this.reduced() ? 1 : 0; if (on) this.kick(); }

  private kick() { if (this.running || !this.cx) return; this.running = true; requestAnimationFrame(this.frame); }
  private star(x: number, y: number, r: number, a: number, rgb: Rgb) {
    const c = this.cx!; c.save(); c.translate(x, y); c.rotate(a); c.fillStyle = `rgba(${rgb},1)`; c.beginPath();
    for (let k = 0; k < 8; k++) { const rr = k % 2 ? r * .28 : r, ang = k * Math.PI / 4; c.lineTo(rr * Math.cos(ang), rr * Math.sin(ang)); }
    c.closePath(); c.fill(); c.restore();
  }
  // now 是 rAF 给的本帧开始时间，可能早于特效创建时记下的 performance.now()：进度一律夹到 ≥ 0，否则半径会算成负数
  private frame = (now: number) => {
    const c = this.cx; if (!c) { this.running = false; return; }
    c.clearRect(0, 0, innerWidth, innerHeight);
    if (this.ambient && Math.random() < .08) this.P.push({ x: Math.random() * innerWidth, y: innerHeight + 10, vx: (Math.random() - .5) * .3, vy: -.35 - Math.random() * .4, life: 1, dec: .0025, r: 1 + Math.random() * 1.6, rot: 0, rgb: Math.random() < .5 ? RGB.lilac : RGB.gold, star: false, drift: true });
    for (let i = this.S.length - 1; i >= 0; i--) {                 // 符文圆环：外圈虚线 + 内圈刻度，旋转着放大再淡出
      const s = this.S[i], p = progress(now, s.t0, s.dur); if (p >= 1) { this.S.splice(i, 1); continue; }
      const e = 1 - Math.pow(1 - p, 3), r = s.r * (.6 + .5 * e), a = Math.sin(Math.PI * p);
      c.save(); c.translate(s.x, s.y); c.rotate(p * 2.4); c.strokeStyle = `rgba(${s.rgb},${a * .9})`; c.shadowColor = `rgba(${s.rgb},.9)`; c.shadowBlur = 10;
      c.lineWidth = 2; c.setLineDash([6, 5]); c.beginPath(); c.arc(0, 0, r, 0, 7); c.stroke(); c.setLineDash([]);
      c.lineWidth = 1.2; c.beginPath(); c.arc(0, 0, r * .72, 0, 7); c.stroke();
      for (let k = 0; k < 12; k++) { const ang = k * Math.PI / 6; c.beginPath(); c.moveTo(Math.cos(ang) * r * .72, Math.sin(ang) * r * .72); c.lineTo(Math.cos(ang) * r * (k % 3 ? .82 : .9), Math.sin(ang) * r * (k % 3 ? .82 : .9)); c.stroke(); }
      c.rotate(-p * 4.8); c.beginPath(); for (let k = 0; k < 3; k++) { const ang = -Math.PI / 2 + k * 2 * Math.PI / 3; c.lineTo(Math.cos(ang) * r * .55, Math.sin(ang) * r * .55); } c.closePath(); c.stroke();
      c.restore();
    }
    for (let i = this.F.length - 1; i >= 0; i--) {                 // 光晕：先快速亮起，再慢慢放大淡出
      const f = this.F[i], p = progress(now, f.t0, f.dur); if (p >= 1) { this.F.splice(i, 1); continue; }
      const a = p < .2 ? p / .2 : 1 - (p - .2) / .8, r = f.r * (.7 + .5 * (1 - Math.pow(1 - p, 3)));
      const g = c.createRadialGradient(f.x, f.y, 0, f.x, f.y, r); g.addColorStop(0, `rgba(${f.rgb},${a * .35})`); g.addColorStop(1, `rgba(${f.rgb},0)`);
      c.fillStyle = g; c.beginPath(); c.arc(f.x, f.y, r, 0, 7); c.fill();
    }
    for (let i = this.W.length - 1; i >= 0; i--) {                 // 冲击波：一圈细光环扩散（t0 可在未来：延迟出现）
      const w = this.W[i]; if (now < w.t0) continue; const p = progress(now, w.t0, w.dur); if (p >= 1) { this.W.splice(i, 1); continue; }
      const e = 1 - Math.pow(1 - p, 3); c.strokeStyle = `rgba(${w.rgb},${(1 - p) * .55})`; c.lineWidth = 2 + 6 * (1 - p); c.beginPath(); c.arc(w.x, w.y, 12 + w.max * e, 0, 7); c.stroke();
    }
    for (let i = this.C.length - 1; i >= 0; i--) {                 // 光迹：发光彗尾 + 白芯 + 光头，沿弧线飞，沿途掉星点，到达炸开
      const m = this.C[i], p = progress(now, m.t0, m.dur), e = 1 - Math.pow(1 - p, 3), u = 1 - e;
      const x = u * u * m.x0 + 2 * u * e * m.mx + e * e * m.x1, y = u * u * m.y0 + 2 * u * e * m.my + e * e * m.y1;
      m.trail.push([x, y]); if (m.trail.length > 26) m.trail.shift();
      c.save(); c.shadowColor = `rgba(${m.rgb},.9)`; c.shadowBlur = 14; c.lineCap = 'round';
      for (let k = 1; k < m.trail.length; k++) { const a = k / m.trail.length; c.strokeStyle = `rgba(${m.rgb},${a})`; c.lineWidth = 1.5 + a * 7; c.beginPath(); c.moveTo(...m.trail[k - 1]); c.lineTo(...m.trail[k]); c.stroke(); }
      c.strokeStyle = 'rgba(255,255,255,.9)'; c.lineWidth = 1.6; c.beginPath(); m.trail.forEach(([tx, ty], k) => (k ? c.lineTo(tx, ty) : c.moveTo(tx, ty))); c.stroke(); c.restore();
      const g = c.createRadialGradient(x, y, 0, x, y, 18); g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(.3, `rgba(${m.rgb},.9)`); g.addColorStop(1, `rgba(${m.rgb},0)`); c.fillStyle = g; c.beginPath(); c.arc(x, y, 18, 0, 7); c.fill();
      if (Math.random() < .7) this.P.push({ x, y, vx: (Math.random() - .5) * 1.2, vy: (Math.random() - .5) * 1.2 + .4, life: 1, dec: .03, r: 1.5 + Math.random() * 2, rot: Math.random() * 6, rgb: m.rgb, star: true });
      if (p >= 1) { this.C.splice(i, 1); this.spark(m.x1, m.y1, m.rgb, 18, 3.2); this.wave(m.x1, m.y1, m.rgb, 60, 520); }
    }
    for (let i = this.P.length - 1; i >= 0; i--) {
      const q = this.P[i]; q.x += q.vx; q.y += q.vy;
      if (q.drift) { q.vx += (Math.random() - .5) * .05; } else { q.vx *= .96; q.vy = q.vy * .96 + .05; }
      q.life -= q.dec; q.rot += .08; if (q.life <= 0 || q.y < -20) { this.P.splice(i, 1); continue; }
      c.globalAlpha = Math.min(1, q.life * 1.4) * (.6 + .4 * Math.sin(now / 60 + i));
      if (q.star) this.star(q.x, q.y, q.r, q.rot, q.rgb); else { c.fillStyle = `rgba(${q.rgb},1)`; c.beginPath(); c.arc(q.x, q.y, q.r * .6, 0, 7); c.fill(); }
      c.globalAlpha = 1;
    }
    if (this.P.length || this.C.length || this.W.length || this.S.length || this.F.length || this.ambient) requestAnimationFrame(this.frame);
    else { this.running = false; c.clearRect(0, 0, innerWidth, innerHeight); }
  };
}

export const magic = new Magic();
