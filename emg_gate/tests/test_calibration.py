"""Test calibration logic."""

import unittest

import numpy as np

from emg_gate.calibrate import calibrate_from_sessions, calibrate_from_streams, evaluate_profile
from emg_gate.capture_session import GESTURE_HARD, GESTURE_LIGHT, GESTURE_REST
from emg_gate.synth import generate


class TestCalibration(unittest.TestCase):
    def test_calibrate_synth_streams(self):
        """Test calibration from synthetic rest/light/hard streams."""
        fs = 500.0
        duration = 2.0

        relax_uV, _ = generate("rest", fs=fs, duration_s=duration, seed=10)
        light_uV, _ = generate("light", fs=fs, duration_s=duration, seed=11)
        hard_uV, _ = generate("hard", fs=fs, duration_s=duration, seed=12)
        lead_uV, _ = generate("lead_off", fs=fs, duration_s=duration, seed=13)

        profile = calibrate_from_streams(
            relax_uV, light_uV, hard_uV, fs=fs, lead_off_uV=lead_uV
        )

        self.assertIn("thresholds", profile)
        self.assertIn("calibration_debug", profile)

        thresholds = profile["thresholds"]
        th_loose = thresholds["th_loose_max"]
        th_hard = thresholds["th_hard_min"]

        self.assertGreater(th_hard, th_loose)
        self.assertGreaterEqual(th_loose, 0.0)
        self.assertLessEqual(th_hard, 1.0)

        cal = profile["calibration_debug"]
        self.assertIn("negatives_ok", cal)
        self.assertIn("committed", cal)

        self.assertTrue(cal["negatives_ok"], "Lead-off should not authorize green")
        self.assertTrue(cal["committed"])

    def test_threshold_ordering(self):
        """Test that calibrated thresholds are properly ordered."""
        fs = 500.0
        duration = 1.5

        relax_uV = np.random.randn(int(fs * duration)) * 10.0
        light_uV = np.random.randn(int(fs * duration)) * 50.0
        hard_uV = np.random.randn(int(fs * duration)) * 120.0

        profile = calibrate_from_streams(relax_uV, light_uV, hard_uV, fs=fs)

        thresholds = profile["thresholds"]
        th_loose = thresholds["th_loose_max"]
        th_hard = thresholds["th_hard_min"]

        self.assertLess(th_loose, th_hard)
        self.assertGreaterEqual(th_loose, 0.05)
        self.assertLessEqual(th_loose, 0.35)

    def test_negative_validation(self):
        """Test that lead_off validation works."""
        fs = 500.0
        duration = 1.0

        relax_uV, _ = generate("rest", fs=fs, duration_s=duration, seed=20)
        light_uV, _ = generate("light", fs=fs, duration_s=duration, seed=21)
        hard_uV, _ = generate("hard", fs=fs, duration_s=duration, seed=22)
        lead_uV, _ = generate("lead_off", fs=fs, duration_s=duration, seed=23)

        profile = calibrate_from_streams(
            relax_uV, light_uV, hard_uV, fs=fs, lead_off_uV=lead_uV
        )

        cal = profile["calibration_debug"]
        neg = cal["negatives"]

        self.assertEqual(neg["authorize_count"], 0, "Lead-off should not authorize")
        self.assertIn(neg["majority_band"], [None, 0], "Lead-off should be band 0")

    def test_evaluate_profile_swapped_thresholds_must_fail(self):
        """Must-fail sample: swapped thresholds yield lower accuracy."""
        sessions_training = []
        sessions_held_out = []
        
        for i in range(20):
            sessions_training.append({
                "gesture_label": GESTURE_REST,
                "held_out": False,
                "feature_window": {"norm": 0.05 + i * 0.002},
            })
            sessions_training.append({
                "gesture_label": GESTURE_LIGHT,
                "held_out": False,
                "feature_window": {"norm": 0.25 + i * 0.01},
            })
            sessions_training.append({
                "gesture_label": GESTURE_HARD,
                "held_out": False,
                "feature_window": {"norm": 0.50 + i * 0.01},
            })
        
        for i in range(10):
            sessions_held_out.append({
                "gesture_label": GESTURE_REST,
                "held_out": True,
                "feature_window": {"norm": 0.06 + i * 0.003},
            })
            sessions_held_out.append({
                "gesture_label": GESTURE_LIGHT,
                "held_out": True,
                "feature_window": {"norm": 0.26 + i * 0.012},
            })
            sessions_held_out.append({
                "gesture_label": GESTURE_HARD,
                "held_out": True,
                "feature_window": {"norm": 0.51 + i * 0.012},
            })
        
        all_sessions = sessions_training + sessions_held_out
        
        good_profile = calibrate_from_sessions(
            all_sessions,
            user_id="test_user",
            device_id="test_device",
        )
        
        good_eval = evaluate_profile(good_profile, all_sessions)
        
        bad_profile = {
            "thresholds": {
                "th_loose_max": good_profile["thresholds"]["th_hard_min"],
                "th_hard_min": good_profile["thresholds"]["th_loose_max"],
            },
            "user_id": "test_user",
            "device_id": "test_device",
        }
        
        bad_eval = evaluate_profile(bad_profile, all_sessions)
        
        accuracy_drop = good_eval["accuracy"] - bad_eval["accuracy"]
        self.assertGreater(
            accuracy_drop, 
            0.3, 
            f"Swapped thresholds must yield >0.3 accuracy drop, got {accuracy_drop:.3f}"
        )

    def test_evaluate_profile_synthetic_high_accuracy(self):
        """Fitted profile should achieve >= 0.8 accuracy on held_out synthetic data."""
        sessions_training = []
        sessions_held_out = []
        
        for i in range(30):
            sessions_training.append({
                "gesture_label": GESTURE_REST,
                "held_out": False,
                "feature_window": {"norm": 0.05 + i * 0.002},
            })
            sessions_training.append({
                "gesture_label": GESTURE_LIGHT,
                "held_out": False,
                "feature_window": {"norm": 0.25 + i * 0.008},
            })
            sessions_training.append({
                "gesture_label": GESTURE_HARD,
                "held_out": False,
                "feature_window": {"norm": 0.50 + i * 0.008},
            })
        
        for i in range(15):
            sessions_held_out.append({
                "gesture_label": GESTURE_REST,
                "held_out": True,
                "feature_window": {"norm": 0.06 + i * 0.003},
            })
            sessions_held_out.append({
                "gesture_label": GESTURE_LIGHT,
                "held_out": True,
                "feature_window": {"norm": 0.26 + i * 0.009},
            })
            sessions_held_out.append({
                "gesture_label": GESTURE_HARD,
                "held_out": True,
                "feature_window": {"norm": 0.51 + i * 0.009},
            })
        
        all_sessions = sessions_training + sessions_held_out
        
        profile = calibrate_from_sessions(
            all_sessions,
            user_id="test_user",
            device_id="test_device",
        )
        
        result = evaluate_profile(profile, all_sessions)
        
        self.assertGreaterEqual(
            result["accuracy"], 
            0.8, 
            f"Expected accuracy >= 0.8 on synthetic held_out data, got {result['accuracy']:.3f}"
        )
        self.assertEqual(result["n"], 45)

    def test_evaluate_profile_no_held_out_raises(self):
        """evaluate_profile must raise ValueError when no held_out sessions exist."""
        sessions = []
        for i in range(10):
            sessions.append({
                "gesture_label": GESTURE_REST,
                "held_out": False,
                "feature_window": {"norm": 0.05 + i * 0.005},
            })
            sessions.append({
                "gesture_label": GESTURE_LIGHT,
                "held_out": False,
                "feature_window": {"norm": 0.25 + i * 0.01},
            })
            sessions.append({
                "gesture_label": GESTURE_HARD,
                "held_out": False,
                "feature_window": {"norm": 0.50 + i * 0.01},
            })
        
        profile = calibrate_from_sessions(
            sessions,
            user_id="test_user",
            device_id="test_device",
        )
        
        with self.assertRaises(ValueError) as ctx:
            evaluate_profile(profile, sessions)
        
        self.assertIn("No held_out sessions", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
