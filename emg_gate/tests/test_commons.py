"""Data commons: bundle / ledger / snapshot / model gate, each with must-fail samples."""

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

try:
    import jsonschema
except ImportError:  # optional; numpy-only is the hard policy
    jsonschema = None

from emg_gate import cli
from emg_gate.commons_bundle import (
    is_clean,
    read_rows,
    IDENTITY_FILE,
    CommonsError,
    build_bundle,
    canonical,
    default_hardware,
    load_or_create_identity,
    make_withdrawal,
    pool_key,
    read_json,
    sha256_hex,
    sign_body,
    verify_bundle,
    write_json,
)
from emg_gate.commons_ledger import Commons, _share_cap
from emg_gate.commons_model import (
    _card_id,
    fit_band_thresholds,
    attest_local,
    gate_model,
    personalize,
    release_model,
    scoreboard,
    status,
    train_generic,
)
from emg_gate.demo_pack import build_demo_pack
from emg_gate.jsonlite import errors as schema_errors
from emg_gate.schemas import load_schema
from emg_gate.session_store import SessionPack

HW = default_hardware(board_rev="demo", firmware_build="demo")
POLICY = {"min_clean_seconds": 5.0}
N_GOOD = 4


def _rehash(bundle: Path, ident=None) -> None:
    """Make a hand-edited bundle internally consistent again (sha, bytes, id; signature if ident given)."""
    man = read_json(bundle / "manifest.json")
    blob = (bundle / "windows.jsonl").read_bytes()
    man["files"]["windows.jsonl"] = {"sha256": sha256_hex(blob), "bytes": len(blob)}
    man["bundle_id"] = "b_" + sha256_hex(f"{man['pool_key']}:{sha256_hex(blob)}:{man['contributor']}".encode())[:16]
    if ident is not None:
        man.pop("sig")
        man["sig"] = sign_body(ident, "manifest", man)
    write_json(bundle / "manifest.json", man)


def _edit_rows(bundle: Path, fn) -> None:
    p = bundle / "windows.jsonl"
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = fn(rows)
    p.write_bytes(("\n".join(canonical(r).decode() for r in rows) + "\n").encode())


class CommonsFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls._tmp.name)
        cls.packs = []
        cls.bundles = []
        for i in range(N_GOOD + 1):  # last one has rest/hard swapped
            pack = cls.base / f"pack_{i}"
            build_demo_pack(pack, user_id=f"alice_{i}", device_id=f"ads_serial_{i}", seconds_per_gesture=6.0,
                            seed=300 + 10 * i, swap_rest_hard=i == N_GOOD)
            out = cls.base / f"bundle_{i}"
            build_bundle(pack, out, HW, granted_on="2026-09-29")
            cls.packs.append(pack)
            cls.bundles.append(out)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.tmp = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def copy_bundle(self, i: int) -> Path:
        dst = self.tmp / f"b{i}"
        shutil.copytree(self.bundles[i], dst)
        return dst

    def commons(self, n: int = N_GOOD, **policy) -> Commons:
        c = Commons.init(self.tmp / "commons", HW, policy={**POLICY, **policy})
        for i in range(n):
            c.contribute(self.bundles[i])
        return c


