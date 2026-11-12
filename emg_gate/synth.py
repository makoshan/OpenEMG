"""Synthetic signal generator for testing and demo.

Scenarios: rest, light, hard, lead_off, poor_contact, line_noise, clip
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


def generate(
    scenario: str,
    *,
    fs: float = 500.0,
    duration_s: float = 2.0,
    seed: int = 42,
) -> Tuple[np.ndarray, str]:
    """Generate synthetic sEMG signal for given scenario.
    
    Returns:
        raw_uV: synthetic signal in microvolts
        forced_quality: quality label to force for this scenario
    """
    rng = np.random.RandomState(seed)
    n = int(fs * duration_s)
    t = np.arange(n) / fs

    if scenario == "rest":
        noise = rng.randn(n) * 5.0
        baseline = 10.0 * np.sin(2.0 * np.pi * 0.5 * t)
        raw_uV = baseline + noise
        forced_quality = None

    elif scenario == "light":
        emg_bursts = 50.0 * rng.randn(n) * (0.3 + 0.7 * np.sin(2.0 * np.pi * 2.0 * t) ** 2)
        noise = rng.randn(n) * 8.0
        raw_uV = emg_bursts + noise
        forced_quality = None

    elif scenario == "hard":
        emg_bursts = 120.0 * rng.randn(n) * (0.5 + 0.5 * np.sin(2.0 * np.pi * 3.0 * t) ** 2)
        noise = rng.randn(n) * 10.0
        raw_uV = emg_bursts + noise
        forced_quality = None

    elif scenario == "lead_off" or scenario == "lead_off_neg":
        raw_uV = rng.randn(n) * 2.0
        forced_quality = "lead_off"

    elif scenario == "poor_contact":
        base = 30.0 * rng.randn(n)
        drift = 100.0 * np.sin(2.0 * np.pi * 0.3 * t)
        dropouts = np.where(rng.rand(n) < 0.05, 0.0, 1.0)
        raw_uV = (base + drift) * dropouts
        forced_quality = "poor_contact"

    elif scenario == "line_noise":
        emg = 40.0 * rng.randn(n) * (0.3 + 0.7 * np.sin(2.0 * np.pi * 1.5 * t) ** 2)
        line = 200.0 * np.sin(2.0 * np.pi * 50.0 * t)
        noise = rng.randn(n) * 10.0
        raw_uV = emg + line + noise
        forced_quality = "line_noise"

    elif scenario == "clip":
        emg = 300.0 * rng.randn(n) * (0.5 + 0.5 * np.sin(2.0 * np.pi * 2.0 * t) ** 2)
        raw_uV = np.clip(emg, -4500.0, 4500.0)
        forced_quality = "clip"

    elif scenario == "confirm_pulse":
        base_rest = rng.randn(n) * 8.0
        pulse_width = int(0.3 * fs)
        pulse_start = n // 2 - pulse_width // 2
        pulse_end = pulse_start + pulse_width
        base_rest[pulse_start:pulse_end] += 60.0 * rng.randn(pulse_width)
        raw_uV = base_rest
        forced_quality = None

    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    return raw_uV, forced_quality
