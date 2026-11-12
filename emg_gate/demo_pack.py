"""Build a synthetic P0 session pack by running synth streams through the chain.

Used by the CLI (`session demo-pack`), the checklist evidence, and tests.
The `omit_*` switches produce must-fail samples for the checklist.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .capture_session import (
    GESTURE_HARD,
    GESTURE_LEAD_OFF_NEG,
    GESTURE_LIGHT,
    GESTURE_REST,
    CaptureSessionError,
)
from .pipeline import run_pipeline
from .quality import quality_label_to_flags
from .session_store import SessionPack
from .synth import generate

_SCENARIO_FOR_GESTURE = {
    GESTURE_REST: "rest",
    GESTURE_LIGHT: "light",
    GESTURE_HARD: "hard",
    GESTURE_LEAD_OFF_NEG: "lead_off",
}
_SWAPPED = {GESTURE_REST: "hard", GESTURE_HARD: "rest"}


def append_stream_as_windows(
    pack: SessionPack,
    session_id: str,
    *,
    gesture_label: str,
    fs: float,
    seconds: float,
    seed: int,
    t0_device_ms: float,
    t0_host_ms: float,
    window_ms: float = 200.0,
    hop_ms: float = 50.0,
    include_raw: bool = False,
    posture_tag: Optional[str] = None,
    scenario: Optional[str] = None,
) -> Dict[str, int]:
    """Run one synthetic stream through the chain and append each hop as a window.

    Windows the protocol rejects (positive gesture with lead_off/clip set by
    the detector) are NOT persisted; they are counted in ``rejected`` exactly
    like a capture app would report them. ``scenario`` overrides the signal
    behind the label (commons must-fail sample: a contributor with swapped labels).
    """
    scenario = scenario or _SCENARIO_FOR_GESTURE[gesture_label]
    raw_uV, forced_q = generate(scenario, fs=fs, duration_s=seconds, seed=seed)
    result = run_pipeline(
        raw_uV,
        fs=fs,
        window_ms=window_ms,
        hop_ms=hop_ms,
        forced_quality=forced_q,
        t0_host_ms=t0_host_ms,
        save_raw=include_raw,
    )
    stored = 0
    rejected = 0
    for frame in result["frames"]:
        flags = quality_label_to_flags(frame["quality"])
        try:
            pack.append_window(
                session_id,
                gesture_label=gesture_label,
                quality=flags,
                obs_ts_device_ms=t0_device_ms + frame["t_rel_ms"],
                obs_ts_host_ms=frame["t_host_ms"],
                fs_hz=fs,
                window_ms=window_ms,
                feature_window={
                    "band": frame["band"],
                    "norm": frame["norm"],
                    "env": frame["env"],
                    "confidence": frame["confidence"],
                },
                raw_window=frame.get("raw_uV") if include_raw else None,
                context={"posture_tag": posture_tag} if posture_tag else None,
                source="synthetic",
            )
            stored += 1
        except CaptureSessionError:
            rejected += 1
    return {"stored": stored, "rejected": rejected}


def build_demo_pack(
    root: Path,
    *,
    user_id: str = "demo_user",
    device_id: str = "ads1292_demo",
    seconds_per_gesture: float = 10.0,
    fs: float = 500.0,
    seed: int = 7,
    donnings: int = 2,
    held_out_redon: bool = True,
    omit_lead_off_neg: bool = False,
    include_raw: bool = False,
    swap_rest_hard: bool = False,
) -> Dict[str, Any]:
    """Create a pack with `donnings` don/doff cycles.

    Donning 1..N-1: rest/light/hard(/lead_off_neg) training sessions.
    Last donning (if held_out_redon): the same gestures marked held_out=true.
    """
    pack = SessionPack.create(root, user_id=user_id, device_id=device_id)
    gestures: List[str] = [GESTURE_REST, GESTURE_LIGHT, GESTURE_HARD]
    if not omit_lead_off_neg:
        gestures.append(GESTURE_LEAD_OFF_NEG)
    postures = ["sit", "stand"]

    t_device = 1_000_000.0
    t_host = 1_790_000_000_000.0
    step_ms = seconds_per_gesture * 1000.0 + 1000.0
    sessions: List[Dict[str, Any]] = []
    k = 0
    for d in range(donnings):
        donning_id = pack.don(f"don_{d + 1:02d}")
        is_held_out = held_out_redon and d == donnings - 1 and donnings > 1
        for g in gestures:
            sid = pack.create_session(
                session_id=f"sess_{d + 1:02d}_{g}",
                held_out=is_held_out,
                context={"posture_tag": postures[d % len(postures)]},
            )
            counts = append_stream_as_windows(
                pack,
                sid,
                gesture_label=g,
                fs=fs,
                seconds=seconds_per_gesture,
                seed=seed + k,
                t0_device_ms=t_device,
                t0_host_ms=t_host,
                include_raw=include_raw,
                posture_tag=postures[d % len(postures)],
                scenario=_SWAPPED.get(g) if swap_rest_hard else None,
            )
            sessions.append(
                {
                    "session_id": sid,
                    "donning_id": donning_id,
                    "gesture": g,
                    "held_out": is_held_out,
                    "n_windows": counts["stored"],
                    "n_rejected": counts["rejected"],
                }
            )
            t_device += step_ms
            t_host += step_ms
            k += 1
        pack.doff()

    return {"root": str(pack.root), "sessions": sessions, "donnings": donnings}
