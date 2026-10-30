"""Owner-launched research verifier/store process; bounded Unix-socket protocol.

Requests contain bytes, typed heads and integer inputs, never code, paths,
verifier callbacks or authority configuration. Same-UID owner/storage compromise
remains possible: a separate process is not a separate immutable trust root.
"""

from __future__ import annotations
import argparse
from dataclasses import asdict
import os
from pathlib import Path
import socket
import socketserver
import select
import struct
import threading
from promotion_v2 import Head, IntegrityFailure, StoreError, canonical, strict_json
from pinned_authority import PinnedAuthority
from transactional_store import TransactionalStore
from proof_gate import Model

MAX_LINE = 32768


def dispatch(store, request):
    if type(request) is not dict:
        raise IntegrityFailure("Object request required")
    op = request.get("op")
    schema = {
        "status": {"op"},
        "promote": {"op", "candidate_hex", "expected", "request_id"},
        "infer": {"op", "expected", "checkpoint", "xs"},
    }
    if op not in schema or set(request) != schema[op]:
        raise IntegrityFailure("Unknown operation or caller-controlled authority field")
    if op == "status":
        return {
            "head": asdict(store.audit()),
            "authority_manifest_sha256": store.authority.manifest_sha256,
        }
    if op == "promote":
        value = request["candidate_hex"]
        if (
            type(value) is not str
            or len(value) > 160
            or any(c not in "0123456789abcdef" for c in value)
            or len(value) % 2
        ):
            raise IntegrityFailure("Invalid canonical artifact hex")
        committed = store.promote(
            bytes.fromhex(value), Head.parse(request["expected"]), request["request_id"]
        )
        return {
            "committed_head": asdict(committed),
            "current_head": asdict(store.audit()),
        }
    xs = request["xs"]
    if (
        type(xs) is not list
        or len(xs) > 256
        or any(type(x) is not int or x.bit_length() > 4096 for x in xs)
    ):
        raise IntegrityFailure("Bounded exact integer inputs required")
    expected = None if request["expected"] is None else Head.parse(request["expected"])
    checkpoint = (
        None if request["checkpoint"] is None else Head.parse(request["checkpoint"])
    )
    snapshot = store.load(expected=expected, checkpoint=checkpoint)
    return {
        "head": asdict(snapshot.head),
        "artifact_hex": snapshot.artifact.hex(),
        "predictions": list(snapshot.batch(tuple(xs))),
        "pcs_authority": False,
    }


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False
    _slots = threading.BoundedSemaphore(4)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(5)
        try:
            raw = self.rfile.readline(MAX_LINE + 1)
            if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
                raise IntegrityFailure("Incomplete/oversized request")
            result = {
                "ok": True,
                "result": dispatch(self.server.store, strict_json(raw[:-1])),
            }
        except (StoreError, ValueError, TypeError, KeyError, RecursionError, OSError):
            # Fixed diagnostic: do not reflect credentials, private paths or tracebacks.
            result = {"ok": False, "error": "rejected_or_unavailable"}
        try:
            self.wfile.write(canonical(result) + b"\n")
        except OSError:
            pass


class PinnedClient:
    """Kernel peer credentials + a retained pidfd bind the owner-launched process.

    Owner must supply the actual child PID, not discover trust from the socket
    pathname. This does not authenticate owner source/configuration or storage.
    """

    def __init__(self, path, server_pid, server_uid=None):
        if type(server_pid) is not int or server_pid <= 0:
            raise IntegrityFailure("Owner process identity required")
        self.path = Path(path)
        self.pid = server_pid
        self.uid = os.getuid() if server_uid is None else server_uid
        self.pidfd = os.pidfd_open(server_pid)

    def close(self):
        if self.pidfd is not None:
            os.close(self.pidfd)
            self.pidfd = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def request(self, request):
        if self.pidfd is None or select.select([self.pidfd], [], [], 0)[0]:
            raise IntegrityFailure("Pinned verifier process exited")
        raw = canonical(request) + b"\n"
        if len(raw) > MAX_LINE:
            raise IntegrityFailure("Request too large")
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(120)
            sock.connect(str(self.path))
            pid, uid, _ = struct.unpack(
                "3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
            )
            if (pid, uid) != (self.pid, self.uid):
                raise IntegrityFailure(
                    "Socket endpoint substituted a different process"
                )
            sock.sendall(raw)
            with sock.makefile("rb") as f:
                result = f.readline(1048577)
        if len(result) > 1048576 or not result.endswith(b"\n"):
            raise IntegrityFailure("Invalid service framing")
        value = strict_json(result[:-1])
        if (
            type(value) is not dict
            or type(value.get("ok")) is not bool
            or set(value) != ({"ok", "result"} if value["ok"] else {"ok", "error"})
        ):
            raise IntegrityFailure("Invalid service response")
        return value


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", required=True, type=Path)
    p.add_argument("--database", required=True, type=Path)
    p.add_argument("--socket", required=True, type=Path)
    p.add_argument("--initialize", action="store_true")
    a = p.parse_args()
    os.umask(0o077)
    # PR_SET_DUMPABLE=0 restricts same-UID ptrace/proc-memory inspection on this
    # Linux host. It does not make source files, storage or owner keys immutable.
    import ctypes

    if ctypes.CDLL(None, use_errno=True).prctl(4, 0, 0, 0, 0) != 0:
        raise RuntimeError("Process memory restriction unavailable")
    authority = PinnedAuthority(a.bundle)
    store = (
        TransactionalStore.initialize(a.database, authority, Model(True, 0, 0))
        if a.initialize
        else TransactionalStore(a.database, authority)
    )
    store.audit()
    with Server(str(a.socket), Handler) as server:
        server.store = store
        server.serve_forever()
