"""Operator-configured, process-separated research receiver. No production authority.

Pins and signatures detect specified mismatches; the host, operator configuration,
Git/source/dependency inventory, OS, compiler and key handling remain trusted.
Pre/post hashes do not exclude transient replacement, in-place writes, malicious
loaders or same-UID/root attacks. Dependency-inventory completeness is not proved.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import struct
import subprocess
import time
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from . import reference

PROTOCOL = "PCS-SCI-BOUND-V1"
MAX_BYTES = 8192


class HostRejected(ValueError):
    pass


def _json(raw: bytes) -> Any:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise HostRejected("duplicate response/config field")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(HostRejected("nonfinite JSON")))
    except RecursionError as exc:
        raise HostRejected("JSON nesting exceeds parser resource limit") from exc


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Pin:
    kind: str
    path: str
    sha256: str

    def __post_init__(self):
        if self.kind not in {"source", "dependency"} or not Path(self.path).is_absolute():
            raise HostRejected("invalid operator pin kind/path")
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise HostRejected("invalid operator digest")


@dataclass(frozen=True)
class OperatorConfig:
    command: tuple[str, ...]
    executable_sha256: str
    pins: tuple[Pin, ...]
    cwd: str
    environment: tuple[tuple[str, str], ...]
    toolchain: str
    timeout_seconds: float = 30
    stdout_limit: int = 32768
    stderr_limit: int = 8192

    def __post_init__(self):
        if (type(self.command) is not tuple or not self.command or len(self.command) > 16
                or not all(type(arg) is str and len(arg) <= 4096 for arg in self.command)
                or not Path(self.command[0]).is_absolute() or not Path(self.cwd).is_absolute()):
            raise HostRejected("invalid fixed operator command")
        Pin("source", self.command[0], self.executable_sha256)
        if (type(self.pins) is not tuple or not self.pins or len(self.pins) > 100000
                or not all(type(pin) is Pin for pin in self.pins)
                or {pin.kind for pin in self.pins} != {"source", "dependency"}
                or len({pin.path for pin in self.pins}) != len(self.pins)):
            raise HostRejected("operator source/dependency inventory required")
        if (type(self.environment) is not tuple or len(self.environment) > 32
                or not all(type(item) is tuple and len(item) == 2 and
                           all(type(v) is str and len(v) <= 32768 for v in item)
                           for item in self.environment)
                or len(dict(self.environment)) != len(self.environment)):
            raise HostRejected("invalid operator environment")
        if not self.toolchain or not isinstance(self.toolchain, str):
            raise HostRejected("operator toolchain identity required")
        if (not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 120
                or type(self.stdout_limit) is not int or not 1024 <= self.stdout_limit <= 65536
                or type(self.stderr_limit) is not int or not 256 <= self.stderr_limit <= 16384):
            raise HostRejected("invalid process resource bounds")

    def identity(self) -> dict[str, Any]:
        return {"command": list(self.command), "executable_sha256": self.executable_sha256,
                "pins": [vars(pin) for pin in self.pins], "cwd": self.cwd,
                "environment_value_sha256": {key: _digest(value.encode()) for key, value in self.environment},
                "toolchain_operator_declared": self.toolchain, "timeout_seconds": self.timeout_seconds,
                "stdout_limit": self.stdout_limit, "stderr_limit": self.stderr_limit}

    @classmethod
    def load(cls, path: Path) -> "OperatorConfig":
        """Only service-launch code calls this; requests cannot select a config."""
        raw = path.read_bytes()
        if len(raw) > 8 * 1024 * 1024:
            raise HostRejected("operator config too large")
        item = _json(raw)
        expected = {"command", "executable_sha256", "pins", "cwd", "environment", "toolchain",
                    "timeout_seconds", "stdout_limit", "stderr_limit"}
        if type(item) is not dict or set(item) != expected:
            raise HostRejected("operator config shape")
        return cls(tuple(item["command"]), item["executable_sha256"],
                   tuple(Pin(**pin) for pin in item["pins"]), item["cwd"],
                   tuple(sorted(item["environment"].items())), item["toolchain"],
                   item["timeout_seconds"], item["stdout_limit"], item["stderr_limit"])


def _check_pins(config: OperatorConfig) -> None:
    pins = (Pin("source", config.command[0], config.executable_sha256), *config.pins)
    for pin in pins:
        path = Path(pin.path)
        if path.is_symlink() or not path.is_file() or _file_digest(path) != pin.sha256:
            raise HostRejected(f"pinned {pin.kind} identity differs: {pin.path}")


def operator_config_for_lean(*, executable: Path, main: Path, cwd: Path,
                             lean_path: str, source_files: tuple[Path, ...],
                             dependency_files: tuple[Path, ...], toolchain: str) -> OperatorConfig:
    """Operator bootstrap only; supplied inventories are not proved complete.

    `lean --deps Main` lists direct imports, not a complete transitive loading
    inventory. The operator must separately review its closure. This helper
    pins exactly the supplied sources/dependencies, Main, host and reference.
    """
    executable, main, cwd = (path.resolve(strict=True) for path in (executable, main, cwd))
    sources = {path.resolve(strict=True) for path in source_files}
    sources.update((main, Path(__file__).resolve(), Path(reference.__file__).resolve()))
    dependencies = {path.resolve(strict=True) for path in dependency_files}
    if not dependencies or sources & dependencies:
        raise HostRejected("distinct reviewed source/dependency inventories required")
    pins = tuple(Pin(kind, str(path), _file_digest(path))
                 for kind, paths in (("source", sources), ("dependency", dependencies))
                 for path in sorted(paths))
    return OperatorConfig((str(executable), "--run", str(main)), _file_digest(executable),
                          pins, str(cwd), (("LEAN_PATH", lean_path),), toolchain,
                          timeout_seconds=60)


def _bounded_process(config: OperatorConfig, framed: bytes) -> bytes:
    """Bound stdin, both output pipes and elapsed time, including blocked writes."""
    process = subprocess.Popen(config.command, cwd=config.cwd, env=dict(config.environment),
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    output, errors = bytearray(), bytearray()
    selector = selectors.DefaultSelector()
    deadline = time.monotonic() + config.timeout_seconds
    offset = 0
    try:
        for stream, event in ((process.stdin, selectors.EVENT_WRITE),
                              (process.stdout, selectors.EVENT_READ),
                              (process.stderr, selectors.EVENT_READ)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, event)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise HostRejected("verifier timeout")
            for key, _ in selector.select(min(remaining, 0.1)):
                stream = key.fileobj
                if stream is process.stdin:
                    try:
                        offset += os.write(stream.fileno(), framed[offset:])
                    except BrokenPipeError:
                        offset = len(framed)
                    if offset == len(framed):
                        selector.unregister(stream)
                        stream.close()
                else:
                    data = os.read(stream.fileno(), 4096)
                    target, limit = ((output, config.stdout_limit) if stream is process.stdout
                                     else (errors, config.stderr_limit))
                    target.extend(data)
                    if len(target) > limit:
                        raise HostRejected("verifier output bound exceeded")
                    if not data:
                        selector.unregister(stream)
                        stream.close()
        process.wait(timeout=max(0.001, deadline - time.monotonic()))
        if process.returncode != 0:
            raise HostRejected(f"verifier process failed: {process.returncode}")
        return bytes(output)
    except subprocess.TimeoutExpired as exc:
        raise HostRejected("verifier timeout") from exc
    finally:
        selector.close()
        # Terminate descendants as well, including a child retaining pipe FDs.
        # The leader may already have exited while a descendant detached its
        # pipes but remains in our session's group. Clean that group in either
        # case. A hostile descendant creating a new session remains out of scope.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def _validated_response(raw: bytes, output: bytes) -> dict[str, Any]:
    if not output.endswith(b"\n") or output.count(b"\n") != 1:
        raise HostRejected("expected exactly one newline-terminated response")
    response = _json(output)
    fields = {"accepted", "protocol", "policy", "raw_hex", "scientific_acceptance",
              "production_authority", "result", "error"}
    if (type(response) is not dict or set(response) != fields
            or type(response["accepted"]) is not bool or type(response["policy"]) is not int
            or response["protocol"] != PROTOCOL or response["policy"] != 1
            or response["raw_hex"] != raw.hex()
            or response["scientific_acceptance"] is not False
            or response["production_authority"] is not False or type(response["error"]) is not str):
        raise HostRejected("verifier response identity/scope mismatch")
    decision = reference.assess(raw)
    if response["accepted"] is not decision.accepted:
        raise HostRejected("Lean/reference acceptance disagreement")
    expected = None
    if decision.accepted:
        result = decision.result
        expected = {key: f"{result[key][0]}/{result[key][1]}" for key in
                    ("finalA", "finalB", "total", "lowerA", "upperA", "lowerB", "upperB")}
        expected.update(stepCount=result["referenceStep"], unitCode=result["unitCode"], physical=result["physical"])
        if response["error"] != "":
            raise HostRejected("accepted response has error")
    elif response["error"] != "decode_or_contract_rejection":
        raise HostRejected("unexpected rejection reason")
    # Canonical JSON distinguishes integer 1 from boolean true, unlike Python ==.
    if _canonical(response["result"]) != _canonical(expected):
        raise HostRejected("exact result mismatch")
    return response


class ReceiverService:
    """Operator instantiates once. Each request supplies bytes, never authority."""
    def __init__(self, config: OperatorConfig):
        self.config = config
        self._key = Ed25519PrivateKey.generate()

    @property
    def public_key_hex(self) -> str:
        return self._key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    def verify_path(self, path: Path) -> dict[str, Any]:
        # A regular-file snapshot only: FIFOs/devices cannot bypass the timeout
        # by blocking before verifier launch. Never reopen this path for replay.
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                    raise HostRejected("input must be a bounded regular file")
                raw = stream.read(MAX_BYTES + 1)
        except (OSError, HostRejected) as exc:
            return self._receipt(None, None, [f"input unavailable: {type(exc).__name__}"])
        return self.verify_bytes(raw)

    def verify_bytes(self, raw: bytes) -> dict[str, Any]:
        response, errors = None, []
        checks = {"pins_before": False, "pins_after": False, "response_checked": False}
        try:
            if type(raw) is not bytes or len(raw) > MAX_BYTES:
                raise HostRejected("request byte bound/type")
            _check_pins(self.config)
            checks["pins_before"] = True
            try:
                output = _bounded_process(self.config, struct.pack(">I", len(raw)) + raw)
            finally:
                _check_pins(self.config)
                checks["pins_after"] = True
            response = _validated_response(raw, output)
            checks["response_checked"] = True
        except (HostRejected, OSError, ValueError, TypeError, RecursionError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
        return self._receipt(raw if type(raw) is bytes and len(raw) <= MAX_BYTES else None, response, errors, checks)

    def _receipt(self, raw, response, errors, checks=None):
        identity = self.config.identity()
        receipt = {"format": "pcs-scientific-receiver-host-receipt-v1", "protocol": PROTOCOL,
                   "policy": 1, "accepted": not errors and response is not None and response["accepted"],
                   "scientific_acceptance": False, "production_authority": False,
                   "raw_hex": raw.hex() if raw is not None and len(raw) <= MAX_BYTES else None,
                   "raw_sha256": _digest(raw) if raw is not None else None,
                   "raw_bytes": len(raw) if raw is not None else None,
                   "verifier_response": response, "errors": errors,
                   "checks": checks or {"pins_before": False, "pins_after": False, "response_checked": False},
                   "operator_config_sha256": _digest(_canonical(identity)), "operator_identity": identity,
                   "trust_scope": "operator/host/OS/compiler/storage/key handling trusted; dependency closure completeness operator-asserted; hashes do not exclude transient substitution",
                   "signing_scope": "ephemeral service key; requires independent public-key pinning; no protected credential or historical occurrence attestation"}
        return {"receipt": receipt, "public_key_hex": self.public_key_hex,
                "signature_hex": self._key.sign(b"PCS-SCI-HOST-RECEIPT-V1\0" + _canonical(receipt)).hex()}


def replay_signed_receipt(envelope: dict[str, Any], expected_public_key_hex: str) -> bool:
    """Authenticate receipt bytes under an independently supplied ephemeral key."""
    try:
        if set(envelope) != {"receipt", "public_key_hex", "signature_hex"} or envelope["public_key_hex"] != expected_public_key_hex:
            return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(expected_public_key_hex)).verify(
            bytes.fromhex(envelope["signature_hex"]),
            b"PCS-SCI-HOST-RECEIPT-V1\0" + _canonical(envelope["receipt"]))
        receipt = envelope["receipt"]
        return (receipt["format"] == "pcs-scientific-receiver-host-receipt-v1"
                and receipt["scientific_acceptance"] is False and receipt["production_authority"] is False)
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operator-config", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    service = ReceiverService(OperatorConfig.load(args.operator_config))
    envelope = service.verify_path(args.request)
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(envelope, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return 0 if envelope["receipt"]["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
