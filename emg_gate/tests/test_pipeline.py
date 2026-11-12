"""Test full pipeline."""

import unittest

import numpy as np

from emg_gate.pipeline import run_pipeline
from emg_gate.synth import generate


class TestPipeline(unittest.TestCase):
    def test_pipeline_rest(self):
        """Test pipeline on rest scenario."""
        raw_uV, _ = generate("rest", fs=500.0, duration_s=1.0, seed=30)
        result = run_pipeline(raw_uV, fs=500.0)

        self.assertIn("summary", result)
        self.assertIn("events", result)
        self.assertIn("frames", result)

        summary = result["summary"]
        self.assertGreater(summary["n_hops"], 0)
        self.assertEqual(summary["fs"], 500.0)

        frames = result["frames"]
        self.assertGreater(len(frames), 0)

        for frame in frames:
            self.assertIn("band", frame)
            self.assertIn("confidence", frame)
            self.assertIn("quality", frame)
            self.assertIn(frame["band"], [0, 1, 2])

    def test_pipeline_light(self):
        """Test pipeline on light scenario."""
        raw_uV, _ = generate("light", fs=500.0, duration_s=1.0, seed=31)
        result = run_pipeline(raw_uV, fs=500.0)

        summary = result["summary"]
        majority = summary.get("majority_band")

        self.assertIsNotNone(majority)
        self.assertIn(majority, [0, 1, 2])

    def test_pipeline_hard(self):
        """Test pipeline on hard scenario."""
        raw_uV, _ = generate("hard", fs=500.0, duration_s=1.0, seed=32)
        result = run_pipeline(raw_uV, fs=500.0)

        summary = result["summary"]
        majority = summary.get("majority_band")

        self.assertIsNotNone(majority)
        self.assertGreaterEqual(majority, 0)

    def test_pipeline_lead_off_suppressed(self):
        """Test that lead_off scenario suppresses authorize."""
        raw_uV, _ = generate("lead_off", fs=500.0, duration_s=1.0, seed=33)
        result = run_pipeline(raw_uV, fs=500.0, forced_quality="lead_off")

        summary = result["summary"]
        self.assertEqual(summary["authorize_count"], 0, "Lead-off must not authorize")
        self.assertGreater(summary["suppressed_count"], 0)

        events = result["events"]
        for ev in events:
            self.assertFalse(ev["authorize"], "No event should authorize on lead_off")

    def test_pipeline_clip_suppressed(self):
        """Test that clip scenario suppresses authorize."""
        raw_uV, _ = generate("clip", fs=500.0, duration_s=1.0, seed=34)
        result = run_pipeline(raw_uV, fs=500.0, forced_quality="clip")

        summary = result["summary"]
        self.assertEqual(summary["authorize_count"], 0, "Clip must not authorize")

    def test_pipeline_notch_auto(self):
        """Test auto notch on line_noise scenario."""
        raw_uV, _ = generate("line_noise", fs=500.0, duration_s=1.0, seed=35)
        result = run_pipeline(raw_uV, fs=500.0, notch_mode="auto")

        summary = result["summary"]
        self.assertTrue(
            summary["notch_applied"], "Notch should be applied for line_noise"
        )

    def test_pipeline_save_raw(self):
        """Test save_raw option."""
        raw_uV, _ = generate("rest", fs=500.0, duration_s=0.5, seed=36)
        result = run_pipeline(raw_uV, fs=500.0, save_raw=True)

        frames = result["frames"]
        self.assertGreater(len(frames), 0)

        for frame in frames:
            self.assertIn("raw_uV", frame)
            self.assertGreater(len(frame["raw_uV"]), 0)

    def test_pipeline_no_raw_default(self):
        """Test that raw is not saved by default."""
        raw_uV, _ = generate("rest", fs=500.0, duration_s=0.5, seed=37)
        result = run_pipeline(raw_uV, fs=500.0, save_raw=False)

        frames = result["frames"]
        for frame in frames:
            self.assertNotIn("raw_uV", frame)

    def test_pipeline_delta2_feature(self):
        """Test delta2 feature extraction."""
        raw_uV, _ = generate("light", fs=500.0, duration_s=1.0, seed=38)
        result = run_pipeline(raw_uV, fs=500.0, enable_delta2=True)

        frames = result["frames"]
        self.assertGreater(len(frames), 0)

        for frame in frames:
            self.assertIn("features", frame)
            self.assertIn("delta2_energy", frame["features"])


if __name__ == "__main__":
    unittest.main()
