"""Read takes saved by the watch capture service (127.0.0.1:8767) as split rows.

Layout written by tiny-ai-watch firmware/usb_emg.save: <root>/<split>/<label>/<stem>.json next
to <stem>.npz. Only the .json metadata is read; the raw .npz is never opened. Takes the service
refused live under <root>/rejected/ and are not read.

The service's `donning` is a per-night counter that the recording UI ties to the split
(train=1, validation=2, test=3), so on its own it does not prove the strap came off. Two checks
catch the gap between the counter and a real re-wear: a donning switch faster than a person can
take the strap off and put it back, and a switch back to a donning already used.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .capture_session import SOURCE_RECORDED

SPLITS = ("train", "validation", "test")
# Hardware knob: a real doff -> re-seat -> don took Mako about 40 s (2026-09-29); switches
# faster than 30 s cannot be a new placement. Slower ones pass even if the strap never came
# off, so a known no-re-wear switch above 30 s has to be written down by hand.
MIN_REDON_S = 30.0


def load_takes(root: Path) -> List[Dict[str, Any]]:
    root = Path(root)
    rows: List[Dict[str, Any]] = []
    for split in SPLITS:
        for meta in sorted((root / split).glob("*/*.json")):
            d = json.loads(meta.read_text(encoding="utf-8"))
            rows.append({
                "split": split,
                "gesture_label": d["label"],
                "held_out": split != "train",
                # The counter restarts every night; the date keeps two nights' "1" apart.
                "donning_id": f"{d['recordedAt'][:10]}#d{int(d['donning'])}",
                "recorded_at": d["recordedAt"],
                "source": SOURCE_RECORDED,
                "quality": {},  # saved takes already passed usb_emg.validate
                "file": str(meta.relative_to(root)),
            })
    if not rows:
        raise ValueError(f"no takes under {root}/{{{','.join(SPLITS)}}}/<label>/*.json")
    return rows


def redon_issues(rows: List[Dict[str, Any]], min_redon_s: float = MIN_REDON_S) -> List[Dict[str, Any]]:
    """Donning switches that cannot be a real re-wear, in recording order."""
    issues: List[Dict[str, Any]] = []
    seen = set()
    prev = None
    for row in sorted(rows, key=lambda r: r["recorded_at"]):
        d = row["donning_id"]
        if prev is not None and d != prev["donning_id"]:
            gap = (datetime.fromisoformat(row["recorded_at"])
                   - datetime.fromisoformat(prev["recorded_at"])).total_seconds()
            base = {"from": prev["donning_id"], "to": d, "at": row["recorded_at"], "gap_s": gap,
                    "from_split": prev["split"], "to_split": row["split"]}
            if d in seen:
                issues.append({"kind": "revisited", **base})
            elif gap < min_redon_s:
                issues.append({"kind": "too_fast", **base})
        seen.add(d)
        prev = row
    return issues
