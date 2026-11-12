"""Late fusion: IMU motion × EMG RMS effort. Features do not decide force."""

import json
import unittest

try:
    import jsonschema
except ImportError:
    jsonschema = None

from emg_gate.cli import main
from emg_gate.fusion import (
    FIVE_CLASS,
    FORCE_VERDICTS,
    IMU_FEATURES,
    MOTIONS,
    VERDICT_DAILY_EFFORT,
    VERDICT_FORCEFUL,
    VERDICT_ISOMETRIC,
    VERDICT_MOTION_WITHOUT_EFFORT,
    VERDICT_REST,
    VERDICT_SUPPRESSED,
    VERDICT_WITHHELD,
    FusionError,
    decision_grid,
    export_label,
    five_class_train_ready,
    fuse,
    fuse_imu_window,
    fuse_pair,
    imu_test_ready,
    imu_train_ready,
    sample_paired_window,
    screen_five_class_label,
)
from emg_gate.quality import SUPPRESS_GREEN
from emg_gate.schemas import load_schema


def _hop(t, band, quality="ok", authorize=False, norm=0.1, envelope="rms"):
    return {
        "t_host_ms": t,
        "band": band,
        "quality": quality,
        "authorize": authorize,
        "norm": norm,
        "envelope": envelope,
    }


class TestFuse(unittest.TestCase):
    def test_punch_and_hard_reports_force(self):
        row = fuse("punch", 2, "ok", True)
        self.assertEqual(row["verdict"], VERDICT_FORCEFUL)
        self.assertTrue(row["report_force"])
        self.assertEqual(row["effort"], "hard")
        self.assertEqual(row["train_label"], "punch")
        self.assertEqual(row["envelope"], "rms")

    def test_punch_and_light_reports_force(self):
        row = fuse("punch", 1, "ok", True)
        self.assertEqual(row["verdict"], VERDICT_FORCEFUL)
        self.assertEqual(row["effort"], "light")

    def test_still_and_hard_is_isometric(self):
        row = fuse("still", 2, "ok", True)
        self.assertEqual(row["verdict"], VERDICT_ISOMETRIC)
        self.assertTrue(row["report_force"])
        self.assertEqual(row["train_label"], "other")

    def test_daily_and_hard_stays_daily(self):
        row = fuse("daily", 2, "ok", True)
        self.assertEqual(row["verdict"], VERDICT_DAILY_EFFORT)
        self.assertEqual(row["train_label"], "other")

    def test_motion_at_rest_is_not_force(self):
        row = fuse("punch", 0, "ok", False)
        self.assertEqual(row["verdict"], VERDICT_MOTION_WITHOUT_EFFORT)
        self.assertFalse(row["report_force"])
        self.assertIsNone(row["effort"])

    def test_still_at_rest(self):
        row = fuse("still", 0, "ok", False)
        self.assertEqual(row["verdict"], VERDICT_REST)
        self.assertFalse(row["report_force"])

    def test_unreleased_effort_is_withheld(self):
        row = fuse("punch", 2, "ok", False)
        self.assertEqual(row["verdict"], VERDICT_WITHHELD)
        self.assertFalse(row["report_force"])

    def test_suppress_green_never_reports_force_even_if_authorize_lies(self):
        for quality in sorted(SUPPRESS_GREEN):
            row = fuse("punch", 2, quality, True)
            self.assertEqual(row["verdict"], VERDICT_SUPPRESSED, quality)
            self.assertFalse(row["report_force"], quality)
            self.assertEqual(row["band"], 0, quality)
            self.assertEqual(row["band_in"], 2, quality)
            self.assertIsNone(row["effort"], quality)

    def test_line_noise_does_not_report_force(self):
        lied = fuse("punch", 2, "line_noise", True)
        self.assertEqual(lied["verdict"], VERDICT_WITHHELD)
        self.assertFalse(lied["report_force"])
        quiet = fuse("still", 0, "line_noise", False)
        self.assertEqual(quiet["verdict"], VERDICT_REST)
        self.assertFalse(quiet["report_force"])

    def test_artifact_follows_authorize(self):
        held = fuse("hook", 2, "artifact_suspect", False)
        self.assertEqual(held["verdict"], VERDICT_WITHHELD)
        released = fuse("hook", 2, "artifact_suspect", True)
        self.assertEqual(released["verdict"], VERDICT_FORCEFUL)
        self.assertTrue(released["report_force"])

    def test_unknown_motion_and_bad_band_raise(self):
        with self.assertRaises(FusionError):
            fuse("other", 2, "ok", True)
        with self.assertRaises(FusionError):
            fuse("punch", True, "ok", True)
        with self.assertRaises(FusionError):
            fuse("punch", 2, "wet", True)

    def test_grid_is_closed(self):
        rows = decision_grid()
        self.assertEqual(len(rows), len(MOTIONS) * 3 * 6 * 2)
        for row in rows:
            self.assertEqual(row["report_force"], row["verdict"] in FORCE_VERDICTS)
            if row["quality"] in SUPPRESS_GREEN:
                self.assertFalse(row["report_force"])
                self.assertEqual(row["verdict"], VERDICT_SUPPRESSED)

    def test_hook_stays_unmerged_until_export_asks(self):
        self.assertEqual(export_label("hook"), "hook")
        self.assertEqual(export_label("uppercut"), "uppercut")
        self.assertEqual(export_label("hook", merge_punch_family=True), "punch")
        self.assertEqual(export_label("still"), "other")
        self.assertEqual(export_label("daily"), "other")


