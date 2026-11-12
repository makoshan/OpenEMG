"""Data commons, part 3: train a shared model on a snapshot, gate it, release it.

The first shared model is deliberately small: one pair of force-band
thresholds (`emg_band_thresholds`), by default the median of every training
contributor's own fit (see fit_band_thresholds). Its job is "works on a new wearer before they
calibrate". Per-user self-calibration (calibrate.py) stays the baseline.

Gate (all must hold, nothing is taken from the card on trust):
- card matches the schema; ledger chain intact
- the snapshot is in the ledger, not stale (no withdrawn bundle), no
  contributor in both train and test, files unchanged
- re-training from the snapshot reproduces the card's parameters
- on every held-out contributor: false_green == 0 and accuracy >=
  policy.min_accuracy (worst contributor, not the mean)

Contributors the snapshot quarantined (clean windows not ordered
rest < light < hard) are named in the card's train.excluded; they are in
neither the fit nor the held-out evaluation. Synthetic snapshots can pass the gate, but the
release is stamped evidence_grade=synthetic: it proves the pipeline, not
that the model generalises to people.
"""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any, Dict, List

from . import SCHEMA_VERSION
from .calibrate import calibrate_from_sessions, evaluate_sessions
from .calibration_profile import create_calibration_profile, validate_calibration_profile
from .capture_session import GESTURE_LEAD_OFF_NEG
from .commons_attest import make_attestation
from .commons_bundle import CommonsError, canonical, is_clean, sha256_hex, write_json
from .commons_ledger import MODEL_LICENSE, Commons
from .jsonlite import errors as schema_errors
from .schemas import load_schema
from .session_store import SessionPack

KIND = "emg_band_thresholds"
PARAM_TOL = 1e-9


def _card_id(card: Dict[str, Any]) -> str:
    return "m_" + sha256_hex(canonical({k: v for k, v in card.items() if k != "model_id"}))[:16]


METHODS = ("median_of_contributors", "pooled")


def fit_band_thresholds(rows_by_contributor: Dict[str, List[Dict[str, Any]]], method: str) -> Dict[str, Any]:
    """Shared thresholds from each contributor's clean training windows.

    median_of_contributors (default): every contributor fits their own
    thresholds with the P1 recipe, the shared pair is the median across
    contributors. One person, one vote, however many windows they sent, and
    fewer than half of the contributors cannot drag the result arbitrarily
    far (scaled-but-ordered data, which the band-order check cannot see).
    Only per-person thresholds are needed, so this also works when windows
    never leave the contributor's machine.

    pooled: one fit over everybody's windows (v0.1 behaviour), kept for
    comparison; the contributor with the most windows weighs the most.
    """
    if method not in METHODS:
        raise CommonsError(f"unknown method {method!r}; use one of {METHODS}")
    kept = {c: [{**r, "held_out": False} for r in rows] for c, rows in sorted(rows_by_contributor.items()) if rows}
    if not kept:
        raise CommonsError("no clean training windows in this snapshot")
    skipped: List[Dict[str, str]] = []
    if method == "pooled":
        try:
            prof = calibrate_from_sessions([r for rows in kept.values() for r in rows], user_id="commons", device_id="commons")
        except ValueError as e:
            raise CommonsError(f"pooled fit failed: {e}") from e
        params = dict(prof["thresholds"])
    else:
        per: Dict[str, Dict[str, float]] = {}
        for c, rows in kept.items():
            try:
                per[c] = calibrate_from_sessions(rows, user_id="c", device_id="c")["thresholds"]
            except ValueError as e:
                skipped.append({"contributor": c, "reason": f"own fit failed: {e}"})
        if not per:
            raise CommonsError("no contributor has enough windows for their own fit")
        params = {k: float(statistics.median(p[k] for p in per.values())) for k in ("th_loose_max", "th_hard_min")}
        if not params["th_loose_max"] < params["th_hard_min"]:
            raise CommonsError(f"median thresholds out of order: {params}")
    # Same negative check as P1: no clean lead-off window may reach band 1 with the shared thresholds.
    leaks = sum(
        1 for rows in kept.values() for r in rows
        if r["gesture_label"] == GESTURE_LEAD_OFF_NEG and r["feature_window"]["norm"] >= params["th_loose_max"]
    )
    if leaks:
        raise CommonsError(f"shared thresholds let {leaks} clean lead_off_neg windows through; refuse")
    return {"params": params, "n_windows": sum(len(r) for r in kept.values()), "skipped": skipped}


