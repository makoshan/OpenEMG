"""One recording splits into IMU, force, and five-class sets. Joint training is refused."""

import json
import tempfile
import unittest
from pathlib import Path

from emg_gate.cli import main
from emg_gate.fusion import IMU_FEATURES, FusionError, sample_paired_window
from emg_gate.split_tracks import (
    DEFAULT_IMU_LABELS,
    build_joint_snapshot,
    rows_from_platform_fixture,
    split_recording,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "platform" / "windows.json"


def _features(fill=0.1):
    return [fill] * IMU_FEATURES


def _imu(session, motion, held_out=False, fill=0.1, **extra):
    row = {
        "track": "imu",
        "session_id": session,
        "donning_id": "don_emg",
        "motion": motion,
        "features": _features(fill),
        "held_out": held_out,
    }
    row.update(extra)
    return row


def _pair(session, motion="punch", band=2, authorize=True, fill=0.1, held_out=False):
    return {
        "track": "paired",
        "session_id": session,
        "donning_id": "don_emg",
        "held_out": held_out,
        "pair": sample_paired_window(
            imu={"motion": motion, "features": _features(fill)},
            emg={"band": band, "authorize": authorize, "norm": 0.2 if band == 0 else 0.7},
        ),
    }


def _ready_imu_rows():
    rows = []
    for label, motion in (("circle", "circle"), ("up_wave", "up_wave"), ("punch", "punch"), ("other", "still")):
        rows.append(_imu(f"{label}-a", motion))
        rows.append(_imu(f"{label}-b", motion))
    return rows


class TestSplit(unittest.TestCase):
    def test_paired_punch_feeds_imu_and_not_force(self):
        result = split_recording([_pair("s-punch", fill=9999.0), _pair("s-punch-2", band=0, authorize=False)])
        windows = result["imu_snapshot"]["windows"]
        self.assertEqual([row["gesture_label"] for row in windows], ["punch", "punch"])
        self.assertEqual(windows[0]["features"][0], 9999.0)
        self.assertNotIn("norm", windows[0])
        self.assertNotIn("effort", windows[0])
        self.assertEqual(result["force_rows"], [])
        self.assertEqual(result["five_rows"], [])
        self.assertTrue(result["decisions"][0]["report_force"])
        self.assertFalse(result["decisions"][1]["report_force"])
        self.assertEqual(result["decisions"][1]["verdict"], "motion_without_effort")

    def test_full_imu_set_can_train_and_short_set_cannot(self):
        ready = split_recording(_ready_imu_rows())
        self.assertTrue(ready["report"]["imu"]["train"]["ready"])
        self.assertFalse(ready["report"]["imu"]["test"]["report_accuracy"])
        self.assertEqual(ready["imu_snapshot"]["labels"], list(DEFAULT_IMU_LABELS))
        short = split_recording([_imu("only", "punch"), _imu("only", "circle")])
        self.assertFalse(short["report"]["imu"]["train"]["ready"])
        self.assertIn("up_wave", short["report"]["imu"]["train"]["thin"])

    def test_held_out_stays_out_of_training_windows(self):
        rows = _ready_imu_rows() + [_imu("held-punch", "punch", held_out=True)]
        result = split_recording(rows)
        self.assertEqual(len(result["imu_snapshot"]["test_windows"]), 1)
        self.assertTrue(all(row["session_id"] != "held-punch" for row in result["imu_snapshot"]["windows"]))
        self.assertFalse(result["report"]["imu"]["test"]["report_accuracy"])

    def test_force_and_five_stay_in_their_own_buckets(self):
        rows = [
            {"track": "force", "session_id": "f1", "donning_id": "don_emg", "gesture_label": "hard"},
            {"track": "five_class", "session_id": "g1", "donning_id": "don_emg", "gesture_label": "pinch"},
        ]
        result = split_recording(rows)
        self.assertEqual(result["force_rows"][0]["gesture_label"], "hard")
        self.assertEqual(result["five_rows"][0]["gesture_label"], "pinch")
        self.assertEqual(result["imu_snapshot"]["windows"], [])
        self.assertFalse(result["report"]["force"]["model"])
        self.assertFalse(result["report"]["five_class"]["model"])
        self.assertFalse(result["report"]["five_class"]["train"]["ready"])

    def test_joint_track_and_mixed_fields_are_refused(self):
        with self.assertRaises(FusionError):
            build_joint_snapshot([_pair("s")])
        with self.assertRaises(FusionError):
            split_recording([{"track": "joint", "session_id": "s", "donning_id": "d"}])
        with self.assertRaises(FusionError):
            split_recording([_imu("s", "punch", gesture_label="hard")])
        with self.assertRaises(FusionError):
            split_recording([{
                "track": "force", "session_id": "s", "donning_id": "d",
                "gesture_label": "hard", "features": _features(),
            }])
        with self.assertRaises(FusionError):
            split_recording([{
                "track": "five_class", "session_id": "s", "donning_id": "d", "gesture_label": "hard",
            }])
        mixed = _pair("s")
        mixed["gesture_label"] = "hard"
        with self.assertRaises(FusionError):
            split_recording([mixed])
        with self.assertRaises(FusionError):
            split_recording([_imu("s", "punch", features=_features()[:11])])
        with self.assertRaises(FusionError):
            split_recording([_imu("s", "hook")])
        mismatched = _pair("s")
        mismatched["donning_id"] = "other-don"
        with self.assertRaises(FusionError):
            split_recording([mismatched])

    def test_hook_merges_only_when_asked(self):
        row = _imu("s1", "hook")
        with self.assertRaises(FusionError):
            split_recording([row])
        merged = split_recording(
            [row, _imu("s2", "hook")],
            merge_punch_family=True,
        )
        self.assertEqual(
            [window["gesture_label"] for window in merged["imu_snapshot"]["windows"]],
            ["punch", "punch"],
        )

    def test_cli_writes_three_sets_and_require_ready_fails_when_short(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "rows.jsonl"
            out = Path(tmp) / "out"
            src.write_text(json.dumps(_pair("s-punch")) + "\n", encoding="utf-8")
            self.assertEqual(main(["split", "--in", str(src), "--out", str(out)]), 0)
            snapshot = json.loads((out / "imu_snapshot.json").read_text(encoding="utf-8"))
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(snapshot["windows"][0]["gesture_label"], "punch")
            self.assertFalse(report["imu"]["train"]["ready"])
            self.assertEqual(main(["split", "--in", str(src), "--out", str(out), "--require-ready"]), 1)
            ready_src = Path(tmp) / "ready.jsonl"
            ready_src.write_text(
                "".join(json.dumps(row) + "\n" for row in _ready_imu_rows()),
                encoding="utf-8",
            )
            self.assertEqual(main(["split", "--in", str(ready_src), "--out", str(out), "--require-ready"]), 0)


class TestPlatformFixture(unittest.TestCase):
    def test_watch_test_split_blocks_continue(self):
        doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
        result = split_recording(rows_from_platform_fixture(doc))
        train = result["imu_snapshot"]["windows"]
        held = result["imu_snapshot"]["test_windows"]
        self.assertEqual(len(train), 4)
        self.assertEqual(len(held), 56)
        self.assertEqual(
            sorted(row["gesture_label"] for row in train),
            ["circle", "punch", "punch", "up_wave"],
        )
        self.assertEqual(result["force_rows"], [])
        self.assertEqual(result["five_rows"], [])
        self.assertFalse(result["report"]["imu"]["continue"])
        self.assertEqual(result["report"]["imu"]["train"]["thin"], ["circle", "up_wave", "other"])
        self.assertTrue(result["report"]["imu"]["test"]["report_accuracy"])

    def test_fixture_cannot_become_force_or_drop_its_split(self):
        doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
        broken = json.loads(json.dumps(doc))
        broken["windows"][0]["gesture_label"] = "hard"
        with self.assertRaises(FusionError):
            split_recording(rows_from_platform_fixture(broken))
        nosplit = json.loads(json.dumps(doc))
        del nosplit["windows"][0]["split"]
        with self.assertRaises(FusionError):
            rows_from_platform_fixture(nosplit)

    def test_cli_fixture_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            self.assertEqual(main(["split", "--fixture", str(FIXTURE), "--out", str(out), "--require-ready"]), 1)
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertFalse(report["imu"]["continue"])
            self.assertEqual(report["force"]["rows"], 0)


if __name__ == "__main__":
    unittest.main()
