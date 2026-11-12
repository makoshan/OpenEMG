"""8767 capture takes -> split rows: grid, leak and re-wear checks. Metadata-only fixtures."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from emg_gate.cli import main
from emg_gate.splits import find_leaks, split_grid
from emg_gate.takes import load_takes, redon_issues


def take(root: Path, split: str, label: str, donning: int, at: str) -> None:
    folder = root / split / label
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{label}-{at.replace(':', '')}"
    (folder / f"{stem}.json").write_text(json.dumps(
        {"label": label, "donning": donning, "recordedAt": at, "emgHz": 1000, "session": "gesture-v1"}))
    (folder / f"{stem}.npz").write_bytes(b"not a real npz; must never be opened")


def clean_night(root: Path) -> None:
    for i, label in enumerate(("rest", "pinch")):
        take(root, "train", label, 1, f"2026-09-27T18:0{i}:00")
        take(root, "validation", label, 2, f"2026-09-27T19:0{i}:00")
        take(root, "test", label, 3, f"2026-09-27T20:0{i}:00")


class TestTakes(unittest.TestCase):
    def test_clean_night_passes(self):
        with TemporaryDirectory() as t:
            root = Path(t); clean_night(root)
            rows = load_takes(root)
            self.assertEqual(len(rows), 6)
            self.assertTrue(all(r["source"] == "recorded" for r in rows))
            grid = split_grid(rows)
            self.assertEqual(grid[("2026-09-27#d1", "pinch")], {"train": 1, "test": 0})
            self.assertEqual(find_leaks(grid), [])
            self.assertEqual(redon_issues(rows), [])
            self.assertEqual(main(["takes-check", "--root", t]), 0)

    def test_must_fail_redon_too_fast(self):
        # 2026-09-28 real pattern: validation started 17 s after the last train take.
        with TemporaryDirectory() as t:
            root = Path(t); clean_night(root)
            take(root, "train", "rub", 1, "2026-09-28T12:31:54")
            take(root, "validation", "rub", 2, "2026-09-28T12:32:11")
            kinds = [i["kind"] for i in redon_issues(load_takes(root))]
            self.assertIn("too_fast", kinds)
            self.assertEqual(main(["takes-check", "--root", t]), 1)

    def test_default_threshold_is_measured_redon(self):
        # Mako's real re-wear took ~40 s: a 40 s switch passes, a 25 s one does not.
        with TemporaryDirectory() as t:
            root = Path(t)
            take(root, "train", "fist", 1, "2026-09-27T18:00:00")
            take(root, "validation", "fist", 2, "2026-09-27T18:00:40")
            self.assertEqual(redon_issues(load_takes(root)), [])
            take(root, "test", "fist", 3, "2026-09-27T18:01:05")
            self.assertEqual([i["kind"] for i in redon_issues(load_takes(root))], ["too_fast"])

    def test_must_fail_donning_revisited(self):
        # 2026-09-27 real pattern: more validation (d2) after test (d3).
        with TemporaryDirectory() as t:
            root = Path(t); clean_night(root)
            take(root, "validation", "snap", 2, "2026-09-27T21:33:07")
            issues = redon_issues(load_takes(root))
            self.assertEqual([i["kind"] for i in issues], ["revisited"])
            self.assertEqual(main(["takes-check", "--root", t]), 1)

    def test_counter_restarts_each_night(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            take(root, "train", "fist", 1, "2026-09-27T18:00:00")
            take(root, "test", "fist", 1, "2026-09-28T18:00:00")
            grid = split_grid(load_takes(root))
            self.assertEqual(set(grid), {("2026-09-27#d1", "fist"), ("2026-09-28#d1", "fist")})
            self.assertEqual(find_leaks(grid), [])

    def test_same_night_same_counter_across_splits_leaks(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            take(root, "train", "snap", 1, "2026-09-27T18:00:00")
            take(root, "test", "snap", 1, "2026-09-27T18:05:00")
            self.assertEqual(find_leaks(split_grid(load_takes(root))), [("2026-09-27#d1", "snap")])

    def test_rejected_and_empty(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            take(root / "rejected", "train", "rest", 1, "2026-09-27T18:00:00")
            with self.assertRaises(ValueError):
                load_takes(root)
            self.assertEqual(main(["takes-check", "--root", t]), 2)


if __name__ == "__main__":
    unittest.main()