class TestBundle(CommonsFixture):
    def test_bundle_carries_no_identifiers_or_absolute_time(self):
        text = (self.bundles[0] / "windows.jsonl").read_text() + (self.bundles[0] / "manifest.json").read_text()
        for leaked in ("alice_0", "ads_serial_0", "sess_01", "don_01", "1790000", "user_id", "device_id"):
            self.assertNotIn(leaked, text)
        rows = [json.loads(l) for l in (self.bundles[0] / "windows.jsonl").read_text().splitlines()]
        self.assertEqual(min(r["t_ms"] for r in rows), 0.0)
        self.assertTrue({r["session"] for r in rows} >= {"s01", "s08"})

    def test_verify_ok_and_rebuild_is_deterministic(self):
        rep = verify_bundle(self.bundles[0], expected_pool_key=pool_key(HW))
        self.assertTrue(rep["ok"], rep["errors"])
        again = build_bundle(self.packs[0], self.tmp / "again", HW, granted_on="2026-09-29")
        self.assertEqual(again["bundle_id"], read_json(self.bundles[0] / "manifest.json")["bundle_id"])
        ident = read_json(self.packs[0] / IDENTITY_FILE)
        self.assertNotIn(ident["seed"], (self.bundles[0] / "manifest.json").read_text())

    def test_must_fail_manifest_edited_after_signing(self):
        b = self.copy_bundle(0)
        man = read_json(b / "manifest.json")
        man["consent"]["license"] = "ODbL-1.0"  # hashes of the rows still match
        write_json(b / "manifest.json", man)
        rep = verify_bundle(b)
        self.assertTrue(any("signature does not verify" in e for e in rep["errors"]), rep["errors"])
        man2 = read_json(self.bundles[1] / "manifest.json")
        man["pubkey"], man["sig"] = man2["pubkey"], man2["sig"]  # someone else's key
        write_json(b / "manifest.json", man)
        rep = verify_bundle(b)
        self.assertTrue(any("contributor is not derived from pubkey" in e for e in rep["errors"]), rep["errors"])

    def test_must_fail_tampered_row(self):
        b = self.copy_bundle(0)
        _edit_rows(b, lambda rows: [{**rows[0], "feature_window": {**rows[0]["feature_window"], "norm": 0.99}}] + rows[1:])
        rep = verify_bundle(b)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("tampered" in e for e in rep["errors"]), rep["errors"])

    def test_must_fail_identifier_even_when_hashes_are_consistent(self):
        b = self.copy_bundle(0)
        _edit_rows(b, lambda rows: [{**rows[0], "user_id": "alice"}] + rows[1:])
        _rehash(b, load_or_create_identity(self.packs[0] / IDENTITY_FILE))
        rep = verify_bundle(b)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("field not allowed: user_id" in e for e in rep["errors"]), rep["errors"])

    def test_must_fail_manifest_counts_lie(self):
        b = self.copy_bundle(0)
        man = read_json(b / "manifest.json")
        man["counts"]["clean_seconds"]["hard"] = 999.0
        # The contributor signs the lie with their own key: the signature is fine, the recount is not.
        man.pop("sig")
        man["sig"] = sign_body(load_or_create_identity(self.packs[0] / IDENTITY_FILE), "manifest", man)
        write_json(b / "manifest.json", man)
        rep = verify_bundle(b)
        self.assertFalse(any("signature" in e for e in rep["errors"]), rep["errors"])
        self.assertFalse(rep["ok"])
        self.assertTrue(any("recomputed" in e for e in rep["errors"]), rep["errors"])

    def test_raw_needs_raw_tier_consent(self):
        pack = self.tmp / "rawpack"
        build_demo_pack(pack, seconds_per_gesture=2.0, include_raw=True)
        feat = build_bundle(pack, self.tmp / "feat", HW)
        self.assertFalse(feat["counts"]["has_raw"], "features tier must strip raw_window")
        raw = build_bundle(pack, self.tmp / "raw", HW, tiers=("features", "raw"))
        self.assertTrue(raw["counts"]["has_raw"])
        self.assertTrue(verify_bundle(self.tmp / "raw")["ok"])
        man = read_json(self.tmp / "raw" / "manifest.json")
        man["consent"]["tiers"] = ["features"]
        write_json(self.tmp / "raw" / "manifest.json", man)
        rep = verify_bundle(self.tmp / "raw")
        self.assertTrue(any("raw_window without raw-tier consent" in e for e in rep["errors"]), rep["errors"])

    def test_must_fail_mixed_sources_and_hardware_mismatch(self):
        pack = self.tmp / "mixed"
        build_demo_pack(pack, seconds_per_gesture=2.0)
        p = SessionPack.open(pack)
        p.don("don_x")
        sid = p.create_session(session_id="sx")
        p.append_window(sid, gesture_label="rest", quality={k: False for k in (
            "lead_off", "poor_contact", "line_noise", "clip", "artifact_suspect")},
            feature_window={"norm": 0.05}, source="recorded")
        with self.assertRaisesRegex(CommonsError, "mixes sources"):
            build_bundle(pack, self.tmp / "mb", HW)
        with self.assertRaisesRegex(CommonsError, "does not match hardware"):
            build_bundle(self.packs[0], self.tmp / "hb", default_hardware(fs_hz=1000.0))


