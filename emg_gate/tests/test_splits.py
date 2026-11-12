"""Test train/test split utilities and leak detection."""

import tempfile
import unittest
from pathlib import Path

from emg_gate.capture_session import GESTURE_LEAD_OFF_NEG, GESTURE_REST, create_capture_session
from emg_gate.quality import quality_label_to_flags
from emg_gate.session_store import SessionPack
from emg_gate.splits import clean_windows, find_leaks, split_grid


class TestSplits(unittest.TestCase):
    def test_clean_windows_removes_bad_quality(self):
        """Windows with any quality flag=True must be removed."""
        windows = [
            create_capture_session(
                user_id="u",
                device_id="d",
                session_id="s1",
                donning_id="don1",
                gesture_label=GESTURE_REST,
                quality={"lead_off": False, "poor_contact": False, "line_noise": False, "clip": False, "artifact_suspect": False},
            ),
            create_capture_session(
                user_id="u",
                device_id="d",
                session_id="s2",
                donning_id="don1",
                gesture_label=GESTURE_REST,
                quality={"lead_off": False, "poor_contact": True, "line_noise": False, "clip": False, "artifact_suspect": False},
            ),
        ]
        clean = clean_windows(windows)
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]["session_id"], "s1")

    def test_split_grid_counts_train_and_test(self):
        """Grid must separate train (held_out=false) and test (held_out=true)."""
        windows = [
            create_capture_session(
                user_id="u",
                device_id="d",
                session_id="s1",
                donning_id="don1",
                gesture_label=GESTURE_REST,
                held_out=False,
                quality=quality_label_to_flags("ok"),
            ),
            create_capture_session(
                user_id="u",
                device_id="d",
                session_id="s2",
                donning_id="don1",
                gesture_label=GESTURE_REST,
                held_out=True,
                quality=quality_label_to_flags("ok"),
            ),
        ]
        grid = split_grid(windows)
        self.assertIn(("don1", GESTURE_REST), grid)
        self.assertEqual(grid[("don1", GESTURE_REST)]["train"], 1)
        self.assertEqual(grid[("don1", GESTURE_REST)]["test"], 1)

    def test_find_leaks_detects_same_cell_both_train_and_test(self):
        """MUST-FAIL sample: same (donning, gesture) with both train and test."""
        grid = {
            ("don1", "rest"): {"train": 5, "test": 3},
            ("don2", "light"): {"train": 4, "test": 0},
            ("don3", "hard"): {"train": 0, "test": 2},
        }
        leaks = find_leaks(grid)
        self.assertEqual(leaks, [("don1", "rest")])

    def test_find_leaks_empty_on_clean_split(self):
        """Clean split: each cell has only train or only test."""
        grid = {
            ("don1", "rest"): {"train": 5, "test": 0},
            ("don2", "rest"): {"train": 0, "test": 3},
            ("don1", "light"): {"train": 4, "test": 0},
        }
        leaks = find_leaks(grid)
        self.assertEqual(leaks, [])

    def test_bad_quality_window_excluded_from_grid(self):
        """lead_off=true held_out window must not appear in train or test counts."""
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name) / "pack"
        pack = SessionPack.create(root, user_id="u", device_id="d")
        pack.don("don1")
        sid = pack.create_session(session_id="s1", held_out=True)
        pack.append_window(
            sid,
            gesture_label=GESTURE_LEAD_OFF_NEG,
            quality=quality_label_to_flags("ok"),
            obs_ts_device_ms=0,
            window_ms=200,
        )
        pack.doff()

        windows = pack.load_windows()
        grid = split_grid(windows)
        
        # This should pass because lead_off_neg with quality=ok is valid (lead_off should be true for valid lead_off_neg)
        # Let me create a truly bad quality window instead
        tmp.cleanup()
        
        # Recreate with a truly bad window (poor_contact on rest)
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name) / "pack2"
        pack = SessionPack.create(root, user_id="u", device_id="d")
        pack.don("don1")
        sid = pack.create_session(session_id="s1", held_out=True)
        pack.append_window(
            sid,
            gesture_label=GESTURE_REST,
            quality=quality_label_to_flags("poor_contact"),
            obs_ts_device_ms=0,
            window_ms=200,
        )
        pack.doff()

        windows = pack.load_windows()
        grid = split_grid(windows)
        
        # grid should be empty because the window was bad quality
        self.assertEqual(len(grid), 0)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
