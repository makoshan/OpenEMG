"""authorize-smoke: run a committed CalibrationProfile against synthetic scenarios.

Pass criteria (ADR sEMG §6 冲突序: 三档可分 + 松脱不假绿):
  - rest → majority band 0, light → 1, hard → 2
  - lead_off / poor_contact / clip → authorize_count == 0 (no false green)

Pure local; no cloud, no LLM. Exit non-zero on any failure.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .pipeline import run_pipeline
from .synth import generate

EXPECTED_BAND = {"rest": 0, "light": 1, "hard": 2}
MUST_NOT_AUTHORIZE = ("lead_off", "poor_contact", "clip")


def authorize_smoke(
    profile: Dict[str, Any],
    *,
    fs: float = 500.0,
    duration_s: float = 2.0,
    seed: int = 11,
) -> Dict[str, Any]:
    th_loose = profile["thresholds"]["th_loose_max"]
    th_hard = profile["thresholds"]["th_hard_min"]
    debug = profile.get("calibration_debug", {})
    norm_scale = float(debug.get("norm_scale_uV", 200.0))

    rows: List[Dict[str, Any]] = []
    ok = True
    for i, scenario in enumerate(list(EXPECTED_BAND) + list(MUST_NOT_AUTHORIZE)):
        raw_uV, forced_q = generate(scenario, fs=fs, duration_s=duration_s, seed=seed + i)
        result = run_pipeline(
            raw_uV,
            fs=fs,
            th_loose_max=th_loose,
            th_hard_min=th_hard,
            norm_scale_uV=norm_scale,
            forced_quality=forced_q,
        )
        s = result["summary"]
        if scenario in EXPECTED_BAND:
            passed = s["majority_band"] == EXPECTED_BAND[scenario]
            criterion = f"majority_band == {EXPECTED_BAND[scenario]}"
        else:
            passed = s["authorize_count"] == 0 and (s["majority_band"] in (None, 0))
            criterion = "authorize_count == 0 and band 0"
        ok = ok and passed
        rows.append(
            {
                "scenario": scenario,
                "criterion": criterion,
                "majority_band": s["majority_band"],
                "authorize_count": s["authorize_count"],
                "suppressed_count": s["suppressed_count"],
                "n_hops": s["n_hops"],
                "pass": passed,
            }
        )

    return {
        "thresholds": {"th_loose_max": th_loose, "th_hard_min": th_hard},
        "profile_stale": bool(profile.get("stale", False)),
        "rows": rows,
        "pass": ok and not profile.get("stale", False),
    }


def format_smoke_report(report: Dict[str, Any]) -> str:
    t = report["thresholds"]
    lines = [
        f"authorize-smoke  th_loose_max={t['th_loose_max']:.3f}  th_hard_min={t['th_hard_min']:.3f}"
        + ("  [STALE PROFILE]" if report["profile_stale"] else ""),
        f"{'scenario':<14}{'band':>5}{'auth':>6}{'suppr':>7}{'hops':>6}  result  criterion",
    ]
    for r in report["rows"]:
        lines.append(
            f"{r['scenario']:<14}{str(r['majority_band']):>5}{r['authorize_count']:>6}"
            f"{r['suppressed_count']:>7}{r['n_hops']:>6}  {'PASS' if r['pass'] else 'FAIL':<6}  {r['criterion']}"
        )
    lines.append(f"overall: {'PASS' if report['pass'] else 'FAIL'}")
    return "\n".join(lines)
