"""Quality detection: lead_off, poor_contact, line_noise, clip, artifact_suspect.

Heuristic detectors for synthetic and real streams.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np


QUALITY_OK = "ok"
QUALITY_LEAD_OFF = "lead_off"
QUALITY_POOR_CONTACT = "poor_contact"
QUALITY_LINE_NOISE = "line_noise"
QUALITY_CLIP = "clip"
QUALITY_ARTIFACT = "artifact_suspect"

SUPPRESS_GREEN = frozenset({QUALITY_LEAD_OFF, QUALITY_POOR_CONTACT, QUALITY_CLIP})

# CaptureSession.quality flag name → label, in priority order (worst first).
_FLAG_PRIORITY = (
    ("clip", QUALITY_CLIP),
    ("lead_off", QUALITY_LEAD_OFF),
    ("poor_contact", QUALITY_POOR_CONTACT),
    ("line_noise", QUALITY_LINE_NOISE),
    ("artifact_suspect", QUALITY_ARTIFACT),
)


def quality_flags_to_label(flags: Dict[str, object]) -> str:
    """Collapse CaptureSession.quality flags into the single gate label."""
    for flag, label in _FLAG_PRIORITY:
        if flags.get(flag) is True:
            return label
    return QUALITY_OK


def quality_label_to_flags(label: str, snr_hint: Optional[float] = None) -> Dict[str, object]:
    """Inverse of quality_flags_to_label; all-false for 'ok'."""
    flags: Dict[str, object] = {flag: (lbl == label) for flag, lbl in _FLAG_PRIORITY}
    if snr_hint is not None:
        flags["snr_hint"] = snr_hint
    return flags


def detect_clip(raw_uV: np.ndarray, clip_uV: float = 4500.0, frac: float = 0.02) -> bool:
    """ADC/AFE saturation: fraction of samples near rail."""
    if len(raw_uV) == 0:
        return False
    return float(np.mean(np.abs(raw_uV) >= clip_uV)) >= frac


def detect_lead_off(
    raw_uV: np.ndarray,
    amp_uV_max: float = 8.0,
    var_uV2_max: float = 25.0,
) -> bool:
    """Near-flat/near-zero: electrode disconnected."""
    if len(raw_uV) == 0:
        return True
    rms = float(np.sqrt(np.mean(raw_uV.astype(np.float64) ** 2)))
    var = float(np.var(raw_uV.astype(np.float64)))
    return rms < amp_uV_max and var < var_uV2_max


def detect_poor_contact(
    raw_uV: np.ndarray,
    fs: float,
    baseline_drift_uV: float = 80.0,
    burst_ratio: float = 4.0,
) -> bool:
    """Unstable baseline / intermittent dropouts (heuristic)."""
    if len(raw_uV) < int(fs * 0.2):
        return False
    x = raw_uV.astype(np.float64)

    win = max(1, int(fs * 0.1))
    kernel = np.ones(win) / win
    slow = np.convolve(x, kernel, mode="same")
    drift = float(np.std(slow))

    hop = max(1, win // 2)
    rms_short = []
    for i in range(0, len(x) - win + 1, hop):
        seg = x[i : i + win]
        rms_short.append(float(np.sqrt(np.mean(seg * seg))))
    if not rms_short:
        return False

    med = float(np.median(rms_short)) + 1e-9
    peak = float(np.max(rms_short))
    return drift > baseline_drift_uV or (peak / med) > burst_ratio and med < 30.0


# Neighbour bins either side of each mains harmonic. With 200 ms at 500 Hz the
# Hann main lobe is ±10 Hz, so the nearest neighbour sits on its first null.
LINE_NEIGHBOR_OFFSETS_HZ = (10.0, 15.0, 20.0, 25.0)
LINE_SNR_RATIO_MIN = 8.0


def detect_line_noise(
    raw_uV: np.ndarray,
    fs: float,
    line_hz: float = 50.0,
    snr_ratio_min: float = LINE_SNR_RATIO_MIN,
    max_harmonic: Optional[int] = None,
) -> bool:
    """Mains fundamental or any harmonic dominates its neighbours (DFT bin check).

    Harmonics are checked up to Nyquist (or ``max_harmonic``): 100 Hz without a
    50 Hz fundamental (full-wave rectified loads) inflates the envelope just the
    same, and a 50 Hz-only check let rest windows through as light/hard.
    """
    n = len(raw_uV)
    if n < int(fs * 0.2) or line_hz <= 0:
        return False

    x = np.asarray(raw_uV, dtype=np.float64)
    idx = np.arange(n, dtype=np.float64)
    slope, intercept = np.polyfit(idx, x, 1)
    x = x - (slope * idx + intercept)
    w = 0.5 - 0.5 * np.cos(2.0 * np.pi * idx / max(n - 1, 1))
    xw = x * w
    t = idx / fs

    def bin_power(freqs: np.ndarray) -> np.ndarray:
        spec = np.exp(-2j * np.pi * np.outer(freqs, t)) @ xw
        return np.abs(spec) ** 2

    top = max(LINE_NEIGHBOR_OFFSETS_HZ)
    h = 1
    while line_hz * h + top < fs / 2.0:
        if max_harmonic is not None and h > max_harmonic:
            break
        f0 = line_hz * h
        offsets = np.array(LINE_NEIGHBOR_OFFSETS_HZ)
        p = bin_power(np.concatenate(([f0], f0 - offsets, f0 + offsets)))
        if p[0] / (np.mean(p[1:]) + 1e-12) >= snr_ratio_min:
            return True
        h += 1
    return False


def assess_quality(
    raw_uV: np.ndarray,
    fs: float,
    clip_uV: float = 4500.0,
    line_hz: float = 50.0,
    forced: Optional[str] = None,
) -> str:
    """Priority: clip > lead_off > poor_contact > line_noise > ok."""
    if forced is not None:
        return forced
    if detect_clip(raw_uV, clip_uV=clip_uV):
        return QUALITY_CLIP
    if detect_lead_off(raw_uV):
        return QUALITY_LEAD_OFF
    if detect_poor_contact(raw_uV, fs):
        return QUALITY_POOR_CONTACT
    if detect_line_noise(raw_uV, fs, line_hz=line_hz):
        return QUALITY_LINE_NOISE
    return QUALITY_OK


def per_window_quality(
    raw_uV: np.ndarray,
    fs: float,
    window_ms: float,
    hop_ms: float,
    clip_uV: float = 4500.0,
    line_hz: float = 50.0,
    forced: Optional[str] = None,
) -> List[str]:
    """Quality label per envelope hop window."""
    if forced is not None:
        win = max(1, int(round(window_ms * fs / 1000.0)))
        hop = max(1, int(round(hop_ms * fs / 1000.0)))
        n = len(raw_uV)
        count = max(0, (n - win) // hop + 1)
        return [forced] * count

    win = max(1, int(round(window_ms * fs / 1000.0)))
    hop = max(1, int(round(hop_ms * fs / 1000.0)))
    n = len(raw_uV)
    out: List[str] = []
    for start in range(0, n - win + 1, hop):
        seg = raw_uV[start : start + win]
        out.append(assess_quality(seg, fs, clip_uV=clip_uV, line_hz=line_hz))
    return out
