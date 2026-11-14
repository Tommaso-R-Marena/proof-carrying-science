#!/usr/bin/env python3
"""Run the real Lean 4.28.0 kernel on one ClaimCheck proof file and write a kernel-run receipt.

    python claimcheck_kernel_runner.py claimcheck-proof.lean [--lean /path/to/lean] [--out kernel-run.json]

Stand-alone: Python 3.9+ standard library only, no network, nothing else from PCS.  Use it for the
proof file the ClaimCheck web page lets you download.  A browser can calculate; only this step
(or an equivalent `lean` run) makes the Lean kernel check the statement.

What it checks before trusting a "pass":
  * the file starts with the reviewed checker (its SHA-256 is fixed below; override with
    --checker-sha256 only if you obtained another reviewed digest independently);
  * the generated part contains no escape hatch (sorry, native_decide, axiom, unsafe, ...);
  * `lean` is version 4.28.0, exits 0, prints nothing on stderr, and prints exactly one axiom
    report per claim theorem, in order, naming only the three standard axioms.

What a pass means: each theorem `run pcs_src pcs_c<i> = <outcome>` in the file is true of the data
bytes embedded in the file.  The expected outcome (matches / does not match the printed number) is
part of the theorem text; this program reports it.  A pass says nothing about whether a sentence in
a paper means that statement, or whether the bytes are the authors' data.
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
SCHEMA = "pcs-claimcheck-kernel-run-v1"


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
    m = re.search(r"def pcs_src : Source := ⟨0x([0-9a-f]+), ([0-9]+)⟩", tail)
    if not m:
        return fail(report, "no embedded data numeral found")
    size = int(m.group(2))
    digits = m.group(1)
    try:
        data = bytes.fromhex(digits.rjust(2 * size, "0")) if size else b""
    except ValueError:
        return fail(report, "the embedded data numeral is malformed")
    if len(data) != size:
        return fail(report, "the embedded data numeral does not fit its stated length")
    report["data_sha256"], report["data_bytes"] = sha(data), size
    stated = re.findall(r"theorem pcs_claim_(\d+) : run pcs_src pcs_c\1 = (.+?) :=\n", tail)
    if not stated or [int(i) for i, _ in stated] != list(range(len(stated))):
        return fail(report, "the claim theorems are missing or not numbered 0, 1, 2, ...")
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
        kind = ("the printed number MATCHES the file under this statement" if outcome.startswith(".checked .consistent") else
                "the printed number DOES NOT MATCH the file under this statement" if outcome.startswith(".checked .inconsistent") else
                "the statistic is UNDEFINED for this file under this statement")
        report["theorems"].append({"theorem": "pcs_claim_%d" % i, "kernel_accepted": True, "proved_outcome": outcome,
                                   "in_words": kind, "axioms": sorted(axioms)})
    report["accepted"] = True
    report["meaning"] = ("The Lean kernel checked every theorem listed here against the data bytes embedded in the proof file. This is a statement "
                         "about those bytes and the typed statement in the file. It is not a statement about a paper.")
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
