"""Aristotle's counterexample for the first decoder still reproduces, and cannot be built against the current one.

The 2026-11-14 run refuted P2 and P3 of the first decoder (`size_t pcs_header_decode(..., size_t *m)`)
with `aristotle/sim/pcs_header_decode_counterexample.c`: when `m` points into `out`, the final store
`*m = len` overwrites the decoded bytes and the call still succeeds.  This test keeps that negative
finding reproducible:

  * it lays the unchanged counterexample out in a temporary directory next to the first decoder
    (`aristotle/sim/pcs_srcbind_v1.c` with each of the two v1 headers, the one submitted and the one
    with the precondition comment), so that its `#include "../../pcs_srcbind.h"` resolves to the v1
    header; builds it with the address and undefined-behaviour sanitizers; runs it; and checks that it
    reports the violation exactly as documented (exit status 1, no sanitizer report);
  * it checks that the same program does not compile against the current decoder
    (`pcs_srcbind.c/.h`), whose interface returns both lengths by value and has no pointer that could
    alias `out`.

Run: python3 research/claimcheck_assurance_v1/c/test_counterexample.py
"""
import hashlib, json, os, shutil, subprocess, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE / "aristotle" / "sim"
CEX = SIM / "pcs_header_decode_counterexample.c"
RECORD = {  # the files kept as the record of the examined version (aristotle/sim/README.md)
    "pcs_srcbind_v1.c": "7a3a661acc8480c51c1fec5b5c7f883c902baee7494453e396f1c47872878ce5",
    "pcs_srcbind_v1_as_submitted.h": "96e44293fc81eb7e58e437451bfabb4c3deea57a168a127f40b804476a4e9a8c",
    "pcs_srcbind_v1.h": "c68b9df8c10611f3b9a6fd923a70d82af152302f478e6a9eecb7479f3cd8b3a7",
    "pcs_header_decode_counterexample.c": "225d5c71adfa7839a999c89ef476dd9d34f99d6606b73d84f56371a6c20cb07f",
}
EXPECTED_LINES = [
    "returned L = 74, *m = 8",
    "out[0..8) = 08 00 00 00 00 00 00 00",
    "expected out[0..8) (P3) = ff ff ff ff ff ff ff ff",
    "P2/P3 VIOLATED: buf[0..L) is the canonical header of ff x 8, not of the final out bytes",
]


def layout(tmp: Path, source: Path, header: Path) -> Path:
    """tmp/c/{pcs_srcbind.c,pcs_srcbind.h} and tmp/c/aristotle/sim/<counterexample>, as in the repository."""
    c = tmp / "c"
    (c / "aristotle" / "sim").mkdir(parents=True)
    shutil.copyfile(source, c / "pcs_srcbind.c")
    shutil.copyfile(header, c / "pcs_srcbind.h")
    shutil.copyfile(CEX, c / "aristotle" / "sim" / CEX.name)
    return c


def build(c: Path, exe: Path):
    cc = os.environ.get("CC", "cc")
    return subprocess.run([cc, "-std=c99", "-Wall", "-Wextra", "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                           "-I", str(c), str(c / "aristotle" / "sim" / CEX.name), str(c / "pcs_srcbind.c"), "-o", str(exe)],
                          capture_output=True, text=True)


def main():
    for name, digest in RECORD.items():
        assert hashlib.sha256((SIM / name).read_bytes()).hexdigest() == digest, f"the record {name} changed"
    report = {"v1_runs": {}, "v2_compiles": None}
    for header in ("pcs_srcbind_v1_as_submitted.h", "pcs_srcbind_v1.h"):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            c = layout(tmp, SIM / "pcs_srcbind_v1.c", SIM / header)
            exe = tmp / "cex"
            b = build(c, exe)
            assert b.returncode == 0, b.stderr
            run = subprocess.run([str(exe)], capture_output=True, text=True, env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
            lines = run.stdout.strip().splitlines()
            assert run.returncode == 1, (run.returncode, run.stdout, run.stderr)
            assert lines == EXPECTED_LINES, lines
            assert "runtime error" not in run.stderr and "AddressSanitizer" not in run.stderr, run.stderr
            report["v1_runs"][header] = {"exit": run.returncode, "violation_reported": True, "sanitizer_reports": 0}
    # The same program against the current decoder: the five-argument call with a length pointer no longer exists.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        c = layout(tmp, HERE / "pcs_srcbind.c", HERE / "pcs_srcbind.h")
        b = build(c, tmp / "cex")
        assert b.returncode != 0, "the v1 counterexample must not compile against the current decoder"
        assert "pcs_header_decode" in b.stderr, b.stderr
        report["v2_compiles"] = False
    report["passed"] = True
    print(json.dumps(report))


if __name__ == "__main__":
    main()
