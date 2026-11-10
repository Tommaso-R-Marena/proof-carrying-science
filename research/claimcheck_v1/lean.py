"""Generate and check per-claim Lean obligations against the fixed checker.

The generated file is: the reviewed checker text (byte-identical, digest pinned),
one data numeral, one claim record and one theorem

    theorem pcs_claim_outcome : run pcs_src pcs_claim = <outcome> := by decide +kernel

Nothing proposed by a model or read from a paper is ever emitted as Lean syntax
other than (a) numerals and (b) string literals drawn from a conservative
character whitelist (anything else is emitted as an explicit byte list).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from .oracle import Outcome
from .spec import ClaimSpec, Cond, sha256_hex

FORMAL_DIR = Path(__file__).resolve().parent / "formal"
CHECKER_PATH = FORMAL_DIR / "ClaimCheck.lean"
CHECKER_PIN_PATH = FORMAL_DIR / "ClaimCheck.lean.sha256"
THEOREM = "pcs_claim_outcome"
TOOLCHAIN = "4.28.0"
ALLOWED_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
MAX_DATA_BYTES = 65536
DEFAULT_TIMEOUT = 600

_SAFE_STRING = re.compile(r"[A-Za-z0-9 _.,:;()\[\]%/+\-#=<>&*!?@^|~]*\Z")
_STAT_LEAN = {
    "count": ".count", "sum": ".sum", "mean": ".mean", "median": ".median", "min": ".min", "max": ".max",
    "var_sample": ".varSample", "sd_sample": ".sdSample", "sd_pop": ".sdPop", "sem": ".sem",
}
_CMP_LEAN = {"eq": ".eq", "ne": ".ne", "lt": ".lt", "le": ".le", "gt": ".gt", "ge": ".ge"}


class LeanUnavailable(RuntimeError):
    pass


def checker_text() -> str:
    """The reviewed checker source; refuses to run if it differs from its pinned digest."""
    raw = CHECKER_PATH.read_bytes()
    pinned = CHECKER_PIN_PATH.read_text(encoding="ascii").split()[0]
    if sha256_hex(raw) != pinned:
        raise LeanUnavailable("ClaimCheck.lean does not match its pinned SHA-256; refusing to use it")
    return raw.decode("utf-8")


def checker_sha256() -> str:
    return CHECKER_PIN_PATH.read_text(encoding="ascii").split()[0]


def lean_bytes(text: str) -> str:
    """A Lean term of type ``List Nat`` equal to the UTF-8 bytes of ``text``."""
    if _SAFE_STRING.match(text):
        return f'b "{text}"'
    return "[" + ", ".join(str(x) for x in text.encode("utf-8")) + "]"


def lean_rat(q: Fraction) -> str:
    return f"(({q.numerator} : Rat) / {q.denominator})"


def _cond(c: Cond) -> str:
    if c.kind == "text_eq":
        return f".textEq ({lean_bytes(c.column)}) ({lean_bytes(c.value)})"
    if c.kind == "text_ne":
        return f".textNe ({lean_bytes(c.column)}) ({lean_bytes(c.value)})"
    return f".num ({lean_bytes(c.column)}) {_CMP_LEAN[c.cmp]} {lean_rat(Fraction(c.value))}"


def _conds(cs: tuple[Cond, ...]) -> str:
    return "[" + ", ".join(_cond(c) for c in cs) + "]"


def lean_claim(spec: ClaimSpec, na_tokens: tuple[str, ...], scale: Fraction) -> str:
    if spec.stat == "share":
        stat = f".share {_conds(spec.sub_filter)}"
    elif spec.stat == "pearson":
        stat = f".pearson ({lean_bytes(spec.x_column)})"
    elif spec.stat == "ols_slope":
        stat = f".olsSlope ({lean_bytes(spec.x_column)})"
    elif spec.stat == "ols_intercept":
        stat = f".olsIntercept ({lean_bytes(spec.x_column)})"
    else:
        stat = _STAT_LEAN[spec.stat]
    column = "none" if spec.column is None else f"some ({lean_bytes(spec.column)})"
    na = "[" + ", ".join(lean_bytes(t) for t in na_tokens) + "]"
    return (
        "{ column := " + column + ",\n"
        "    filter := " + _conds(spec.filter) + ",\n"
        "    stat := " + stat + ",\n"
        "    naTokens := " + na + ",\n"
        "    scale := " + lean_rat(scale) + ",\n"
        "    reported := " + lean_bytes(spec.reported) + " }"
    )


def lean_outcome(o: Outcome) -> str:
    if not o.defined:
        return f".undefined .{o.reason}"
    if o.value_kind == "rat":
        value = f"(.rat {lean_rat(o.value)})"
    else:
        value = f"(.sqrt ({o.sign} : Int) {lean_rat(o.value)})"
    return f".checked .{o.verdict} {value} {o.used} {o.missing}"


def obligation_tail(data: bytes, spec: ClaimSpec, na_tokens: tuple[str, ...], scale: Fraction, outcome: Outcome) -> str:
    """Everything after the checker text.  Deterministic in its arguments."""
    numeral = "0x" + (data.hex() or "0")
    return (
        "\n-- ===== generated obligation (data numeral, claim, expected outcome) =====\n"
        "open PCS.ClaimCheck\n\n"
        f"def pcs_src : Source := ⟨{numeral}, {len(data)}⟩\n\n"
        "def pcs_claim : Claim :=\n"
        f"  {lean_claim(spec, na_tokens, scale)}\n\n"
        f"theorem {THEOREM} : run pcs_src pcs_claim = {lean_outcome(outcome)} := by decide +kernel\n\n"
        f"#print axioms {THEOREM}\n"
    )


def obligation_source(data: bytes, spec: ClaimSpec, na_tokens: tuple[str, ...], scale: Fraction, outcome: Outcome) -> str:
    if len(data) > MAX_DATA_BYTES:
        raise ValueError("data file exceeds the kernel-check size bound")
    return checker_text() + obligation_tail(data, spec, na_tokens, scale, outcome)


def find_lean() -> str:
    exe = os.environ.get("PCS_CLAIMCHECK_LEAN") or shutil.which("lean")
    if not exe:
        raise LeanUnavailable("no `lean` executable found (set PCS_CLAIMCHECK_LEAN or PATH)")
    return exe


_VERSION_CACHE: dict[str, str] = {}


def lean_version(exe: str) -> str:
    if exe not in _VERSION_CACHE:
        try:
            out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60, check=False).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise LeanUnavailable(f"cannot run lean: {type(exc).__name__}") from None
        if f"version {TOOLCHAIN}," not in out:
            raise LeanUnavailable(f"Lean {TOOLCHAIN} is required; found: {out[:80]!r}")
        _VERSION_CACHE[exe] = out
    return _VERSION_CACHE[exe]


@dataclass(frozen=True)
class LeanResult:
    accepted: bool
    axioms: tuple[str, ...]
    seconds: float
    toolchain: str
    source_sha256: str
    detail: str

    def to_json(self) -> dict:
        return {
            "kernel_accepted": self.accepted, "axioms": list(self.axioms), "seconds": round(self.seconds, 3),
            "toolchain": self.toolchain, "obligation_sha256": self.source_sha256, "detail": self.detail,
            "theorem": THEOREM, "tactic": "decide +kernel",
        }


_AXIOM_LINE = re.compile(r"'" + THEOREM + r"' depends on axioms: \[([A-Za-z0-9_., ]*)\]\Z")
_NO_AXIOM_LINE = "'" + THEOREM + "' does not depend on any axioms"


def check_source(source: str, *, timeout: int = DEFAULT_TIMEOUT, keep: Path | None = None) -> LeanResult:
    """Run the real Lean compiler on one obligation.  Fail closed on anything unexpected."""
    exe = find_lean()
    version = lean_version(exe)
    digest = sha256_hex(source.encode("utf-8"))
    forbidden = ("sorry", "native_decide", "axiom ", "unsafe ", "implemented_by", "extern ", "partial ", "ofReduceBool")
    tail = re.sub(r'"[^"\n]*"', '""', source[len(checker_text()):])  # string literals cannot contain quotes
    if any(word in tail for word in forbidden):
        return LeanResult(False, (), 0.0, version, digest, "generated obligation contains a forbidden token")
    with tempfile.TemporaryDirectory(prefix="pcs-claimcheck-") as tmp:
        path = Path(tmp) / "Obligation.lean"
        path.write_text(source, encoding="utf-8")
        if keep is not None:
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.write_text(source, encoding="utf-8")
        start = time.monotonic()
        try:
            proc = subprocess.run(
                [exe, str(path)], capture_output=True, text=True, timeout=timeout, check=False, cwd=tmp,
                env={"PATH": os.environ.get("PATH", ""), "HOME": tmp, "LANG": "C.UTF-8"},
            )
        except subprocess.TimeoutExpired:
            return LeanResult(False, (), time.monotonic() - start, version, digest, f"Lean timed out after {timeout}s")
        seconds = time.monotonic() - start
    out = proc.stdout.strip()
    if proc.returncode != 0:
        first = (out or proc.stderr.strip()).splitlines()[:1]
        return LeanResult(False, (), seconds, version, digest, "Lean rejected the obligation: " + (first[0][:240] if first else "no output"))
    if proc.stderr.strip():
        return LeanResult(False, (), seconds, version, digest, "unexpected Lean diagnostics on stderr")
    if out == _NO_AXIOM_LINE:
        axioms: tuple[str, ...] = ()
    else:
        m = _AXIOM_LINE.match(out)
        if not m:
            return LeanResult(False, (), seconds, version, digest, "unexpected Lean output (warnings or extra messages)")
        axioms = tuple(a.strip() for a in m.group(1).split(",") if a.strip())
    if not set(axioms) <= ALLOWED_AXIOMS:
        return LeanResult(False, axioms, seconds, version, digest, "theorem depends on a non-standard axiom")
    return LeanResult(True, axioms, seconds, version, digest, "kernel accepted")
