// Live single-channel EMG → force → picture. Pure: no DOM, no serial. The page (emg_demo.html)
// feeds it lines from the emg_usb firmware's `s` stream and draws whatever it returns; node
// runs the same code in check_emg_demo.js.
//
// Stream line: "S <millis> <worn_of_10> v0 v1 ... v9"  ten 1 kHz ADC counts, 12-bit, 1.65 V mid.
// One channel of surface EMG reads how hard the flexors work and when, not which finger
// moved (evidence/2026-09-23-emg-db6.md: effort yes/no 0.96, which-grasp 0.44 across days),
// so the demo shows exactly that: an envelope, a baseline, and an on/off effort gate.
const HZ = 1000, MID = 2048, CHUNK = 10;

function parseLine(line) {
  const f = line.trim().split(/\s+/);
  if (f[0] !== 'S' || f.length !== 3 + CHUNK) return null;
  const t = +f[1], worn = +f[2], samples = f.slice(3).map(Number);
  if (!Number.isFinite(t) || !(worn >= 0 && worn <= CHUNK) || samples.some(v => !Number.isFinite(v))) return null;
  return { t, worn, samples };
}

// RMS over the last `windowMs` around the running midpoint. The 1.65 V bias drifts with contact and
// temperature, so the midpoint is a slow average of the signal itself, never the datasheet's 2048.
class Envelope {
  constructor(windowMs = 100) {
    this.n = Math.max(1, Math.round(HZ * windowMs / 1000));
    this.buf = new Float64Array(this.n); this.i = 0; this.filled = 0; this.sumSq = 0;
    this.mid = MID; this.value = 0;
  }
  push(v) {
    this.mid += (v - this.mid) * 0.001;          // ~1 s time constant
    const d = v - this.mid, old = this.buf[this.i];
    this.sumSq += d * d - old * old; this.buf[this.i] = d;
    this.i = (this.i + 1) % this.n; this.filled = Math.min(this.filled + 1, this.n);
    this.value = Math.sqrt(Math.max(this.sumSq, 0) / this.filled);
    return this.value;
  }
}

// Effort on when the envelope clears the relaxed floor by `on` times, off again below `off`
// times: two thresholds so a hovering signal does not flicker. The floor is learned from the
// quietest recent second (a running minimum), not from a calibration button the booth visitor
// would never press. Not worn = never on, whatever the numbers say.
class EffortGate {
  constructor({ on = 3, off = 2, floorMs = 3000 } = {}) {
    this.on = on; this.off = off; this.active = false;
    this.floor = Infinity; this.window = []; this.floorN = Math.round(floorMs / CHUNK);
  }
  update(envelope, worn) {
    this.window.push(envelope); if (this.window.length > this.floorN) this.window.shift();
    this.floor = Math.max(Math.min(...this.window), 1e-6);
    const ratio = envelope / this.floor;
    if (!worn) this.active = false;
    else if (!this.active && ratio > this.on) this.active = true;
    else if (this.active && ratio < this.off) this.active = false;
    // force: 0 at the floor, 1 at ten times it -- a display scale, not a calibration
    this.force = Math.max(0, Math.min(1, Math.log10(Math.max(ratio, 1)) ));
    return { active: this.active, force: this.force, ratio, floor: this.floor };
  }
}

// No hardware: a relaxed floor with mains hum, a burst while `pressed`. Same line format as the
// firmware so the page cannot tell the two apart -- which is the point of testing it this way.
function synthLine(t, pressed, rnd = Math.random) {
  const v = [];
  for (let k = 0; k < CHUNK; k++) {
    const ms = t + k;
    let x = MID + 4 * (rnd() - 0.5) * 2 + 2 * Math.sin(2 * Math.PI * 50 * ms / 1000);
    if (pressed) x += 120 * (rnd() - 0.5) * 2;
    v.push(Math.round(x));
  }
  return `S ${t} 10 ${v.join(' ')}`;
}

// 2nd-order Butterworth high-pass, 20 Hz at 1 kHz: the ISEK corner below which motion
// artefact lives and muscle does not (usb_emg.py keeps the same 20 Hz for SMR).
class Highpass {
  constructor(fc = 20, fs = HZ) {
    const K = Math.tan(Math.PI * fc / fs), n = 1 / (1 + Math.SQRT2 * K + K * K);
    this.b0 = n; this.b1 = -2 * n; this.b2 = n; this.a1 = 2 * (K * K - 1) * n; this.a2 = (1 - Math.SQRT2 * K + K * K) * n;
    this.x1 = this.x2 = this.y1 = this.y2 = 0;
  }
  push(x) {
    const y = this.b0 * x + this.b1 * this.x1 + this.b2 * this.x2 - this.a1 * this.y1 - this.a2 * this.y2;
    this.x2 = this.x1; this.x1 = x; this.y2 = this.y1; this.y1 = y; return y;
  }
}

