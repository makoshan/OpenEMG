"""CLI entry point for EMG Gate P0+P1.

  run                 Run the chain on synthetic scenarios (frames/events/summary)
  session ...         P0 pack: create / don / doff / new / append / mark-held-out / demo-pack
  export              Export a pack (default strips raw; --include-raw is dev-only)
  cloud-safe-export   Export a pack as CloudSafeEvent rows (schema rejects raw)
  checklist           P0 acceptance checklist on a pack (sat / unsat per item)
  calibrate           Commit a CalibrationProfile (synthetic or --from-pack); --rollback
  authorize-smoke     Run a committed profile against synthetic scenarios
  fuse                Late-fuse one IMU motion with one EMG RMS band (no training)
  split               Bucket a recording into IMU / force / five-class sets
  commons ...         Same-hardware data commons: bundle / verify / contribute / withdraw /
                      merge / export / verify-repo / git-sync / share / snapshot / train /
                      gate / release / status / personalize / attest / scoreboard

Everything is local. No upload code exists in this package; a commons is a
directory, and moving bundles between machines is up to the people involved.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from . import __version__
from .calibrate import (
    CalibrationCommitError,
    calibrate_from_sessions,
    calibrate_synth_demo,
    commit_profile,
    evaluate_profile,
    evaluate_sessions,
    load_profile,
    rollback_profile,
)
from .capture_session import CaptureSessionError, VALID_GESTURES
from .commons_bundle import (
    IDENTITY_FILE,
    CommonsError,
    build_bundle,
    default_hardware,
    load_or_create_identity,
    make_withdrawal,
    read_json,
    verify_bundle,
)
from .commons_demo import run_demo
from .commons_git import export_objects, git_sync, share, verify_repo
from .commons_ledger import Commons
from .commons_model import (
    attest_local,
    gate_model,
    personalize,
    release_model,
    scoreboard,
    status,
    train_generic,
)
from .checklist import ADR_MIN_SECONDS_PER_GESTURE, check_p0_acceptance, format_checklist_report
from .splits import find_leaks, split_grid
from .takes import MIN_REDON_S, load_takes, redon_issues
from .demo_pack import build_demo_pack
from .fusion import FusionError, fuse, fuse_pair
from .split_tracks import rows_from_platform_fixture, split_recording
from .pipeline import run_pipeline
from .quality import quality_label_to_flags
from .session_store import SessionPack, SessionPackError
from .smoke import authorize_smoke, format_smoke_report
from .synth import generate

SCENARIOS = ["rest", "light", "hard", "lead_off", "poor_contact", "line_noise", "clip", "confirm_pulse"]
QUALITY_LABELS = ["ok", "lead_off", "poor_contact", "line_noise", "clip", "artifact_suspect"]


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------- run ----------------


def cmd_run(args: argparse.Namespace) -> int:
    scenarios = SCENARIOS if args.scenario == "all" else [args.scenario]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for scenario in scenarios:
        raw_uV, forced_q = generate(scenario, fs=args.fs, duration_s=args.duration, seed=args.seed)
        result = run_pipeline(
            raw_uV,
            fs=args.fs,
            window_ms=args.window_ms,
            hop_ms=args.hop_ms,
            th_loose_max=args.th_loose,
            th_hard_min=args.th_hard,
            enable_delta2=args.enable_delta2,
            forced_quality=forced_q,
            save_raw=args.save_raw,
        )
        summary = result["summary"]
        write_jsonl(out_dir / f"frames_{scenario}.jsonl", result["frames"])
        write_jsonl(out_dir / f"events_{scenario}.jsonl", result["events"])
        write_json(out_dir / f"summary_{scenario}.json", summary)
        print(
            f"{scenario:<14} hops={summary['n_hops']:<4} majority_band={summary.get('majority_band')} "
            f"quality={summary['stream_quality']} authorize={summary['authorize_count']}"
        )
    print(f"\nOutput written to: {out_dir}")
    return 0


# ---------------- session ----------------


def cmd_session(args: argparse.Namespace) -> int:
    pack_dir = Path(args.pack)
    try:
        if args.session_cmd == "create":
            pack = SessionPack.create(pack_dir, user_id=args.user, device_id=args.device)
            print(f"pack created: {pack.root}")
            return 0

        if args.session_cmd == "demo-pack":
            info = build_demo_pack(
                pack_dir,
                seconds_per_gesture=args.seconds,
                donnings=args.donnings,
                held_out_redon=not args.no_held_out,
                omit_lead_off_neg=args.omit_lead_off_neg,
                include_raw=args.include_raw,
                seed=args.seed,
            )
            for s in info["sessions"]:
                flag = " held_out" if s["held_out"] else ""
                print(
                    f"  {s['session_id']:<24} {s['donning_id']:<8} {s['gesture']:<13} "
                    f"stored={s['n_windows']:<5} rejected={s['n_rejected']}{flag}"
                )
            print(f"demo pack: {info['root']}  donnings={info['donnings']}")
            return 0

        pack = SessionPack.open(pack_dir)
        if args.session_cmd == "don":
            print(f"donning_id: {pack.don(args.donning_id)}")
        elif args.session_cmd == "doff":
            ended = pack.doff()
            print(f"doffed: {ended}" if ended else "no active donning")
        elif args.session_cmd == "new":
            ctx = {"posture_tag": args.posture} if args.posture else None
            sid = pack.create_session(session_id=args.session_id, held_out=args.held_out, context=ctx)
            print(f"session_id: {sid}  donning_id: {pack.session_meta(sid)['donning_id']}")
        elif args.session_cmd == "append":
            quality = json.loads(args.quality_json) if args.quality_json else quality_label_to_flags(args.quality)
            feature = None
            if args.norm is not None:
                feature = {"norm": args.norm}
                if args.band is not None:
                    feature["band"] = args.band
            raw = json.loads(args.raw_json) if args.raw_json else None
            row = pack.append_window(
                args.session,
                gesture_label=args.gesture,
                quality=quality,
                obs_ts_device_ms=args.ts_device,
                obs_ts_host_ms=args.ts_host,
                fs_hz=args.fs,
                window_ms=args.window_ms,
                feature_window=feature,
                raw_window=raw,
            )
            print(f"appended: session={row['session_id']} gesture={row['gesture_label']} ts_device={row['obs_ts_device_ms']}")
        elif args.session_cmd == "mark-held-out":
            pack.mark_held_out(args.session, not args.off)
            print(f"{args.session}: held_out={not args.off}")
        else:
            return 1
        return 0
    except (SessionPackError, CaptureSessionError, json.JSONDecodeError) as exc:
        print(f"REJECTED: {exc}", file=sys.stderr)
        return 2


# ---------------- export / checklist ----------------


def cmd_export(args: argparse.Namespace) -> int:
    try:
        pack = SessionPack.open(Path(args.pack))
    except SessionPackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        info = pack.export(Path(args.out), include_raw=args.include_raw, mixed_ok=args.mixed_ok)
        print(json.dumps(info, ensure_ascii=False, indent=2))
        print(f"source_recorded={info['source_recorded']} source_synthetic={info['source_synthetic']}", file=sys.stderr)
        if args.include_raw:
            print("WARNING: raw_window included — developer export, local only, never upload.", file=sys.stderr)
        return 0
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


def cmd_cloud_safe_export(args: argparse.Namespace) -> int:
    try:
        pack = SessionPack.open(Path(args.pack))
    except SessionPackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    info = pack.export_cloud_safe(Path(args.out))
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print("all rows validated against CloudSafeEvent schema (no raw fields)")
    return 0


def cmd_checklist(args: argparse.Namespace) -> int:
    results = check_p0_acceptance(Path(args.pack), min_seconds_per_gesture=args.min_seconds)
    report = format_checklist_report(results)
    print(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report + "\n", encoding="utf-8")
        write_json(Path(args.out).with_suffix(".json"), results)
    return 0 if results["all_sat"] else 1


def cmd_takes_check(args: argparse.Namespace) -> int:
    try:
        rows = load_takes(Path(args.root))
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    grid = split_grid(rows)
    leaks = find_leaks(grid)
    issues = redon_issues(rows, args.min_redon_s)
    labels = sorted({g for _, g in grid})
    print(f"takes={len(rows)} source=recorded min_redon_s={args.min_redon_s:g}")
    print("| donning | " + " | ".join(labels) + " |")
    for d in sorted({d for d, _ in grid}):
        cells = []
        for g in labels:
            c = grid.get((d, g), {"train": 0, "test": 0})
            parts = [f"T{c['train']}"] * bool(c["train"]) + [f"H{c['test']}"] * bool(c["test"])
            cells.append("+".join(parts) or "·")
        print(f"| {d} | " + " | ".join(cells) + " |")
    for d, g in leaks:
        print(f"LEAK same cell in train and held-out: {d} {g}")
    for i in issues:
        print(f"REDON {i['kind']}: {i['from']}({i['from_split']}) -> {i['to']}({i['to_split']}) at {i['at']} gap {i['gap_s']:.0f}s")
    ok = not leaks and not issues
    print("PASS" if ok else "FAIL")
    if args.out:
        write_json(Path(args.out), {"takes": len(rows), "leaks": leaks, "redon_issues": issues,
                                    "grid": {f"{d}:{g}": c for (d, g), c in grid.items()}, "pass": ok})
    return 0 if ok else 1


# ---------------- calibrate / smoke ----------------


def cmd_calibrate(args: argparse.Namespace) -> int:
    out_path = Path(args.out)
    store_dir = Path(args.store_dir) if args.store_dir else out_path.parent / "profile_store"

    if args.rollback:
        try:
            prev = rollback_profile(out_path, store_dir)
        except Exception as exc:  # noqa: BLE001 - surface any rollback failure to the operator
            print(f"rollback failed: {exc}", file=sys.stderr)
            return 1
        if prev is None:
            print("no prev_profile_ref on the active profile; nothing to roll back")
            return 1
        print("rolled back to previous profile")
        _print_profile(prev)
        return 0

    try:
        if args.from_pack:
            pack = SessionPack.open(Path(args.from_pack))
            windows = pack.load_windows()
            profile = calibrate_from_sessions(
                windows,
                user_id=pack.meta["user_id"],
                device_id=pack.meta["device_id"],
                donning_id=args.donning_id,
            )
            profile = commit_profile(profile, out_path, store_dir)
            print(f"calibrated from pack ({profile['calibration_debug']['n_training_windows']} training windows, "
                  f"{profile['calibration_debug']['n_held_out_windows']} held_out windows excluded)")
            _print_profile(profile)
            report = evaluate_sessions(profile, windows, held_out_only=True)
            print("held_out evaluation (after commit, never part of fit):")
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if args.eval_out:
                write_json(Path(args.eval_out), report)
        elif args.against:
            if not args.sessions:
                print("error: --against requires --sessions", file=sys.stderr)
                return 1
            
            prev_profile = load_profile(Path(args.against))
            pack = SessionPack.open(Path(args.sessions))
            windows = pack.load_windows()
            
            new_profile = calibrate_from_sessions(
                windows,
                user_id=pack.meta["user_id"],
                device_id=pack.meta["device_id"],
                donning_id=args.donning_id,
            )
            new_profile = commit_profile(new_profile, out_path, store_dir)
            
            prev_eval = evaluate_profile(prev_profile, windows)
            new_eval = evaluate_profile(new_profile, windows)
            
            output = {
                "prev_profile": args.against,
                "prev_accuracy": prev_eval["accuracy"],
                "new_profile": str(out_path),
                "new_accuracy": new_eval["accuracy"],
                "accuracy_diff": new_eval["accuracy"] - prev_eval["accuracy"],
                "n_held_out": new_eval["n"],
            }
            print(json.dumps(output, ensure_ascii=False))
        else:
            profile = calibrate_synth_demo(
                out_path, fs=args.fs, duration_s=args.duration, seed=args.seed, store_dir=store_dir
            )
            print("calibrated from synthetic rest/light/hard (+ lead_off negatives)")
            _print_profile(profile)
    except (CalibrationCommitError, SessionPackError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1

    print(f"active profile: {out_path}\nstore: {store_dir}")
    return 0


def _print_profile(profile: Dict[str, Any]) -> None:
    th = profile["thresholds"]
    print(f"  th_loose_max: {th['th_loose_max']:.3f}")
    print(f"  th_hard_min:  {th['th_hard_min']:.3f}")
    print(f"  created_at:   {profile['created_at']}  stale={profile.get('stale', False)}")
    print(f"  prev_profile_ref: {profile.get('prev_profile_ref')}")
    debug = profile.get("calibration_debug", {})
    if "negatives_ok" in debug:
        print(f"  negatives_ok: {debug['negatives_ok']}  committed: {debug.get('committed')}")


def cmd_authorize_smoke(args: argparse.Namespace) -> int:
    try:
        profile = load_profile(Path(args.profile))
    except Exception as exc:  # noqa: BLE001 - any unreadable/invalid profile must fail the smoke
        print(f"cannot load profile: {exc}", file=sys.stderr)
        return 2
    report = authorize_smoke(profile, fs=args.fs, duration_s=args.duration, seed=args.seed)
    print(format_smoke_report(report))
    if args.out:
        write_json(Path(args.out), report)
    return 0 if report["pass"] else 1


def cmd_fuse(args: argparse.Namespace) -> int:
    if args.pair and (args.motion is not None or args.band is not None):
        print("pass either --pair or --motion/--band", file=sys.stderr)
        return 2
    try:
        if args.pair:
            decision = fuse_pair(json.loads(Path(args.pair).read_text(encoding="utf-8")))
        else:
            if args.motion is None or args.band is None:
                print("need --motion and --band, or --pair", file=sys.stderr)
                return 2
            decision = fuse(args.motion, args.band, args.quality, args.authorize)
    except (FusionError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(decision, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    if bool(args.src) == bool(args.fixture):
        print("pass exactly one of --in or --fixture", file=sys.stderr)
        return 2
    try:
        if args.fixture:
            doc = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
            rows = rows_from_platform_fixture(doc)
        else:
            text = Path(args.src).read_text(encoding="utf-8")
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        result = split_recording(
            rows,
            imu_labels=args.imu_labels,
            merge_punch_family=args.merge_punch_family,
        )
    except (FusionError, json.JSONDecodeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    out = Path(args.out)
    write_json(out / "imu_snapshot.json", result["imu_snapshot"])
    write_jsonl(out / "force_rows.jsonl", result["force_rows"])
    write_jsonl(out / "five_rows.jsonl", result["five_rows"])
    write_jsonl(out / "decisions.jsonl", result["decisions"])
    write_json(out / "report.json", result["report"])
    print(json.dumps(result["report"], ensure_ascii=False, sort_keys=True))
    if args.require_ready and not result["report"]["imu"]["train"]["ready"]:
        return 1
    return 0


# ---------------- commons ----------------


def _print(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_commons(args: argparse.Namespace) -> int:
    try:
        return _commons(args)
    except CommonsError as e:
        print(f"REJECTED: {e}", file=sys.stderr)
        return 2


def _commons(args: argparse.Namespace) -> int:
    c = args.commons_cmd
    if c == "hardware-template":
        write_json(Path(args.out), default_hardware())
        print(f"wrote {args.out}; fill board_rev / firmware_build and check every field against your build")
        return 0
    if c == "init":
        policy = json.loads(args.policy_json) if args.policy_json else None
        commons = Commons.init(Path(args.root), read_json(args.hardware), data_license=args.license, policy=policy)
        _print(commons.meta)
        return 0
    if c == "bundle":
        tiers = ["features", "raw"] if args.raw else ["features"]
        man = build_bundle(Path(args.pack), Path(args.out), read_json(args.hardware), tiers=tiers,
                           license=args.license, identity_path=Path(args.identity) if args.identity else None)
        _print({k: man[k] for k in ("bundle_id", "contributor", "pool_key", "source", "counts", "consent")})
        print(f"signing key stays in {args.identity or Path(args.pack) / IDENTITY_FILE}; never share it",
              file=sys.stderr)
        return 0
    if c == "share":
        rep = share(Path(args.pack), read_json(args.hardware), Path(args.root), Path(args.repo),
                    tiers=("features", "raw") if args.raw else ("features",), push=args.push,
                    identity_path=Path(args.identity) if args.identity else None)
        _print({k: rep[k] for k in ("bundle_id", "contributor", "added", "committed", "pushed")})
        return 0
    if c == "verify-repo":
        errs = verify_repo(Path(args.repo))
        _print({"ok": not errs, "errors": errs})
        return 0 if not errs else 1
    if c == "verify":
        pk = lic = None
        if args.root:
            meta = Commons.open(Path(args.root)).meta
            pk, lic = meta["pool_key"], meta["data_license"]
        rep = verify_bundle(Path(args.bundle), expected_pool_key=pk, expected_license=lic)
        _print({"ok": rep["ok"], "errors": rep["errors"], "n_rows": len(rep["rows"]),
                "bundle_id": (rep["manifest"] or {}).get("bundle_id")})
        return 0 if rep["ok"] else 1
    if c == "personalize":
        profile = personalize(read_json(args.model), Path(args.pack))
        write_json(Path(args.out), profile)
        _print({"picked": profile["calibration_debug"]["picked"], "thresholds": profile["thresholds"],
                "validated_on_held_out": profile["calibration_debug"]["validated_on_held_out"],
                "held_out_scores": profile["calibration_debug"]["held_out_scores"]})
        return 0
    commons = Commons.open(Path(args.root))
    if c == "contribute":
        _print(commons.contribute(Path(args.bundle)))
        return 0
    if c == "withdraw":
        if not Path(args.identity).exists():
            raise CommonsError(f"identity file {args.identity} not found")
        ident = load_or_create_identity(Path(args.identity))
        man_path = commons.bundles_dir / args.bundle_id / "manifest.json"
        if not man_path.exists():
            raise CommonsError(f"bundle {args.bundle_id} is not in this replica")
        notice = make_withdrawal(ident, read_json(man_path))
        if args.notice_out:
            write_json(Path(args.notice_out), notice)
        _print(commons.withdraw(notice))
        return 0
    if c == "export":
        _print(export_objects(commons, Path(args.to)))
        return 0
    if c == "git-sync":
        rep = git_sync(commons, Path(args.repo), push=args.push)
        _print(rep)
        return 0
    if c == "merge":
        _print(commons.merge(Path(args.from_root)))
        return 0
    if c == "attest":
        ident = load_or_create_identity(Path(args.identity or Path(args.pack) / IDENTITY_FILE))
        att = attest_local(read_json(args.model), Path(args.pack), ident, made_on=time.strftime("%Y-%m-%d"))
        commons.add_attestation(att)
        _print({k: att[k] for k in att if k != "sig"})
        return 0
    if c == "scoreboard":
        _print(scoreboard(commons, args.model_id))
        return 0
    if c == "snapshot":
        snap = commons.snapshot()
        _print({k: snap[k] for k in ("snapshot_id", "source", "bundles", "train", "test", "train_cap")})
        return 0
    if c == "train":
        card = train_generic(commons, args.snapshot, method=args.method)
        write_json(Path(args.out), card)
        _print(card)
        return 0
    if c == "gate":
        rep = gate_model(commons, read_json(args.model))
        if args.out:
            write_json(Path(args.out), rep)
        _print(rep)
        return 0 if rep["verdict"] == "pass" else 1
    if c == "release":
        _print(release_model(commons, read_json(args.model)))
        return 0
    if c == "status":
        st = status(commons)
        _print(st)
        return 0 if st["ledger_ok"] else 1
    raise AssertionError(c)


def cmd_commons_demo(args: argparse.Namespace) -> int:
    try:
        out = run_demo(Path(args.root), Path(args.work), contributors=args.contributors,
                       seconds=args.seconds, poisoned=args.poisoned)
    except CommonsError as e:
        print(f"REJECTED: {e}", file=sys.stderr)
        return 2
    _print({"snapshot": out["snapshot"], "train": out["train"], "test": out["test"],
            "excluded": out["card"]["train"]["excluded"], "verdict": out["gate"]["verdict"],
            "evidence_grade": out["gate"]["evidence_grade"], "per_contributor": out["gate"]["per_contributor"],
            "release": out.get("release")})
    return 0 if out["gate"]["verdict"] == "pass" else 1


# ---------------- parser ----------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"EMG Gate P0+P1 CLI v{__version__}")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Run chain on synthetic scenario(s)")
    p_run.add_argument("--scenario", choices=SCENARIOS + ["all"], default="rest")
    p_run.add_argument("--out", required=True)
    p_run.add_argument("--fs", type=float, default=500.0)
    p_run.add_argument("--duration", type=float, default=2.0)
    p_run.add_argument("--window-ms", type=float, default=200.0)
    p_run.add_argument("--hop-ms", type=float, default=50.0)
    p_run.add_argument("--th-loose", type=float, default=0.15)
    p_run.add_argument("--th-hard", type=float, default=0.40)
    p_run.add_argument("--enable-delta2", action="store_true")
    p_run.add_argument("--save-raw", action="store_true", help="dev only; raw stays local")
    p_run.add_argument("--seed", type=int, default=42)

    p_s = sub.add_parser("session", help="P0 session pack operations")
    p_s.add_argument("--pack", required=True, help="pack directory")
    ss = p_s.add_subparsers(dest="session_cmd", required=True)
    s_create = ss.add_parser("create", help="create an empty pack")
    s_create.add_argument("--user", required=True)
    s_create.add_argument("--device", required=True)
    s_don = ss.add_parser("don", help="electrodes on → new donning_id")
    s_don.add_argument("--donning-id")
    ss.add_parser("doff", help="electrodes off → active donning closed")
    s_new = ss.add_parser("new", help="new session under the active donning")
    s_new.add_argument("--session-id")
    s_new.add_argument("--held-out", action="store_true")
    s_new.add_argument("--posture")
    s_app = ss.add_parser("append", help="append one validated window")
    s_app.add_argument("--session", required=True)
    s_app.add_argument("--gesture", required=True, choices=sorted(VALID_GESTURES))
    s_app.add_argument("--quality", choices=QUALITY_LABELS, default="ok")
    s_app.add_argument("--quality-json", help="explicit quality flags object (overrides --quality)")
    s_app.add_argument("--norm", type=float)
    s_app.add_argument("--band", type=int, choices=[0, 1, 2])
    s_app.add_argument("--raw-json", help="dev only: JSON array of uV samples")
    s_app.add_argument("--ts-device", type=float)
    s_app.add_argument("--ts-host", type=float)
    s_app.add_argument("--fs", type=float, default=500.0)
    s_app.add_argument("--window-ms", type=float, default=200.0)
    s_mark = ss.add_parser("mark-held-out", help="mark / unmark a session as held_out")
    s_mark.add_argument("--session", required=True)
    s_mark.add_argument("--off", action="store_true")
    s_demo = ss.add_parser("demo-pack", help="build a synthetic pack (2 donnings, held_out re-don)")
    s_demo.add_argument("--seconds", type=float, default=10.0, help="seconds per gesture per donning")
    s_demo.add_argument("--donnings", type=int, default=2)
    s_demo.add_argument("--no-held-out", action="store_true", help="must-fail sample: no held_out")
    s_demo.add_argument("--omit-lead-off-neg", action="store_true", help="must-fail sample: no negatives")
    s_demo.add_argument("--include-raw", action="store_true", help="dev only: store raw_window locally")
    s_demo.add_argument("--seed", type=int, default=7)

    p_exp = sub.add_parser("export", help="export pack (default strips raw)")
    p_exp.add_argument("--pack", required=True)
    p_exp.add_argument("--out", required=True)
    p_exp.add_argument("--include-raw", action="store_true", help="developer flag; local only")
    p_exp.add_argument("--mixed-ok", action="store_true", help="allow mixed recorded/synthetic sources")

    p_cloud = sub.add_parser("cloud-safe-export", help="export pack as CloudSafeEvent rows")
    p_cloud.add_argument("--pack", required=True)
    p_cloud.add_argument("--out", required=True)

    p_chk = sub.add_parser("checklist", help="P0 acceptance checklist on a pack")
    p_chk.add_argument("--pack", required=True)
    p_chk.add_argument("--min-seconds", type=float, default=ADR_MIN_SECONDS_PER_GESTURE,
                       help=f"valid seconds per gesture (ADR: {ADR_MIN_SECONDS_PER_GESTURE:g})")
    p_chk.add_argument("--out", help="write report .md (+ .json next to it)")

    p_cal = sub.add_parser("calibrate", help="commit CalibrationProfile; --rollback")
    p_cal.add_argument("--out", required=True, help="active profile path")
    p_cal.add_argument("--store-dir", help="archive dir (default: <out dir>/profile_store)")
    p_cal.add_argument("--from-pack", help="fit from a session pack (held_out excluded)")
    p_cal.add_argument("--donning-id", help="donning_id to stamp on the profile")
    p_cal.add_argument("--eval-out", help="write held_out evaluation JSON")
    p_cal.add_argument("--rollback", action="store_true")
    p_cal.add_argument("--against", help="compare against previous profile (requires --sessions)")
    p_cal.add_argument("--sessions", help="session pack directory for --against comparison")
    p_cal.add_argument("--fs", type=float, default=500.0)
    p_cal.add_argument("--duration", type=float, default=2.0)
    p_cal.add_argument("--seed", type=int, default=7)

    p_smoke = sub.add_parser("authorize-smoke", help="run profile against synthetic scenarios")
    p_smoke.add_argument("--profile", required=True)
    p_smoke.add_argument("--out")
    p_smoke.add_argument("--fs", type=float, default=500.0)
    p_smoke.add_argument("--duration", type=float, default=2.0)
    p_smoke.add_argument("--seed", type=int, default=11)

    p_fuse = sub.add_parser("fuse", help="Late-fuse one IMU motion with one EMG RMS band")
    p_fuse.add_argument("--pair", help="paired-window JSON file")
    p_fuse.add_argument("--motion")
    p_fuse.add_argument("--band", type=int)
    p_fuse.add_argument("--quality", default="ok")
    p_fuse.add_argument("--authorize", action="store_true")

    p_split = sub.add_parser("split", help="Bucket a recording into IMU, force, and five-class sets")
    p_split.add_argument("--in", dest="src", help="JSONL rows")
    p_split.add_argument("--fixture", help="platform windows.json; split=test stays held out")
    p_split.add_argument("--out", required=True, help="directory for the three sets and report.json")
    p_split.add_argument("--imu-label", action="append", dest="imu_labels",
                         help="intended IMU class; repeat for each. Default: circle up_wave punch other")
    p_split.add_argument("--merge-punch-family", action="store_true",
                         help="export hook and uppercut as punch")
    p_split.add_argument("--require-ready", action="store_true",
                         help="exit 1 unless every IMU class has two sessions")
    p_takes = sub.add_parser("takes-check", help="split grid + re-wear check on 8767 capture takes")
    p_takes.add_argument("--root", required=True, help="<project>/data/emg/emg-gesture-data")
    p_takes.add_argument("--min-redon-s", type=float, default=MIN_REDON_S,
                         help="shortest believable doff/don gap in seconds (tune on a real re-wear)")
    p_takes.add_argument("--out", help="write report JSON")

    p_c = sub.add_parser("commons", help="same-hardware data commons (local directories only)")
    cs = p_c.add_subparsers(dest="commons_cmd", required=True)
    c_tpl = cs.add_parser("hardware-template", help="write a HardwareProfile to fill in")
    c_tpl.add_argument("--out", required=True)
    c_init = cs.add_parser("init", help="create a commons for one hardware pool")
    c_init.add_argument("--root", required=True)
    c_init.add_argument("--hardware", required=True, help="HardwareProfile JSON")
    c_init.add_argument("--license", default="CDLA-Permissive-2.0")
    c_init.add_argument("--policy-json", help='override policy, e.g. {"min_clean_seconds": 60}')
    c_b = cs.add_parser("bundle", help="local pack -> pseudonymous contribution bundle")
    c_b.add_argument("--pack", required=True)
    c_b.add_argument("--hardware", required=True)
    c_b.add_argument("--out", required=True)
    c_b.add_argument("--license", default="CDLA-Permissive-2.0")
    c_b.add_argument("--raw", action="store_true", help="also share raw_window (separate raw-tier consent)")
    c_b.add_argument("--identity", help=f"identity file (default <pack>/{IDENTITY_FILE})")
    c_v = cs.add_parser("verify", help="recompute a bundle from its files; exit 1 on any error")
    c_v.add_argument("--bundle", required=True)
    c_v.add_argument("--root", help="also check pool and license against this commons")
    c_ct = cs.add_parser("contribute", help="verify + copy a bundle into the commons ledger")
    c_ct.add_argument("--root", required=True)
    c_ct.add_argument("--bundle", required=True)
    c_w = cs.add_parser("withdraw", help="remove your bundle (needs your identity file)")
    c_w.add_argument("--root", required=True)
    c_w.add_argument("--bundle-id", required=True)
    c_w.add_argument("--identity", required=True)
    c_w.add_argument("--notice-out", help="also write the signed notice, to hand to other replicas")
    c_m = cs.add_parser("merge", help="pull signed bundles / withdrawals / attestations from another replica")
    c_m.add_argument("--root", required=True)
    c_m.add_argument("--from", dest="from_root", required=True, help="another replica's directory")
    c_x = cs.add_parser("export", help="write shareable objects into a git exchange repo's working tree")
    c_x.add_argument("--root", required=True)
    c_x.add_argument("--to", required=True, help="exchange repo working tree")
    c_vr = cs.add_parser("verify-repo", help="layout + every object in an exchange repo; exit 1 on any error")
    c_vr.add_argument("--repo", required=True)
    c_g2 = cs.add_parser("git-sync", help="pull -> import -> export -> verify -> commit; push only with --push")
    c_g2.add_argument("--root", required=True)
    c_g2.add_argument("--repo", required=True, help="local clone of the shared commons repo")
    c_g2.add_argument("--push", action="store_true", help="also push to origin (publishes your bundles)")
    c_sh = cs.add_parser("share", help="one step for contributors: bundle -> local replica -> git-sync")
    c_sh.add_argument("--pack", required=True)
    c_sh.add_argument("--hardware", required=True)
    c_sh.add_argument("--root", required=True, help="your local replica (created on first use)")
    c_sh.add_argument("--repo", required=True, help="local clone of the shared commons repo")
    c_sh.add_argument("--raw", action="store_true", help="also share raw_window (separate raw-tier consent)")
    c_sh.add_argument("--identity", help=f"identity file (default <pack>/{IDENTITY_FILE})")
    c_sh.add_argument("--push", action="store_true", help="also push to origin (publishes your bundle)")
    c_p = cs.add_parser("personalize", help="shared model + your own pack -> your personal profile (local only)")
    c_p.add_argument("--model", required=True, help="released model card JSON")
    c_p.add_argument("--pack", required=True)
    c_p.add_argument("--out", required=True, help="CalibrationProfile to use on your device")
    c_a = cs.add_parser("attest", help="evaluate a model on your own held-out donning; publish signed numbers only")
    c_a.add_argument("--root", required=True)
    c_a.add_argument("--model", required=True)
    c_a.add_argument("--pack", required=True)
    c_a.add_argument("--identity", help=f"identity file (default <pack>/{IDENTITY_FILE})")
    c_sb = cs.add_parser("scoreboard", help="median / worst of backed, independent attestations for a model")
    c_sb.add_argument("--root", required=True)
    c_sb.add_argument("--model-id", required=True)
    c_s = cs.add_parser("snapshot", help="freeze active bundles; split train/test by contributor")
    c_s.add_argument("--root", required=True)
    c_t = cs.add_parser("train", help="fit the shared band thresholds on a snapshot")
    c_t.add_argument("--root", required=True)
    c_t.add_argument("--snapshot", required=True)
    c_t.add_argument("--out", required=True)
    c_t.add_argument("--method", choices=["median_of_contributors", "pooled"], default="median_of_contributors",
                     help="median of each contributor's own fit (default, robust) or one pooled fit")
    c_g = cs.add_parser("gate", help="model gate: reproduce + held-out contributors; exit 1 on fail")
    c_g.add_argument("--root", required=True)
    c_g.add_argument("--model", required=True)
    c_g.add_argument("--out")
    c_r = cs.add_parser("release", help="gate, then record the model in the ledger")
    c_r.add_argument("--root", required=True)
    c_r.add_argument("--model", required=True)
    c_st = cs.add_parser("status", help="ledger summary and stale models; exit 1 if the chain is broken")
    c_st.add_argument("--root", required=True)

    p_cd = sub.add_parser("commons-demo", help="synthetic end-to-end commons run (evidence_grade=synthetic)")
    p_cd.add_argument("--root", required=True, help="new commons directory")
    p_cd.add_argument("--work", required=True, help="scratch dir for packs and bundles")
    p_cd.add_argument("--contributors", type=int, default=4)
    p_cd.add_argument("--seconds", type=float, default=16.0, help="seconds per gesture per donning")
    p_cd.add_argument("--poisoned", type=int, default=0, help="extra contributors with rest/hard swapped")
    return parser


HANDLERS = {
    "run": cmd_run,
    "session": cmd_session,
    "export": cmd_export,
    "cloud-safe-export": cmd_cloud_safe_export,
    "checklist": cmd_checklist,
    "calibrate": cmd_calibrate,
    "authorize-smoke": cmd_authorize_smoke,
    "fuse": cmd_fuse,
    "split": cmd_split,
    "takes-check": cmd_takes_check,
    "commons": cmd_commons,
    "commons-demo": cmd_commons_demo,
}


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    return HANDLERS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
