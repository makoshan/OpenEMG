"""Full DSP pipeline: raw → gate events + frames.

Integrates filters, quality, gate logic.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np

from . import CHAIN_VERSION, SCHEMA_VERSION
from . import filters as F
from . import gate as G
from . import quality as Q


def run_pipeline(
    raw_uV: np.ndarray,
    *,
    fs: float = 500.0,
    window_ms: float = 200.0,
    hop_ms: float = 50.0,
    hpf_hz: float = 20.0,
    notch_hz: float = 50.0,
    notch_mode: str = "auto",
    envelope: str = "rms",
    th_loose_max: float = 0.15,
    th_hard_min: float = 0.40,
    norm_scale_uV: float = 200.0,
    enable_delta2: bool = False,
    forced_quality: Optional[str] = None,
    t0_host_ms: Optional[float] = None,
    save_raw: bool = False,
) -> Dict[str, Any]:
    """Execute default chain; return frames + events (no cloud upload)."""
    raw_uV = np.asarray(raw_uV, dtype=np.float64)
    if t0_host_ms is None:
        t0_host_ms = time.time() * 1000.0

    debiased, dc = F.debias(raw_uV)
    hp = F.highpass(debiased, fs, fc=hpf_hz)

    stream_q = Q.assess_quality(raw_uV, fs, line_hz=notch_hz, forced=forced_quality)
    # The notch only sits on the fundamental, so only a 50 Hz hit turns it on;
    # a harmonic-only hit still marks windows line_noise and blocks authorize.
    use_notch = notch_mode == "always" or (
        notch_mode == "auto"
        and stream_q == Q.QUALITY_LINE_NOISE
        and Q.detect_line_noise(raw_uV, fs, line_hz=notch_hz, max_harmonic=1)
    )
    filt = F.notch50(hp, fs, f0=notch_hz) if use_notch else hp
    rect = F.rectify(filt)

    if envelope == "ma":
        env, t_rel_ms = F.envelope_ma(rect, fs, window_ms, hop_ms)
    else:
        env, t_rel_ms = F.envelope_rms(rect, fs, window_ms, hop_ms)

    qualities = Q.per_window_quality(
        raw_uV, fs, window_ms, hop_ms, line_hz=notch_hz, forced=forced_quality
    )
    n = len(env)
    qualities = (qualities + [stream_q] * n)[:n]
    t_host = t0_host_ms + t_rel_ms

    events = G.gate_hops(
        env,
        qualities,
        th_loose_max=th_loose_max,
        th_hard_min=th_hard_min,
        norm_scale_uV=norm_scale_uV,
        t_host_ms=t_host,
    )

    delta2_feat = None
    if enable_delta2:
        delta2_feat = F.delta2_energy(hp, fs, window_ms, hop_ms)
        if len(delta2_feat) > n:
            delta2_feat = delta2_feat[:n]
        elif len(delta2_feat) < n:
            pad = np.zeros(n - len(delta2_feat))
            delta2_feat = np.concatenate([delta2_feat, pad])

    frames: List[Dict[str, Any]] = []
    for i, ev in enumerate(events):
        frame: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "chain_version": CHAIN_VERSION,
            "fs": fs,
            "window_ms": window_ms,
            "hop_ms": hop_ms,
            "hop_index": i,
            "t_host_ms": ev["t_host_ms"],
            "t_rel_ms": float(t_rel_ms[i]),
            "band": ev["band"],
            "confidence": ev["confidence"],
            "quality": ev["quality"],
            "norm": ev["norm"],
            "env": ev["env"],
            "dc_offset_uV": dc,
            "notch_applied": use_notch,
            "event_suppressed": ev["event_suppressed"],
            "authorize": ev["authorize"],
        }
        if enable_delta2 and delta2_feat is not None:
            frame["features"] = {"delta2_energy": float(delta2_feat[i])}
        if save_raw:
            win = max(1, int(round(window_ms * fs / 1000.0)))
            hop = max(1, int(round(hop_ms * fs / 1000.0)))
            start = i * hop
            frame["raw_uV"] = raw_uV[start : start + win].tolist()
        frames.append(frame)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "chain_version": CHAIN_VERSION,
        "fs": fs,
        "window_ms": window_ms,
        "hop_ms": hop_ms,
        "n_samples": int(len(raw_uV)),
        "n_hops": n,
        "dc_offset_uV": dc,
        "notch_mode": notch_mode,
        "notch_applied": use_notch,
        "stream_quality": stream_q,
        "enable_delta2": enable_delta2,
        "save_raw": save_raw,
        "th_loose_max": th_loose_max,
        "th_hard_min": th_hard_min,
        "band_histogram": _hist([e["band"] for e in events]),
        "quality_histogram": _hist([e["quality"] for e in events]),
        "authorize_count": sum(1 for e in events if e["authorize"]),
        "suppressed_count": sum(1 for e in events if e["event_suppressed"]),
        "majority_band": _majority([e["band"] for e in events]),
    }
    return {"summary": summary, "events": events, "frames": frames}


def _hist(vals: List[Any]) -> Dict[str, int]:
    h: Dict[str, int] = {}
    for v in vals:
        k = str(v)
        h[k] = h.get(k, 0) + 1
    return h


def _majority(bands: List[int]) -> Optional[int]:
    if not bands:
        return None
    if len(bands) >= 5:
        mid = bands[len(bands) // 5 : -len(bands) // 5 or None]
    else:
        mid = bands
    counts = _hist(mid)
    return int(max(counts.items(), key=lambda kv: kv[1])[0])
