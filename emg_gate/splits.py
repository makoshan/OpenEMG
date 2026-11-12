"""Train/test split utilities for EMG session data.

ADR-2026-09-23-EMG §1: donning_id × gesture_label grid + leak detection + bad window removal.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .capture_session import GESTURE_LEAD_OFF_NEG, POSITIVE_GESTURES

# Five-class labels as the watch capture service saves them (takes.py); rest is already positive.
WATCH_GESTURES = frozenset({"pinch", "rub", "snap", "fist"})


def clean_windows(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove windows where quality flags indicate bad data.

    This is the single entry point for all training and export: only clean
    windows may enter the fit or the test set.
    
    Qualified = positive gesture with all flags false, or lead_off_neg with
    lead_off=true (and other flags false).
    """
    clean = []
    for sess in sessions:
        quality = sess.get("quality", {})
        if not isinstance(quality, dict):
            continue
        gesture = sess.get("gesture_label", "")
        
        # For lead_off_neg, lead_off=True is expected; check other flags
        if gesture == GESTURE_LEAD_OFF_NEG:
            if not quality.get("lead_off"):
                continue
            other_flags = {k: v for k, v in quality.items() if k not in ("lead_off", "snr_hint")}
            if any(other_flags.values()):
                continue
        # For positive gestures, all flags must be False
        elif gesture in POSITIVE_GESTURES | WATCH_GESTURES:
            flags = {k: v for k, v in quality.items() if k != "snr_hint"}
            if any(flags.values()):
                continue
        else:
            # Unknown gesture: skip
            continue
            
        clean.append(sess)
    return clean


def split_grid(sessions: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, int]]:
    """Count train and test windows per (donning_id, gesture_label) cell.

    Returns dict[(donning_id, gesture_label)] = {"train": n, "test": n}.
    Only clean windows (via clean_windows) are counted.
    """
    clean = clean_windows(sessions)
    grid: Dict[Tuple[str, str], Dict[str, int]] = {}
    for sess in clean:
        donning = sess.get("donning_id")
        gesture = sess.get("gesture_label")
        held_out = sess.get("held_out", False)
        if not donning or not gesture:
            continue
        key = (str(donning), str(gesture))
        if key not in grid:
            grid[key] = {"train": 0, "test": 0}
        if held_out:
            grid[key]["test"] += 1
        else:
            grid[key]["train"] += 1
    return grid


def find_leaks(grid: Dict[Tuple[str, str], Dict[str, int]]) -> List[Tuple[str, str]]:
    """Return (donning_id, gesture_label) cells where both train and test > 0."""
    leaks = []
    for (donning, gesture), counts in sorted(grid.items()):
        if counts["train"] > 0 and counts["test"] > 0:
            leaks.append((donning, gesture))
    return leaks
