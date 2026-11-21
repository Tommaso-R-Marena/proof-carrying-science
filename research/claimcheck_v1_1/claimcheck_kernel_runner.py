#!/usr/bin/env python3
"""Run the real Lean 4.28.0 kernel on one ClaimCheck proof file and write a kernel-run receipt.

    python claimcheck_kernel_runner.py claimcheck-proof.lean [--lean /path/to/lean] [--out kernel-run.json]
                                         [--max-memory-mb N]

Stand-alone: Python 3.9+ standard library only, no network, nothing else from PCS.  Use it for the
proof file the ClaimCheck web page lets you download.  A browser can calculate; only this step
(or an equivalent `lean` run) makes the Lean kernel check the statement.

What it checks before trusting a "pass":
  * the file starts with the reviewed checker (its SHA-256 is fixed below; override with
    --checker-sha256 only if you obtained another reviewed digest independently);
  * the generated part is in the canonical form of the ClaimCheck generator's grammar (one spelling
    per value): one data numeral, claim records built from literals only, one batch theorem, and one
    fixed-form theorem per claim proved from the batch theorem.  Anything else -- another definition
    (for example one that shadows `run`), a macro, a comment, an option, a different proof, text
    after the last theorem -- is refused before Lean is started.  The grammar admits claim settings
    the ClaimCheck page never writes (other missing-value tokens, any positive scale, other spellings
    of the reported value); such settings can force either verdict, so the receipt lists every
    claim's settings and flags the ones the page never writes.  Read them before the verdict;
  * `lean` is version 4.28.0, exits 0, prints nothing on stderr, and prints exactly one axiom
    report per claim theorem, in order, naming only the three standard axioms.

Which `lean` runs: the one given with --lean (or PCS_CLAIMCHECK_LEAN), made absolute once;
otherwise the first `lean` (`lean.exe` on Windows) in an absolute PATH entry.  Empty and relative
PATH entries (which mean the current directory) are skipped, and a `lean` found in the current
directory or next to the proof file is refused unless given explicitly: a file planted beside a
download must not run.  The same absolute path is used for the version check and the proof, with
the same reduced environment, and the receipt records it and its SHA-256.

Resources: Lean is given no memory limit unless --max-memory-mb is set (POSIX only).  A 33 KB
benchmark file needs about 3.2 GB; files near the 64 KB cap can need more than 7 GB and may still
fail.  Run files from others with a limit.  Any error of the runner itself gives a refusal with a
report (never a crash), and --out is replaced atomically.

Receipt schema pcs-claimcheck-kernel-run-v2.  The previous runner (schema v1) checked the
generated part only for a few forbidden words and accepted a hand-written proof file that defined
its own `run`; do not rely on v1 receipts for files you did not generate yourself.

What a pass means, and what it does not:
  * it verifies the supplied mathematical obligation: each theorem `run pcs_src pcs_c<i> = <outcome>`
    in the file, about the reviewed checker's `run`, is true of the data bytes embedded in the file;
  * it does not verify that the obligation faithfully represents a paper: whether a sentence means
    that statement, whether the reported value is the paper's number, and whether the bytes are the
    authors' data are not established by any kernel run.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import unicodedata
from fractions import Fraction

REVIEWED_CHECKER_SHA256 = "35c83b283b18f50c3fa9d1bb3f42ec0beca1d6a7458d14ebf7180d9927b9edf9"
MARKER = "\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n"
FORBIDDEN = ("sorry", "native_decide", "axiom ", "unsafe ", "implemented_by", "extern ", "partial ", "ofReduceBool")
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
SCHEMA = "pcs-claimcheck-kernel-run-v2"


# ---- strict grammar of the generated part: the canonical language of claimcheck_v1/lean.py::batch_tail ----
# It fixes the form and the spelling, not the values: claim settings the page never writes (other NA tokens,
# other positive scales, other reported spellings) are in the language; statement() reports and flags them.
# Canonical: every value has one spelling, the generator's.  The same language is the image of
# `renderTail` in research/claimcheck_assurance_v1/formal/ClaimCheckAssurance/Claims.lean, where the
# Lean parser is proved to accept exactly it (agreement with this parser is tested, not proved).

NAT = r"(?:0|[1-9][0-9]*)"
INT = r"(?:0|-?[1-9][0-9]*)"                      # no "-0"
BYTE = r"(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])"
SAFE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 _.,:;()[]%/+-#=<>&*!?@^|~"
SAFE = r"[A-Za-z0-9 _.,:;()\[\]%/+\-#=<>&*!?@^|~]*"
BYTES = rf'(?:b "{SAFE}"|\[{BYTE}(?:, {BYTE})*\])'   # a list only when some byte is not a safe character (checked below)
RAT = rf"\(\({INT} : Rat\) / [1-9][0-9]*\)"         # in lowest terms (checked below)
CMP = r"\.(?:eq|ne|lt|le|gt|ge)"
COND = rf"(?:\.textEq \({BYTES}\) \({BYTES}\)|\.textNe \({BYTES}\) \({BYTES}\)|\.num \({BYTES}\) {CMP} {RAT})"
CONDS = rf"\[(?:{COND}(?:, {COND})*)?\]"
STAT = (rf"(?:\.count|\.sum|\.mean|\.median|\.min|\.max|\.varSample|\.sdSample|\.sdPop|\.sem|\.share {CONDS}"
        rf"|\.pearson \({BYTES}\)|\.olsSlope \({BYTES}\)|\.olsIntercept \({BYTES}\))")
COLUMN = rf"(?:none|some \({BYTES}\))"
NALIST = rf"\[(?:{BYTES}(?:, {BYTES})*)?\]"
VALUE = rf"(?:\(\.rat {RAT}\)|\(\.sqrt \((?:-1|0|1) : Int\) \(\({NAT} : Rat\) / [1-9][0-9]*\)\))"
UNDEFINED = (r"(?:sourceNotWellFormed|csvMalformed|columnNotFound|nonNumericCell|emptySelection|degenerate"
             r"|badReportedLiteral|badScale|missingColumn)")
OUTCOME = rf"(?:\.undefined \.{UNDEFINED}|\.checked \.(?:consistent|inconsistent) {VALUE} {NAT} {NAT})"

PREAMBLE = "open PCS.ClaimCheck\n\n"
SRC = re.compile(r"def pcs_src : Source := ⟨0x([0-9a-f]+), (0|[1-9][0-9]*)⟩\n\n")
OUTCOME_RE = re.compile(OUTCOME)
MAX_CLAIMS = 256
MAX_DATA_BYTES = 65536          # the generator's bound (claimcheck_v1/lean.py) and MAXD of the Lean header model
MAX_LITERAL_DIGITS = 1000       # a resource limit of this runner (Python's int() refuses > 4300 digits); not part of the grammar

# What the ClaimCheck page and generator write.  Used only to FLAG settings in the receipt, never to accept or refuse.
PAGE_NA_TOKENS = [b"", b"NA"]
_UNITS = ({"kg": 1000, "g": 1, "mg": Fraction(1, 1000), "ug": Fraction(1, 10**6)},
          {"km": 1000, "m": 1, "cm": Fraction(1, 100), "mm": Fraction(1, 1000), "um": Fraction(1, 10**6)},
          {"d": 86400, "h": 3600, "min": 60, "s": 1, "ms": Fraction(1, 1000)},
          {"L": 1, "mL": Fraction(1, 1000), "uL": Fraction(1, 10**6)},
          {"fraction": 1, "%": Fraction(1, 100)})        # the fixed unit table of claimcheck_v1/spec.py and the page
UNIT_RATIOS = frozenset(Fraction(a) / Fraction(b) for family in _UNITS for a in family.values() for b in family.values())
PAGE_REPORTED = re.compile(r"[+-]?(?:[0-9]{1,18}(?:\.[0-9]{0,12})?|\.[0-9]{1,12})(?:[eE][+-]?[0-9]{1,3})?")


class NotCanonical(ValueError):
    pass


_SAFE_BYTES = frozenset(SAFE_CHARS.encode("ascii"))
_QUOTED = re.compile(r'b "[^"]*"')
_RAT_LITERAL = re.compile(r"\(\((-?[0-9]+) : Rat\) / ([0-9]+)\)")
_BYTE_LIST = re.compile(r"\[([0-9]+(?:, [0-9]+)*)\]")


def _canonical_literals(text: str) -> None:
    """The literals of one claim or outcome must be the generator's spelling of their values."""
    bare = _QUOTED.sub('b ""', text)          # string contents cannot hide or imitate a literal
    for num, den in _RAT_LITERAL.findall(bare):
        if len(num.lstrip("-")) > MAX_LITERAL_DIGITS or len(den) > MAX_LITERAL_DIGITS:
            raise NotCanonical(f"a number literal has more than {MAX_LITERAL_DIGITS} digits; this runner refuses it (a resource limit)")
        if math.gcd(abs(int(num)), int(den)) != 1:
            raise NotCanonical("a fraction is not in lowest terms")
    for body in _BYTE_LIST.findall(bare):
        if all(int(v) in _SAFE_BYTES for v in body.split(", ")):
            raise NotCanonical("a byte string that has a quoted spelling is written as a list of numbers")


