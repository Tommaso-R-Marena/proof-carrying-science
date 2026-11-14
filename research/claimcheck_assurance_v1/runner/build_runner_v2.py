"""Derive claimcheck_kernel_runner_v2.py from the v1.1 runner: same program, but the generated part
of the proof file must be in canonical form (strict_tail.parse_tail), not merely free of a few
forbidden words.  Deterministic; run from the repository root."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = HERE.parents[1] / "claimcheck_v1_1" / "claimcheck_kernel_runner.py"
src = V1.read_text(encoding="utf-8")
strict = (HERE / "strict_tail.py").read_text(encoding="utf-8")
body = strict.split('import re\n', 1)[1]


def swap(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old))
    return text.replace(old, new)


src = swap(src, 'SCHEMA = "pcs-claimcheck-kernel-run-v1"', 'SCHEMA = "pcs-claimcheck-kernel-run-v2"')
src = swap(src, "\n\ndef sha(data):", "\n\n# ---- strict grammar of the generated part (copied from strict_tail.py) ----\n" + body.rstrip() + "\n\n\ndef sha(data):")
a = src.index('    m = re.search(r"def pcs_src : Source := ⟨0x([0-9a-f]+), ([0-9]+)⟩", tail)')
b = src.index("    lean = lean or os.environ.get")
src = src[:a] + '''    try:
        data, outcomes = parse_tail(tail)
    except NotCanonical as exc:
        return fail(report, "the generated part is not in canonical form (" + str(exc) + "); nothing was run")
    size = len(data)
    report["generated_part_canonical"] = True
    report["data_sha256"], report["data_bytes"] = sha(data), size
    stated = [(str(i), o) for i, o in enumerate(outcomes)]
''' + src[b:]
(HERE / "claimcheck_kernel_runner_v2.py").write_text(src, encoding="utf-8")
print("wrote claimcheck_kernel_runner_v2.py", len(src))