def train_generic(commons: Commons, snapshot_id: str, *, method: str = "median_of_contributors") -> Dict[str, Any]:
    snap = commons.load_snapshot(snapshot_id)
    train_rows, _ = commons.snapshot_rows(snapshot_id)
    by_c: Dict[str, List[Dict[str, Any]]] = {c: [] for c in snap["train"]}
    for r in train_rows:
        by_c[r["contributor"]].append(r)
    fit = fit_band_thresholds(by_c, method)
    card = {
        "schema_version": SCHEMA_VERSION,
        "model_id": "",
        "kind": KIND,
        "snapshot_id": snapshot_id,
        "pool_key": snap["pool_key"],
        "source": snap["source"],
        "params": fit["params"],
        "train": {
            "method": method,
            "n_contributors": len(snap["train"]) - len(fit["skipped"]),
            "n_windows": fit["n_windows"],
            "excluded": snap["quarantined"] + fit["skipped"],
        },
        "license": MODEL_LICENSE,
    }
    card["model_id"] = _card_id(card)
    return card


def _accuracy(ev: Dict[str, Any]) -> float:
    n = sum(b["n"] for b in ev["per_gesture"].values())
    return (sum(b["correct"] for b in ev["per_gesture"].values()) / n) if n else float("nan")


def _eval_contributor(params: Dict[str, float], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    prof = {"thresholds": params}
    clean = [r for r in rows if is_clean(r)]
    ev_clean = evaluate_sessions(prof, clean, held_out_only=False)
    ev_all = evaluate_sessions(prof, rows, held_out_only=False)
    out: Dict[str, Any] = {
        "n_clean": ev_clean["n_windows"],
        "accuracy": round(_accuracy(ev_clean), 4),
        "false_green": ev_all["false_green"],
        "own_calibration": None,
    }
    # Baseline: the same person's self-calibration, scored on their own re-worn (held_out) donning.
    held = [r for r in clean if r["held_out"]]
    try:
        own = calibrate_from_sessions(clean, user_id="own", device_id="own")
    except ValueError:
        own = None
    if own and held:
        out["own_calibration"] = {
            "n_held_out": len(held),
            "accuracy_own": round(_accuracy(evaluate_sessions(own, held, held_out_only=False)), 4),
            "accuracy_generic": round(_accuracy(evaluate_sessions(prof, held, held_out_only=False)), 4),
        }
    return out


def gate_model(commons: Commons, card: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any = None) -> bool:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    report: Dict[str, Any] = {"model_id": card.get("model_id"), "checks": checks, "per_contributor": {}}
    errs = schema_errors(load_schema("commons_model_card"), card)
    ok = check("card_schema", not errs, errs[:5])
    ok = check("card_id", ok and card["model_id"] == _card_id(card), "model_id must hash the card") and ok
    ledger_errs = commons.verify_ledger()
    ok = check("ledger_chain", not ledger_errs, ledger_errs[:5]) and ok
    if ok:
        snap_errs = commons.snapshot_issues(card["snapshot_id"])
        ok = check("snapshot_usable", not snap_errs, snap_errs) and ok
    if ok:
        snap = commons.load_snapshot(card["snapshot_id"])
        ok = check(
            "snapshot_matches_card",
            snap["pool_key"] == card["pool_key"] == commons.meta["pool_key"] and snap["source"] == card["source"],
            {"pool_key": snap["pool_key"], "source": snap["source"]},
        ) and ok
    if ok:
        again = train_generic(commons, card["snapshot_id"], method=card["train"]["method"])
        same = (
            all(abs(again["params"][k] - card["params"][k]) <= PARAM_TOL for k in card["params"])
            and again["train"] == card["train"]
        )
        ok = check("reproducible", same, {"retrained": again["params"], "card": card["params"]}) and ok
    if ok:
        _, test = commons.snapshot_rows(card["snapshot_id"])
        per = {c: _eval_contributor(card["params"], rows) for c, rows in sorted(test.items())}
        report["per_contributor"] = per
        fg = sum(p["false_green"] for p in per.values())
        worst = min((p["accuracy"] for p in per.values()), default=float("nan"))
        floor = commons.policy["min_accuracy"]
        check("held_out_contributors", len(per) >= 1, len(per))
        check("false_green_zero", fg == 0, fg)
        check("worst_contributor_accuracy", worst >= floor, {"worst": worst, "floor": floor})
    report["verdict"] = "pass" if all(c["ok"] for c in checks) else "fail"
    report["evidence_grade"] = card.get("source")
    return report


def release_model(commons: Commons, card: Dict[str, Any]) -> Dict[str, Any]:
    report = gate_model(commons, card)
    if report["verdict"] != "pass":
        failed = [c["name"] for c in report["checks"] if not c["ok"]]
        raise CommonsError(f"gate failed: {failed}")
    if card["model_id"] in commons.state()["models"]:
        raise CommonsError(f"model {card['model_id']} already released")
    record = {"card": card, "gate": report}
    write_json(commons.models_dir / f"{card['model_id']}.json", record)
    body = {
        "model_id": card["model_id"],
        "snapshot_id": card["snapshot_id"],
        "evidence_grade": report["evidence_grade"],
        "gate_sha256": sha256_hex(canonical(report)),
    }
    commons._append("model", body)
    return body


def status(commons: Commons) -> Dict[str, Any]:
    """Ledger summary; a released model whose snapshot went stale must be re-trained."""
    st = commons.state()
    models = {
        mid: {**m, "issues": commons.snapshot_issues(m["snapshot_id"])} for mid, m in sorted(st["models"].items())
    }
    return {
        "pool_key": commons.meta["pool_key"],
        "ledger_ok": not commons.verify_ledger(),
        "active_bundles": len(st["active"]),
        "contributors": len({b["contributor"] for b in st["active"].values()}),
        "withdrawn_bundles": len(st["withdrawn"]),
        "snapshots": sorted(st["snapshots"]),
        "models": models,
        "stale_models": sorted(m for m, v in models.items() if v["issues"]),
    }


# ---------- your own data: personal model and local evaluation ----------

PRIOR_WINDOWS = 600  # the shared model counts as ~30 s of your own clean windows (50 ms hop)


def _pack_rows(pack_root: Path) -> List[Dict[str, Any]]:
    rows = SessionPack.open(pack_root).load_windows()
    return [r for r in rows if "norm" in (r.get("feature_window") or {})]


def _score(params: Dict[str, float], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    prof = {"thresholds": params}
    clean = [r for r in rows if is_clean(r)]
    return {
        "n": len(clean),
        "accuracy": round(_accuracy(evaluate_sessions(prof, clean, held_out_only=False)), 4) if clean else None,
        "false_green": evaluate_sessions(prof, rows, held_out_only=False)["false_green"],
    }


def personalize(card: Dict[str, Any], pack_root: Path, *, prior_windows: int = PRIOR_WINDOWS) -> Dict[str, Any]:
    """Shared model as a prior + your own calibration windows, chosen on your own re-worn donning.

    Candidates: the shared thresholds, your own fit, and a blend weighted by how
    many clean calibration windows you have (n / (n + prior_windows)). The pick
    is the best accuracy on your held_out rows with false_green == 0; with no
    held_out rows the blend is returned and marked unvalidated. Runs locally;
    nothing is written outside the returned CalibrationProfile.
    """
    errs = schema_errors(load_schema("commons_model_card"), card)
    if errs:
        raise CommonsError("model card: " + "; ".join(errs))
    pack = SessionPack.open(pack_root)
    rows = _pack_rows(pack_root)
    fit_rows = [r for r in rows if not r.get("held_out") and is_clean(r)]
    held = [r for r in rows if r.get("held_out")]
    shared = dict(card["params"])
    candidates: Dict[str, Dict[str, float]] = {"shared": shared}
    try:
        own = calibrate_from_sessions(fit_rows, user_id="own", device_id="own")
        if own["calibration_debug"]["committed"]:
            candidates["own"] = dict(own["thresholds"])
    except ValueError:
        pass
    n = len(fit_rows)
    if "own" in candidates:
        w = n / (n + prior_windows)
        blend = {k: w * candidates["own"][k] + (1 - w) * shared[k] for k in shared}
        if blend["th_loose_max"] < blend["th_hard_min"]:
            candidates["blend"] = blend
    scores = {name: _score(p, held) for name, p in candidates.items()} if held else {}
    if scores:
        ok = [k for k in ("blend", "own", "shared") if k in scores and scores[k]["false_green"] == 0]
        if not ok:
            raise CommonsError("every candidate lets a lead-off window through on your held-out rows")
        pick = max(ok, key=lambda k: scores[k]["accuracy"])  # ties keep the earlier (blend first)
    else:
        pick = "blend" if "blend" in candidates else "shared"
    meta = pack.meta
    profile = create_calibration_profile(
        meta["user_id"], meta["device_id"],
        candidates[pick]["th_loose_max"], candidates[pick]["th_hard_min"],
    )
    profile["calibration_debug"] = {
        "committed": True,
        "personalized_from": card["model_id"],
        "picked": pick,
        "validated_on_held_out": bool(scores),
        "own_clean_windows": n,
        "prior_windows": prior_windows,
        "candidates": candidates,
        "held_out_scores": scores,
        "notes": "Personal profile. Built and kept on this machine; not part of any commons.",
    }
    validate_calibration_profile(profile)
    return profile


def attest_local(card: Dict[str, Any], pack_root: Path, ident: Dict[str, str], *, made_on: str) -> Dict[str, Any]:
    """Evaluate a shared model on your own held-out donning; sign only the numbers."""
    errs = schema_errors(load_schema("commons_model_card"), card)
    if errs or card["model_id"] != _card_id(card):
        raise CommonsError("model card is invalid or its model_id does not hash the card")
    rows = _pack_rows(pack_root)
    held = [r for r in rows if r.get("held_out")]
    if not any(is_clean(r) for r in held):
        raise CommonsError("no clean held_out windows in this pack; mark a re-worn session held_out first")
    shared = _score(card["params"], held)
    body: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "model_id": card["model_id"],
        "snapshot_id": card["snapshot_id"],
        "pool_key": card["pool_key"],
        "n_windows": shared["n"],
        "accuracy": shared["accuracy"],
        "false_green": shared["false_green"],
        "rows_sha256": sha256_hex(b"".join(canonical(r) + b"\n" for r in held)),
        "made_on": made_on,
    }
    try:
        own = calibrate_from_sessions([r for r in rows if is_clean(r)], user_id="own", device_id="own")
        body["accuracy_own"] = _score(own["thresholds"], held)["accuracy"]
    except ValueError:
        pass
    return make_attestation(ident, body)


def scoreboard(commons: Commons, model_id: str) -> Dict[str, Any]:
    """Aggregate attestations. Only 'backed' ones count: the signer has an active verified bundle here.

    'independent' = the signer was not in the model's training contributors, so
    the result is a real held-out person, not a re-test of training data.
    """
    st = commons.state()
    active_contributors = {b["contributor"] for b in st["active"].values()}
    train: List[str] = []
    atts = commons.attestations(model_id)
    if atts:
        try:
            train = commons.load_snapshot(atts[0]["snapshot_id"])["train"]
        except CommonsError:
            train = []
    rows = [
        {
            "contributor": a["contributor"],
            "accuracy": a["accuracy"],
            "accuracy_own": a.get("accuracy_own"),
            "false_green": a["false_green"],
            "n_windows": a["n_windows"],
            "backed": a["contributor"] in active_contributors,
            "independent": a["contributor"] not in train,
        }
        for a in atts
    ]
    counted = [r for r in rows if r["backed"]]
    indep = [r["accuracy"] for r in counted if r["independent"]]
    return {
        "model_id": model_id,
        "n_attestations": len(rows),
        "n_backed": len(counted),
        "n_independent": len(indep),
        "median_accuracy_independent": float(statistics.median(indep)) if indep else None,
        "worst_accuracy_independent": min(indep) if indep else None,
        "false_green_backed": sum(r["false_green"] for r in counted),
        "rows": rows,
    }
