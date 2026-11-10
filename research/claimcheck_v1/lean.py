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
THEOREM_PREFIX = "pcs_claim_"
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


def batch_tail(data: bytes, items: list[tuple[ClaimSpec, tuple[str, ...], Fraction, Outcome]]) -> str:
    """Everything after the checker text for one batch of claims about one data file.

    ``pcs_batch`` makes the kernel parse the bytes once and evaluate every claim; each
    ``pcs_claim_i`` is then the stand-alone statement ``run pcs_src pcs_c<i> = <outcome>``, obtained
    through the general lemma ``run_of_runAll`` proved in the checker.  Deterministic in its arguments.
    """
    if not items:
        raise ValueError("empty batch")
    numeral = "0x" + (data.hex() or "0")
    parts = [
        "\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n"
        "open PCS.ClaimCheck\n\n"
        f"def pcs_src : Source := ⟨{numeral}, {len(data)}⟩\n\n"
    ]
    for i, (spec, na, scale, _outcome) in enumerate(items):
        parts.append(f"def pcs_c{i} : Claim :=\n  {lean_claim(spec, na, scale)}\n\n")
    claims = ", ".join(f"pcs_c{i}" for i in range(len(items)))
    outcomes = ",\n    ".join(lean_outcome(o) for _s, _n, _k, o in items)
    parts.append(f"theorem pcs_batch : runAll pcs_src [{claims}] =\n    [{outcomes}] := by decide +kernel\n\n")
    for i, (_s, _n, _k, outcome) in enumerate(items):
        parts.append(f"theorem pcs_claim_{i} : run pcs_src pcs_c{i} = {lean_outcome(outcome)} :=\n"
                     f"  run_of_runAll pcs_batch {i} rfl rfl\n#print axioms pcs_claim_{i}\n\n")
    return "".join(parts)


def batch_source(data: bytes, items: list[tuple[ClaimSpec, tuple[str, ...], Fraction, Outcome]]) -> str:
    if len(data) > MAX_DATA_BYTES:
        raise ValueError("data file exceeds the kernel-check size bound")
    return checker_text() + batch_tail(data, items)


def obligation_source(data: bytes, spec: ClaimSpec, na_tokens: tuple[str, ...], scale: Fraction, outcome: Outcome) -> str:
    """A batch of one."""
    return batch_source(data, [(spec, na_tokens, scale, outcome)])


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
    claims: int = 1

    def to_json(self, index: int = 0) -> dict:
        return {
            "kernel_accepted": self.accepted, "axioms": list(self.axioms), "batch_seconds": round(self.seconds, 3),
            "batch_size": self.claims, "index": index, "theorem": f"{THEOREM_PREFIX}{index}",
            "statement": f"run pcs_src pcs_c{index} = <expected outcome>",
            "toolchain": self.toolchain, "obligation_sha256": self.source_sha256, "detail": self.detail,
            "tactic": "decide +kernel (in pcs_batch), then run_of_runAll",
        }


_AXIOM_LINE = re.compile(r"'" + THEOREM_PREFIX + r"(\d+)' depends on axioms: \[([A-Za-z0-9_., ]*)\]\Z")
_NO_AXIOM_LINE = re.compile(r"'" + THEOREM_PREFIX + r"(\d+)' does not depend on any axioms\Z")


def check_source(source: str, *, claims: int = 1, timeout: int = DEFAULT_TIMEOUT, keep: Path | None = None) -> LeanResult:
    """Run the real Lean compiler on one obligation file.  Fail closed on anything unexpected.

    Accepted only if Lean exits 0, prints nothing on stderr, and prints exactly one axiom report per
    claim theorem, in order, each naming only standard axioms.
    """
    exe = find_lean()
    version = lean_version(exe)
    digest = sha256_hex(source.encode("utf-8"))
    forbidden = ("sorry", "native_decide", "axiom ", "unsafe ", "implemented_by", "extern ", "partial ", "ofReduceBool")
    tail = re.sub(r'"[^"\n]*"', '""', source[len(checker_text()):])  # string literals cannot contain quotes
    if any(word in tail for word in forbidden):
        return LeanResult(False, (), 0.0, version, digest, "generated obligation contains a forbidden token", claims)
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
            return LeanResult(False, (), time.monotonic() - start, version, digest, f"Lean timed out after {timeout}s", claims)
        seconds = time.monotonic() - start
    out = proc.stdout.strip()
    if proc.returncode != 0:
        first = (out or proc.stderr.strip()).splitlines()[:1]
        return LeanResult(False, (), seconds, version, digest,
                          "Lean rejected the obligation: " + (first[0][:240] if first else "no output"), claims)
    if proc.stderr.strip():
        return LeanResult(False, (), seconds, version, digest, "unexpected Lean diagnostics on stderr", claims)
    lines = out.splitlines()
    if len(lines) != claims:
        return LeanResult(False, (), seconds, version, digest, "unexpected Lean output (warnings or extra messages)", claims)
    used: set[str] = set()
    for i, line in enumerate(lines):
        m = _AXIOM_LINE.match(line)
        if m:
            if int(m.group(1)) != i:
                return LeanResult(False, (), seconds, version, digest, "axiom reports out of order", claims)
            used |= {a.strip() for a in m.group(2).split(",") if a.strip()}
        else:
            m = _NO_AXIOM_LINE.match(line)
            if not m or int(m.group(1)) != i:
                return LeanResult(False, (), seconds, version, digest, "unexpected Lean output (warnings or extra messages)", claims)
    if not used <= ALLOWED_AXIOMS:
        return LeanResult(False, tuple(sorted(used)), seconds, version, digest, "a theorem depends on a non-standard axiom", claims)
    return LeanResult(True, tuple(sorted(used)), seconds, version, digest, "kernel accepted", claims)


def check_items(data: bytes, items: list[tuple[ClaimSpec, tuple[str, ...], Fraction, Outcome]], *, timeout: int = DEFAULT_TIMEOUT,
                keep_dir: Path | None = None, name: str = "batch") -> list[dict]:
    """Kernel-check a batch; if the batch is rejected, re-check every claim alone so that one wrong
    prediction cannot block (or hide behind) the others.  Returns one JSON record per item."""
    keep = None if keep_dir is None else keep_dir / f"{name}.lean"
    res = check_source(batch_source(data, items), claims=len(items), timeout=timeout, keep=keep)
    if res.accepted or len(items) == 1:
        out = []
        for i in range(len(items)):
            rec = res.to_json(i)
            rec["checker_sha256"] = checker_sha256()
            if keep is not None:
                rec["obligation_file"] = keep.name
            out.append(rec)
        return out
    if keep is not None and keep.exists():
        keep.unlink()
    out = []
    for i, item in enumerate(items):
        out.extend(check_items(data, [item], timeout=timeout, keep_dir=keep_dir, name=f"{name}-single-{i:03d}"))
        out[-1]["isolated_after_batch_rejection"] = True
    return out
