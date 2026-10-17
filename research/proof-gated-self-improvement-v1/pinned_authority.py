"""Pinned native Lean checks on Linux write-sealed snapshots in Bubblewrap.

The process has no network or host checkout/storage mounts. Host kernel,
Bubblewrap, system shared libraries, compiler and owner configuration remain
trusted. Same-UID storage/owner compromise is NOT prevented by this mechanism.
"""

from __future__ import annotations
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
from contextlib import contextmanager
from promotion_v2 import (
    IntegrityFailure,
    ProposalRejected,
    blob_hash,
    canonical,
    strict_json,
    _read_regular,
)
from build_authority import ROOT, source_inventory

# Linux UAPI constants; some portable CPython builds omit their names.
# Runtime F_GET_SEALS is mandatory; no emulated or unsealed fallback.
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
SEALS = 0x0001 | 0x0002 | 0x0004 | 0x0008
MAX_NATIVE = 128 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@contextmanager
def sealed(raw: bytes, name="pgsi-snapshot"):
    if type(raw) is not bytes:
        raise IntegrityFailure("Snapshot must be exact bytes")
    fd = os.memfd_create(name, os.MFD_ALLOW_SEALING | os.MFD_CLOEXEC)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise IntegrityFailure("Short sealed write")
            view = view[written:]
        os.lseek(fd, 0, os.SEEK_SET)
        fcntl.fcntl(fd, F_ADD_SEALS, SEALS)
        if fcntl.fcntl(fd, F_GET_SEALS) & SEALS != SEALS:
            raise IntegrityFailure("Kernel seals unavailable")
        if os.pread(fd, len(raw) + 1, 0) != raw:
            raise IntegrityFailure("Snapshot changed")
        yield fd
    finally:
        os.close(fd)


