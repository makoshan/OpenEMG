"""authorize-smoke + commit_profile/rollback through the real CLI flow."""

import json
import tempfile
import unittest
from pathlib import Path

from emg_gate.calibrate import (
    CalibrationCommitError,
    calibrate_from_sessions,
    calibrate_synth_demo,
    commit_profile,
    evaluate_sessions,
    load_profile,
    rollback_profile,
)
from emg_gate.calibration_profile import create_calibration_profile
from emg_gate.cli import main
from emg_gate.demo_pack import build_demo_pack
from emg_gate.session_store import SessionPack
from emg_gate.smoke import authorize_smoke


class TestAuthorizeSmoke(unittest.TestCase):
    def test_demo_profile_passes_and_no_false_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = calibrate_synth_demo(Path(tmp) / "p.json", duration_s=1.5)
        report = authorize_smoke(profile, duration_s=1.5)
        self.assertTrue(report["pass"], report)
        by = {r["scenario"]: r for r in report["rows"]}
        for bad in ("lead_off", "poor_contact", "clip"):
            self.assertEqual(by[bad]["authorize_count"], 0, bad)
        self.assertEqual(by["hard"]["majority_band"], 2)
        self.assertEqual(by["rest"]["majority_band"], 0)

    def test_stale_profile_fails_smoke(self):
        p = create_calibration_profile("u", "d", 0.1, 0.4, stale=True)
        self.assertFalse(authorize_smoke(p, duration_s=1.0)["pass"])

    def test_bad_thresholds_fail_smoke(self):
        # th_hard_min so high that "hard" cannot reach band 2 → must FAIL, not silently pass
        p = create_calibration_profile("u", "d", 0.05, 0.99)
        report = authorize_smoke(p, duration_s=1.5)
        self.assertFalse(report["pass"])
        self.assertFalse({r["scenario"]: r for r in report["rows"]}["hard"]["pass"])


class TestCommitAndRollback(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.active = self.base / "active.json"
        self.store = self.base / "store"

    def tearDown(self):
        self._tmp.cleanup()

    def test_second_commit_sets_prev_ref_then_rollback_restores(self):
        v1 = calibrate_synth_demo(self.active, duration_s=1.0, seed=1, store_dir=self.store)
        self.assertNotIn("prev_profile_ref", v1)
        v2 = calibrate_synth_demo(self.active, duration_s=1.0, seed=99, store_dir=self.store)
        self.assertIn("prev_profile_ref", v2)
        self.assertTrue((self.store / v2["prev_profile_ref"]).exists())
        self.assertNotEqual(v1["thresholds"], v2["thresholds"])

        restored = rollback_profile(self.active, self.store)
        self.assertEqual(restored["thresholds"], v1["thresholds"])
        self.assertEqual(load_profile(self.active)["thresholds"], v1["thresholds"])
        stale = [json.loads(p.read_text()) for p in self.store.glob("active_stale_*.json")]
        self.assertEqual(len(stale), 1)
        self.assertTrue(stale[0]["stale"])
        self.assertEqual(stale[0]["thresholds"], v2["thresholds"])
        self.assertIsNone(rollback_profile(self.active, self.store), "v1 had no prev → second rollback is a no-op")

    def test_commit_refuses_false_green_profile(self):
        p = create_calibration_profile("u", "d", 0.1, 0.4)
        p["calibration_debug"] = {"committed": False, "error": "lead_off false-green; refuse commit"}
        with self.assertRaises(CalibrationCommitError):
            commit_profile(p, self.active, self.store)
        self.assertFalse(self.active.exists())

    def test_cli_calibrate_twice_then_rollback(self):
        self.assertEqual(main(["calibrate", "--out", str(self.active), "--store-dir", str(self.store), "--duration", "1", "--seed", "3"]), 0)
        first = load_profile(self.active)
        self.assertEqual(main(["calibrate", "--out", str(self.active), "--store-dir", str(self.store), "--duration", "1", "--seed", "77"]), 0)
        self.assertIsNotNone(load_profile(self.active).get("prev_profile_ref"))
        self.assertEqual(main(["calibrate", "--out", str(self.active), "--store-dir", str(self.store), "--rollback"]), 0)
        self.assertEqual(load_profile(self.active)["thresholds"], first["thresholds"])
        self.assertEqual(main(["calibrate", "--out", str(self.active), "--store-dir", str(self.store), "--rollback"]), 1)


class TestCalibrateFromPack(unittest.TestCase):
    def test_from_pack_excludes_held_out_and_evaluates_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pack"
            build_demo_pack(root, seconds_per_gesture=3.0)
            pack = SessionPack.open(root)
            windows = pack.load_windows()
            n_held = sum(1 for w in windows if w["held_out"])
            self.assertGreater(n_held, 0)

            profile = calibrate_from_sessions(windows, user_id="u", device_id="d")
            dbg = profile["calibration_debug"]
            self.assertEqual(dbg["n_held_out_windows"], n_held)
            self.assertEqual(dbg["n_training_windows"] + n_held, len(windows))
            self.assertTrue(dbg["negatives_ok"])

            # held_out windows are scored only AFTER the fit
            report = evaluate_sessions(profile, windows, held_out_only=True)
            self.assertEqual(report["n_windows"], n_held)
            self.assertEqual(report["false_green"], 0)
            self.assertIn("lead_off_neg", report["per_gesture"])

            active = Path(tmp) / "p.json"
            rc = main(["calibrate", "--out", str(active), "--from-pack", str(root), "--eval-out", str(Path(tmp) / "eval.json")])
            self.assertEqual(rc, 0)
            self.assertTrue((Path(tmp) / "eval.json").exists())
            self.assertEqual(main(["authorize-smoke", "--profile", str(active), "--duration", "1.5"]), 0)


if __name__ == "__main__":
    unittest.main()
