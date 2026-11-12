"""P0 checklist: one passing pack and one must-fail sample per item."""

import tempfile
import unittest
from pathlib import Path

from emg_gate.checklist import ADR_MIN_SECONDS_PER_GESTURE, check_p0_acceptance, format_checklist_report
from emg_gate.demo_pack import build_demo_pack
from emg_gate.quality import quality_label_to_flags
from emg_gate.session_store import SessionPack

SECONDS = 3.0  # short synthetic streams; threshold lowered to match in tests
# Roughly 20-25 % of synthetic rest windows are rejected / flagged by the
# heuristic detectors (lead_off at ~5 uV, DFT line_noise false positives), so a
# passing pack is asserted at 50 % of the streamed seconds. The ADR threshold
# (120 s) is exercised separately in test_adr_threshold_fails_on_short_pack.
PASS_FRACTION = 0.5


class TestChecklist(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _pack(self, name, **kw):
        root = self.base / name
        build_demo_pack(root, seconds_per_gesture=SECONDS, **kw)
        return root

    def test_full_demo_pack_passes(self):
        root = self._pack("good")
        res = check_p0_acceptance(root, min_seconds_per_gesture=SECONDS * PASS_FRACTION)
        self.assertTrue(res["all_sat"], format_checklist_report(res))
        report = format_checklist_report(res)
        self.assertIn("放宽", report, "lowered threshold must be disclosed in the report")

    def test_adr_threshold_fails_on_short_pack(self):
        root = self._pack("short")
        res = check_p0_acceptance(root)  # default = ADR 120 s
        self.assertFalse(res["items"]["gesture_durations"]["sat"])
        self.assertEqual(res["min_seconds_per_gesture"], ADR_MIN_SECONDS_PER_GESTURE)
        self.assertFalse(res["all_sat"])

    def test_must_fail_missing_lead_off_neg(self):
        root = self._pack("no_neg", omit_lead_off_neg=True)
        res = check_p0_acceptance(root, min_seconds_per_gesture=SECONDS * PASS_FRACTION)
        self.assertFalse(res["items"]["gesture_durations"]["sat"])
        self.assertFalse(res["items"]["gesture_durations"]["detail"]["per_gesture"]["lead_off_neg"]["sat"])
        self.assertTrue(res["items"]["gesture_durations"]["detail"]["per_gesture"]["hard"]["sat"])

    def test_must_fail_single_donning(self):
        root = self._pack("one_don", donnings=1)
        res = check_p0_acceptance(root, min_seconds_per_gesture=SECONDS * PASS_FRACTION)
        self.assertFalse(res["items"]["redon_new_donning_id"]["sat"])
        self.assertFalse(res["items"]["held_out_markable"]["sat"], "single donning cannot have a held_out re-don")

    def test_must_fail_no_held_out(self):
        root = self._pack("no_held", held_out_redon=False)
        res = check_p0_acceptance(root, min_seconds_per_gesture=SECONDS * PASS_FRACTION)
        self.assertFalse(res["items"]["held_out_markable"]["sat"])
        self.assertTrue(res["items"]["redon_new_donning_id"]["sat"])

    def test_raw_in_pack_never_reaches_default_export(self):
        root = self._pack("raw", include_raw=True)
        res = check_p0_acceptance(root, min_seconds_per_gesture=SECONDS * PASS_FRACTION)
        item = res["items"]["export_reproducible_no_raw"]
        self.assertTrue(item["detail"]["pack_stores_raw_locally"])
        self.assertFalse(item["detail"]["default_export_has_raw"])
        self.assertTrue(item["sat"])

    def test_must_fail_tampered_window(self):
        root = self._pack("tamper")
        pack = SessionPack.open(root)
        wpath = next(iter(sorted((root / "windows").glob("*.jsonl"))))
        # inject a row with a non-whitelisted field straight into storage
        rows = wpath.read_text().splitlines()
        rows[0] = rows[0][:-1] + ',"free_text_label":"squeeze"}'
        wpath.write_text("\n".join(rows) + "\n")
        res = check_p0_acceptance(root, min_seconds_per_gesture=SECONDS * PASS_FRACTION)
        self.assertFalse(res["items"]["session_and_donning_ids"]["sat"])
        self.assertEqual(res["items"]["session_and_donning_ids"]["detail"]["n_invalid_windows"], 1)
        self.assertIsNotNone(pack)

    def test_not_a_pack(self):
        res = check_p0_acceptance(self.base / "nope")
        self.assertFalse(res["all_sat"])
        self.assertTrue(all(not v["sat"] for v in res["items"].values()))

    def test_positive_windows_with_bad_quality_do_not_count(self):
        root = self.base / "manual"
        pack = SessionPack.create(root, user_id="u", device_id="d")
        pack.don("d1")
        sid = pack.create_session(session_id="s")
        for i in range(10):
            pack.append_window(sid, gesture_label="rest", quality=quality_label_to_flags("poor_contact"), obs_ts_device_ms=i * 200, window_ms=200)
        pack.doff()
        res = check_p0_acceptance(root, min_seconds_per_gesture=1.0)
        self.assertEqual(res["items"]["gesture_durations"]["detail"]["per_gesture"]["rest"]["valid_s_train"], 0.0)

    def test_must_fail_split_leak(self):
        """MUST-FAIL: same (donning, gesture) with both held_out=false and held_out=true."""
        root = self.base / "leak"
        pack = SessionPack.create(root, user_id="u", device_id="d")
        pack.don("don1")
        # training window
        s1 = pack.create_session(session_id="s1_train", held_out=False)
        pack.append_window(s1, gesture_label="rest", quality=quality_label_to_flags("ok"), obs_ts_device_ms=0, window_ms=200)
        # test window in SAME (donning, gesture) cell
        s2 = pack.create_session(session_id="s2_test", held_out=True)
        pack.append_window(s2, gesture_label="rest", quality=quality_label_to_flags("ok"), obs_ts_device_ms=200, window_ms=200)
        pack.doff()
        
        res = check_p0_acceptance(root, min_seconds_per_gesture=0.1)
        self.assertFalse(res["items"]["no_split_leak"]["sat"], "leak must be detected")
        self.assertFalse(res["all_sat"], "all_sat must be False when leak present")
        leaks = res["items"]["no_split_leak"]["detail"]["leaks"]
        self.assertIn(("don1", "rest"), leaks)

    def test_clean_split_no_leak(self):
        """Clean split: different donnings for train vs test."""
        root = self.base / "clean"
        pack = SessionPack.create(root, user_id="u", device_id="d")
        # train donning
        pack.don("don1")
        s1 = pack.create_session(session_id="s1", held_out=False)
        pack.append_window(s1, gesture_label="rest", quality=quality_label_to_flags("ok"), obs_ts_device_ms=0, window_ms=200)
        pack.doff()
        # test donning (different donning_id)
        pack.don("don2")
        s2 = pack.create_session(session_id="s2", held_out=True)
        pack.append_window(s2, gesture_label="rest", quality=quality_label_to_flags("ok"), obs_ts_device_ms=200, window_ms=200)
        pack.doff()
        
        res = check_p0_acceptance(root, min_seconds_per_gesture=0.1)
        self.assertTrue(res["items"]["no_split_leak"]["sat"], "no leak should be present")
        leaks = res["items"]["no_split_leak"]["detail"]["leaks"]
        self.assertEqual(leaks, [])

    def test_bad_quality_excluded_from_leak_detection(self):
        """poor_contact=true held_out window must not count in grid (no train or test)."""
        root = self.base / "bad_qual"
        pack = SessionPack.create(root, user_id="u", device_id="d")
        pack.don("don1")
        s1 = pack.create_session(session_id="s1", held_out=True)
        pack.append_window(s1, gesture_label="rest", quality=quality_label_to_flags("poor_contact"), obs_ts_device_ms=0, window_ms=200)
        pack.doff()
        
        res = check_p0_acceptance(root, min_seconds_per_gesture=0.1)
        grid = res["items"]["no_split_leak"]["detail"]["grid"]
        # grid should not contain this cell because quality was bad
        self.assertNotIn("don1:rest", grid)


if __name__ == "__main__":
    unittest.main()