class TestWindow(unittest.TestCase):
    def test_peak_authorized_band_inside_window(self):
        hops = [
            _hop(1000, 0, norm=0.05),
            _hop(1200, 2, authorize=True, norm=0.7),
            _hop(1400, 1, authorize=True, norm=0.3),
            _hop(4000, 2, authorize=True, norm=0.9),
        ]
        row = fuse_imu_window("punch", 1000, 2000, hops, fs_hz=52)
        self.assertEqual(row["verdict"], VERDICT_FORCEFUL)
        self.assertEqual(row["effort"], "hard")
        self.assertEqual(row["emg_hops"], 3)
        self.assertTrue(row["profile_match"])
        self.assertEqual(row["norm"], 0.7)

    def test_hop_outside_the_window_cannot_create_force(self):
        hops = [_hop(999, 2, authorize=True, norm=0.9), _hop(1000, 0, norm=0.04)]
        row = fuse_imu_window("circle", 1000, 2000, hops, fs_hz=52)
        self.assertEqual(row["verdict"], VERDICT_MOTION_WITHOUT_EFFORT)
        self.assertFalse(row["report_force"])

    def test_no_overlap_raises(self):
        with self.assertRaises(FusionError):
            fuse_imu_window("punch", 1000, 2000, [_hop(3001, 2, authorize=True)])

    def test_any_lead_off_blocks_the_window(self):
        hops = [
            _hop(1100, 2, authorize=True, norm=0.8),
            _hop(1500, 0, quality="lead_off", norm=0.01),
        ]
        row = fuse_imu_window("still", 1000, 2000, hops)
        self.assertEqual(row["verdict"], VERDICT_SUPPRESSED)
        self.assertFalse(row["report_force"])
        self.assertFalse(row["profile_match"])

    def test_ma_envelope_rejected(self):
        with self.assertRaises(FusionError):
            fuse_imu_window("punch", 0, 2000, [_hop(100, 2, authorize=True, envelope="ma")])