class PinnedAuthority:
    """Owner selects bundle once. No per-request verifier/source substitution."""

    def __init__(self, bundle: Path):
        bundle = Path(bundle).resolve()
        raw = _read_regular(bundle / "manifest.json", 32768)
        m = strict_json(raw)
        if (
            type(m) is not dict
            or set(m)
            != {
                "format",
                "wire_version",
                "binary_sha256",
                "bwrap_sha256",
                "lean_version",
                "sources",
                "generated_bridge_c_sha256",
                "kernel_proved_native_execution_correspondence",
            }
            or m["format"] != "pgsi-native-authority-manifest-v1"
            or m["wire_version"] != "PGSI1"
            or m["kernel_proved_native_execution_correspondence"] is not False
        ):
            raise IntegrityFailure("Unapproved authority manifest")
        if m["sources"] != source_inventory():
            raise IntegrityFailure(
                "Authority source differs from reviewed integration boundary"
            )
        if not m["lean_version"].startswith("Lean (version 4.28.0,"):
            raise IntegrityFailure("Unapproved Lean version")
        executable = _read_regular(bundle / "pgsi-authority", MAX_NATIVE)
        if sha(executable) != m["binary_sha256"]:
            raise IntegrityFailure("Native executable pin mismatch")
        if sha(_read_regular(Path("/usr/bin/bwrap"), MAX_NATIVE)) != m["bwrap_sha256"]:
            raise IntegrityFailure("Sandbox executable pin mismatch")
        self._executable = executable
        self.manifest_sha256 = sha(raw)
        self.binary_sha256 = m["binary_sha256"]
        self._bwrap_sha256 = m["bwrap_sha256"]
        self.lean_version = m["lean_version"]

    def _run(self, args, files=(), input=None, timeout=30):
        if sha(self._executable) != self.binary_sha256:
            raise IntegrityFailure("In-memory executable differs from owner pin")
        if sha(_read_regular(Path("/usr/bin/bwrap"), MAX_NATIVE)) != self._bwrap_sha256:
            raise IntegrityFailure("Sandbox changed after startup")
        from contextlib import ExitStack

        try:
            with ExitStack() as stack:
                executable = stack.enter_context(
                    sealed(self._executable, "pgsi-authority")
                )
                cmd = [
                    "/usr/bin/bwrap",
                    "--unshare-all",
                    "--die-with-parent",
                    "--new-session",
                    "--cap-drop",
                    "ALL",
                    "--clearenv",
                    "--setenv",
                    "LC_ALL",
                    "C",
                    "--setenv",
                    "LANG",
                    "C",
                ]
                for lib in ["/lib", "/lib64", "/usr/lib"]:
                    if Path(lib).is_dir():
                        cmd += ["--ro-bind", lib, lib]
                cmd += [
                    "--proc",
                    "/proc",
                    "--dev",
                    "/dev",
                    "--tmpfs",
                    "/tmp",
                    "--dir",
                    "/work",
                    "--chdir",
                    "/work",
                    "--perms",
                    "0500",
                    "--ro-bind-data",
                    str(executable),
                    "/authority",
                ]
                fds = [executable]
                for name, raw in files:
                    fd = stack.enter_context(sealed(raw))
                    fds.append(fd)
                    cmd += ["--perms", "0400", "--ro-bind-data", str(fd), name]
                cmd += ["--", "/authority", *args]
                p = subprocess.run(
                    cmd,
                    **(
                        {"stdin": subprocess.DEVNULL}
                        if input is None
                        else {"input": input}
                    ),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    pass_fds=fds,
                    env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
                    timeout=timeout,
                    check=False,
                )
                for fd, raw in zip(fds, [self._executable, *[raw for _, raw in files]]):
                    if os.pread(fd, len(raw) + 1, 0) != raw:
                        raise IntegrityFailure("Snapshot changed during verification")
                return p
        except (OSError, subprocess.TimeoutExpired) as e:
            raise IntegrityFailure("Native sandbox unavailable or timed out") from e

    def authorize(self, old: bytes, new: bytes):
        from sealed_inference import decode_sealed_model

        decode_sealed_model(old)
        decode_sealed_model(new)
        p = self._run(
            ["gate", "/incumbent.pgsi", "/candidate.pgsi"],
            [("/incumbent.pgsi", old), ("/candidate.pgsi", new)],
        )
        if p.returncode != 0 or p.stdout != b"ACCEPT\n" or p.stderr:
            raise ProposalRejected(
                "Pinned Lean authority did not authorize exact snapshots"
            )
        return {
            "authority_manifest_sha256": self.manifest_sha256,
            "authority_binary_sha256": self.binary_sha256,
            "old_sha256": blob_hash(old),
            "new_sha256": blob_hash(new),
            "verdict": "ACCEPT",
            "scope": "Lean finite-corpus predicate; native execution/host correspondence unproved",
        }

    def probe(self, records):
        records = list(records)
        if len(records) > 20000:
            raise ValueError("Probe count exceeds research budget")
        raw = b"".join(canonical(record) + b"\n" for record in records)
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError("Probe bytes exceed budget")
        p = self._run(["probe"], input=raw, timeout=120)
        if p.returncode or p.stderr:
            raise IntegrityFailure("Native probe failed")
        try:
            result = [json.loads(line) for line in p.stdout.splitlines()]
        except (ValueError, UnicodeError) as e:
            raise IntegrityFailure("Invalid native probe result") from e
        if len(result) != len(records):
            raise IntegrityFailure("Incomplete native probe")
        return result

    def transitions(self, pairs):
        pairs = list(pairs)
        if len(pairs) > 20000:
            raise ValueError("Transition budget exceeded")
        raw = b"".join(
            canonical({"old_hex": a.hex(), "new_hex": b.hex()}) + b"\n"
            for a, b in pairs
        )
        p = self._run(["transitions"], input=raw, timeout=120)
        if p.returncode or p.stderr:
            raise IntegrityFailure("Native transition probe failed")
        try:
            rows = [json.loads(line) for line in p.stdout.splitlines()]
        except (ValueError, UnicodeError) as e:
            raise IntegrityFailure("Invalid transition results") from e
        if len(rows) != len(pairs):
            raise IntegrityFailure("Incomplete transition results")
        return rows