def _claim(i: int):
    # the named groups only capture; they do not change the language
    return re.compile(rf"def pcs_c{i} : Claim :=\n  \{{ column := (?P<column>{COLUMN}),\n    filter := (?P<filter>{CONDS}),\n"
                      rf"    stat := (?P<stat>{STAT}),\n    naTokens := (?P<na>{NALIST}),\n    scale := (?P<scale>{RAT}),\n"
                      rf"    reported := (?P<reported>{BYTES}) \}}\n\n")


_BYTES_RE = re.compile(BYTES)


def _bytes_value(literal: str) -> bytes:
    if literal.startswith('b "'):
        return literal[3:-1].encode("ascii")
    return bytes(int(v) for v in literal[1:-1].split(", "))


def _bytes_list(literal: str) -> list:
    """The byte strings of a canonical list literal `[b "x", [1, 2], ...]`, in order."""
    out, pos, inner = [], 1, literal
    while pos < len(inner) - 1:
        m = _BYTES_RE.match(inner, pos)
        out.append(_bytes_value(m.group(0)))
        pos = m.end() + (2 if inner.startswith(", ", m.end()) else 0)
    return out


def _shown(raw: bytes) -> str:
    """Readable text for a byte string, or its hex digits when it is not plain printable ASCII."""
    if all(32 <= b < 127 for b in raw):
        return raw.decode("ascii")
    return "0x" + raw.hex()