class TestPairedWindow(unittest.TestCase):
    def test_pair_reports_force_and_ignores_features(self):
        quiet = sample_paired_window(imu={"features": [0.0] * IMU_FEATURES})
        loud = sample_paired_window(imu={"features": [9999.0] * IMU_FEATURES})
        a = fuse_pair(quiet)
        b = fuse_pair(loud)
        self.assertEqual(a["verdict"], b["verdict"])
        self.assertTrue(a["report_force"])
        self.assertEqual(a["verdict"], VERDICT_FORCEFUL)
        self.assertNotIn("features", a)

    def test_large_imu_features_do_not_make_rest_into_force(self):
        record = sample_paired_window(
            imu={"motion": "still", "features": [9999.0] * IMU_FEATURES},
            emg={"band": 0, "authorize": False, "norm": 0.04},
        )
        row = fuse_pair(record)
        self.assertEqual(row["verdict"], VERDICT_REST)
        self.assertFalse(row["report_force"])

    def test_single_gesture_label_rejected(self):
        record = sample_paired_window(gesture_label="hard")
        with self.assertRaises(FusionError):
            fuse_pair(record)

    def test_non_rms_envelope_rejected(self):
        record = sample_paired_window(emg={"envelope": "ma"})
        with self.assertRaises(FusionError):
            fuse_pair(record)

    def test_short_feature_vector_rejected(self):
        record = sample_paired_window(imu={"features": [0.1] * 11})
        with self.assertRaises(FusionError):
            fuse_pair(record)

    def test_schema_enum_matches_motions(self):
        enum = load_schema("paired_window")["$defs"]["imu"]["properties"]["motion"]["enum"]
        self.assertEqual(tuple(enum), MOTIONS)
        self.assertNotIn("gesture_label", load_schema("paired_window")["properties"])

    def test_jsonschema_accepts_sample_when_installed(self):
        if jsonschema is None:
            self.skipTest("jsonschema not installed")
        jsonschema.validate(sample_paired_window(), load_schema("paired_window"))

    def test_cli_pair_and_reject(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pair.json"
            path.write_text(json.dumps(sample_paired_window()), encoding="utf-8")
            self.assertEqual(main(["fuse", "--pair", str(path)]), 0)
            path.write_text(json.dumps(sample_paired_window(gesture_label="punch")), encoding="utf-8")
            self.assertEqual(main(["fuse", "--pair", str(path)]), 2)
        self.assertEqual(main(["fuse", "--motion", "up_wave", "--band", "0"]), 0)
        self.assertEqual(main(["fuse", "--motion", "up_wave", "--band", "2", "--authorize"]), 0)
        self.assertEqual(main(["fuse"]), 2)


class TestTrainGates(unittest.TestCase):
    def test_imu_needs_two_sessions_and_ten_held_out(self):
        labels = ("circle", "up_wave", "punch", "other")
        blocked = imu_train_ready({"circle": 2, "up_wave": 2, "punch": 1, "other": 2}, labels)
        self.assertFalse(blocked["ready"])
        self.assertEqual(blocked["thin"], ["punch"])
        ready = imu_train_ready({"circle": 2, "up_wave": 2, "punch": 2, "other": 2}, labels)
        self.assertTrue(ready["ready"])
        short = imu_test_ready({"circle": 10, "up_wave": 10, "punch": 9, "other": 10}, labels)
        self.assertFalse(short["report_accuracy"])
        self.assertEqual(short["thin"], ["punch"])
        enough = imu_test_ready({"circle": 10, "up_wave": 10, "punch": 10, "other": 10}, labels)
        self.assertTrue(enough["report_accuracy"])

    def test_force_labels_cannot_enter_five_class(self):
        for label in ("rest", "light", "hard", "lead_off_neg", "confirm_pulse"):
            with self.assertRaises(FusionError):
                screen_five_class_label(label)
        for label in FIVE_CLASS:
            self.assertEqual(screen_five_class_label(label), label)
        counts = {label: 20 for label in FIVE_CLASS}
        counts["hard"] = 20
        leaked = five_class_train_ready(counts, min_count=10)
        self.assertFalse(leaked["ready"])
        self.assertEqual(leaked["leaks"], ["hard"])
        fresh = five_class_train_ready({label: 10 for label in FIVE_CLASS}, min_count=10)
        self.assertTrue(fresh["ready"])
        self.assertFalse(five_class_train_ready({}, min_count=1)["ready"])
        mixed = {label: 10 for label in FIVE_CLASS}
        mixed["circle"] = 10
        foreign = five_class_train_ready(mixed, min_count=10)
        self.assertFalse(foreign["ready"])
        self.assertEqual(foreign["foreign"], ["circle"])


if __name__ == "__main__":
    unittest.main()
