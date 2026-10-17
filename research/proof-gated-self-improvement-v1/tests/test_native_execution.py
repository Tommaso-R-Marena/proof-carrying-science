"""Real native Lean tests. No fake affirmative oracle is used here.

Ordinary unit discovery may skip these when no owner-built bundle is supplied.
The dedicated CI lane sets PCS_PGSI_REQUIRE_NATIVE=1, making omission an error.
"""

import copy
from dataclasses import asdict
import itertools
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pinned_authority import PinnedAuthority, sealed, SEALS, F_GET_SEALS
from transactional_store import TransactionalStore, request_hash
from authority_service import PinnedClient
from proof_gate import Model, wire_bytes, check, POLICY_HASH
from promotion_v2 import (
    Head,
    IntegrityFailure,
    ProposalRejected,
    StaleHead,
    canonical,
    receipt_hash,
)
import fcntl

BUNDLE = os.environ.get("PCS_PGSI_AUTHORITY_BUNDLE")
if os.environ.get("PCS_PGSI_REQUIRE_NATIVE") == "1" and not BUNDLE:
    raise RuntimeError("Mandatory native authority bundle missing; refusing skipped CI")
HERE = Path(__file__).resolve().parents[1]
A = Model(True, 0, 0)
B = Model(True, 1, 1)
C = Model(True, 2, 1)


