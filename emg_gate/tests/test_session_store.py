"""P0 session pack: create / don-doff / append (reject before persist) / export."""

import json
import tempfile
import unittest
from pathlib import Path

from emg_gate.capture_session import CaptureSessionError
from emg_gate.cloud_safe_event import validate_cloud_safe_event
from emg_gate.quality import quality_label_to_flags
from emg_gate.session_store import SessionPack, SessionPackError

OK = quality_label_to_flags("ok")
LEAD_OFF = quality_label_to_flags("lead_off")


class TestSessionPack(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "pack"
        self.pack = SessionPack.create(self.root, user_id="u1", device_id="ads1292_a")

    def tearDown(self):
        self._tmp.cleanup()

    def test_session_requires_active_donning(self):
        with self.assertRaises(SessionPackError):
            self.pack.create_session()
        self.pack.don("don_1")
        sid = self.pack.create_session()
        self.assertEqual(self.pack.session_meta(sid)["donning_id"], "don_1")

    def test_doff_forces_new_donning_id(self):
        self.pack.don("don_1")
        self.pack.create_session(session_id="s1")
        self.pack.doff()
        with self.assertRaises(SessionPackError):
            self.pack.create_session(session_id="s2")
        with self.assertRaises(SessionPackError, msg="re-using an old donning_id must be refused"):
            self.pack.don("don_1")
        self.pack.don("don_2")
        self.pack.create_session(session_id="s2")
        ids = {self.pack.session_meta(s)["donning_id"] for s in ("s1", "s2")}
        self.assertEqual(ids, {"don_1", "don_2"})
        donnings = self.pack.meta["donnings"]
        self.assertIsNotNone(donnings[0]["ended_at"])
        self.assertIsNone(donnings[1]["ended_at"])

    def test_append_rejects_before_persist(self):
        self.pack.don("don_1")
        sid = self.pack.create_session(session_id="s1")
        with self.assertRaises(CaptureSessionError):
            self.pack.append_window(sid, gesture_label="light", quality=LEAD_OFF, feature_window={"norm": 0.3})
        with self.assertRaises(CaptureSessionError):
            self.pack.append_window(sid, gesture_label="wave", quality=OK)
        with self.assertRaises(CaptureSessionError):
            self.pack.append_window(sid, gesture_label="rest", quality={"lead_off": False})
        self.assertFalse((self.root / "windows" / "s1.jsonl").exists(), "rejected rows must not touch disk")

        row = self.pack.append_window(sid, gesture_label="rest", quality=OK, feature_window={"norm": 0.05, "band": 0})
        self.assertEqual(row["donning_id"], "don_1")
        self.assertEqual(len(self.pack.load_windows()), 1)
        neg = self.pack.append_window(sid, gesture_label="lead_off_neg", quality=LEAD_OFF, feature_window={"norm": 0.01})
        self.assertTrue(neg["quality"]["lead_off"])

    def test_mark_held_out_propagates_to_windows(self):
        self.pack.don("don_1")
        sid = self.pack.create_session(session_id="s1")
        self.pack.append_window(sid, gesture_label="rest", quality=OK, feature_window={"norm": 0.05})
        self.assertFalse(self.pack.load_windows()[0]["held_out"])
        self.pack.mark_held_out(sid, True)
        self.assertTrue(self.pack.session_meta(sid)["held_out"])
        self.assertTrue(all(r["held_out"] for r in self.pack.load_windows()))

    def test_export_reproducible_and_strips_raw_by_default(self):
        self.pack.don("don_1")
        sid = self.pack.create_session(session_id="s1")
        for i in range(5):
            self.pack.append_window(
                sid,
                gesture_label="rest",
                quality=OK,
                obs_ts_device_ms=1000 + i * 50,
                obs_ts_host_ms=2000 + i * 50,
                feature_window={"norm": 0.05, "band": 0},
                raw_window=[0.1 * i, 0.2, 0.3],
            )
        self.assertTrue(all("raw_window" in r for r in self.pack.load_windows()), "pack keeps raw locally")

        out = Path(self._tmp.name)
        e1 = self.pack.export(out / "a.jsonl")
        e2 = self.pack.export(out / "b.jsonl")
        self.assertEqual(e1["sha256"], e2["sha256"])
        self.assertFalse(e1["has_raw"])
        for line in (out / "a.jsonl").read_text().splitlines():
            self.assertNotIn("raw_window", json.loads(line))

        dev = self.pack.export(out / "dev.jsonl", include_raw=True)
        self.assertTrue(dev["has_raw"])
        self.assertNotEqual(dev["sha256"], e1["sha256"])

    def test_cloud_safe_export_has_no_raw_and_validates(self):
        self.pack.don("don_1")
        sid = self.pack.create_session(session_id="s1")
        self.pack.append_window(sid, gesture_label="hard", quality=OK, feature_window={"norm": 0.7, "band": 2, "confidence": 0.9}, raw_window=[1.0, 2.0])
        self.pack.append_window(sid, gesture_label="lead_off_neg", quality=LEAD_OFF, feature_window={"norm": 0.0, "band": 0})
        out = Path(self._tmp.name) / "cloud.jsonl"
        info = self.pack.export_cloud_safe(out)
        self.assertEqual(info["n_rows"], 2)
        rows = [json.loads(l) for l in out.read_text().splitlines()]
        for r in rows:
            validate_cloud_safe_event(r)
            self.assertNotIn("raw_window", r)
        self.assertEqual(rows[1]["quality"], "lead_off")

    def test_valid_coverage_unions_overlapping_windows(self):
        self.pack.don("don_1")
        sid = self.pack.create_session(session_id="s1")
        # 200 ms windows at 50 ms hop: 5 windows cover 400 ms, not 1000 ms
        for i in range(5):
            self.pack.append_window(sid, gesture_label="rest", quality=OK, obs_ts_device_ms=i * 50, window_ms=200, feature_window={"norm": 0.05})
        # a poor_contact rest window must not count as valid
        self.pack.append_window(sid, gesture_label="rest", quality=quality_label_to_flags("poor_contact"), obs_ts_device_ms=5000, window_ms=200)
        cov = self.pack.valid_coverage_ms()
        self.assertAlmostEqual(cov["rest"], 400.0)

    def test_export_counts_source_and_rejects_mixed(self):
        """Test export counts source and rejects mixed recorded/synthetic."""
        self.pack.don("don_1")
        sid1 = self.pack.create_session(session_id="s1")
        self.pack.append_window(sid1, gesture_label="rest", quality=OK, feature_window={"norm": 0.05}, source="recorded")
        self.pack.append_window(sid1, gesture_label="rest", quality=OK, feature_window={"norm": 0.06}, source="recorded")
        
        sid2 = self.pack.create_session(session_id="s2")
        self.pack.append_window(sid2, gesture_label="light", quality=OK, feature_window={"norm": 0.3}, source="synthetic")
        
        out = Path(self._tmp.name) / "mixed.jsonl"
        
        with self.assertRaises(ValueError) as ctx:
            self.pack.export(out)
        self.assertIn("mixed sources", str(ctx.exception))
        
        info = self.pack.export(out, mixed_ok=True)
        self.assertEqual(info["source_recorded"], 2)
        self.assertEqual(info["source_synthetic"], 1)

    def test_export_all_recorded_passes(self):
        """Test export with only recorded sessions passes."""
        self.pack.don("don_1")
        sid = self.pack.create_session(session_id="s1")
        self.pack.append_window(sid, gesture_label="rest", quality=OK, feature_window={"norm": 0.05}, source="recorded")
        self.pack.append_window(sid, gesture_label="light", quality=OK, feature_window={"norm": 0.3}, source="recorded")
        
        out = Path(self._tmp.name) / "recorded.jsonl"
        info = self.pack.export(out)
        self.assertEqual(info["source_recorded"], 2)
        self.assertEqual(info["source_synthetic"], 0)

    def test_export_all_synthetic_passes(self):
        """Test export with only synthetic sessions passes."""
        self.pack.don("don_1")
        sid = self.pack.create_session(session_id="s1")
        self.pack.append_window(sid, gesture_label="rest", quality=OK, feature_window={"norm": 0.05}, source="synthetic")
        self.pack.append_window(sid, gesture_label="light", quality=OK, feature_window={"norm": 0.3}, source="synthetic")
        
        out = Path(self._tmp.name) / "synth.jsonl"
        info = self.pack.export(out)
        self.assertEqual(info["source_recorded"], 0)
        self.assertEqual(info["source_synthetic"], 2)


if __name__ == "__main__":
    unittest.main()