class TestLedger(CommonsFixture):
    def test_pool_and_license_are_enforced(self):
        other = Commons.init(self.tmp / "gain12", default_hardware(gain=12), policy=POLICY)
        with self.assertRaisesRegex(CommonsError, "not this commons' pool"):
            other.contribute(self.bundles[0])
        # board_rev / firmware_build are recorded but do not split the pool
        self.assertEqual(pool_key(HW), pool_key(default_hardware(board_rev="B", firmware_build="x")))
        lic = Commons.init(self.tmp / "odbl", HW, data_license="ODbL-1.0", policy=POLICY)
        with self.assertRaisesRegex(CommonsError, "license"):
            lic.contribute(self.bundles[0])

    def test_duplicate_and_short_bundles_rejected(self):
        c = self.commons(n=1)
        with self.assertRaisesRegex(CommonsError, "already contributed"):
            c.contribute(self.bundles[0])
        strict = Commons.init(self.tmp / "strict", HW, policy={"min_clean_seconds": 1000.0})
        with self.assertRaisesRegex(CommonsError, "clean seconds below"):
            strict.contribute(self.bundles[0])

    def test_must_fail_ledger_edit(self):
        c = self.commons(n=1)
        self.assertEqual(c.verify_ledger(), [])
        lines = c.ledger_path.read_text().splitlines()
        e = json.loads(lines[1])
        e["body"]["contributor"] = "c_" + "0" * 16
        lines[1] = canonical(e).decode()
        c.ledger_path.write_text("\n".join(lines) + "\n")
        self.assertTrue(any("edited" in x for x in c.verify_ledger()))

    def test_snapshot_needs_enough_contributors_and_one_source(self):
        with self.assertRaisesRegex(CommonsError, "min_contributors"):
            self.commons(n=3).snapshot()
        c = Commons.init(self.tmp / "mix", HW, policy=POLICY)
        c.contribute(self.bundles[0])
        rec = self.tmp / "recpack"
        shutil.copytree(self.packs[1], rec)
        for w in (rec / "windows").glob("*.jsonl"):
            w.write_text(w.read_text().replace('"source": "synthetic"', '"source": "recorded"'))
        build_bundle(rec, self.tmp / "recb", HW)
        c.contribute(self.tmp / "recb")
        with self.assertRaisesRegex(CommonsError, "never share a snapshot"):
            c.snapshot()

    def test_snapshot_splits_by_contributor_and_catches_edits(self):
        c = self.commons()
        snap = c.snapshot()
        self.assertEqual(len(snap["test"]), 1)
        self.assertFalse(set(snap["train"]) & set(snap["test"]))
        self.assertEqual(c.snapshot_issues(snap["snapshot_id"]), [])
        p = c.snapshots_dir / f"{snap['snapshot_id']}.json"
        edited = read_json(p)
        edited["test"].append(edited["train"][0])
        write_json(p, edited)
        issues = c.snapshot_issues(snap["snapshot_id"])
        self.assertTrue(any("edited" in x for x in issues), issues)
        self.assertTrue(any("contributor leak" in x for x in issues), issues)

    def test_share_cap(self):
        self.assertEqual(_share_cap({"a": 1000, "b": 10, "c": 10}, 0.5), 20)
        self.assertEqual(_share_cap({"a": 10, "b": 10, "c": 10}, 0.5), 10)
        with self.assertRaises(CommonsError):
            _share_cap({"a": 10, "b": 10}, 0.4)

    def test_withdraw_needs_secret_deletes_files_and_stales_models(self):
        c = self.commons()
        snap = c.snapshot()
        card = train_generic(c, snap["snapshot_id"])
        release_model(c, card)
        man = read_json(self.bundles[0] / "manifest.json")
        bid = man["bundle_id"]
        stranger = load_or_create_identity(self.packs[1] / IDENTITY_FILE)
        with self.assertRaisesRegex(CommonsError, "did not sign"):
            make_withdrawal(stranger, man)
        forged = {**make_withdrawal(load_or_create_identity(self.packs[0] / IDENTITY_FILE), man)}
        forged["sig"] = make_withdrawal(stranger, {**man, "contributor": stranger["contributor"]})["sig"]
        with self.assertRaisesRegex(CommonsError, "signature does not verify"):
            c.withdraw(forged)
        body = c.withdraw(make_withdrawal(load_or_create_identity(self.packs[0] / IDENTITY_FILE), man))
        self.assertEqual(body["stales_snapshots"], [snap["snapshot_id"]])
        with self.assertRaisesRegex(CommonsError, "cannot come back"):
            c.contribute(self.bundles[0])
        self.assertFalse((c.bundles_dir / bid).exists())
        st = status(c)
        self.assertEqual(st["stale_models"], [card["model_id"]])
        rep = gate_model(c, card)
        self.assertEqual(rep["verdict"], "fail")
        self.assertIn("snapshot_usable", [x["name"] for x in rep["checks"] if not x["ok"]])


