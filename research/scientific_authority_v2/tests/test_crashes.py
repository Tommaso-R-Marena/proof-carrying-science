"""Actual process exits in local and witness SQLite commit windows.

Injection changes only termination timing. Positive science, signatures,
transactions, network calls and normal recovery all use the actual implementation.
These approximate process failure, not physical disk/power-loss durability.
"""
from contextlib import contextmanager
import json
import multiprocessing
import os
from pathlib import Path
import time

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from research.authorization_history_v1 import history
from research.scientific_witness_v1.client import WitnessClient
from research.scientific_witness_v1.protocol import decode_anchor
from research.scientific_witness_v1.store import WitnessStore
from research.scientific_witness_v1.server import make_server
from research.scientific_authority_v2.coordinator import ScientificAuthority, recover
from .support import Fixture, record


def terminate_at(marker, phase):
    Path(marker).write_text(phase)
    os._exit(71)


def coordinator_worker(path, root, anchor, config, url, public_key, intent, phase, marker):
    client = WitnessClient(url, root, config, public_key)
    authority = ScientificAuthority(path, root, anchor, config, client)
    if phase == "before_prepare":
        client.prepare = lambda _: terminate_at(marker, phase)
    elif phase == "after_prepare":
        authority._history.append = lambda _: terminate_at(marker, phase)
    elif phase == "during_local_transaction":
        original = history._connect
        def traced(path):
            connection = original(path)
            def trace(sql):
                if sql.startswith("UPDATE head SET"):
                    terminate_at(marker, phase)  # Actual event INSERT already ran, no COMMIT.
            connection.set_trace_callback(trace)
            return connection
        history._connect = traced
    elif phase in {"after_local_commit", "after_finalize"}:
        original = client.finalize
        def final(digest):
            if phase == "after_finalize": original(digest)
            terminate_at(marker, phase)
        client.finalize = final
    elif phase in {"before_eligibility", "after_eligibility_before_return"}:
        original, calls = authority.current, 0
        def current():
            nonlocal calls
            calls += 1
            if calls == 2 and phase == "before_eligibility": terminate_at(marker, phase)
            snapshot = original()
            if calls == 2: terminate_at(marker, phase)
            return snapshot
        authority.current = current
    authority.submit(intent)
    raise AssertionError("Fault point was not reached")


def witness_worker(path, root, config, private_key, phase, ready, marker):
    store = WitnessStore(path, root, config, Ed25519PrivateKey.from_private_bytes(private_key))
    original = store._connection
    @contextmanager
    def traced(*args, **kwargs):
        with original(*args, **kwargs) as connection:
            armed = False
            def trace(sql):
                nonlocal armed
                if (phase == "witness_prepare_transaction" and sql.startswith("INSERT INTO pending")):
                    armed = True
                if (phase == "witness_finalize_transaction" and sql.startswith("INSERT INTO events")):
                    armed = True
                if armed and sql == "COMMIT": terminate_at(marker, phase)
            connection.set_trace_callback(trace)
            yield connection
    store._connection = traced
    if phase == "witness_after_finalize_commit":
        finalize = store.finalize
        def finalized(digest):
            finalize(digest)
            terminate_at(marker, phase)
        store.finalize = finalized
    server = make_server(store)
    Path(ready).write_text(json.dumps({"port": server.server_port}))
    server.serve_forever(poll_interval=.05)


CASES = [
    ("before_prepare", 0, 0, False, 0),
    ("after_prepare", 0, 0, True, 1),
    ("during_local_transaction", 0, 0, True, 1),
    ("after_local_commit", 1, 0, True, 1),
    ("after_finalize", 1, 1, False, 1),
    ("before_eligibility", 1, 1, False, 1),
    ("after_eligibility_before_return", 1, 1, False, 1),
    ("witness_prepare_transaction", 0, 0, False, 0),
    ("witness_finalize_transaction", 1, 0, True, 1),
    ("witness_after_finalize_commit", 1, 1, False, 1),
]


@pytest.mark.parametrize("phase,local_generation,witness_generation,pending,recovered_generation", CASES)
def test_real_crash_window(phase, local_generation, witness_generation, pending, recovered_generation):
    context = multiprocessing.get_context("spawn")
    fixture = Fixture()
    actor = None
    start = time.monotonic()
    try:
        intent = fixture.signed()
        marker = fixture.out / "fault-reached"
        if phase.startswith("witness_"):
            fixture.stop()
            ready = fixture.out / "fault-server-ready"
            actor = context.Process(target=witness_worker, args=(fixture.witness_path, fixture.root,
                fixture.config, fixture.key.private_bytes_raw(), phase, ready, marker))
            actor.start()
            deadline = time.monotonic() + 60
            while not ready.is_file():
                if not actor.is_alive(): raise AssertionError("Fault server failed before readiness")
                if time.monotonic() >= deadline: raise AssertionError("Fault server startup exceeded deadline")
                time.sleep(.05)
            client = WitnessClient("http://127.0.0.1:" + str(json.loads(ready.read_text())["port"]),
                                   fixture.root, fixture.config, fixture.key.public_key().public_bytes_raw())
            authority = ScientificAuthority(fixture.local, fixture.root, fixture.anchor, fixture.config, client)
            with pytest.raises(ValueError): authority.submit(intent)
        else:
            actor = context.Process(target=coordinator_worker, args=(fixture.local, fixture.root,
                fixture.anchor, fixture.config, fixture.url, fixture.key.public_key().public_bytes_raw(),
                intent, phase, marker))
            actor.start()
        actor.join(timeout=100)
        assert not actor.is_alive(), "Crash test exceeded deadline"
        assert actor.exitcode == 71 and marker.read_text() == phase
        # Restart the normal witness after a fault-server death, with same pinned key/root.
        if phase.startswith("witness_"): fixture.restart()
        view = fixture.client.checkpoint()
        assert decode_anchor(view["anchor"]).generation == witness_generation
        assert (view["pending"] is not None) == pending
        if local_generation == 0:
            local = history.History(fixture.local, fixture.root, fixture.anchor).snapshot()
        else:
            next_anchor = history._advance(fixture.root, fixture.anchor,
                                            history.Envelope.decode(intent), set())
            local = history.History(fixture.local, fixture.root, next_anchor).snapshot()
        assert local.anchor.generation == local_generation
        if pending or local_generation != witness_generation:
            with pytest.raises(ValueError):
                ScientificAuthority(fixture.local, fixture.root, local.anchor, fixture.config, fixture.client)
        recovered = recover(fixture.local, fixture.root, fixture.config, fixture.client,
                            resolve_pending=pending)
        assert recovered.anchor.generation == recovered_generation
        assert recovered.new_authorization_created is False
        reopened = ScientificAuthority(fixture.local, fixture.root, recovered.anchor,
                                        fixture.config, fixture.client)
        assert reopened.current().anchor == recovered.anchor
        record(phase, {"phase": phase, "status": "EXECUTED_PASS", "exitcode": actor.exitcode,
            "local_generation_after_crash": local_generation,
            "witness_generation_after_crash": witness_generation, "pending_after_crash": pending,
            "recovered_generation": recovered_generation, "new_authorization_created": False,
            "wall_seconds": time.monotonic() - start,
            "failure_model": "Actual process os._exit; not physical power loss",
            "actual_lean_positive_verdicts": True, "profile": "A:same-host-separate-processes"})
    finally:
        if actor is not None and actor.is_alive(): actor.terminate(); actor.join(timeout=10)
        fixture.close()
