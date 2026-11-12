"""Test P1 gaps: held_out exclusion, schema unification, rollback."""

import json
import tempfile
import unittest
from pathlib import Path

from emg_gate.calibrate import (
    calibrate_from_sessions,
    calibrate_from_streams,
    rollback_profile,
)
from emg_gate.calibration_profile import validate_calibration_profile
from emg_gate.capture_session import create_capture_session
from emg_gate.synth import generate


class TestP1Gaps(unittest.TestCase):
    def test_held_out_excluded_from_fit(self):
        """Test that held_out=true sessions are excluded from threshold fitting."""
        sessions = []
        
        # Training sessions (will be used for fit)
        for i in range(10):
            sess = create_capture_session(
                user_id="test_user",
                device_id="test_device",
                session_id=f"sess_{i}",
                donning_id="don_001",
                gesture_label="rest",
                feature_window={"band": 0, "norm": 0.05 + i * 0.005},
                held_out=False,
            )
            sessions.append(sess)
        
        for i in range(10):
            sess = create_capture_session(
                user_id="test_user",
                device_id="test_device",
                session_id=f"sess_{i+10}",
                donning_id="don_001",
                gesture_label="light",
                feature_window={"band": 1, "norm": 0.20 + i * 0.01},
                held_out=False,
            )
            sessions.append(sess)
        
        for i in range(10):
            sess = create_capture_session(
                user_id="test_user",
                device_id="test_device",
                session_id=f"sess_{i+20}",
                donning_id="don_001",
                gesture_label="hard",
                feature_window={"band": 2, "norm": 0.45 + i * 0.02},
                held_out=False,
            )
            sessions.append(sess)
        
        # Held-out sessions (should be excluded)
        for i in range(5):
            sess = create_capture_session(
                user_id="test_user",
                device_id="test_device",
                session_id=f"sess_held_{i}",
                donning_id="don_002",
                gesture_label="rest",
                feature_window={"band": 0, "norm": 0.80},  # Outlier
                held_out=True,
            )
            sessions.append(sess)

        profile = calibrate_from_sessions(
            sessions,
            user_id="test_user",
            device_id="test_device",
            donning_id="don_001",
        )

        validate_calibration_profile(profile)
        
        cal_debug = profile.get("calibration_debug", {})
        self.assertEqual(cal_debug["n_training_windows"], 30)
        self.assertEqual(cal_debug["n_held_out_windows"], 5)
        
        th_loose = profile["thresholds"]["th_loose_max"]
        # Should be computed from training data (norm ~ 0.05-0.10)
        # NOT from held_out outliers (norm=0.80)
        self.assertLess(th_loose, 0.25, "Held-out outliers should not affect threshold")

    def test_calibration_profile_schema_unified(self):
        """Test that calibrate_from_streams outputs valid CalibrationProfile schema."""
        fs = 500.0
        duration = 1.0
        
        relax_uV, _ = generate("rest", fs=fs, duration_s=duration, seed=100)
        light_uV, _ = generate("light", fs=fs, duration_s=duration, seed=101)
        hard_uV, _ = generate("hard", fs=fs, duration_s=duration, seed=102)
        lead_uV, _ = generate("lead_off", fs=fs, duration_s=duration, seed=103)

        profile = calibrate_from_streams(
            relax_uV,
            light_uV,
            hard_uV,
            user_id="schema_test_user",
            device_id="schema_test_device",
            donning_id="don_schema",
            fs=fs,
            lead_off_uV=lead_uV,
        )

        # Must validate with CalibrationProfile schema
        validate_calibration_profile(profile)
        
        # Check canonical fields
        self.assertIn("schema_version", profile)
        self.assertIn("user_id", profile)
        self.assertIn("device_id", profile)
        self.assertIn("chain_ver", profile)
        self.assertIn("thresholds", profile)
        self.assertIn("created_at", profile)
        
        thresholds = profile["thresholds"]
        self.assertIn("th_loose_max", thresholds)
        self.assertIn("th_hard_min", thresholds)
        
        # Check that thresholds are valid
        th_loose = thresholds["th_loose_max"]
        th_hard = thresholds["th_hard_min"]
        self.assertGreater(th_hard, th_loose)
        self.assertGreaterEqual(th_loose, 0.0)
        self.assertLessEqual(th_hard, 1.0)

    def test_rollback_profile(self):
        """Test commit → rollback roundtrip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir)
            current_path = store_dir / "current.json"
            
            # Create initial profile (v1)
            profile_v1 = calibrate_from_streams(
                *[generate("rest", seed=i)[0] for i in [200, 201, 202]],
                user_id="rollback_user",
                device_id="rollback_device",
                fs=500.0,
            )
            th_v1_loose = profile_v1["thresholds"]["th_loose_max"]
            
            current_path.write_text(json.dumps(profile_v1, indent=2), encoding="utf-8")
            
            # Create new profile (v2) with prev_profile_ref
            prev_ref = "prev_v1.json"
            (store_dir / prev_ref).write_text(
                json.dumps(profile_v1, indent=2), encoding="utf-8"
            )
            
            profile_v2 = calibrate_from_streams(
                *[generate("light", seed=i)[0] for i in [210, 211, 212]],
                user_id="rollback_user",
                device_id="rollback_device",
                fs=500.0,
                prev_profile_ref=prev_ref,
            )
            th_v2_loose = profile_v2["thresholds"]["th_loose_max"]
            
            # v2 should differ from v1
            self.assertNotEqual(th_v2_loose, th_v1_loose)
            
            current_path.write_text(json.dumps(profile_v2, indent=2), encoding="utf-8")
            
            # Rollback to v1
            restored = rollback_profile(current_path, store_dir)
            
            self.assertIsNotNone(restored)
            self.assertEqual(
                restored["thresholds"]["th_loose_max"],
                th_v1_loose,
                "Rollback should restore v1 thresholds"
            )
            
            # Check current.json now contains v1
            current_content = json.loads(current_path.read_text(encoding="utf-8"))
            self.assertEqual(
                current_content["thresholds"]["th_loose_max"], th_v1_loose
            )
            
            # Check stale file was created
            stale_files = list(store_dir.glob("current_stale_*.json"))
            self.assertEqual(len(stale_files), 1)
            stale = json.loads(stale_files[0].read_text(encoding="utf-8"))
            self.assertTrue(stale["stale"])
            self.assertEqual(stale["thresholds"]["th_loose_max"], th_v2_loose)

    def test_rollback_no_prev_ref(self):
        """Test rollback returns None when no prev_profile_ref."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir)
            current_path = store_dir / "current.json"
            
            profile = calibrate_from_streams(
                *[generate("rest", seed=i)[0] for i in [300, 301, 302]],
                user_id="no_rollback_user",
                device_id="no_rollback_device",
                fs=500.0,
            )
            
            current_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
            
            result = rollback_profile(current_path, store_dir)
            self.assertIsNone(result, "Should return None when no prev_profile_ref")


if __name__ == "__main__":
    unittest.main()
