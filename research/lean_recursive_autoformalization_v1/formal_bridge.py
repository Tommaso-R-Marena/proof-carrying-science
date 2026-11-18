"""Bridge from Python capability vectors to the Lean PGRA acceptance gate.

The Lean CLI (`PCS.V2.ProofGatedFormalizationArtifacts`) is the reference
authority for ACCEPT/REJECT. Python only proposes wire bytes and invokes:

  cd research/lean_recursive_autoformalization_v1/lean && \\
    lake env lean --run PCS/V2/ProofGatedFormalizationArtifacts.lean \\
      <old.pgra> <new.pgra>

Wire format (exact UTF-8, no trailing newline):
  PGRA1|<code>,<code>,...
where codes are CaseStatus.toNat: fail=0, abstain=1, supported=2.

The Lean package lives under this research directory (not formal/PCS/V2/) so the
frozen V7 ProofGated*.lean census is undisturbed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
import os
import subprocess
import tempfile
from typing import Iterable, Sequence

WIRE_MAGIC = "PGRA1"

# formal/ relative to this file: research/lean_recursive_autoformalization_v1/ -> ../../formal
_REPO_ROOT = Path(__file__).resolve().parents[2]
_FORMAL_DIR = _REPO_ROOT / "formal"
_ARTIFACTS_LEAN = "PCS/V2/ProofGatedFormalizationArtifacts.lean"


class CaseStatus(IntEnum):
    FAIL = 0
    ABSTAIN = 1
    SUPPORTED = 2


Capability = tuple[CaseStatus, ...]


def encode_capability(cap: Sequence[CaseStatus | int]) -> bytes:
    """Canonical PGRA1 wire bytes (no trailing newline)."""
    codes: list[str] = []
    for s in cap:
        n = int(s)
        if n not in (0, 1, 2):
            raise ValueError(f"invalid CaseStatus code: {n}")
        codes.append(str(n))
    body = ",".join(codes)
    return f"{WIRE_MAGIC}|{body}".encode("ascii")


def decode_capability(raw: bytes | str) -> Capability:
    text = raw.decode("ascii") if isinstance(raw, (bytes, bytearray)) else raw
    if not text.startswith(f"{WIRE_MAGIC}|"):
        raise ValueError("bad magic")
    body = text[len(WIRE_MAGIC) + 1 :]
    if body == "":
        return ()
    out: list[CaseStatus] = []
    for part in body.split(","):
        if part != str(int(part)) or int(part) not in (0, 1, 2):
            raise ValueError(f"noncanonical status token: {part!r}")
        out.append(CaseStatus(int(part)))
    return tuple(out)


def loss(cap: Sequence[CaseStatus | int]) -> int:
    return sum(1 for s in cap if int(s) == CaseStatus.FAIL)


def preserves(old: Sequence[CaseStatus | int], new: Sequence[CaseStatus | int]) -> bool:
    if len(old) != len(new):
        return False
    for a, b in zip(old, new):
        if int(a) != CaseStatus.FAIL and int(b) != int(a):
            return False
    return True


def expands(old: Sequence[CaseStatus | int], new: Sequence[CaseStatus | int]) -> bool:
    if len(old) != len(new):
        return False
    return any(int(a) == CaseStatus.FAIL and int(b) != CaseStatus.FAIL for a, b in zip(old, new))


def python_accept(old: Sequence[CaseStatus | int], new: Sequence[CaseStatus | int]) -> bool:
    """Shadow checker (not authority). Matches Lean `accept` on equal-length vectors."""
    return preserves(old, new) and expands(old, new) and loss(new) < loss(old)


@dataclass(frozen=True)
class LeanVerdict:
    accepted: bool
    stdout: str
    stderr: str
    returncode: int
    old_wire: bytes
    new_wire: bytes


def _lean_env() -> dict[str, str]:
    env = os.environ.copy()
    elan = str(Path.home() / ".elan" / "bin")
    path = env.get("PATH", "")
    if elan not in path.split(os.pathsep):
        env["PATH"] = elan + os.pathsep + path
    return env


def lean_accept_wire(old_wire: bytes, new_wire: bytes, *, timeout: float = 120.0) -> LeanVerdict:
    """Invoke `lake env lean --run` on the artifacts CLI. Fail-closed on errors."""
    if not _FORMAL_DIR.is_dir():
        raise FileNotFoundError(f"formal directory not found: {_FORMAL_DIR}")
    with tempfile.TemporaryDirectory(prefix="pgra-") as tmp:
        tmp_path = Path(tmp)
        old_path = tmp_path / "old.pgra"
        new_path = tmp_path / "new.pgra"
        old_path.write_bytes(old_wire)
        new_path.write_bytes(new_wire)
        cmd = [
            "lake",
            "env",
            "lean",
            "--run",
            _ARTIFACTS_LEAN,
            str(old_path),
            str(new_path),
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(_FORMAL_DIR),
            env=_lean_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        accepted = proc.returncode == 0 and out == "ACCEPT"
        return LeanVerdict(accepted, out, err, proc.returncode, old_wire, new_wire)


def lean_accept(old: Sequence[CaseStatus | int], new: Sequence[CaseStatus | int], **kwargs) -> LeanVerdict:
    return lean_accept_wire(encode_capability(old), encode_capability(new), **kwargs)


def typecheck_core(*, timeout: float = 300.0) -> subprocess.CompletedProcess[str]:
    """Typecheck the self-contained core module via lake env lean."""
    cmd = ["lake", "env", "lean", "PCS/V2/ProofGatedFormalization.lean"]
    return subprocess.run(
        cmd,
        cwd=str(_FORMAL_DIR),
        env=_lean_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def build_modules(modules: Iterable[str] | None = None, *, timeout: float = 600.0) -> subprocess.CompletedProcess[str]:
    """`lake build` one or more PCS.V2 PGRA modules."""
    mods = list(modules) if modules is not None else [
        "PCS.V2.ProofGatedFormalization",
        "PCS.V2.ProofGatedFormalizationArtifacts",
    ]
    cmd = ["lake", "build", *mods]
    return subprocess.run(
        cmd,
        cwd=str(_FORMAL_DIR),
        env=_lean_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _demo() -> int:
    old = (CaseStatus.FAIL, CaseStatus.FAIL, CaseStatus.FAIL, CaseStatus.ABSTAIN)
    new = (CaseStatus.SUPPORTED, CaseStatus.FAIL, CaseStatus.FAIL, CaseStatus.ABSTAIN)
    print("wire old:", encode_capability(old).decode())
    print("wire new:", encode_capability(new).decode())
    print("python_accept:", python_accept(old, new))
    print("typecheck_core …")
    tc = typecheck_core()
    print("typecheck returncode:", tc.returncode)
    if tc.stdout:
        print(tc.stdout[-2000:])
    if tc.stderr:
        print(tc.stderr[-2000:])
    if tc.returncode != 0:
        return tc.returncode
    print("lean_accept …")
    v = lean_accept(old, new)
    print("lean:", v.stdout, "rc=", v.returncode, "accepted=", v.accepted)
    if v.stderr:
        print(v.stderr[-2000:])
    return 0 if v.accepted else 1


if __name__ == "__main__":
    raise SystemExit(_demo())