def statement(m) -> dict:
    """The settings of one canonical claim record, and the ones the ClaimCheck page never writes."""
    num, den = _RAT_LITERAL.fullmatch(m.group("scale")).groups()
    scale = Fraction(int(num), int(den))
    na = _bytes_list(m.group("na"))
    reported = _bytes_value(m.group("reported"))
    column = m.group("column")
    shown = {"column": None if column == "none" else _shown(_bytes_value(column[len("some ("):-1])),
             "filter": m.group("filter"), "stat": m.group("stat"), "na_tokens": [_shown(t) for t in na],
             "scale": str(scale), "reported": _shown(reported)}
    notes = []
    if na != PAGE_NA_TOKENS:
        notes.append('the missing-value tokens are not the page\'s ("" and "NA"): rows can be dropped or kept at will')
    if scale not in UNIT_RATIOS:
        notes.append("the scale is not a ratio of two units of one family of the fixed unit table")
    text = reported.decode("ascii", "replace")
    if not (reported.isascii() and PAGE_REPORTED.fullmatch(text)):
        notes.append("the reported value is not a decimal literal the page accepts")
    else:
        mantissa, _, exponent = text.lower().partition("e")
        if exponent and int(exponent) > 0 and not mantissa.strip("+-.0"):
            notes.append("the reported value is zero with a positive exponent: its rounding interval contains every statistic "
                         "of smaller magnitude than half of 10^" + exponent.lstrip("+"))
    return {"settings": shown, "settings_the_page_never_writes": notes}


def parse_tail(tail: str):
    """Return (data bytes, [outcome literal per claim]) or raise NotCanonical."""
    data, _, outcomes = parse_tail_claims(tail)
    return data, outcomes


