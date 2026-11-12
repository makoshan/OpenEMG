"""Synthetic end-to-end run of the commons: packs → bundles → ledger → snapshot → model → gate.

Proves the mechanics only. Every row is source=synthetic, so a release made
here is stamped evidence_grade=synthetic and says nothing about real wearers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .commons_bundle import build_bundle, default_hardware
from .commons_ledger import Commons
from .commons_model import gate_model, release_model, train_generic
from .demo_pack import build_demo_pack


def build_contributor(work: Path, i: int, hardware: Dict[str, Any], *, seconds: float, swap: bool = False) -> Path:
    pack = work / f"pack_{i:02d}"
    build_demo_pack(pack, user_id=f"demo_{i}", device_id=f"ads_{i}", seconds_per_gesture=seconds,
                    seed=100 + 10 * i, swap_rest_hard=swap)
    out = work / f"bundle_{i:02d}"
    build_bundle(pack, out, hardware, granted_on="2026-09-29")
    return out


def run_demo(
    root: Path,
    work: Path,
    *,
    contributors: int = 4,
    seconds: float = 16.0,
    poisoned: int = 0,
    policy: Optional[Dict[str, Any]] = None,
    release: bool = True,
) -> Dict[str, Any]:
    hw = default_hardware(board_rev="demo", firmware_build="demo")
    commons = Commons.init(root, hw, policy=policy)
    for i in range(contributors + poisoned):
        commons.contribute(build_contributor(work, i, hw, seconds=seconds, swap=i >= contributors))
    snap = commons.snapshot()
    card = train_generic(commons, snap["snapshot_id"])
    gate = gate_model(commons, card)
    out = {"snapshot": snap["snapshot_id"], "train": snap["train"], "test": snap["test"], "card": card, "gate": gate}
    if release and gate["verdict"] == "pass":
        out["release"] = release_model(commons, card)
    return out
