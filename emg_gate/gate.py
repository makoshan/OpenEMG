"""Three-band gate logic: envelope → band 0/1/2 + confidence + quality suppression."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .quality import SUPPRESS_GREEN


def band_from_norm(norm: float, th_loose_max: float, th_hard_min: float) -> int:
    """band 0=rest, 1=light, 2=hard."""
    if norm < th_loose_max:
        return 0
    if norm < th_hard_min:
        return 1
    return 2


def confidence_from_norm(
    norm: float,
    band: int,
    th_loose_max: float,
    th_hard_min: float,
) -> float:
    """Distance-to-boundary heuristic in [0, 1]."""
    if band == 0:
        margin = th_loose_max - norm
        span = max(th_loose_max, 1e-6)
        c = 0.5 + 0.5 * np.clip(margin / span, 0.0, 1.0)
    elif band == 1:
        mid = 0.5 * (th_loose_max + th_hard_min)
        half = 0.5 * (th_hard_min - th_loose_max) + 1e-6
        c = 1.0 - abs(norm - mid) / half * 0.5
        c = float(np.clip(c, 0.35, 0.95))
    else:
        margin = norm - th_hard_min
        span = max(1.0 - th_hard_min, 1e-6)
        c = 0.55 + 0.45 * np.clip(margin / span, 0.0, 1.0)
    return float(np.clip(c, 0.0, 1.0))


def apply_quality_gate(
    band: int,
    confidence: float,
    quality: str,
    *,
    high_conf: float = 0.6,
) -> Dict[str, Any]:
    """Hard rule: lead_off/poor_contact/clip → force band=0, low conf, suppress authorize."""
    event_suppressed = False
    out_band = band
    out_conf = confidence

    if quality in SUPPRESS_GREEN:
        event_suppressed = True
        out_band = 0
        out_conf = min(confidence, 0.25)
    elif quality == "line_noise" and band >= 1:
        out_conf = min(confidence, 0.45)
        event_suppressed = True

    authorize = (out_band >= 1) and (out_conf >= high_conf) and (not event_suppressed)

    return {
        "band": int(out_band),
        "confidence": float(out_conf),
        "quality": quality,
        "event_suppressed": bool(event_suppressed),
        "authorize": bool(authorize),
    }


def gate_hops(
    env: np.ndarray,
    qualities: List[str],
    *,
    th_loose_max: float,
    th_hard_min: float,
    norm_scale_uV: float,
    t_host_ms: Optional[np.ndarray] = None,
    high_conf: float = 0.6,
) -> List[Dict[str, Any]]:
    """Map each hop envelope to gated event fields."""
    scale = max(norm_scale_uV, 1e-9)
    events: List[Dict[str, Any]] = []

    for i, e in enumerate(env):
        norm = float(np.clip(e / scale, 0.0, 1.0))
        raw_band = band_from_norm(norm, th_loose_max, th_hard_min)
        raw_conf = confidence_from_norm(norm, raw_band, th_loose_max, th_hard_min)
        q = qualities[i] if i < len(qualities) else "ok"
        gated = apply_quality_gate(raw_band, raw_conf, q, high_conf=high_conf)

        ev = {
            "hop_index": i,
            "env": float(e),
            "norm": norm,
            "band_raw": raw_band,
            **gated,
        }
        if t_host_ms is not None and i < len(t_host_ms):
            ev["t_host_ms"] = float(t_host_ms[i])
        events.append(ev)

    return events
