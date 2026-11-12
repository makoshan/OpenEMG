"""DSP filter chain: DC removal, HPF, notch, rectify, envelope.

Pure numpy implementation (no scipy). Biquad IIR filters.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


def debias(x: np.ndarray) -> Tuple[np.ndarray, float]:
    """Remove DC offset."""
    x = np.asarray(x, dtype=np.float64)
    dc = float(np.mean(x))
    return x - dc, dc


def biquad_coeffs_highpass(fs: float, fc: float, q: float = 0.707) -> np.ndarray:
    """2nd-order Butterworth HPF biquad coefficients [b0, b1, b2, a0, a1, a2]."""
    w0 = 2.0 * np.pi * fc / fs
    alpha = np.sin(w0) / (2.0 * q)
    cos_w0 = np.cos(w0)

    b0 = (1.0 + cos_w0) / 2.0
    b1 = -(1.0 + cos_w0)
    b2 = (1.0 + cos_w0) / 2.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha

    return np.array([b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0])


def biquad_coeffs_notch(fs: float, f0: float, q: float = 30.0) -> np.ndarray:
    """2nd-order notch filter biquad coefficients."""
    w0 = 2.0 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2.0 * q)
    cos_w0 = np.cos(w0)

    b0 = 1.0
    b1 = -2.0 * cos_w0
    b2 = 1.0
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha

    return np.array([b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0])


def apply_biquad(x: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
    """Apply biquad IIR filter (Direct Form I)."""
    x = np.asarray(x, dtype=np.float64)
    b0, b1, b2, _, a1, a2 = coeffs
    y = np.zeros_like(x)
    x1, x2 = 0.0, 0.0
    y1, y2 = 0.0, 0.0

    for i in range(len(x)):
        y[i] = b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, x[i]
        y2, y1 = y1, y[i]

    return y


def highpass(x: np.ndarray, fs: float, fc: float = 20.0) -> np.ndarray:
    """HPF ≈20 Hz (2nd-order Butterworth)."""
    coeffs = biquad_coeffs_highpass(fs, fc, q=0.707)
    return apply_biquad(x, coeffs)


def notch50(x: np.ndarray, fs: float, f0: float = 50.0, q: float = 30.0) -> np.ndarray:
    """50 Hz notch filter."""
    coeffs = biquad_coeffs_notch(fs, f0, q=q)
    return apply_biquad(x, coeffs)


def rectify(x: np.ndarray) -> np.ndarray:
    """Full-wave rectification."""
    return np.abs(x)


def envelope_rms(
    x: np.ndarray, fs: float, window_ms: float, hop_ms: float
) -> Tuple[np.ndarray, np.ndarray]:
    """RMS envelope with overlapping windows.
    
    Returns:
        env: RMS values per window
        t_rel_ms: time offset in ms for each window center
    """
    x = np.asarray(x, dtype=np.float64)
    win = max(1, int(round(window_ms * fs / 1000.0)))
    hop = max(1, int(round(hop_ms * fs / 1000.0)))
    n_hops = max(0, (len(x) - win) // hop + 1)

    env = np.zeros(n_hops, dtype=np.float64)
    t_rel_ms = np.zeros(n_hops, dtype=np.float64)

    for i in range(n_hops):
        start = i * hop
        seg = x[start : start + win]
        env[i] = float(np.sqrt(np.mean(seg * seg)))
        t_rel_ms[i] = (start + win / 2.0) * 1000.0 / fs

    return env, t_rel_ms


def envelope_ma(
    x: np.ndarray, fs: float, window_ms: float, hop_ms: float
) -> Tuple[np.ndarray, np.ndarray]:
    """MAV (Mean Absolute Value) envelope."""
    x = np.asarray(x, dtype=np.float64)
    win = max(1, int(round(window_ms * fs / 1000.0)))
    hop = max(1, int(round(hop_ms * fs / 1000.0)))
    n_hops = max(0, (len(x) - win) // hop + 1)

    env = np.zeros(n_hops, dtype=np.float64)
    t_rel_ms = np.zeros(n_hops, dtype=np.float64)

    for i in range(n_hops):
        start = i * hop
        seg = x[start : start + win]
        env[i] = float(np.mean(np.abs(seg)))
        t_rel_ms[i] = (start + win / 2.0) * 1000.0 / fs

    return env, t_rel_ms


def delta2_energy(
    x: np.ndarray, fs: float, window_ms: float, hop_ms: float
) -> np.ndarray:
    """2nd-order difference energy (parallel feature, NOT HPF replacement)."""
    x = np.asarray(x, dtype=np.float64)
    # Δ²x[n] = x[n] - 2*x[n-1] + x[n-2]
    d2 = np.zeros(len(x), dtype=np.float64)
    if len(x) >= 3:
        d2[2:] = x[2:] - 2.0 * x[1:-1] + x[:-2]

    win = max(1, int(round(window_ms * fs / 1000.0)))
    hop = max(1, int(round(hop_ms * fs / 1000.0)))
    n_hops = max(0, (len(d2) - win) // hop + 1)

    energy = np.zeros(n_hops, dtype=np.float64)
    for i in range(n_hops):
        start = i * hop
        seg = d2[start : start + win]
        energy[i] = float(np.sum(seg * seg))

    return energy