@unittest.skipUnless(BUNDLE, "Owner-built native authority bundle required")
class NativeBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = PinnedAuthority(Path(BUNDLE))

    def test_kernel_write_seals_are_enforced(self):
        with sealed(b"actual-snapshot") as fd:
            self.assertEqual(fcntl.fcntl(fd, F_GET_SEALS) & SEALS, SEALS)
            with self.assertRaises(OSError):
                os.pwrite(fd, b"X", 0)
            with self.assertRaises(OSError):
                os.ftruncate(fd, 1)
            self.assertEqual(os.pread(fd, 100, 0), b"actual-snapshot")

    def test_real_positive_negative_and_malformed_authorization(self):
        self.assertEqual(
            self.authority.authorize(wire_bytes(A), wire_bytes(B))["verdict"], "ACCEPT"
        )
        with self.assertRaises(ProposalRejected):
            self.authority.authorize(wire_bytes(C), wire_bytes(A))
        with self.assertRaises(IntegrityFailure):
            self.authority.authorize(wire_bytes(A), b"PGSI1|R|01|1")

    def test_exhaustive_8450_codec_and_exact_prediction_correspondence(self):
        models = [
            Model(r, w, b)
            for r, w, b in itertools.product(
                (False, True), range(-32, 33), range(-32, 33)
            )
        ]
        xs = tuple(range(-20, 21)) + (-(10**80), 10**80)
        rows = self.authority.probe(
            {"raw_hex": wire_bytes(m).hex(), "xs": [str(x) for x in xs]} for m in models
        )
        for m, row in zip(models, rows):
            self.assertTrue(row["valid"])
            self.assertEqual(row["wire"].encode("ascii"), wire_bytes(m))
            self.assertEqual(
                (row["relu"], int(row["weight"]), int(row["bias"])),
                (m.relu, m.weight, m.bias),
            )
            expected = [
                max(0, m.weight * x + m.bias) if m.relu else m.weight * x + m.bias
                for x in xs
            ]
            self.assertEqual([int(v) for v in row["predictions"]], expected)
            self.assertEqual([m.predict(x) for x in xs], expected)
            self.assertIs(row["finite_from_zero"], check(A, m).accepted)
        self.assertEqual(len(rows), 8450)

    def test_malformed_codec_and_original_runtime_compatibility(self):
        invalid = [
            b"",
            b"PGSI1|R|-0|0",
            b"PGSI1|R|+1|1",
            b"PGSI1|R|01|1",
            b"PGSI1|R|1|01",
            b"PGSI1|R|1|-0",
            b"PGSI1|R|33|1",
            b"PGSI1|L|-33|1",
            b"PGSI1|R|1|1\n",
            b"PGSI1|R|1|1\r\n",
            b"PGSI1|R|1|1 ",
            b"PGSI1|R|1|1|x",
            b"PGSI2|R|1|1",
            b"PGSI1|Q|1|1",
            b"PGSI1|R|1|1\0",
            b"\xff",
            b"PGSI1|R|\xff1|1",
            "PGSI1|R|١|1".encode(),
            "ＰＧＳＩ１|R|1|1".encode(),
            b"\xef\xbb\xbfPGSI1|R|1|1",
        ]
        rows = self.authority.probe(
            {"raw_hex": raw.hex(), "xs": ["0"]} for raw in invalid
        )
        self.assertTrue(all(row == {"valid": False} for row in rows))
        from sealed_inference import decode_sealed_model

        for raw in invalid:
            with self.assertRaises(IntegrityFailure):
                decode_sealed_model(raw)
        # Actual original imported IO CLI, not a rewritten Python parser.
        for raw in [
            wire_bytes(B),
            invalid[1],
            invalid[8],
            invalid[15],
            invalid[16],
            invalid[17],
        ]:
            p = self.authority._run(
                ["legacy", "/a", "/b"], [("/a", wire_bytes(A)), ("/b", raw)]
            )
            self.assertEqual(
                p.returncode == 0 and p.stdout == b"ACCEPT\n" and p.stderr == b"",
                raw == wire_bytes(B),
            )

    def test_actual_no_host_store_secret_network_or_writable_executable(self):
        with tempfile.TemporaryDirectory() as d, socket.socket() as listener:
            host = Path(d) / "private-canary"
            host.write_text("not visible to verifier")
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                pass  # positive control
            with patch.dict(os.environ, {"PCS_PGSI_TEST_SECRET": "do-not-inherit"}):
                p = self.authority._run(["isolation", str(host), str(port)])
            self.assertEqual((p.returncode, p.stderr), (0, b""))
            r = json.loads(p.stdout)
            for key in [
                "host_path_visible",
                "parent_secret_visible",
                "host_loopback_connected",
                "authority_writable",
            ]:
                self.assertIs(r[key], False)
            self.assertNotEqual(r["net_namespace"], os.readlink("/proc/self/ns/net"))

    def test_binary_substitution_and_manifest_corruption_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            shutil.copyfile(Path(BUNDLE) / "manifest.json", d / "manifest.json")
            (d / "pgsi-authority").write_bytes(b"fake affirmative executable")
            with self.assertRaises(IntegrityFailure):
                PinnedAuthority(d)
            (d / "manifest.json").write_bytes(b'{"format":1,"format":2}')
            with self.assertRaises(IntegrityFailure):
                PinnedAuthority(d)

    def test_verified_executable_snapshot_does_not_reopen_mutable_binary(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for n in ["manifest.json", "pgsi-authority"]:
                shutil.copyfile(Path(BUNDLE) / n, d / n)
            authority = PinnedAuthority(d)
            (d / "pgsi-authority").write_bytes(b"changed after verified read")
            self.assertEqual(
                authority.authorize(wire_bytes(A), wire_bytes(B))["verdict"], "ACCEPT"
            )
            with self.assertRaises(IntegrityFailure):
                PinnedAuthority(d)


@unittest.skipUnless(BUNDLE, "Owner-built native authority bundle required")
class TransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = PinnedAuthority(Path(BUNDLE))

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.path = Path(self.t.name) / "state.sqlite"
        self.store = TransactionalStore.initialize(self.path, self.authority, A)

    def test_real_two_generations_receipt_replay_and_sealed_predictions(self):
        a = self.store.audit()
        b = self.store.promote(wire_bytes(B), a, "1" * 32)
        c = self.store.promote(wire_bytes(C), b, "2" * 32)
        self.assertEqual(self.store.audit(checkpoint=b), c)
        snapshot = self.store.load(expected=c)
        self.assertEqual(
            snapshot.batch(tuple(range(-100, 101))),
            tuple(max(0, 2 * x + 1) for x in range(-100, 101)),
        )
        with self.assertRaises(StaleHead):
            self.store.load(expected=b)
        self.path.unlink()  # no path reopening during prediction
        self.assertEqual(snapshot.predict(99), 199)

    def test_stale_generation_and_conflicting_policy_do_not_commit(self):
        a = self.store.audit()
        b = self.store.promote(wire_bytes(B), a, "1" * 32)
        with self.assertRaises(StaleHead):
            self.store.promote(wire_bytes(C), a, "2" * 32)
        bad = Head(b.generation, b.active_sha256, "a" * 64, b.last_receipt_sha256)
        with self.assertRaises(StaleHead):
            self.store.promote(wire_bytes(C), bad, "3" * 32)
        self.assertEqual(self.store.audit(), b)

    def test_no_caller_verifier_substitution_interface(self):
        with self.assertRaises(TypeError):
            self.store.promote(
                wire_bytes(B), self.store.audit(), "1" * 32, verifier=lambda *_: True
            )

    def test_duplicate_acknowledgement_never_reactivates_old_model(self):
        a = self.store.audit()
        b = self.store.promote(wire_bytes(B), a, "1" * 32)
        c = self.store.promote(wire_bytes(C), b, "2" * 32)
        self.assertEqual(self.store.promote(wire_bytes(B), a, "1" * 32), b)
        self.assertEqual(self.store.audit(), c)
        with self.assertRaises(IntegrityFailure):
            self.store.promote(wire_bytes(C), a, "1" * 32)

    def test_negative_real_authority_leaves_no_orphans(self):
        a = self.store.audit()
        with self.assertRaises(ProposalRejected):
            self.store.promote(wire_bytes(A), a, "1" * 32)
        self.assertEqual(self.store.audit(), a)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM receipts").fetchone(), (0,)
            )
            self.assertEqual(db.execute("SELECT COUNT(*) FROM blobs").fetchone(), (1,))

    def test_concurrent_real_promotions_have_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor

        before = self.store.audit()

        def attempt(i):
            try:
                return self.store.promote(
                    wire_bytes(B if i % 2 else C), before, f"{i:032x}"
                )
            except StaleHead:
                return None

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(1, 5)))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(self.store.audit().generation, 1)

    def test_complete_rollback_is_detectable_only_with_independent_checkpoint(self):
        backup = Path(self.t.name) / "genesis.sqlite"
        with sqlite3.connect(self.path) as source, sqlite3.connect(backup) as dest:
            source.backup(dest)
        a = self.store.audit()
        b = self.store.promote(wire_bytes(B), a, "1" * 32)
        with sqlite3.connect(backup) as source, sqlite3.connect(self.path) as dest:
            source.backup(dest)
        self.assertEqual(self.store.audit(), a)  # deliberate limitation, not hidden
        with self.assertRaises(StaleHead):
            self.store.audit(checkpoint=b)

    def test_structurally_rehashed_fake_positive_history_fails_real_replay(self):
        a = self.store.audit()
        self.store.promote(wire_bytes(B), a, "1" * 32)
        with sqlite3.connect(self.path) as db:
            event = json.loads(db.execute("SELECT body FROM receipts").fetchone()[0])
            event["new_sha256"] = a.active_sha256
            event["request_sha256"] = request_hash(a, wire_bytes(A))
            event["authority"]["new_sha256"] = a.active_sha256
            raw = canonical(event)
            head = Head(1, a.active_sha256, POLICY_HASH, receipt_hash(raw))
            db.execute("DELETE FROM blobs WHERE digest!=?", (a.active_sha256,))
            db.execute("UPDATE receipts SET body=?", (raw,))
            db.execute(
                'UPDATE state SET body=? WHERE name="HEAD"', (canonical(asdict(head)),)
            )
        with self.assertRaises(IntegrityFailure):
            self.store.audit()

    def test_receipt_mutation_fails_closed(self):
        a = self.store.audit()
        self.store.promote(wire_bytes(B), a, "1" * 32)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE receipts SET body=?", (b"{}",))
        with self.assertRaises(IntegrityFailure):
            self.store.load()

    def test_missing_blob_fails_closed(self):
        self.store.audit()
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM blobs")
        with self.assertRaises(IntegrityFailure):
            self.store.load()

    def test_oversized_and_mistyped_metadata_fail_closed_before_json_loading(self):
        with sqlite3.connect(self.path) as db:
            original = db.execute(
                'SELECT body FROM state WHERE name="HEAD"'
            ).fetchone()[0]
        for raw in [b"x" * 4097, "non-byte metadata"]:
            with sqlite3.connect(self.path) as db:
                db.execute('UPDATE state SET body=? WHERE name="HEAD"', (raw,))
            with self.assertRaises(IntegrityFailure):
                self.store.audit()
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE state SET body=? WHERE name="HEAD"', (original,))
        self.assertEqual(self.store.audit().generation, 0)

    def test_malformed_canonical_candidate_never_enters_database(self):
        head = self.store.audit()
        for raw in [b"PGSI1|R|-0|0", b"PGSI1|R|1|1\n", b"PGSI1|R|33|1", b"\xff"]:
            with self.assertRaises(IntegrityFailure):
                self.store.promote(raw, head, "a" * 32)
        self.assertEqual(self.store.audit(), head)

    def test_portable_history_fresh_receiver_replay_and_tamper_controls(self):
        from replay_history import replay_history

        a = self.store.audit()
        initial = self.store.export_history(expected=a)
        b = self.store.promote(wire_bytes(B), a, "1" * 32)
        c = self.store.promote(wire_bytes(C), b, "2" * 32)
        package = self.store.export_history(expected=c)
        fresh = PinnedAuthority(Path(BUNDLE))
        replay = replay_history(package, fresh, expected=c, xs=(-(10**60), 0, 10**60))
        self.assertEqual(replay["transitions_freshly_rechecked"], 2)
        self.assertFalse(replay["producer_history_authenticated"])
        history = Path(self.t.name) / "history.json"
        checkpoint = Path(self.t.name) / "expected.json"
        history.write_bytes(canonical(package))
        checkpoint.write_bytes(canonical(asdict(c)))
        cli = subprocess.run(
            [
                sys.executable,
                str(HERE / "replay_history.py"),
                "--bundle",
                BUNDLE,
                "--history",
                str(history),
                "--expected-head",
                str(checkpoint),
            ],
            cwd=HERE,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(cli.returncode, 0, cli.stderr.decode())
        self.assertEqual(json.loads(cli.stdout)["transitions_freshly_rechecked"], 2)

        self.assertEqual(replay["predictions"], [0, 1, 2 * 10**60 + 1])
        with self.assertRaises(StaleHead):
            replay_history(initial, fresh, expected=c)
        changed = copy.deepcopy(package)
        changed["blobs"][c.active_sha256] = wire_bytes(A).hex()
        with self.assertRaises(IntegrityFailure):
            replay_history(changed, fresh, expected=c)
        changed = copy.deepcopy(package)
        changed["receipts"].reverse()
        with self.assertRaises(IntegrityFailure):
            replay_history(changed, fresh, expected=c)

    def test_process_crash_before_commit_rolls_back_and_after_commit_retries(self):
        code = r"""
import os,sys,sqlite3
from pathlib import Path
from pinned_authority import PinnedAuthority
from transactional_store import TransactionalStore
from proof_gate import Model,wire_bytes
mode=sys.argv[3]
class Crash(sqlite3.Connection):
 def execute(self,sql,*args,**kwargs):
  if sql=='COMMIT' and mode=='before':os._exit(77)
  result=super().execute(sql,*args,**kwargs)
  if sql=='COMMIT' and mode=='after':os._exit(78)
  return result
real=sqlite3.connect
sqlite3.connect=lambda *a,**kw:real(*a,**kw,factory=Crash)
s=TransactionalStore(Path(sys.argv[1]),PinnedAuthority(Path(sys.argv[2])))
s.promote(wire_bytes(Model(True,1,1)),s.audit(),'1'*32)
"""
        before = self.store.audit()
        for mode, returncode in [("before", 77), ("after", 78)]:
            proc = subprocess.run(
                [sys.executable, "-c", code, str(self.path), BUNDLE, mode],
                cwd=HERE,
                env={"PATH": os.environ["PATH"], "PYTHONPATH": str(HERE)},
                capture_output=True,
                timeout=40,
            )
            self.assertEqual(proc.returncode, returncode, proc.stderr.decode())
            recovered = self.store.audit()
            self.assertEqual(recovered.generation, 0 if mode == "before" else 1)
        self.assertEqual(self.store.promote(wire_bytes(B), before, "1" * 32), recovered)


@unittest.skipUnless(BUNDLE, "Owner-built native authority bundle required")
class ProcessServiceTests(unittest.TestCase):
    def test_separate_process_real_gate_cannot_be_monkeypatched_by_client(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            sock = td / "authority.sock"
            db = td / "state.sqlite"
            env = {"PATH": os.environ["PATH"], "PYTHONPATH": str(HERE)}
            proc = subprocess.Popen(
                [
                    sys.executable,
                    str(HERE / "authority_service.py"),
                    "--bundle",
                    BUNDLE,
                    "--database",
                    str(db),
                    "--socket",
                    str(sock),
                    "--initialize",
                ],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            try:
                for _ in range(100):
                    if sock.exists():
                        break
                    if proc.poll() is not None:
                        raise AssertionError(proc.stderr.read().decode())
                    time.sleep(0.05)
                client = PinnedClient(sock, proc.pid)
                self.addCleanup(client.close)
                call = lambda _, request: client.request(request)
                # A same-UID listener at a substituted path cannot impersonate
                # the owner-launched process, even with a fake positive response.
                fake_path = td / "substituted.sock"
                with socket.socket(socket.AF_UNIX) as fake:
                    fake.bind(str(fake_path))
                    fake.listen()
                    with PinnedClient(fake_path, proc.pid) as wrong_peer:
                        with self.assertRaises(IntegrityFailure):
                            wrong_peer.request({"op": "status"})
                try:
                    mem = os.open(f"/proc/{proc.pid}/mem", os.O_RDWR)
                except PermissionError:
                    memory_denied = True
                else:
                    os.close(mem)
                    memory_denied = False
                self.assertTrue(
                    memory_denied, "Same-UID client can inspect verifier memory"
                )
                initial = call(sock, {"op": "status"})["result"]["head"]
                accepted = call(
                    sock,
                    {
                        "op": "promote",
                        "candidate_hex": wire_bytes(C).hex(),
                        "expected": initial,
                        "request_id": "1" * 32,
                    },
                )
                self.assertTrue(accepted["ok"])
                head = accepted["result"]["current_head"]
                with patch("proof_gate.artifact_gate", return_value=True):
                    rejected = call(
                        sock,
                        {
                            "op": "promote",
                            "candidate_hex": wire_bytes(A).hex(),
                            "expected": head,
                            "request_id": "2" * 32,
                        },
                    )
                self.assertFalse(rejected["ok"])
                self.assertFalse(
                    call(sock, {"op": "status", "verdict": "ACCEPT"})["ok"]
                )
                self.assertFalse(
                    call(
                        sock,
                        {
                            "op": "promote",
                            "candidate_path": "/tmp/fake",
                            "expected": head,
                            "request_id": "3" * 32,
                        },
                    )["ok"]
                )
                r = call(
                    sock,
                    {
                        "op": "infer",
                        "expected": head,
                        "checkpoint": head,
                        "xs": [-10, 0, 10],
                    },
                )
                self.assertTrue(r["ok"])
                self.assertEqual(r["result"]["predictions"], [0, 1, 21])
                self.assertFalse(
                    call(
                        sock,
                        {
                            "op": "infer",
                            "expected": head,
                            "checkpoint": None,
                            "xs": [True],
                        },
                    )["ok"]
                )
            finally:
                proc.terminate()
                proc.wait(timeout=5)
                proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