class TestModelGate(CommonsFixture):
    def test_pass_on_synthetic_is_stamped_synthetic(self):
        c = self.commons()
        card = train_generic(c, c.snapshot()["snapshot_id"])
        rep = gate_model(c, card)
        self.assertEqual(rep["verdict"], "pass", rep["checks"])
        self.assertEqual(rep["evidence_grade"], "synthetic")
        rel = release_model(c, card)
        self.assertEqual(rel["evidence_grade"], "synthetic")
        with self.assertRaisesRegex(CommonsError, "already released"):
            release_model(c, card)
        if jsonschema is not None:
            jsonschema.validate(card, load_schema("commons_model_card"))

    def test_swapped_labels_are_named_not_trained_on(self):
        c = self.commons(n=N_GOOD + 1)
        swapped = read_json(self.bundles[N_GOOD] / "manifest.json")["contributor"]
        snap = c.snapshot()
        card = train_generic(c, snap["snapshot_id"])
        rep = gate_model(c, card)
        self.assertEqual([q["contributor"] for q in snap["quarantined"]], [swapped])
        self.assertEqual(card["train"]["excluded"], snap["quarantined"])
        self.assertNotIn(swapped, snap["train"] + snap["test"])
        self.assertEqual(rep["verdict"], "pass", rep["checks"])

    def test_must_fail_tampered_card(self):
        c = self.commons()
        card = train_generic(c, c.snapshot()["snapshot_id"])
        bad = {**card, "params": {**card["params"], "th_hard_min": 0.9}}
        rep = gate_model(c, bad)
        self.assertIn("card_id", [x["name"] for x in rep["checks"] if not x["ok"]])
        bad["model_id"] = _card_id(bad)
        rep = gate_model(c, bad)
        self.assertEqual(rep["verdict"], "fail")
        self.assertIn("reproducible", [x["name"] for x in rep["checks"] if not x["ok"]])
        with self.assertRaisesRegex(CommonsError, "gate failed"):
            release_model(c, bad)

    def test_must_fail_accuracy_floor(self):
        c = self.commons(min_accuracy=1.01)
        card = train_generic(c, c.snapshot()["snapshot_id"])
        rep = gate_model(c, card)
        self.assertEqual([x["name"] for x in rep["checks"] if not x["ok"]], ["worst_contributor_accuracy"])


class TestRobustAggregation(CommonsFixture):
    """One contributor whose data is ordered but scaled passes the band-order check; the fit must not follow them."""

    def rows(self):
        return {f"c{i}": [r for r in read_rows(self.bundles[i]) if is_clean(r)] for i in range(N_GOOD)}

    @staticmethod
    def scaled(rows, k, dup):
        out = []
        for _ in range(dup):
            for r in rows:
                fw = dict(r["feature_window"])
                if r["gesture_label"] != "lead_off_neg":
                    fw["norm"] = min(1.0, fw["norm"] * k)
                out.append({**r, "feature_window": fw})
        return out

    def shift(self, method, k, dup):
        good = self.rows()
        base = fit_band_thresholds(good, method)["params"]
        attacked = fit_band_thresholds({**good, "evil": self.scaled(good["c1"], k, dup)}, method)["params"]
        return max(abs(attacked[p] - base[p]) for p in base)

    def test_must_fail_scaled_contributor_moves_pooled_not_median(self):
        for k, dup in ((3.0, 1), (3.0, 5), (0.3, 5)):
            with self.subTest(k=k, dup=dup):
                self.assertGreater(self.shift("pooled", k, dup), 0.1, "pooled fit follows the attacker (why it is not the default)")
                self.assertLess(self.shift("median_of_contributors", k, dup), 0.01)

    def test_default_method_is_recorded_and_reproduced(self):
        c = self.commons()
        snap = c.snapshot()
        card = train_generic(c, snap["snapshot_id"])
        self.assertEqual(card["train"]["method"], "median_of_contributors")
        self.assertEqual(gate_model(c, card)["verdict"], "pass")
        pooled = train_generic(c, snap["snapshot_id"], method="pooled")
        self.assertNotEqual(pooled["model_id"], card["model_id"])
        self.assertEqual(gate_model(c, pooled)["verdict"], "pass")
        swapped = {**card, "train": {**card["train"], "method": "pooled"}}
        swapped["model_id"] = _card_id(swapped)
        self.assertIn("reproducible", [x["name"] for x in gate_model(c, swapped)["checks"] if not x["ok"]])