def parse_tail_claims(tail: str):
    """Return (data bytes, [statement per claim], [outcome literal per claim]) or raise NotCanonical."""
    if not tail.startswith(PREAMBLE):
        raise NotCanonical("the generated part does not start with the fixed preamble")
    pos = len(PREAMBLE)
    m = SRC.match(tail, pos)
    if not m:
        raise NotCanonical("no canonical data numeral")
    if len(m.group(2)) > len(str(MAX_DATA_BYTES)):
        raise NotCanonical(f"the stated data length is larger than {MAX_DATA_BYTES} bytes, the most this runner accepts")
    digits, size = m.group(1), int(m.group(2))
    if size > MAX_DATA_BYTES:
        raise NotCanonical(f"the embedded data has {size} bytes; this runner accepts at most {MAX_DATA_BYTES}")
    if not ((size == 0 and digits == "0") or (size > 0 and len(digits) == 2 * size)):
        raise NotCanonical("the data numeral is not the two-digits-per-byte dump of a file of the stated length")
    data = bytes.fromhex(digits) if size else b""
    pos = m.end()
    n = 0
    statements = []
    while n < MAX_CLAIMS:
        m = _claim(n).match(tail, pos)
        if not m:
            break
        _canonical_literals(m.group(0))
        statements.append(statement(m))
        pos, n = m.end(), n + 1
    if n == 0:
        raise NotCanonical("no claim in canonical form")
    if n == MAX_CLAIMS and _claim(n).match(tail, pos):
        raise NotCanonical(f"more than {MAX_CLAIMS} claims in one file; this runner accepts at most {MAX_CLAIMS}")
    head = "theorem pcs_batch : runAll pcs_src [" + ", ".join(f"pcs_c{i}" for i in range(n)) + "] =\n    ["
    if not tail.startswith(head, pos):
        raise NotCanonical("the batch theorem is missing or does not list exactly the claims defined")
    pos += len(head)
    outcomes = []
    for i in range(n):
        m = OUTCOME_RE.match(tail, pos)
        if not m:
            raise NotCanonical(f"outcome {i} of the batch theorem is not a literal outcome")
        _canonical_literals(m.group(0))
        outcomes.append(m.group(0))
        pos = m.end()
        sep = ",\n    " if i + 1 < n else "] := by decide +kernel\n\n"
        if not tail.startswith(sep, pos):
            raise NotCanonical("the batch theorem is not in canonical form")
        pos += len(sep)
    for i, outcome in enumerate(outcomes):
        theorem = (f"theorem pcs_claim_{i} : run pcs_src pcs_c{i} = {outcome} :=\n"
                   f"  run_of_runAll pcs_batch {i} rfl rfl\n#print axioms pcs_claim_{i}\n\n")
        if not tail.startswith(theorem, pos):
            raise NotCanonical(f"theorem pcs_claim_{i} is missing, altered or states another outcome than the batch theorem")
        pos += len(theorem)
    if pos != len(tail):
        raise NotCanonical("there is text after the last theorem")
    return data, statements, outcomes


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(path) -> str:
    """The proof file's name for the receipt: undecodable bytes and control or format characters replaced."""
    name = os.path.basename(os.fsdecode(path)).encode("utf-8", "surrogateescape").decode("utf-8", "replace")
    return "".join("\ufffd" if unicodedata.category(c) in ("Cc", "Cf", "Cs", "Zl", "Zp") else c for c in name)