// RBJ notch, bandwidth in Hz (constant across harmonics, like usb_emg.NOTCH_BW_HZ).
class Notch {
  constructor(f0, bw = 2, fs = HZ) {
    const w = 2 * Math.PI * f0 / fs, Q = f0 / bw, al = Math.sin(w) / (2 * Q), a0 = 1 + al;
    this.b0 = 1 / a0; this.b1 = -2 * Math.cos(w) / a0; this.b2 = 1 / a0; this.a1 = this.b1; this.a2 = (1 - al) / a0;
    this.x1 = this.x2 = this.y1 = this.y2 = 0;
  }
  push(x) { return Highpass.prototype.push.call(this, x); }
}
// The ADR chain before the envelope, identical to usb_emg.clean: 20 Hz HPF, then a notch on every
// mains harmonic to 450 Hz. Output is zero-mean.
class Cleaner {
  constructor(mains = 50) { this.hp = new Highpass(20); this.n = []; for (let f = mains; f <= 450; f += mains) this.n.push(new Notch(f)); }
  push(x) { let y = this.hp.push(x); for (const n of this.n) y = n.push(y); return y; }
}
// Share of 20-450 Hz power on mains harmonics (±2 Hz) in a spectrum() result.
function mainsShare(sp, mains = 50) {
  let m = 0, t = 0;
  for (let i = 0; i < sp.power.length; i++) { const f = i * sp.hz; if (f < 20 || f > 450) continue; t += sp.power[i];
    if (Math.abs(f - mains * Math.round(f / mains)) <= 2) m += sp.power[i]; }
  return t > 0 ? m / t : 0;
}

// One channel split into `n` log-spaced bands between lo and hi Hz (RBJ band-pass, 0 dB peak).
// This is what the PULSE-style 16-row view draws: the same electrode, sixteen frequency slices,
// not sixteen electrodes. push(x) returns the n band outputs for one sample.
class BandBank {
  constructor(n = 16, lo = 20, hi = 450, fs = HZ) {
    this.edges = Array.from({ length: n + 1 }, (_, i) => lo * Math.pow(hi / lo, i / n));
    this.bands = [];
    for (let i = 0; i < n; i++) {
      const a = this.edges[i], b = this.edges[i + 1], f0 = Math.sqrt(a * b), Q = f0 / (b - a);
      const w = 2 * Math.PI * f0 / fs, al = Math.sin(w) / (2 * Q), a0 = 1 + al;
      this.bands.push({ b0: al / a0, b1: 0, b2: -al / a0, a1: -2 * Math.cos(w) / a0, a2: (1 - al) / a0, x1: 0, x2: 0, y1: 0, y2: 0, f0 });
    }
    this.out = new Float64Array(n);
  }
  push(x) { for (let i = 0; i < this.bands.length; i++) this.out[i] = Highpass.prototype.push.call(this.bands[i], x); return this.out; }
}

// In-place radix-2 FFT; re/im Float64Array of power-of-two length.
function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k, b = a + len / 2, tr = re[b] * cr - im[b] * ci, ti = re[b] * ci + im[b] * cr;
        re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
        [cr, ci] = [cr * wr - ci * wi, cr * wi + ci * wr];
      }
    }
  }
}

// Hann-windowed power spectrum of the last `n` samples (n power of two). Returns
// { power: Float64Array(n/2+1), hz: bin width, medianHz, smrDb } with SMR defined as in
// usb_emg.py: 20-450 Hz power over sub-20 Hz power, capped at 60 dB.
function spectrum(samples, n = 1024, fs = HZ) {
  const re = new Float64Array(n), im = new Float64Array(n), off = samples.length - n;
  let mean = 0; for (let i = 0; i < n; i++) mean += samples[off + i]; mean /= n;
  for (let i = 0; i < n; i++) re[i] = (samples[off + i] - mean) * (0.5 - 0.5 * Math.cos(2 * Math.PI * i / (n - 1)));
  fft(re, im);
  const power = new Float64Array(n / 2 + 1), hz = fs / n;
  for (let i = 0; i <= n / 2; i++) power[i] = re[i] * re[i] + im[i] * im[i];
  let low = 0, band = 0, medianHz = 0;
  for (let i = 0; i <= n / 2; i++) { const f = i * hz; if (f < 20) low += power[i]; else if (f <= 450) band += power[i]; }
  for (let i = 0, acc = 0; i <= n / 2; i++) { const f = i * hz; if (f < 20 || f > 450) continue; acc += power[i]; if (acc >= band / 2) { medianHz = f; break; } }
  const smrDb = band > 0 && low > 0 ? Math.min(10 * Math.log10(band / low), 60) : 60;
  return { power, hz, medianHz, smrDb };
}

// Bounded browser timing diagnostics; intervals are not end-to-end/optical latency.
class StreamTiming {
  constructor() { this.last = {}; this.stats = {}; }
  observe(kind, ms, phase = 'idle') {
    if (!Number.isFinite(ms)) throw Error('Invalid monotonic timestamp');
    const key = phase + ':' + kind;
    const s = this.stats[key] ||= {events: 0, intervals: 0, maxGapMs: 0, totalGapMs: 0};
    s.events++;
    const previous = this.last[kind];
    if (previous != null && ms >= previous) {
      const gap = ms - previous;
      s.intervals++; s.maxGapMs = Math.max(s.maxGapMs, gap); s.totalGapMs += gap;
    }
    this.last[kind] = ms;
  }
  snapshot() { return JSON.parse(JSON.stringify(this.stats)); }
}

if (typeof module !== 'undefined') module.exports = { StreamTiming, parseLine, Envelope, EffortGate, Highpass, Notch, Cleaner, BandBank, mainsShare, fft, spectrum, synthLine, HZ, MID, CHUNK };
