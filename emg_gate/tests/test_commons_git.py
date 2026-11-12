"""Data commons over git: exchange repo layout, verify-repo must-fail samples, sync between replicas."""

import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from emg_gate.commons_bundle import (
    IDENTITY_FILE,
    CommonsError,
    load_or_create_identity,
    make_withdrawal,
    read_json,
    write_json,
)
from emg_gate.commons_git import export_objects, git_sync, share, verify_repo
from emg_gate.commons_ledger import Commons
from emg_gate.tests.test_commons import HW, N_GOOD, POLICY, CommonsFixture

HAS_GIT = shutil.which("git") is not None


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout


@unittest.skipUnless(HAS_GIT, "git not installed")
class GitFixture(CommonsFixture):
    def setUp(self):
        super().setUp()
        cfg = self.tmp / "gitconfig"
        cfg.write_text("[user]\n\tname = commons-test\n\temail = test@localhost\n"
                       "[commit]\n\tgpgsign = false\n[init]\n\tdefaultBranch = main\n")
        patcher = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(cfg), "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def replica(self, name, idx):
        c = Commons.init(self.tmp / name, HW, policy=POLICY)
        for i in idx:
            c.contribute(self.bundles[i])
        return c

    def shared(self):
        """A bare 'shared' repo plus a helper to clone it."""
        bare = self.tmp / "shared.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        return bare

    def clone(self, bare, name):
        dst = self.tmp / name
        subprocess.run(["git", "clone", "-q", str(bare), str(dst)], check=True, capture_output=True)
        return dst


class TestExchangeRepo(GitFixture):
    def test_export_layout_and_license(self):
        c = self.replica("a", [0, 1])
        repo = self.tmp / "x"
        repo.mkdir()
        rep = export_objects(c, repo)
        self.assertEqual(rep["bundles"], 2)
        self.assertEqual(verify_repo(repo), [])
        self.assertTrue((repo / "LICENSE").read_text().startswith("Community Data License Agreement - Permissive - Version 2.0"))
        self.assertEqual(read_json(repo / "commons.json")["data_license"], "CDLA-Permissive-2.0")
        files = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file())
        self.assertFalse([f for f in files if "ledger" in f or "snapshot" in f or IDENTITY_FILE in f], files)
        self.assertEqual(export_objects(c, repo)["bundles"], 0, "second export is a no-op")

    def test_must_fail_repo_contents(self):
        c = self.replica("a", [0, 1])
        repo = self.tmp / "x"
        repo.mkdir()
        export_objects(c, repo)
        bid = read_json(self.bundles[0] / "manifest.json")["bundle_id"]

        # an identity file committed by mistake
        shutil.copyfile(self.packs[0] / IDENTITY_FILE, repo / IDENTITY_FILE)
        errs = verify_repo(repo)
        self.assertTrue(any("not allowed" in e and IDENTITY_FILE in e for e in errs), errs)
        self.assertTrue(any("private identity file" in e for e in errs), errs)
        (repo / IDENTITY_FILE).unlink()

        # a tampered bundle
        w = repo / "bundles" / bid / "windows.jsonl"
        good = w.read_bytes()
        w.write_bytes(good.replace(b'"norm":0.', b'"norm":0.9', 1))
        self.assertTrue(any("tampered" in e for e in verify_repo(repo)))
        w.write_bytes(good)

        # a withdrawn bundle still present
        notice = make_withdrawal(load_or_create_identity(self.packs[0] / IDENTITY_FILE), read_json(self.bundles[0] / "manifest.json"))
        write_json(repo / "withdrawals" / f"{bid}.json", notice)
        self.assertTrue(any("present although its contributor withdrew it" in e for e in verify_repo(repo)))
        shutil.rmtree(repo / "bundles" / bid)
        self.assertEqual(verify_repo(repo), [])

        # the license text replaced
        (repo / "LICENSE").write_text("all rights reserved\n")
        self.assertTrue(any("LICENSE is not" in e for e in verify_repo(repo)))

    def test_export_refuses_other_pool(self):
        c = self.replica("a", [0])
        repo = self.tmp / "x"
        repo.mkdir()
        export_objects(c, repo)
        from emg_gate.commons_bundle import default_hardware
        other = Commons.init(self.tmp / "g12", default_hardware(gain=12), policy=POLICY)
        with self.assertRaisesRegex(CommonsError, "repo is pool"):
            export_objects(other, repo)