def find_lean(explicit, proof_path):
    """(absolute path, how it was found) or (None, why not).  See the module docstring."""
    given = explicit or os.environ.get("PCS_CLAIMCHECK_LEAN")
    if given:
        path = os.path.abspath(given)
        if not os.path.isfile(path):
            return None, "the lean given with --lean or PCS_CLAIMCHECK_LEAN does not exist: " + path
        return path, "given explicitly"
    names = ("lean.exe",) if os.name == "nt" else ("lean",)
    here = {os.path.normcase(os.path.realpath(os.getcwd())), os.path.normcase(os.path.realpath(os.path.dirname(os.path.abspath(proof_path))))}
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry or not os.path.isabs(entry):
            continue                               # an empty or relative entry means the current directory
        for name in names:
            candidate = os.path.join(entry, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                if os.path.normcase(os.path.realpath(entry)) in here:
                    return None, ("refusing the lean found in the current directory or next to the proof file (" + candidate
                                  + "): pass --lean with the path of your Lean 4.28.0")
                return candidate, "the first lean in an absolute PATH entry"
    return None, "no `lean` executable found; install Lean 4.28.0 (https://lean-lang.org) or pass --lean"


def lean_env(home: str) -> dict:
    """The reduced environment for both Lean calls.  ELAN_HOME lets an elan-installed `lean` find its toolchain."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": home, "LANG": "C.UTF-8"}
    elan = os.environ.get("ELAN_HOME") or os.path.join(os.path.expanduser("~"), ".elan")
    if os.path.isdir(elan):
        env["ELAN_HOME"] = elan
    if os.name == "nt":
        for key in ("SYSTEMROOT", "SystemRoot", "TEMP", "TMP"):
            if key in os.environ:
                env[key] = os.environ[key]
    return env


def memory_limit(mb):
    if not mb or os.name != "posix":
        return None
    def apply():
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (mb * 1024 * 1024, mb * 1024 * 1024))
    return apply


def fail(report, why, code=1):
    report["accepted"] = False
    report["why_not"] = why
    return report, code


def run(path, lean, checker_sha256, timeout, max_memory_mb=None):
    report = {"schema": SCHEMA, "authority": "RESEARCH_ONLY_NOT_PCS_V06_AUTHORITY", "proof_file": safe_name(path),
              "reviewed_checker_sha256": checker_sha256, "checker_pin_overridden": checker_sha256 != REVIEWED_CHECKER_SHA256,
              "utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "host": platform.platform(),
              "accepted": False, "theorems": []}
    try:
        return _run(report, path, lean, checker_sha256, timeout, max_memory_mb)
    except Exception as exc:              # any failure of the runner itself is a refusal with a report, never a crash
        report["theorems"] = []
        report.pop("meaning", None)
        return fail(report, "the runner could not complete (" + type(exc).__name__ + "); nothing is established")


def _run(report, path, lean, checker_sha256, timeout, max_memory_mb):
    with open(path, "rb") as fh:
        raw = fh.read()
    report["proof_file_sha256"], report["proof_file_bytes"] = sha(raw), len(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return fail(report, "the file is not UTF-8 text")
    if text.count(MARKER) != 1:
        return fail(report, "this is not a ClaimCheck proof file (the generated-obligations marker is missing or repeated)")
    head, tail = text.split(MARKER)
    if sha(head.encode("utf-8")) != checker_sha256:
        return fail(report, "the checker at the top of the file is not the reviewed checker")
    stripped = re.sub(r'"[^"\n]*"', '""', tail)
    bad = [w.strip() for w in FORBIDDEN if w in stripped]
    if bad:
        return fail(report, "the generated part contains a forbidden token: " + ", ".join(bad))
    try:
        data, statements, outcomes = parse_tail_claims(tail)
    except NotCanonical as exc:
        return fail(report, "the generated part is not in canonical form (" + str(exc) + "); nothing was run")
    size = len(data)
    report["generated_part_canonical"] = True
    report["data_sha256"], report["data_bytes"] = sha(data), size
    stated = [(str(i), o) for i, o in enumerate(outcomes)]
    lean, found = find_lean(lean, path)
    if not lean:
        return fail(report, found, 2)
    report["lean_executable"], report["lean_found"] = lean, found
    with open(lean, "rb") as fh:
        report["lean_executable_sha256"] = sha(fh.read())
    with tempfile.TemporaryDirectory(prefix="claimcheck-run-") as tmp:
        env = lean_env(tmp)
        try:
            version = subprocess.run([lean, "--version"], capture_output=True, text=True, timeout=60, cwd=tmp, env=env).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            return fail(report, "cannot run lean: " + type(exc).__name__, 2)
        report["lean"] = version[:200]
        if "version 4.28.0," not in version:
            return fail(report, "Lean 4.28.0 is required; found: " + version[:80], 2)
        copy = os.path.join(tmp, "Obligation.lean")
        with open(copy, "wb") as fh:
            fh.write(raw)
        if max_memory_mb:
            report["max_memory_mb"] = max_memory_mb if os.name == "posix" else "not applied (POSIX only)"
        try:
            proc = subprocess.run([lean, copy], capture_output=True, text=True, timeout=timeout, cwd=tmp, env=env,
                                  preexec_fn=memory_limit(max_memory_mb))
        except subprocess.TimeoutExpired:
            return fail(report, "Lean did not finish within %d s; nothing is established" % timeout)
    if proc.returncode != 0:
        first = (proc.stdout.strip() or proc.stderr.strip()).splitlines()[:1]
        return fail(report, "Lean rejected the file: " + (first[0][:200] if first else "no output (possibly killed for lack of memory)"))
    if proc.stderr.strip():
        return fail(report, "unexpected diagnostics from Lean")
    lines = proc.stdout.strip().splitlines()
    if len(lines) != len(stated):
        return fail(report, "unexpected output from Lean (warnings or extra messages)")
    for i, line in enumerate(lines):
        m = re.fullmatch(r"'pcs_claim_(\d+)' depends on axioms: \[([A-Za-z0-9_., ]*)\]", line)
        axioms = set()
        if m:
            axioms = {a.strip() for a in m.group(2).split(",") if a.strip()}
        else:
            m = re.fullmatch(r"'pcs_claim_(\d+)' does not depend on any axioms", line)
        if not m or int(m.group(1)) != i or not axioms <= ALLOWED_AXIOMS:
            return fail(report, "axiom report %d is missing, out of order or names a non-standard axiom" % i)
        outcome = stated[i][1].strip()
        st = statements[i]["settings"]
        kind = ("the reported value MATCHES the statistic of the embedded data under this typed statement"
                if outcome.startswith(".checked .consistent") else
                "the reported value DOES NOT MATCH the statistic of the embedded data under this typed statement"
                if outcome.startswith(".checked .inconsistent") else
                "the statistic is UNDEFINED for the embedded data under this typed statement")
        kind += (" (reported %r; %s of column %r; filter %s; missing-value tokens %s; scale %s)"
                 % (st["reported"], st["stat"], st["column"], st["filter"], st["na_tokens"], st["scale"]))
        report["theorems"].append({"theorem": "pcs_claim_%d" % i, "kernel_accepted": True, "proved_outcome": outcome,
                                   "in_words": kind, "axioms": sorted(axioms), "statement": st,
                                   "settings_the_page_never_writes": statements[i]["settings_the_page_never_writes"]})
    report["all_settings_as_the_page_writes"] = not any(s["settings_the_page_never_writes"] for s in statements)
    report["accepted"] = True
    report["meaning"] = ("The Lean kernel checked every theorem listed here against the data bytes embedded in the proof file: the supplied "
                         "mathematical obligation, with the settings listed for each theorem, holds. This does not show that the obligation "
                         "faithfully represents a paper: whether a sentence means this statement, whether its settings are the right ones, and "
                         "whether these bytes are the authors' data are not established by a kernel run.")
    if report["checker_pin_overridden"]:
        report["meaning"] += (" The checker's digest was supplied on the command line and is NOT the reviewed digest built into this runner: "
                              "the theorems are about that checker's `run`, which no one has reviewed here.")
    report["establishes"] = "the supplied mathematical obligation, about the embedded data bytes"
    report["does_not_establish"] = "that the obligation represents any sentence of a paper, or that the bytes are the authors' data"
    return report, 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("proof_file")
    ap.add_argument("--lean")
    ap.add_argument("--checker-sha256", default=REVIEWED_CHECKER_SHA256)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--max-memory-mb", type=int, help="POSIX only: limit Lean's address space to this many MiB")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    report, code = run(args.proof_file, args.lean, args.checker_sha256, args.timeout, args.max_memory_mb)
    text = json.dumps(report, indent=1, ensure_ascii=True)       # escapes control and direction-changing characters
    if args.out:
        partial = args.out + ".partial"
        with open(partial, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        os.replace(partial, args.out)
    print(text)
    if report["accepted"]:
        for t in report["theorems"]:
            print("KERNEL-CHECKED  %s: %s" % (t["theorem"], t["in_words"]), file=sys.stderr)
            for note in t["settings_the_page_never_writes"]:
                print("    NOTE: " + note, file=sys.stderr)
        if report["checker_pin_overridden"]:
            print("    NOTE: the checker digest was supplied on the command line; it is not the reviewed checker", file=sys.stderr)
    else:
        print("NOT ESTABLISHED: " + report["why_not"], file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
