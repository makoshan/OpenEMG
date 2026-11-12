// Fails loudly if the live-EMG demo logic breaks. Run: node firmware/check_emg_demo.js
const assert = require('assert');
const { parseLine, Envelope, EffortGate, Highpass, Cleaner, BandBank, mainsShare, spectrum, synthLine, CHUNK, HZ } = require('./emg_demo.js');

// ---- framing: the firmware's line parses, everything else is refused
const ok = parseLine('S 1234 10 2048 2050 2046 2049 2048 2047 2048 2051 2048 2048');
assert.deepStrictEqual([ok.t, ok.worn, ok.samples.length], [1234, 10, CHUNK]);
for (const bad of ['EMG 1000 2000 abc 1000', 'S 1 10 1 2 3', 'S x 10 ' + '1 '.repeat(10).trim(),
                   'S 1 11 ' + '1 '.repeat(10).trim(), 'S 1 10 ' + '1 '.repeat(9).trim() + ' nan', ''])
  assert.strictEqual(parseLine(bad), null, `accepted: ${JSON.stringify(bad)}`);

// ---- envelope: a burst raises it, relaxing brings it back near the floor
let seed = 1; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const env = new Envelope(100), gate = new EffortGate();
const run = (ms, pressed, worn = true) => {
  let last;
  for (let t = 0; t < ms; t += CHUNK) {
    const line = synthLine(t, pressed, rnd), p = parseLine(line);
    assert.ok(p, 'synth line must parse like a firmware line');
    let e; for (const v of p.samples) e = env.push(v);
    last = gate.update(e, worn ? p.worn : 0);
  }
  return last;
};
const relaxed = run(3000, false);
assert.ok(!relaxed.active && relaxed.force < 0.2, `relaxed reads as effort: ${JSON.stringify(relaxed)}`);
const squeezed = run(500, true);
assert.ok(squeezed.active && squeezed.ratio > 3, `squeeze not seen: ${JSON.stringify(squeezed)}`);
const released = run(1000, false);
assert.ok(!released.active, `gate stuck on after release: ${JSON.stringify(released)}`);

// ---- must fail: the same squeeze with the strap off must never light the gate
const off = run(500, true, false);
assert.ok(!off.active && off.ratio > 3, `strap off but gate on: ${JSON.stringify(off)}`);
run(1000, false);

// ---- hysteresis: a signal parked between off and on thresholds keeps its state
const g = new EffortGate({ on: 3, off: 2 });
for (let i = 0; i < 300; i++) g.update(1, 10);           // floor = 1
assert.ok(!g.update(2.5, 10).active, 'between thresholds from off must stay off');
assert.ok(g.update(3.5, 10).active, 'above on must switch on');
assert.ok(g.update(2.5, 10).active, 'between thresholds from on must stay on');
assert.ok(!g.update(1.5, 10).active, 'below off must switch off');

// ---- spectrum: a 100 Hz tone lands in the 100 Hz bin; SMR sees drift and ignores muscle
const tone = Float64Array.from({ length: 2048 }, (_, i) => 2048 + 100 * Math.sin(2 * Math.PI * 100 * i / HZ));
let sp = spectrum(tone); let peak = 0; for (let i = 1; i < sp.power.length; i++) if (sp.power[i] > sp.power[peak]) peak = i;
assert.ok(Math.abs(peak * sp.hz - 100) < 2, `tone peak at ${peak * sp.hz} Hz`);
assert.ok(Math.abs(sp.medianHz - 100) < 3, `median ${sp.medianHz}`);
const drift = Float64Array.from({ length: 2048 }, (_, i) => 2048 + 400 * Math.sin(2 * Math.PI * 1 * i / HZ) + 20 * Math.sin(2 * Math.PI * 100 * i / HZ));
assert.ok(spectrum(drift).smrDb < 0 && sp.smrDb > 20, `smr tone ${sp.smrDb} drift ${spectrum(drift).smrDb}`);
// ---- high-pass: 1 Hz swing is gone, 100 Hz survives
const hp = new Highpass(20); let out = [];
for (let i = 0; i < 4000; i++) out.push(hp.push(400 * Math.sin(2 * Math.PI * 1 * i / HZ) + 20 * Math.sin(2 * Math.PI * 100 * i / HZ)));
const tail = out.slice(2000); const rms = Math.sqrt(tail.reduce((a, v) => a + v * v, 0) / tail.length);
assert.ok(rms > 10 && rms < 20, `hp output rms ${rms}: 100 Hz tone alone is ~14`);
// ---- cleaner: 200 counts of 50 Hz + 60 of 150 Hz vanish, a 80 Hz muscle-band tone survives
const cl = new Cleaner(50), mix = [];
for (let i = 0; i < 6000; i++) mix.push(cl.push(200 * Math.sin(2 * Math.PI * 50 * i / HZ) + 60 * Math.sin(2 * Math.PI * 150 * i / HZ) + 20 * Math.sin(2 * Math.PI * 80 * i / HZ)));
const settled = mix.slice(4000), crms = Math.sqrt(settled.reduce((a, v) => a + v * v, 0) / settled.length);
assert.ok(crms > 11 && crms < 17, `cleaner rms ${crms}: the 80 Hz tone alone is ~14`);
const humSp = spectrum(Float64Array.from({ length: 2048 }, (_, i) => 200 * Math.sin(2 * Math.PI * 50 * i / HZ) + 2 * Math.sin(2 * Math.PI * 80 * i / HZ)));
const tone80 = spectrum(Float64Array.from({ length: 2048 }, (_, i) => 100 * Math.sin(2 * Math.PI * 80 * i / HZ)));   // 100 Hz would be a mains harmonic
assert.ok(mainsShare(humSp) > 0.9 && mainsShare(tone80) < 0.1, `mains share hum ${mainsShare(humSp)} tone ${mainsShare(tone80)}`);
// ---- band bank: an 80 Hz tone lands in the band whose edges contain 80, and a 300 Hz tone higher up
const bandOf = f => { const bb = new BandBank(); const e = new Float64Array(16);
  for (let i = 0; i < 4000; i++) { const o = bb.push(Math.sin(2 * Math.PI * f * i / HZ)); if (i > 2000) for (let k = 0; k < 16; k++) e[k] += o[k] * o[k]; }
  return [e.indexOf(Math.max(...e)), bb.edges]; };
const [b80, edges] = bandOf(80), [b300] = bandOf(300);
assert.ok(edges[b80] <= 80 && 80 <= edges[b80 + 1], `80 Hz landed in band ${b80} (${edges[b80].toFixed(0)}-${edges[b80 + 1].toFixed(0)})`);
assert.ok(b300 > b80, `300 Hz band ${b300} not above 80 Hz band ${b80}`);
console.log('EMG demo: framing, envelope, effort gate, strap-off refusal, hysteresis, spectrum/SMR, high-pass, mains notch, band bank passed');
