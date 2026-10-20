"""Actual Lean, real Ed25519, SQLite transactions and a real server subprocess.

No positive scientific verdict is mocked. Fixtures use a partial research pin
inventory, not independently administered infrastructure or full loader attestation.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
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

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research.authorization_history_v1 import history
from research.scientific_history_v1.test_receiver import real_config, FIXTURES
from research.scientific_receiver_v1 import host
from .store import WitnessStore
from . import store as store_module
from .client import WitnessClient, DirectWitnessClient
from .server import dispatch, make_server
from .protocol import (PROTOCOL, Rejected, canonical, digest, verify, anchor_json,
                       decode_anchor, root_id)

HERE=Path(__file__).resolve().parent


def witness_config():
    config=real_config()
    additions=tuple(host.Pin("source",str(p),digest(p.read_bytes()))
                    for p in sorted(HERE.glob("*.py")) if not p.name.startswith("test_"))
    return replace(config,pins=(*config.pins,*additions))


def config_json(config):
    return {"command":list(config.command),"executable_sha256":config.executable_sha256,
            "pins":[vars(p) for p in config.pins],"cwd":config.cwd,
            "environment":dict(config.environment),"toolchain":config.toolchain,
            "timeout_seconds":config.timeout_seconds,"stdout_limit":config.stdout_limit,
            "stderr_limit":config.stderr_limit}


class WitnessRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=witness_config()
        cls.genesis=(FIXTURES/"zero-step.wire").read_bytes()
        cls.candidate=(FIXTURES/"one-step.wire").read_bytes()

    def setUp(self):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);self.directory=Path(td.name)
        self.path=self.directory/"witness.sqlite"
        self.authority,self.intent_witness,self.key=(Ed25519PrivateKey.generate() for _ in range(3))
        self.root=history.Root(self.authority.public_key().public_bytes_raw(),
            self.intent_witness.public_key().public_bytes_raw(),b"PCS-SCI-HISTORY-V1",
            digest(canonical(self.config.identity())).encode(),b"genesis",self.genesis)
        self.root=replace(self.root,checker=bytes.fromhex(digest(canonical(self.config.identity()))))
        self.store=WitnessStore.create(self.path,self.root,self.config,self.key)
        self.initial=history.initial(self.root)

    def intent(self,raw=None,anchor=None,event_id=b"event",**changes):
        payload=history.proposed_payload(self.root,anchor or self.initial,event_id=event_id,
            candidate=self.candidate if raw is None else raw,certificate=b"")
        payload=replace(payload,**changes)
        return history.Envelope(payload,self.authority.sign(payload.signing_bytes()),
                                self.intent_witness.sign(payload.signing_bytes())).encode()

    def checkpoint(self,store=None):
        return DirectWitnessClient(store or self.store).checkpoint()

    def test_actual_science_prepare_finalize_persistence_and_exact_export(self):
        raw=self.intent();prepared=self.store.prepare(raw)
        p=verify(prepared,self.root,self.store.public_key,kind="prepared")
        self.assertEqual(p["intent"],raw.hex())
        self.assertEqual(p["verification"]["response"]["result"]["finalA"],"7/2")
        before=self.checkpoint();self.assertEqual(decode_anchor(before["anchor"]),self.initial)
        self.assertEqual(before["pending"]["intent"],raw.hex())
        final=self.store.finalize(digest(raw));f=verify(final,self.root,self.store.public_key,kind="finalized")
        self.assertEqual(f["anchor"]["generation"],1)
        reopened=WitnessStore(self.path,self.root,self.config,self.key)
        exported=DirectWitnessClient(reopened).export()
        self.assertEqual(exported["envelopes"],[raw.hex()]);self.assertIsNone(exported["pending"])
        self.assertEqual(exported["anchor"],f["anchor"])

    def test_real_cosigned_false_science_does_not_prepare(self):
        before=self.path.read_bytes()
        for name in ("wrong-total","wrong-environment","physical-intermediate-negative"):
            with self.subTest(name=name),self.assertRaises(Rejected):
                self.store.prepare(self.intent((FIXTURES/(name+".wire")).read_bytes()))
            self.assertEqual(self.path.read_bytes(),before)
        self.assertIsNone(self.checkpoint()["pending"])

    def test_invalid_signature_policy_checker_and_certificate_never_launch_lean(self):
        valid=history.Envelope.decode(self.intent())
        raws=[replace(valid,authority_signature=bytes(64)).encode(),
              self.intent(policy=b"wrong"),self.intent(checker=bytes(32)),self.intent(certificate=b"untrusted")]
        with patch.object(self.store._service,"verify_bytes",side_effect=AssertionError("must authenticate first")):
            for raw in raws:
                with self.subTest(raw=digest(raw)),self.assertRaises(Rejected):self.store.prepare(raw)

    def test_pending_conflict_and_idempotency(self):
        raw=self.intent();first=self.store.prepare(raw)
        with patch.object(self.store._service,"verify_bytes",side_effect=AssertionError("no new science for replay")):
            self.assertEqual(self.store.prepare(raw),first)
            with self.assertRaises(Rejected):self.store.prepare(self.intent(event_id=b"conflict"))
        self.assertEqual(self.checkpoint()["anchor"],anchor_json(self.initial))

    def test_finalize_requires_exact_pending_and_stale_intents_never_advance(self):
        with self.assertRaises(Rejected):self.store.finalize("00"*32)
        raw=self.intent();self.store.prepare(raw)
        with self.assertRaises(Rejected):self.store.finalize("00"*32)
        final=self.store.finalize(digest(raw));self.assertEqual(self.store.finalize(digest(raw)),final)
        with patch.object(self.store._service,"verify_bytes",side_effect=AssertionError("stale before science")):
            with self.assertRaises(Rejected):self.store.prepare(self.intent(event_id=b"stale"))

    def test_pinned_bootstrap_rejects_store_root_key_and_profile_substitution(self):
        for root,config,key in ((replace(self.root,genesis_id=b"other"),self.config,self.key),
                (self.root,self.config,Ed25519PrivateKey.generate()),
                (self.root,replace(self.config,timeout_seconds=59),self.key),
                (self.root,self.config,self.authority), (self.root,self.config,self.intent_witness)):
            with self.subTest(root=root.genesis_id),self.assertRaises(Rejected):
                WitnessStore(self.path,root,config,key)

    def test_missing_corrupt_symlink_and_unknown_schema_fail_closed(self):
        missing=self.path.with_name("missing.sqlite")
        with self.assertRaises(Rejected):WitnessStore(missing,self.root,self.config,self.key)
        self.assertFalse(missing.exists())
        symlink=self.path.with_name("link.sqlite");symlink.symlink_to(self.path)
        with self.assertRaises(Rejected):WitnessStore(symlink,self.root,self.config,self.key)
        with sqlite3.connect(self.path) as c:c.execute("CREATE TABLE hostile (x INTEGER)")
        with self.assertRaises(Rejected):self.checkpoint()

    def test_rollback_producer_view_detected_by_fresh_witness_but_all_witness_state_rollback_limit(self):
        snapshot=self.path.read_bytes();raw=self.intent();self.store.prepare(raw);self.store.finalize(digest(raw))
        current=decode_anchor(self.checkpoint()["anchor"])
        self.assertNotEqual(current,self.initial)  # Old producer checkpoint cannot match current witness.
        # Explicit boundary: restoring the witness's own DB too removes its only
        # durable monotonic memory. A separate retained observer is required.
        self.path.write_bytes(snapshot)
        rolled=WitnessStore(self.path,self.root,self.config,self.key)
        self.assertEqual(decode_anchor(self.checkpoint(rolled)["anchor"]),self.initial)

    def test_two_actual_store_instances_conflict_with_one_durable_successor(self):
        other=WitnessStore(self.path,self.root,self.config,self.key)
        raws=[self.intent(event_id=b"one"),self.intent(event_id=b"two")]
        def attempt(store,raw):
            try:return store.prepare(raw)
            except Rejected:return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(lambda item:attempt(*item),zip((self.store,other),raws)))
        self.assertEqual(sum(o is not None for o in outcomes),1)
        pending=self.checkpoint()["pending"]
        self.assertIn(pending["intent"],[r.hex() for r in raws])
        self.store.finalize(pending["intent_sha256"])
        self.assertEqual(self.checkpoint()["anchor"]["generation"],1)

    def test_dispatch_bounds_and_nonce_freshness(self):
        nonce=os.urandom(32);req={"protocol":PROTOCOL,"action":"checkpoint","nonce":nonce.hex()}
        e=dispatch(self.store,req)
        verify(e,self.root,self.store.public_key,kind="response:checkpoint",nonce=nonce)
        with self.assertRaises(Rejected):verify(e,self.root,self.store.public_key,kind="response:checkpoint",nonce=os.urandom(32))
        for request in ({**req,"key":"00"},{**req,"protocol":"V0"},{**req,"action":"shell"},{**req,"nonce":"00"}):
            with self.assertRaises(Rejected):dispatch(self.store,request)

    def test_postwrite_export_budget_failure_rolls_back_checked_prepare(self):
        before=self.path.read_bytes()
        initial_size=len(canonical(self.store.export(bytes(32))))
        # Negative-only budget reduction. Mathematical verdict is still actual Lean;
        # staged state must be rejected and rolled back before any receipt returns.
        with patch.object(store_module,"MAX_RESPONSE",initial_size+32):
            with self.assertRaisesRegex(Rejected,"export budget"):self.store.prepare(self.intent())
        self.assertEqual(self.path.read_bytes(),before)
        self.assertIsNone(self.checkpoint()["pending"])

    def test_postwrite_page_budget_failure_rolls_back_checked_prepare(self):
        before=self.path.read_bytes()
        with patch.object(store_module,"MAX_DATABASE",len(before)):
            with self.assertRaisesRegex(Rejected,"page budget"):self.store.prepare(self.intent())
        self.assertEqual(self.path.read_bytes(),before)
        self.assertIsNone(self.checkpoint()["pending"])

    def launch(self):
        paths={name:self.directory/name for name in ("root.json","config.json","key.raw","ready.json")}
        paths["root.json"].write_bytes(self.root.encode())
        paths["config.json"].write_bytes(canonical(config_json(self.config)))
        fd=os.open(paths["key.raw"],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as stream:stream.write(self.key.private_bytes_raw())
        command=[sys.executable,"-m","research.scientific_witness_v1.server","serve","--db",str(self.path),
            "--root",str(paths["root.json"]),"--config",str(paths["config.json"]),"--key",str(paths["key.raw"]),
            "--ready-file",str(paths["ready.json"])]
        process=subprocess.Popen(command,cwd=HERE.parents[1],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        def stop():
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            if process.stderr:process.stderr.close()
        self.addCleanup(stop)
        deadline=time.monotonic()+45
        while not paths["ready.json"].exists():
            if process.poll() is not None:self.fail("Witness exited: "+process.stderr.read().decode())
            if time.monotonic()>deadline:self.fail("Actual witness startup timeout")
            time.sleep(.05)
        ready=json.loads(paths["ready.json"].read_bytes())
        self.assertEqual(ready["witness_key"],self.store.public_key.hex())
        return WitnessClient("http://127.0.0.1:"+str(ready["port"]),self.root,self.config,self.store.public_key),process

    def test_actual_separate_server_client_signature_and_complete_material(self):
        client,process=self.launch();self.assertIsNone(process.poll())
        self.assertEqual(client.checkpoint()["anchor"],anchor_json(self.initial))
        raw=self.intent();prepared=client.prepare(raw)["receipt"]
        verify(prepared,self.root,self.store.public_key,kind="prepared")
        self.assertIsNotNone(client.checkpoint()["pending"])
        client.finalize(digest(raw));exported=client.export()
        self.assertEqual(exported["envelopes"],[raw.hex()]);self.assertIsNone(exported["pending"])
        self.assertEqual(exported["anchor"]["generation"],1)
        wrong=WitnessClient(client._url,self.root,self.config,bytes(32))
        with self.assertRaises(Rejected):wrong.checkpoint()

    def test_transport_rejects_unsafe_remote_http_and_server_unavailable(self):
        with self.assertRaises(Rejected):WitnessClient("http://example.org",self.root,self.config,self.store.public_key)
        with self.assertRaises(Rejected):make_server(self.store,bind="0.0.0.0")
        sock=socket.socket();sock.bind(("127.0.0.1",0));port=sock.getsockname()[1];sock.close()
        client=WitnessClient("http://127.0.0.1:"+str(port),self.root,self.config,self.store.public_key,timeout=1)
        with self.assertRaises(Rejected):client.checkpoint()


if __name__=="__main__":unittest.main(verbosity=2)