class TestGitSync(GitFixture):
    def test_two_replicas_converge_and_withdrawal_travels(self):
        bare = self.shared()
        a, b = self.replica("a", [0, 1]), self.replica("b", [2, 3])
        ra, rb = self.clone(bare, "clone_a"), self.clone(bare, "clone_b")

        self.assertTrue(git_sync(a, ra, push=True)["pushed"])
        rep = git_sync(b, rb, push=True)
        self.assertEqual(len(rep["imported"]["added"]), 2, "b pulled a's two bundles")
        git_sync(a, ra, push=True)
        self.assertEqual(sorted(a.state()["active"]), sorted(b.state()["active"]))
        self.assertEqual(len(a.state()["active"]), N_GOOD)
        self.assertEqual(a.snapshot()["snapshot_id"], b.snapshot()["snapshot_id"])

        man = read_json(self.bundles[2] / "manifest.json")
        b.withdraw(make_withdrawal(load_or_create_identity(self.packs[2] / IDENTITY_FILE), man))
        git_sync(b, rb, push=True)
        self.assertFalse((rb / "bundles" / man["bundle_id"]).exists())
        rep = git_sync(a, ra, push=True)
        self.assertEqual(rep["imported"]["withdrawn"], [man["bundle_id"]])
        self.assertNotIn(man["bundle_id"], a.state()["active"])
        self.assertEqual(verify_repo(ra), [])
        self.assertEqual(_git(ra, "status", "--porcelain"), "")

    def test_no_push_without_flag(self):
        bare = self.shared()
        a = self.replica("a", [0])
        ra = self.clone(bare, "clone_a")
        rep = git_sync(a, ra)
        self.assertTrue(rep["committed"])
        self.assertFalse(rep["pushed"])
        self.assertEqual(_git(bare, "for-each-ref").strip(), "", "nothing reached the shared repo")

    def test_must_fail_refuses_to_commit_bad_state(self):
        a = self.replica("a", [0])
        ra = self.tmp / "solo"
        subprocess.run(["git", "init", "-q", str(ra)], check=True)
        git_sync(a, ra)
        head = _git(ra, "rev-parse", "HEAD")
        shutil.copyfile(self.packs[0] / IDENTITY_FILE, ra / IDENTITY_FILE)
        with self.assertRaisesRegex(CommonsError, "refusing to commit"):
            git_sync(a, ra)
        self.assertEqual(_git(ra, "rev-parse", "HEAD"), head, "no commit was made")
        with self.assertRaisesRegex(CommonsError, "not a git working tree"):
            git_sync(a, self.tmp / "nope")


class TestShare(GitFixture):
    def test_one_command_share_is_idempotent_and_pushes_only_when_asked(self):
        bare = self.shared()
        clone = self.clone(bare, "clone")
        rep = share(self.packs[0], HW, self.tmp / "mine", clone, policy=POLICY)
        self.assertTrue(rep["added"] and rep["committed"])
        self.assertFalse(rep["pushed"])
        self.assertEqual(_git(bare, "for-each-ref").strip(), "")
        again = share(self.packs[0], HW, self.tmp / "mine", clone, push=True, policy=POLICY)
        self.assertEqual(again["bundle_id"], rep["bundle_id"])
        self.assertFalse(again["added"], "same pack, nothing new")
        self.assertTrue(again["pushed"])
        other = self.clone(bare, "other")
        self.assertEqual(verify_repo(other), [])
        self.assertTrue((other / "bundles" / rep["bundle_id"]).is_dir())
        self.assertFalse(list(other.rglob(IDENTITY_FILE)), "identity never leaves the pack")


if __name__ == "__main__":
    unittest.main()
