"""PGSC6 fixed-policy, fail-closed state controller (research POSIX only).

The *public* promote() method invokes the actual Lean 4.28.0 V6 certificate
checker with a hard-coded mathematical policy, a store-derived generation, and
a store-derived active artifact. The untrusted caller may supply ONLY the
certificate bytes and an expected audited HEAD snapshot.

Trust assumptions NOT proved:
  - The Python process, Lean executable/source, and formal dependencies are
    trustworthy, not modifiable by the proposal process.
  - The store directory and its entire history cannot be replaced by someone
    with the same OS privileges. Cooperative flock is not a hostile writer ACL.
  - fsync/rename/file-descriptor IO behave as specified by the OS.
  - SHA-256 is not adversarially collided.
  - A full historical rollback is not detectable without external anchoring.
  - This does NOT turn mathematical Lean proofs into proof of Python/OS code.

Disk layout has canonical JSON genesis, atomic HEAD, append-only numbered
receipts, content-addressed artifacts/certificates, and a cooperating lock.
Crash after a receipt but before HEAD deliberately leaves the store unusable
until separately reviewed; there is no automatic insecure recovery.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import fcntl
import hashlib
import os
import stat
import subprocess
import tempfile
from typing import Iterator

from pgsc6_reference import Policy, decode_certificate, reference_certificate_passes
from pgsi2_wide_runtime import Arch, Wide, WireReject, decode, encode
from promotion_v2 import (
    Head, IntegrityFailure, StaleHead, ProposalRejected,
    canonical, strict_json, _read_regular, _write_once, _replace_head,
    require_hash, ZERO_HASH
)

VERSION = "pgsc6-pinned-v1"
ARTIFACT_PREFIX = b"PGSC6-ACTIVE-v1\x00"
CERT_PREFIX = b"PGSC6-CERT-v1\x00"
RECEIPT_PREFIX = b"PGSC6-RECEIPT-v1\x00"

# Policy is set by the controller's trusted code, independently of proposals.
# The Lean CLI separately uses compiled ProofGatedStrongGate.specWide.
ARCH = Arch(8, 32)
CORPUS = tuple(range(-4, 5))
LOW, HIGH = -(10**9), 10**9
TARGET_BYTES = b"PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2"
INITIAL_BYTES = b"PGSI2-WIDE|0"
POLICY = Policy(ARCH, decode(TARGET_BYTES, ARCH), CORPUS, LOW, HIGH)
RESEARCH = Path(__file__).resolve().parent
FORMAL_DIR = RESEARCH.parents[1] / "formal"
ORACLE = RESEARCH / "pgsc6_actual_lean_oracle.lean"

MAX_CERT_BYTES = 65536
MAX_MODEL_BYTES = 65536
MAX_RECEIPT_BYTES = 4096
MAX_ORACLE_BYTES = 65536


def digest(domain: bytes, raw: bytes) -> str:
    return hashlib.sha256(domain + raw).hexdigest()


POLICY_DIGEST = digest(b"PGSC6-POLICY-v1\x00", canonical({
    "version": VERSION,
    "max_width": ARCH.max_width,
    "max_abs_parameter": ARCH.bound,
    "target": TARGET_BYTES.decode("ascii"),
    "corpus": list(CORPUS),
    "low": LOW, "high": HIGH,
    "predicate": 1,
}))


def _regular_dir(path: Path) -> None:
    if path.is_symlink() or not path.is_dir() or path.resolve() != path:
        raise IntegrityFailure("linked or missing protected directory")


def _lockfile(path: Path) -> int:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise IntegrityFailure("unsafe lock file")
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
    opened = os.fstat(fd)
    if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino) or (
        opened.st_nlink != 1 or not stat.S_ISREG(opened.st_mode)
    ):
        os.close(fd)
        raise IntegrityFailure("lock substituted")
    return fd


@dataclass(frozen=True)
class PinnedSnapshot:
    head: Head
    raw: bytes
    model: Wide

    def predict(self, x: int) -> int:
        return self.model.predict(x)


class PinnedPGSC6Store:
    def __init__(self, root: Path):
        if os.name != "posix":
            raise IntegrityFailure("POSIX experimental host required")
        self.root = Path(root).absolute()

    @staticmethod
    def _artifact_digest(raw: bytes) -> str:
        return digest(ARTIFACT_PREFIX, raw)

    @staticmethod
    def _certificate_digest(raw: bytes) -> str:
        return digest(CERT_PREFIX, raw)

    @staticmethod
    def _receipt_digest(raw: bytes) -> str:
        return digest(RECEIPT_PREFIX, raw)

    def _dirs(self) -> None:
        _regular_dir(self.root)
        for folder in ("models", "certificates", "receipts"):
            _regular_dir(self.root / folder)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self._dirs()
        fd = _lockfile(self.root / ".lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _model_path(self, name: str) -> Path:
        require_hash(name)
        return self.root / "models" / (name + ".pgsi2")

    def _cert_path(self, name: str) -> Path:
        require_hash(name)
        return self.root / "certificates" / (name + ".pgsc6")

    def _model(self, name: str) -> bytes:
        raw = _read_regular(self._model_path(name), MAX_MODEL_BYTES)
        if self._artifact_digest(raw) != name:
            raise IntegrityFailure("model content digest mismatch")
        try:
            m = decode(raw, ARCH, max_bytes=MAX_MODEL_BYTES)
        except (WireReject, ValueError, TypeError) as exc:
            raise IntegrityFailure("invalid model in store") from exc
        if encode(m) != raw:
            raise IntegrityFailure("noncanonical active model")
        return raw

    def _cert(self, name: str) -> bytes:
        raw = _read_regular(self._cert_path(name), MAX_CERT_BYTES)
        if self._certificate_digest(raw) != name:
            raise IntegrityFailure("certificate content digest mismatch")
        return raw

    def _write_artifact(self, raw: bytes) -> str:
        if type(raw) is not bytes or not raw or len(raw) > MAX_MODEL_BYTES:
            raise IntegrityFailure("invalid model artifact bytes")
        name = self._artifact_digest(raw)
        path = self._model_path(name)
        if not path.exists() and not path.is_symlink():
            _write_once(path, raw)
        if self._model(name) != raw:
            raise IntegrityFailure("colliding/substituted model")
        return name

    def _write_certificate(self, raw: bytes) -> str:
        if type(raw) is not bytes or not raw or len(raw) > MAX_CERT_BYTES:
            raise IntegrityFailure("invalid certificate bytes")
        name = self._certificate_digest(raw)
        path = self._cert_path(name)
        if not path.exists() and not path.is_symlink():
            _write_once(path, raw)
        if self._cert(name) != raw:
            raise IntegrityFailure("colliding/substituted certificate")
        return name

    @staticmethod
    def _oracle_digest() -> str:
        return hashlib.sha256(_read_regular(ORACLE, MAX_ORACLE_BYTES)).hexdigest()

    @staticmethod
    def _formal_source_digest() -> str:
        """Detect accidental V6 source/config drift since store initialization.

        This is NOT a binary/oleans attestation, signature, or protection
        against an adversary able to rewrite the store and its genesis.
        """
        project = FORMAL_DIR
        sources = sorted((project / "PCS" / "V2").glob("ProofGated*.lean"))
        essentials = [project / "lean-toolchain", project / "lakefile.toml",
                      project / "lake-manifest.json"]
        if len(sources) < 14:
            raise IntegrityFailure("missing formal certificate source closure")
        h = hashlib.sha256(b"PGSC6-FORMAL-SOURCES-v1\x00")
        for path in sorted([*sources, *essentials]):
            if not path.is_relative_to(project):
                raise IntegrityFailure("formal source escaped project")
            raw = _read_regular(path, 1024 * 1024)
            h.update(str(path.relative_to(project)).encode("utf-8") + b"\x00")
            h.update(hashlib.sha256(raw).digest())
        return h.hexdigest()

    @classmethod
    def initialize(cls, root: Path) -> "PinnedPGSC6Store":
        """Create new unowned directory; never reinitialize existing state."""
        root = Path(root).absolute()
        root.mkdir(mode=0o700, exist_ok=False, parents=False)
        os.chmod(root, 0o700)
        for name in ("models", "certificates", "receipts"):
            (root / name).mkdir(mode=0o700)
        _write_once(root / ".lock", b"")
        store = cls(root)
        with store._locked():
            base = store._write_artifact(INITIAL_BYTES)
            oracle_hash = store._oracle_digest()
            _write_once(root / "GENESIS.json", canonical({
                "version": VERSION, "policy_sha256": POLICY_DIGEST,
                "oracle_sha256": oracle_hash, "formal_sources_sha256": store._formal_source_digest(),
                "initial_model_sha256": base,
            }))
            _write_once(root / "HEAD.json", canonical(Head(
                0, base, POLICY_DIGEST, ZERO_HASH
            ).__dict__))
        return store

    def _audit_locked(self) -> Head:
        self._dirs()
        genesis = strict_json(_read_regular(self.root / "GENESIS.json", MAX_RECEIPT_BYTES))
        if type(genesis) is not dict or set(genesis) != {
            "version", "policy_sha256", "oracle_sha256", "initial_model_sha256"
        } or genesis["version"] != VERSION or genesis["policy_sha256"] != POLICY_DIGEST:
            raise IntegrityFailure("genesis does not match fixed policy")
        if genesis["oracle_sha256"] != self._oracle_digest():
            raise IntegrityFailure("Lean oracle source changed since genesis")
        if genesis["formal_sources_sha256"] != self._formal_source_digest():
            raise IntegrityFailure("Lean formal source/configuration changed since genesis")
        previous = genesis["initial_model_sha256"]
        require_hash(previous)
        self._model(previous)
        head = Head.parse(strict_json(_read_regular(self.root / "HEAD.json", MAX_RECEIPT_BYTES)))
        if head.policy_sha256 != POLICY_DIGEST:
            raise IntegrityFailure("head policy mismatch")
        names = {p.name for p in (self.root / "receipts").iterdir()}
        expected_names = {f"{i:08d}.json" for i in range(1, head.generation + 1)}
        if names != expected_names:
            raise IntegrityFailure("missing/orphaned receipt: fail closed on crash/rollback")
        last_receipt = ZERO_HASH
        for generation in range(1, head.generation + 1):
            path = self.root / "receipts" / f"{generation:08d}.json"
            receipt_raw = _read_regular(path, MAX_RECEIPT_BYTES)
            record = strict_json(receipt_raw)
            if not isinstance(record, dict) or set(record) != {
                "version", "generation", "previous_model_sha256",
                "candidate_model_sha256", "certificate_sha256", "policy_sha256",
                "previous_receipt_sha256", "oracle_sha256", "verification"
            } or record != {
                "version": VERSION,
                "generation": generation,
                "previous_model_sha256": previous,
                "candidate_model_sha256": record.get("candidate_model_sha256"),
                "certificate_sha256": record.get("certificate_sha256"),
                "policy_sha256": POLICY_DIGEST,
                "previous_receipt_sha256": last_receipt,
                "oracle_sha256": genesis["oracle_sha256"],
                "verification": "real-Lean-PGSC6-accepted; unsigned research record",
            }:
                raise IntegrityFailure("invalid receipt chain")
            candidate_name = record["candidate_model_sha256"]
            certificate_name = record["certificate_sha256"]
            require_hash(candidate_name)
            require_hash(certificate_name)
            candidate = self._model(candidate_name)
            cert_raw = self._cert(certificate_name)
            if not reference_certificate_passes(cert_raw, POLICY, generation-1,
                                                self._model(previous)):
                raise IntegrityFailure("receipt evidence no longer replays")
            parsed = decode_certificate(cert_raw)
            if parsed.candidate != candidate:
                raise IntegrityFailure("receipt candidate mismatch")
            previous = candidate_name
            last_receipt = self._receipt_digest(receipt_raw)
        if head.active_sha256 != previous or head.last_receipt_sha256 != last_receipt:
            raise IntegrityFailure("head/receipt divergence")
        self._model(head.active_sha256)
        return head

    def audit(self) -> Head:
        with self._locked():
            return self._audit_locked()

    def snapshot(self, expected: Head | None = None) -> PinnedSnapshot:
        with self._locked():
            head = self._audit_locked()
            if expected is not None and expected != head:
                raise StaleHead("stale inference expectation")
            raw = self._model(head.active_sha256)
            return PinnedSnapshot(head, raw, decode(raw, ARCH))

    def _real_lean_authorizes(self, generation: int, active: bytes,
                              certificate: bytes) -> bool:
        """No public verifier substitution. Only fixed-source actual Lean oracle."""
        # Audit the file again immediately before constructing the process.
        with tempfile.TemporaryDirectory(prefix="pgsc6-verify-", dir=self.root) as tmp:
            d = Path(tmp)
            old_path = d / "active.pgsi2"
            cert_path = d / "candidate.pgsc6"
            _write_once(old_path, active)
            _write_once(cert_path, certificate)
            # No shell, fixed CLI and source. Source/dependencies/OS remain trusted.
            proc = subprocess.run(
                ["lake", "env", "lean", "--run", str(ORACLE), "check",
                 str(generation), str(old_path), str(cert_path)],
                cwd=FORMAL_DIR,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                check=False,
            )
            if _read_regular(old_path, MAX_MODEL_BYTES) != active or (
                _read_regular(cert_path, MAX_CERT_BYTES) != certificate
            ):
                raise IntegrityFailure("verification snapshot changed")
            if proc.stderr or proc.returncode not in (0, 1):
                raise IntegrityFailure("Lean executable failed or produced errors")
            if proc.returncode == 0:
                return proc.stdout == b"ACCEPT_PGSC6\n"
            return False

    def promote(self, certificate_bytes: bytes, expected: Head) -> Head:
        """Only proposer input is PGSC6 certificate bytes; policy stays fixed."""
        if type(certificate_bytes) is not bytes or len(certificate_bytes) > MAX_CERT_BYTES:
            raise ProposalRejected("invalid certificate byte type/size")
        if type(expected) is not Head:
            raise TypeError("expected an audited Head")
        with self._locked():
            head = self._audit_locked()
            if head != expected:
                raise StaleHead("stale generation/active/policy head")
            old_bytes = self._model(head.active_sha256)
            if not reference_certificate_passes(
                certificate_bytes, POLICY, head.generation, old_bytes
            ):
                raise ProposalRejected("certificate fails independent fixed-policy prefilter")
            parsed = decode_certificate(certificate_bytes)
            try:
                candidate = decode(parsed.candidate, ARCH)
            except WireReject as exc:
                raise ProposalRejected("candidate is not canonical") from exc
            # Fresh second-environment Lean execution required.
            if not self._real_lean_authorizes(head.generation, old_bytes, certificate_bytes):
                raise ProposalRejected("actual Lean V6 checker refused candidate")
            if self._model(head.active_sha256) != old_bytes or (
                self._audit_locked() != head
            ) or self._oracle_digest() != strict_json(
                _read_regular(self.root / "GENESIS.json", MAX_RECEIPT_BYTES)
            )["oracle_sha256"]:
                raise IntegrityFailure("verified incumbent or authority changed")
            candidate_bytes = encode(candidate)
            new_name = self._write_artifact(candidate_bytes)
            cert_name = self._write_certificate(certificate_bytes)
            receipt = {
                "version": VERSION, "generation": head.generation + 1,
                "previous_model_sha256": head.active_sha256,
                "candidate_model_sha256": new_name,
                "certificate_sha256": cert_name,
                "policy_sha256": POLICY_DIGEST,
                "previous_receipt_sha256": head.last_receipt_sha256,
                "oracle_sha256": self._oracle_digest(),
                "verification": "real-Lean-PGSC6-accepted; unsigned research record",
            }
            raw = canonical(receipt)
            receipt_name = self._receipt_digest(raw)
            _write_once(self.root / "receipts" / f"{head.generation+1:08d}.json", raw)
            next_head = Head(head.generation+1, new_name, POLICY_DIGEST, receipt_name)
            _replace_head(self.root / "HEAD.json", canonical(next_head.__dict__))
            return next_head
