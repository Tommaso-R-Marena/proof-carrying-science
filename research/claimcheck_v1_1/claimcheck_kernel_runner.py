#!/usr/bin/env python3
"""Run the real Lean 4.28.0 kernel on one ClaimCheck proof file and write a kernel-run receipt.

    python claimcheck_kernel_runner.py claimcheck-proof.lean [--lean /path/to/lean] [--out kernel-run.json]

Stand-alone: Python 3.9+ standard library only, no network, nothing else from PCS.  Use it for the
proof file the ClaimCheck web page lets you download.  A browser can calculate; only this step
(or an equivalent `lean` run) makes the Lean kernel check the statement.

What it checks before trusting a "pass":
  * the file starts with the reviewed checker (its SHA-256 is fixed below; override with
    --checker-sha256 only if you obtained another reviewed digest independently);
  * the generated part is exactly in the form the ClaimCheck generator writes: one data numeral,
    claim records built from literals only, one batch theorem, and one fixed-form theorem per claim
    proved from the batch theorem.  Anything else -- another definition (for example one that
    shadows `run`), a macro, a comment, an option, a different proof, text after the last theorem --
    is refused before Lean is started;
  * `lean` is version 4.28.0, exits 0, prints nothing on stderr, and prints exactly one axiom
    report per claim theorem, in order, naming only the three standard axioms.

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
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

REVIEWED_CHECKER_SHA256 = "35c83b283b18f50c3fa9d1bb3f42ec0beca1d6a7458d14ebf7180d9927b9edf9"
MARKER = "\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n"
FORBIDDEN = ("sorry", "native_decide", "axiom ", "unsafe ", "implemented_by", "extern ", "partial ", "ofReduceBool")
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
SCHEMA = "pcs-claimcheck-kernel-run-v2"


# ---- strict grammar of the generated part: exactly the language of claimcheck_v1/lean.py::batch_tail ----

NAT = r"(?:0|[1-9][0-9]*)"
INT = r"-?(?:0|[1-9][0-9]*)"
SAFE = r"[A-Za-z0-9 _.,:;()\[\]%/+\-#=<>&*!?@^|~]*"
BYTES = rf'(?:b "{SAFE}"|\[(?:{NAT}(?:, {NAT})*)?\])'
RAT = rf"\(\({INT} : Rat\) / [1-9][0-9]*\)"
CMP = r"\.(?:eq|ne|lt|le|gt|ge)"
COND = rf"(?:\.textEq \({BYTES}\) \({BYTES}\)|\.textNe \({BYTES}\) \({BYTES}\)|\.num \({BYTES}\) {CMP} {RAT})"
CONDS = rf"\[(?:{COND}(?:, {COND})*)?\]"
STAT = (rf"(?:\.count|\.sum|\.mean|\.median|\.min|\.max|\.varSample|\.sdSample|\.sdPop|\.sem|\.share {CONDS}"
        rf"|\.pearson \({BYTES}\)|\.olsSlope \({BYTES}\)|\.olsIntercept \({BYTES}\))")
COLUMN = rf"(?:none|some \({BYTES}\))"
NALIST = rf"\[(?:{BYTES}(?:, {BYTES})*)?\]"
VALUE = rf"(?:\(\.rat {RAT}\)|\(\.sqrt \({INT} : Int\) {RAT}\))"
OUTCOME = rf"(?:\.undefined \.[A-Za-z]+|\.checked \.(?:consistent|inconsistent) {VALUE} {NAT} {NAT})"

PREAMBLE = "open PCS.ClaimCheck\n\n"
SRC = re.compile(r"def pcs_src : Source := ⟨0x([0-9a-f]+), (0|[1-9][0-9]*)⟩\n\n")
OUTCOME_RE = re.compile(OUTCOME)
MAX_CLAIMS = 256
MAX_DATA_BYTES = 65536          # the generator's bound (claimcheck_v1/lean.py) and MAXD of the Lean header model


class NotCanonical(ValueError):
    pass


def _claim(i: int):
    return re.compile(rf"def pcs_c{i} : Claim :=\n  \{{ column := {COLUMN},\n    filter := {CONDS},\n    stat := {STAT},\n"
                      rf"    naTokens := {NALIST},\n    scale := {RAT},\n    reported := {BYTES} \}}\n\n")


def parse_tail(tail: str):
    """Return (data bytes, [outcome literal per claim]) or raise NotCanonical."""
    if not tail.startswith(PREAMBLE):
        raise NotCanonical("the generated part does not start with the fixed preamble")
    pos = len(PREAMBLE)
    m = SRC.match(tail, pos)
    if not m:
        raise NotCanonical("no canonical data numeral")
    digits, size = m.group(1), int(m.group(2))
    if size > MAX_DATA_BYTES:
        raise NotCanonical(f"the embedded data has {size} bytes; this runner accepts at most {MAX_DATA_BYTES}")
    if not ((size == 0 and digits == "0") or (size > 0 and len(digits) == 2 * size)):
        raise NotCanonical("the data numeral is not the two-digits-per-byte dump of a file of the stated length")
    data = bytes.fromhex(digits) if size else b""
    pos = m.end()
    n = 0
    while n < MAX_CLAIMS:
        m = _claim(n).match(tail, pos)
        if not m:
            break
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
    return data, outcomes


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fail(report, why, code=1):
    report["accepted"] = False
    report["why_not"] = why
    return report, code


def run(path, lean, checker_sha256, timeout):
    raw = open(path, "rb").read()
    report = {"schema": SCHEMA, "authority": "RESEARCH_ONLY_NOT_PCS_V06_AUTHORITY", "proof_file": os.path.basename(path),
              "proof_file_sha256": sha(raw), "proof_file_bytes": len(raw), "reviewed_checker_sha256": checker_sha256,
              "utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "host": platform.platform(),
              "accepted": False, "theorems": []}
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
        data, outcomes = parse_tail(tail)
    except NotCanonical as exc:
        return fail(report, "the generated part is not in canonical form (" + str(exc) + "); nothing was run")
    size = len(data)
    report["generated_part_canonical"] = True
    report["data_sha256"], report["data_bytes"] = sha(data), size
    stated = [(str(i), o) for i, o in enumerate(outcomes)]
    lean = lean or os.environ.get("PCS_CLAIMCHECK_LEAN") or shutil.which("lean")
    if not lean:
        return fail(report, "no `lean` executable found; install Lean 4.28.0 (https://lean-lang.org) or pass --lean", 2)
    try:
        version = subprocess.run([lean, "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return fail(report, "cannot run lean: " + type(exc).__name__, 2)
    report["lean"] = version
    if "version 4.28.0," not in version:
        return fail(report, "Lean 4.28.0 is required; found: " + version[:80], 2)
    with tempfile.TemporaryDirectory(prefix="claimcheck-run-") as tmp:
        copy = os.path.join(tmp, "Obligation.lean")
        with open(copy, "wb") as fh:
            fh.write(raw)
        try:
            proc = subprocess.run([lean, copy], capture_output=True, text=True, timeout=timeout, cwd=tmp,
                                  env={"PATH": os.environ.get("PATH", ""), "HOME": tmp, "LANG": "C.UTF-8"})
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
        kind = ("the reported value MATCHES the statistic of the embedded data under this typed statement"
                if outcome.startswith(".checked .consistent") else
                "the reported value DOES NOT MATCH the statistic of the embedded data under this typed statement"
                if outcome.startswith(".checked .inconsistent") else
                "the statistic is UNDEFINED for the embedded data under this typed statement")
        report["theorems"].append({"theorem": "pcs_claim_%d" % i, "kernel_accepted": True, "proved_outcome": outcome,
                                   "in_words": kind, "axioms": sorted(axioms)})
    report["accepted"] = True
    report["meaning"] = ("The Lean kernel checked every theorem listed here against the data bytes embedded in the proof file: the supplied "
                         "mathematical obligation holds. This does not show that the obligation faithfully represents a paper: whether a "
                         "sentence means this statement, and whether these bytes are the authors' data, are not established by a kernel run.")
    report["establishes"] = "the supplied mathematical obligation, about the embedded data bytes"
    report["does_not_establish"] = "that the obligation represents any sentence of a paper, or that the bytes are the authors' data"
    return report, 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("proof_file")
    ap.add_argument("--lean")
    ap.add_argument("--checker-sha256", default=REVIEWED_CHECKER_SHA256)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    report, code = run(args.proof_file, args.lean, args.checker_sha256, args.timeout)
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    if report["accepted"]:
        for t in report["theorems"]:
            print("KERNEL-CHECKED  %s: %s" % (t["theorem"], t["in_words"]), file=sys.stderr)
    else:
        print("NOT ESTABLISHED: " + report["why_not"], file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