class TestSchemasAndCli(CommonsFixture):
    def test_jsonlite_agrees_with_jsonschema(self):
        man = read_json(self.bundles[0] / "manifest.json")
        row = json.loads((self.bundles[0] / "windows.jsonl").read_text().splitlines()[0])
        for name, obj in (("commons_manifest", man), ("commons_row", row), ("hardware_profile", HW)):
            self.assertEqual(schema_errors(load_schema(name), obj), [], name)
            bad = {**obj, "free_text": "x"}
            self.assertTrue(schema_errors(load_schema(name), bad), name)
            if jsonschema is not None:
                jsonschema.validate(obj, load_schema(name))
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(bad, load_schema(name))

    def test_compiled_check_agrees_with_errors(self):
        from emg_gate.jsonlite import compile_check
        c = self.commons()
        card = train_generic(c, c.snapshot()["snapshot_id"])
        att = attest_local(card, self.packs[0], load_or_create_identity(self.packs[0] / IDENTITY_FILE), made_on="2026-09-30")
        samples = {
            "commons_manifest": read_json(self.bundles[0] / "manifest.json"),
            "commons_row": json.loads((self.bundles[0] / "windows.jsonl").read_text().splitlines()[0]),
            "hardware_profile": HW,
            "commons_model_card": card,
            "commons_attestation": att,
        }
        wrong = [None, True, -1, 1.5, "x", [], {}]
        for name, obj in samples.items():
            schema, ok = load_schema(name), compile_check(load_schema(name))
            variants = [obj, {**obj, "free_text": "x"}]
            variants += [{k: v for k, v in obj.items() if k != drop} for drop in obj]
            variants += [{**obj, k: w} for k in obj for w in wrong]
            for v in variants:
                self.assertEqual(ok(v), not schema_errors(schema, v), (name, v if len(str(v)) < 300 else str(v)[:300]))

    def test_cli_verify_exit_codes(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(cli.main(["commons", "verify", "--bundle", str(self.bundles[0])]), 0)
        b = self.copy_bundle(1)
        (b / "windows.jsonl").write_text("{}\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["commons", "verify", "--bundle", str(b)]), 1)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["commons", "status", "--root", str(self.tmp / "nope")]), 2)


if __name__ == "__main__":
    unittest.main()


class TestEd25519(unittest.TestCase):
    def test_rfc8032_vectors(self):
        from emg_gate import ed25519
        vectors = [
            ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
             "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
             "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
            ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
             "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
             "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
        ]
        for seed, pub, msg, sig in vectors:
            seed, msg = bytes.fromhex(seed), bytes.fromhex(msg)
            self.assertEqual(ed25519.public_key(seed).hex(), pub)
            self.assertEqual(ed25519.sign(seed, msg).hex(), sig)
            self.assertTrue(ed25519.verify(bytes.fromhex(pub), msg, bytes.fromhex(sig)))
            self.assertFalse(ed25519.verify(bytes.fromhex(pub), msg + b"x", bytes.fromhex(sig)))


class TestDecentralized(CommonsFixture):
    """No master copy: replicas exchange signed objects and compute the same ids."""

    def replica(self, name, idx):
        c = Commons.init(self.tmp / name, HW, policy=POLICY)
        for i in idx:
            c.contribute(self.bundles[i])
        return c

    def test_replicas_converge_to_the_same_snapshot_and_model(self):
        a = self.replica("a", [0, 1])
        b = self.replica("b", [3, 2])
        self.assertEqual(sorted(a.merge(b.root)["added"]), sorted(read_json(self.bundles[i] / "manifest.json")["bundle_id"] for i in (2, 3)))
        b.merge(a.root)
        sa, sb = a.snapshot(), b.snapshot()
        self.assertEqual(sa["snapshot_id"], sb["snapshot_id"])
        self.assertEqual(train_generic(a, sa["snapshot_id"])["model_id"], train_generic(b, sb["snapshot_id"])["model_id"])
        self.assertNotEqual(a.entries()[-1]["hash"], b.entries()[-1]["hash"], "local logs differ; objects agree")

    def test_withdrawal_travels_and_blocks_reentry_everywhere(self):
        a = self.replica("a", [0, 1, 2, 3])
        b = self.replica("b", [])
        man = read_json(self.bundles[0] / "manifest.json")
        a.withdraw(make_withdrawal(load_or_create_identity(self.packs[0] / IDENTITY_FILE), man))
        rep = b.merge(a.root)
        self.assertIn(man["bundle_id"], rep["withdrawn"], "notice applies even though b never had the bundle")
        self.assertEqual(len(rep["added"]), 3)
        with self.assertRaisesRegex(CommonsError, "cannot come back"):
            b.contribute(self.bundles[0])

    def test_merge_refuses_other_pool_and_tampered_objects(self):
        a = self.replica("a", [0])
        other = Commons.init(self.tmp / "g12", default_hardware(gain=12), policy=POLICY)
        with self.assertRaisesRegex(CommonsError, "other replica is pool"):
            a.merge(other.root)
        b = self.replica("b", [1])
        _edit_rows(b.bundles_dir / read_json(self.bundles[1] / "manifest.json")["bundle_id"],
                   lambda rows: rows[1:])
        rep = a.merge(b.root)
        self.assertEqual(rep["added"], [])
        self.assertEqual(len(rep["skipped"]), 1)


class TestYourOwnData(CommonsFixture):
    def released(self):
        c = self.commons()
        card = train_generic(c, c.snapshot()["snapshot_id"])
        release_model(c, card)
        return c, card

    def weak_pack(self):
        """A wearer whose signal is 40% of everyone else's: the shared thresholds misfire."""
        pack = self.tmp / "weak"
        build_demo_pack(pack, user_id="weak", device_id="ads_weak", seconds_per_gesture=6.0, seed=900)
        for w in (pack / "windows").glob("*.jsonl"):
            rows = [json.loads(l) for l in w.read_text().splitlines() if l.strip()]
            for r in rows:
                r["feature_window"]["norm"] *= 0.4
            w.write_text("".join(json.dumps(r) + "\n" for r in rows))
        return pack

    def test_personal_model_beats_shared_for_a_weak_wearer(self):
        _, card = self.released()
        prof = personalize(card, self.weak_pack())
        dbg = prof["calibration_debug"]
        self.assertTrue(dbg["validated_on_held_out"])
        self.assertIn(dbg["picked"], ("own", "blend"))
        self.assertGreater(dbg["held_out_scores"][dbg["picked"]]["accuracy"], dbg["held_out_scores"]["shared"]["accuracy"])
        self.assertEqual(prof["user_id"], "weak", "personal profile stays keyed to the local user")

    def test_attestations_are_signed_backed_and_marked_independent(self):
        c, card = self.released()
        snap = c.load_snapshot(card["snapshot_id"])
        packs = {read_json(self.bundles[i] / "manifest.json")["contributor"]: self.packs[i] for i in range(N_GOOD)}
        for contributor, pack in packs.items():
            att = attest_local(card, pack, load_or_create_identity(pack / IDENTITY_FILE), made_on="2026-09-29")
            self.assertTrue(c.add_attestation(att))
            self.assertNotIn("norm", json.dumps(att), "only numbers leave the machine")
        stranger = self.weak_pack()
        c.add_attestation(attest_local(card, stranger, load_or_create_identity(stranger / IDENTITY_FILE), made_on="2026-09-29"))
        board = scoreboard(c, card["model_id"])
        self.assertEqual(board["n_attestations"], N_GOOD + 1)
        self.assertEqual(board["n_backed"], N_GOOD, "a stranger with no bundle here is not counted")
        self.assertEqual(board["n_independent"], len(snap["test"]))
        bad = {**att, "accuracy": 0.0}
        with self.assertRaisesRegex(CommonsError, "signature does not verify"):
            c.add_attestation(bad)
        self.assertFalse(c.add_attestation(att), "same attestation again is a no-op")
