"""Live gesture events from the wristband stream: onset-triggered, one inference per burst.

The product behaviour from the global plan: no 20 Hz sliding inference. A cheap envelope watches
the stream; when it rises above the resting floor the detector waits until the 0.4 s window the
CNN was trained on (0.15 s before the onset, 0.25 s after) is complete, runs the folded numpy
network once, and emits one event. Then a refractory period. Scale and floor come from the first
seconds after the detector starts, labels unseen -- "戴上先标定" is exactly this.

    python3 emg_live.py --check           # synthetic stream: one burst -> one event, rest -> none, refractory
"""
import argparse
from collections import deque

import numpy as np

HZ = 1000          # detector runs at the CNN's rate; 2 kHz input is pair-averaged
WIN, PRE = 400, 150


def softmax(z):
    e = np.exp(z - z.max()); return e / e.sum()


class Detector:
    def __init__(self, classify, channels, hz_in=2000, calib_s=3.0, on_ratio=4.0, min_on_ms=30, refractory_ms=600, min_conf=.6):
        """classify(window (ch, WIN) normalised) -> (label, confidence)."""
        self.classify, self.channels, self.step = classify, list(channels), hz_in // HZ
        self.calib_n, self.on_ratio, self.min_on, self.refractory, self.min_conf = int(calib_s * HZ), on_ratio, min_on_ms, refractory_ms, min_conf
        self.reset()

    def reset(self):
        """边界后重新学习基线，禁止沿用旧幅度与未完成的动作。"""
        self.ring = deque(maxlen=2 * HZ); self.t = 0                       # last 2 s at 1 kHz, (ch,) rows
        self.mean = None; self.env = deque(maxlen=20)                       # 1-pole baseline; 20 ms RMS window
        self.calib, self.scale, self.floor = [], None, None
        self.above, self.pending, self.last_event_t = 0, None, -10 ** 9
        self.events, self.inferences, self.n_infer = [], [], 0             # every onset's verdict, including rest/unsure (debugging aid)

    def feed(self, emg_uv):
        """emg_uv (n, 8) at hz_in -> list of new events."""
        x = emg_uv[:, self.channels].astype(np.float32)
        x = x[:len(x) // self.step * self.step].reshape(-1, self.step, len(self.channels)).mean(1)
        out = []
        for row in x:
            self.mean = row if self.mean is None else self.mean + (row - self.mean) * .001
            hp = row - self.mean
            self.ring.append(hp); self.t += 1
            self.env.append(hp ** 2)
            env = np.sqrt(np.mean(self.env, 0))                              # per-channel 20 ms RMS: a finger lights one electrode, not all
            if len(self.calib) < self.calib_n:                              # first seconds: learn scale and floor, no events
                self.calib.append(hp)
                if len(self.calib) == self.calib_n:
                    c = np.stack(self.calib); self.scale = np.median(np.abs(c), 0) + 1e-6
                    self.floor = np.median(np.abs(c), 0) * 1.25 + 1e-6            # median, not RMS: a stray burst during calibration must not lift the floor
                continue
            if self.pending is None and self.t - self.last_event_t > self.refractory:
                self.above = self.above + 1 if (env > self.floor * self.on_ratio).any() else 0
                if self.above >= self.min_on:
                    self.pending = self.t - self.min_on                     # onset = when the rise began
                    self.above = 0
            if self.pending is not None and self.t >= self.pending + (WIN - PRE):
                win = np.stack(list(self.ring)[-WIN:]).T / self.scale[:, None]
                label, conf = self.classify(win)
                onset, self.last_event_t, self.pending = self.pending, self.t, None
                ev = {'t_ms': int(onset), 'label': label, 'conf': round(float(conf), 3), 'emitted': label != 'rest' and conf >= self.min_conf}
                self.inferences.append(ev); del self.inferences[:-50]; self.n_infer += 1
                if ev['emitted']:
                    self.events.append(ev); out.append(ev)
        return out

    @property
    def ready(self):
        return self.scale is not None


def cnn_classifier(npz_path):
    """The folded CNN from emg_cnn_export.save_npz, pure numpy."""
    from emg_cnn_export import load_npz, forward
    m = load_npz(npz_path)
    def classify(win):
        p = softmax(forward(m['convs'], m['head'], (win * 1.0).astype(np.float32)))
        i = int(p.argmax()); return m['classes'][i], float(p[i])
    return classify, m['channels']


def _stream(rng, seconds, bursts):
    """Synthetic 2 kHz x 8 ch µV: resting noise with (t_s, gain_vector, dur_s) bursts."""
    n = int(seconds * 2000); x = rng.normal(0, 8, (n, 8))
    for t, gain, dur in bursts:
        a = int(t * 2000); b = a + int(dur * 2000); x[a:b] *= gain / 8
    return x.astype(np.int32)


def check():
    rng = np.random.default_rng(0)
    g_mid = np.array([60, 40, 8, 8, 8, 8, 20, 8.]); g_fist = np.full(8, 45.)
    def classify(win):                                                     # energy pattern, not a model: tests the plumbing
        e = (win ** 2).mean(1); return ('middle' if e[0] > 2 * e[3] else 'fist'), .9
    ch = [0, 2, 4, 6]
    def run(bursts, seconds=8):
        d = Detector(classify, ch); x = _stream(rng, seconds, bursts); ev = []
        for i in range(0, len(x), 64): ev += d.feed(x[i:i + 64])           # chunked like the serial reader
        assert d.ready; return ev
    ev = run([(4.0, g_mid, .5), (6.0, g_fist, .5)])
    assert [e['label'] for e in ev] == ['middle', 'fist'], ev
    assert abs(ev[0]['t_ms'] - 4000) < 60 and abs(ev[1]['t_ms'] - 6000) < 60, ev
    assert run([]) == [], 'events on a resting stream'
    assert len(run([(4.0, g_mid, .5), (4.3, g_fist, .5)])) == 1, 'refractory did not hold'
    assert run([(1.0, g_mid, .5)]) == [], 'fired during calibration'
    # The real folded network, pure numpy, must reproduce the PyTorch logits stored at export time.
    from pathlib import Path
    npz = Path(__file__).with_name('emg-public') / 'gni_4ch_3g.npz'
    if npz.exists():
        from emg_cnn_export import load_npz, forward
        m, probe = load_npz(npz), np.load(npz.with_suffix('.probe.npz'))
        diff = max(float(np.abs(forward(m['convs'], m['head'], x) - l).max()) for x, l in zip(probe['x'], probe['logits']))
        assert diff < 1e-3, diff
        print(f'live check passed: 2 bursts -> 2 events, rest -> none, refractory, calibration; numpy CNN vs torch {diff:.1e}')
    else:
        print('live check passed (plumbing only; no exported CNN npz to compare)')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--check', action='store_true'); p.parse_args(); check()
