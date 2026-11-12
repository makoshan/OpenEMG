"""Mains detection: harmonics must not pass rest as effort; clean signal stays ok.

Must-fail samples (2026-10-01): with the 50 Hz-only detector, rest + a 100 Hz
tone authorized 1245/1404 windows, and clean windows were labelled line_noise
about 12 % of the time. See evidence/2026-10-01-emg-xhs-pipeline.md.
"""

import unittest

import numpy as np

from emg_gate import quality as Q
from emg_gate.pipeline import run_pipeline
from emg_gate.synth import generate

FS = 500.0
N = int(FS * 6)
T = np.arange(N) / FS


def _rest(seed, a50=0.0, a100=0.0):
    rng = np.random.default_rng(seed)
    return (rng.normal(0.0, 8.0, N)
            + a50 * np.sin(2.0 * np.pi * 50.0 * T)
            + a100 * np.sin(2.0 * np.pi * 100.0 * T + 0.3))


def _window_rate(streams):
    hits = total = 0
    for x in streams:
        for i in range(0, len(x) - 100 + 1, 25):
            total += 1
            hits += Q.detect_line_noise(x[i : i + 100], FS)
    return hits / total


class TestLineNoise(unittest.TestCase):
    def test_rest_with_100hz_only_never_authorizes(self):
        for seed in range(4):
            result = run_pipeline(_rest(seed, a100=60.0), fs=FS, t0_host_ms=0)
            self.assertEqual(result["summary"]["authorize_count"], 0, f"seed {seed}")

    def test_harmonic_only_marks_line_noise_without_notch(self):
        result = run_pipeline(_rest(0, a100=60.0), fs=FS, t0_host_ms=0)
        self.assertEqual(result["summary"]["stream_quality"], Q.QUALITY_LINE_NOISE)
        self.assertFalse(result["summary"]["notch_applied"])

    def test_fundamental_still_turns_notch_on(self):
        result = run_pipeline(_rest(0, a50=60.0), fs=FS, t0_host_ms=0)
        self.assertTrue(result["summary"]["notch_applied"])
        self.assertEqual(result["summary"]["authorize_count"], 0)

    def test_max_harmonic_limits_the_check(self):
        x = _rest(0, a100=60.0)
        self.assertTrue(Q.detect_line_noise(x, FS))
        self.assertFalse(Q.detect_line_noise(x, FS, max_harmonic=1))

    def test_white_noise_false_positive_rate(self):
        streams = [np.random.default_rng(1000 + s).normal(0.0, 8.0, N) for s in range(20)]
        self.assertLess(_window_rate(streams), 0.05)

    def test_effort_windows_rarely_labelled_line_noise(self):
        streams = [generate(sc, fs=FS, duration_s=6.0, seed=s)[0]
                   for sc in ("light", "hard") for s in range(10)]
        self.assertLess(_window_rate(streams), 0.05)


if __name__ == "__main__":
    unittest.main()
