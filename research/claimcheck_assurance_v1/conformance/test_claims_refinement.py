"""The proved Lean parser of the claims part and the stand-alone runner's Python parser agree.

`ClaimCheckAssurance.Claims` proves that `parseTail` accepts exactly the renderings of valid values
(`parseTail_iff`), that a rendering is determined by its values (`renderTail_injective`) and by their
meaning in the checker (`same_meaning_same_text`).  This test executes that same `parseTail` (via
`lean --run ClaimsRefinement.lean`) and compares it, vector by vector, with `parse_tail` of the
installed runner (`research/claimcheck_v1_1/claimcheck_kernel_runner.py`): accept or reject, and for
accepted tails the data, the number of claims and the outcome texts.

Vectors: the generated part of every committed obligation file; tails written by the generator
(`claimcheck_v1/lean.py::batch_tail`) for random data, claims and outcomes, including strings with
quotes, backslashes and non-ASCII characters; the same tails with a non-canonical spelling put in
(a quoted string as numbers, a fraction not in lowest terms, -0, leading zeros, a byte above 255, a
square-root sign of 2, a negative radicand, an unknown reason, an empty byte list); every truncation
and many single-character deletions, insertions and substitutions of small tails; byte-level
mutations that break UTF-8; the forgeries of the runner finding; boundaries the random generator
does not reach (65,536 and 65,537 data bytes, 256 and 257 claims, hand-written byte lists, empty,
all-safe and 5,000-character strings, every statistic with every comparison and nested share
filters, extreme rationals, square roots of sign -1, 0 and 1, every undefined reason), which both
parsers must accept (`edge-accept`) or both refuse (`edge-reject`); and every token of three tails
deleted, doubled or replaced by a near miss.  Agreement on these inputs is evidence that the Python
parser computes the proved function; it is a test, not a proof.

Run (needs Lean 4.28.0 on PATH and `formal/build.sh` run first):
  python3 research/claimcheck_assurance_v1/conformance/test_claims_refinement.py [--out FILE]
"""
import argparse, json, os, random, re, resource, struct, subprocess, sys, tempfile, time
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parent
ROOT = ASSURANCE.parents[1]
sys.path.insert(0, str(ROOT))
from research.claimcheck_v1.lean import batch_tail  # noqa: E402
from research.claimcheck_v1.oracle import Outcome  # noqa: E402
from research.claimcheck_v1.spec import ClaimSpec, Cond  # noqa: E402
from research.claimcheck_v1_1.claimcheck_kernel_runner import NotCanonical, parse_tail  # noqa: E402

MARKER = b"\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n"
REASONS = ["sourceNotWellFormed", "csvMalformed", "columnNotFound", "nonNumericCell", "emptySelection", "degenerate",
           "badReportedLiteral", "badScale", "missingColumn"]
PLAIN_STATS = ["count", "sum", "mean", "median", "min", "max", "var_sample", "sd_sample", "sd_pop", "sem"]
ALPHABET = list("abcXYZ019 _.,:;()[]%/+-#=<>&*!?@^|~") + ['"', "\\", "$", "'", "`", "{", "}", "é", "–", "µ", "中", "\t"]


def h(d: bytes) -> int:
    v = 0
    for x in d:
        v = (v * 257 + x + 1) % 2305843009213693951
    return v


def python_line(buf: bytes) -> str:
    try:
        text = buf.decode("utf-8")
        data, outcomes = parse_tail(text)
    except (UnicodeDecodeError, NotCanonical):
        return "N"
    return f"A {len(data)} {h(data)} {len(outcomes)} " + "|".join(outcomes)


def rstr(rng, k=6):
    return "".join(rng.choice(ALPHABET) for _ in range(rng.randrange(0, k)))


def rcond(rng):
    kind = rng.choice(["text_eq", "text_ne", "num"])
    if kind == "num":
        value = str(Fraction(rng.randrange(-500, 500), rng.choice([1, 2, 4, 10, 100])))
        value = value if "/" not in value else str(float(Fraction(value)))
        return Cond(kind, rstr(rng) or "x", value, rng.choice(["eq", "ne", "lt", "le", "gt", "ge"]))
    return Cond(kind, rstr(rng) or "x", rstr(rng))


def rspec(rng):
    stat = rng.choice(PLAIN_STATS + ["share", "pearson", "ols_slope", "ols_intercept"])
    column = None if stat in ("count", "share") and rng.random() < 0.5 else (rstr(rng) or "c")
    return ClaimSpec(stat=stat, reported=rng.choice(["1", "2.5", "-0.75", "100", rstr(rng)]), column=column,
                     x_column=(rstr(rng) or "x") if stat in ("pearson", "ols_slope", "ols_intercept") else None,
                     filter=tuple(rcond(rng) for _ in range(rng.randrange(0, 3))),
                     sub_filter=tuple(rcond(rng) for _ in range(rng.randrange(0, 3))) if stat == "share" else ())


def routcome(rng):
    k = rng.random()
    if k < 0.2:
        return Outcome(defined=False, reason=rng.choice(REASONS))
    if k < 0.6:
        return Outcome(defined=True, verdict=rng.choice(["consistent", "inconsistent"]), value_kind="rat",
                       value=Fraction(rng.randrange(-10**6, 10**6), rng.randrange(1, 10**4)), used=rng.randrange(0, 999),
                       missing=rng.randrange(0, 99))
    return Outcome(defined=True, verdict=rng.choice(["consistent", "inconsistent"]), value_kind="sqrt",
                   value=Fraction(rng.randrange(0, 10**6), rng.randrange(1, 10**4)), sign=rng.choice([-1, 0, 1]),
                   used=rng.randrange(0, 999), missing=rng.randrange(0, 99))


def generated(rng):
    data = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 40)))
    items = [(rspec(rng), tuple(rng.choice(["", "NA", "n/a", "–", '"'] ) for _ in range(rng.randrange(0, 3))),
              Fraction(rng.randrange(1, 1000), rng.choice([1, 10, 100, 1000])), routcome(rng)) for _ in range(rng.randrange(1, 5))]
    text = batch_tail(data, items)
    assert text.startswith(MARKER.decode("utf-8"))
    return text[len(MARKER.decode("utf-8")):]          # the generated part is what follows the marker


SAFE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 _.,:;()[]%/+-#=<>&*!?@^|~"
STATS = PLAIN_STATS + ["share", "pearson", "ols_slope", "ols_intercept"]
CMPS = ["eq", "ne", "lt", "le", "gt", "ge"]


def part(data, items):
    """The generated part (after the marker) that the real generator writes."""
    text = batch_tail(data, items)
    marker = MARKER.decode("utf-8")
    assert text.startswith(marker)
    return text[len(marker):]


def edge_vectors(rng):
    """Boundaries the random generator does not reach.  `edge-accept` vectors must be accepted by both
    parsers, `edge-reject` vectors refused by both; the comparison itself is the test."""
    undef = Outcome(defined=False, reason="csvMalformed")
    plain = lambda **kw: (ClaimSpec(**({"stat": "mean", "reported": "1", "column": "a"} | kw)), ("", "NA"), Fraction(1), undef)
    acc, rej = [], []
    big = bytes(rng.randrange(256) for _ in range(65536))
    acc.append(part(big, [plain()]))                       # data of exactly the cap (65,536 bytes)
    rej.append(part(big + b"\x00", [plain()]))             # one byte over: the generator writes it; both must refuse
    acc += [part(b"", [plain()]), part(b"\x00", [plain()]), part(bytes(range(256)), [plain()])]
    acc.append(part(b"a\n1\n", [plain() for _ in range(256)]))   # exactly 256 claims
    rej.append(part(b"a\n1\n", [plain() for _ in range(257)]))   # one claim over
    long_safe = "".join(rng.choice(SAFE_CHARS) for _ in range(5000))
    for kw in ({"column": ""}, {"column": SAFE_CHARS, "reported": SAFE_CHARS}, {"column": long_safe},
               {"column": "é" * 1000}, {"column": "\\", "reported": '"'}, {"column": "\x7f", "reported": "\x00"},
               {"column": None, "stat": "count"}, {"column": "x", "reported": "-0.000000000000000000001"}):
        acc.append(part(b"a\n1\n", [plain(**kw)]))
    # every statistic, every comparison, nested share filters
    conds = [Cond("num", "c" + k, v, k) for k, v in zip(CMPS, ["0", "-1.5", "1e3", "123456789012345678901234567890.25", "-0.001", "7"])]
    conds += [Cond("text_eq", "g", "A"), Cond("text_ne", "", ""), Cond("text_eq", "é", '"')]
    for st in STATS:
        spec = ClaimSpec(stat=st, reported="2.5", column=None if st in ("count", "share") else "y",
                         x_column="x" if st in ("pearson", "ols_slope", "ols_intercept") else None,
                         filter=tuple(conds), sub_filter=tuple(conds) if st == "share" else ())
        acc.append(part(b"x,y\n1,2\n", [(spec, ("", "NA", "–"), Fraction(1), undef)]))
    # scales and outcomes at the extremes
    big_q = [Fraction(0), Fraction(-7, 3), Fraction(10**40 + 1, 10**40), Fraction(-(10**50), 10**25 + 3), Fraction(1, 10**30)]
    outs = [Outcome(defined=False, reason=r) for r in REASONS]
    for q in big_q:
        outs.append(Outcome(defined=True, verdict="consistent", value_kind="rat", value=q, used=0, missing=0))
    for sign in (-1, 0, 1):
        for rad in (Fraction(0), Fraction(1, 3), Fraction(10**40, 7)):
            outs.append(Outcome(defined=True, verdict="inconsistent", value_kind="sqrt", value=rad, sign=sign,
                                used=10**12, missing=999999))
    for q in big_q:
        acc.append(part(b"a\n1\n", [(ClaimSpec(stat="mean", reported="1", column="a"), (), q, o) for o in outs]))
    # byte lists written by hand: canonical ones accepted, non-canonical ones refused
    base = part(b"a\n1\n", [plain(column="X")])
    assert 'some (b "X")' in base
    for lst in ("[0, 127, 128, 255]", "[128]", "[0]", "[255, 255]"):
        acc.append(base.replace('some (b "X")', f"some ({lst})", 1))
    for lst in ("[256]", "[0, 256]", "[007]", "[00]", "[]", "[88]", "[88, 89]", "[0,127]", "[ 0]", "[-1]"):
        rej.append(base.replace('some (b "X")', f"some ({lst})", 1))
    return [("edge-accept", t.encode("utf-8")) for t in acc] + [("edge-reject", t.encode("utf-8")) for t in rej]


TOKEN = re.compile(r'b "[^"]*"|-?[0-9]+|[A-Za-z_][A-Za-z0-9_]*|\s+|.', re.S)
NEAR = {"(": "[", ")": "]", "[": "(", "]": ")", ",": ";", ":": "=", "=": ":", ".": ",", "⟨": "(", "⟩": ")", "{": "(", "}": ")",
        "/": "%", "+": "-", "-": "+"}


def token_mutations(tails):
    """Every single token of each tail deleted, duplicated, or replaced by a near miss."""
    out = []
    for t in tails:
        toks = TOKEN.findall(t)
        assert "".join(toks) == t
        for i, tok in enumerate(toks):
            variants = ["", tok + tok]
            if tok.startswith('b "'):
                body = tok[3:-1]
                variants += ['b ""', f'b "{body}x"', "[" + ", ".join(str(b) for b in body.encode()) + "]" if body else "[]"]
            elif re.fullmatch(r"-?[0-9]+", tok):
                n = int(tok)
                variants += [str(n + 1), "0" + tok.lstrip("-"), str(-n) if n else "-0"]
            elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tok):
                variants += [tok.swapcase(), tok + "x", tok[:-1] if len(tok) > 1 else "x"]
            elif tok.isspace():
                variants += [tok + " ", "\n" if tok == " " else " "]
            else:
                variants.append(NEAR.get(tok, "?"))
            for v in variants:
                if v != tok:
                    out.append(("token", ("".join(toks[:i]) + v + "".join(toks[i + 1:])).encode("utf-8")))
    return out


NONCANONICAL = [
    ('some (b "c")', "some ([99])"), ("((1 : Rat) / 1)", "((2 : Rat) / 2)"), ("((0 : Rat) / 1)", "((-0 : Rat) / 1)"),
    ("((1 : Rat) / 1)", "((01 : Rat) / 1)"), ("[226, 128, 147]", "[226, 128, 403]"), ("[226, 128, 147]", "[226, 128, 0147]"),
    ("(.sqrt (1 : Int)", "(.sqrt (2 : Int)"), ("(.sqrt (-1 : Int) ((", "(.sqrt (-1 : Int) ((-"), (".undefined .csvMalformed", ".undefined .csvmalformed"),
    ('reported := b ""', "reported := []"), ("naTokens := [b \"\"", "naTokens := [[]"), ("((1 : Rat) / 10)", "((10 : Rat) / 100)"),
    (".checked .consistent", ".checked .Consistent"), ("filter := []", "filter := [ ]"), (" 0]", " 00]"),
]


def vectors(rng):
    out = []
    for ob in sorted((ROOT / "research/claimcheck_v1/benchmark/results/bundles").glob("*/obligations/*.lean")):
        out.append(("committed", ob.read_bytes().split(MARKER, 1)[1]))
    gen = [generated(rng) for _ in range(400)]
    out += [("generated", g.encode("utf-8")) for g in gen]
    for g in gen:
        for old, new in NONCANONICAL:
            if old in g:
                out.append(("noncanonical", g.replace(old, new, 1).encode("utf-8")))
    small = sorted(gen, key=len)[:6]
    for g in small:
        for i in range(len(g)):
            out.append(("truncation", g[:i].encode("utf-8")))
        for _ in range(300):
            i = rng.randrange(len(g))
            c = rng.choice(ALPHABET + ["\n", "0", "1", "9"])
            op = rng.randrange(3)
            m = g[:i] + g[i + 1:] if op == 0 else g[:i] + c + g[i:] if op == 1 else g[:i] + c + g[i + 1:]
            out.append(("mutation", m.encode("utf-8")))
        raw = bytearray(g.encode("utf-8"))
        for _ in range(60):
            b = bytearray(raw)
            b[rng.randrange(len(b))] = rng.choice([0x80, 0xC3, 0xE2, 0xFF, 0x00])
            out.append(("bytes", bytes(b)))
    forged = (ROOT / "research/claimcheck_assurance_v1/findings/record/forged_tail.lean.txt").read_bytes()
    out.append(("forgery", forged))
    g = small[0]
    for extra in ("def helper : Nat := 0\n\n", "namespace X\n", "set_option maxRecDepth 1 in\n", "-- note\n"):
        out.append(("forgery", g.replace("def pcs_c0", extra + "def pcs_c0", 1).encode("utf-8")))
    out.append(("forgery", (g + "theorem extra : True := trivial\n").encode("utf-8")))
    out += edge_vectors(rng)
    shareful = [x for x in gen if ".share [" in x and "(.sqrt" in x][:1] + [x for x in gen if ".num (" in x][:1] + small[:1]
    out += token_mutations(shareful)
    return out


def unlimited_stack():
    resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    rng = random.Random(20261116)
    vec = vectors(rng)
    build = ASSURANCE / "formal" / ".build"
    assert (build / "ClaimCheckAssurance" / "Claims.olean").exists(), "run formal/build.sh first"
    with tempfile.TemporaryDirectory() as tmp:
        inp, outp = Path(tmp) / "vectors.bin", Path(tmp) / "lean.txt"
        inp.write_bytes(b"".join(struct.pack(">I", len(v)) + v for _, v in vec))
        env = dict(os.environ, LEAN_PATH=str(build))
        started = time.monotonic()
        subprocess.run(["lean", "--run", str(HERE / "ClaimsRefinement.lean"), str(inp), str(outp)], check=True, env=env,
                       preexec_fn=unlimited_stack, timeout=3600)
        lean_seconds = time.monotonic() - started
        lean_lines = outp.read_text(encoding="utf-8").splitlines()
    assert len(lean_lines) == len(vec), (len(lean_lines), len(vec))
    report = {"vectors": len(vec), "by_kind": {}, "disagreements": []}
    for (kind, v), lean_line in zip(vec, lean_lines):
        py = python_line(v)
        k = report["by_kind"].setdefault(kind, {"vectors": 0, "accepted": 0})
        k["vectors"] += 1
        k["accepted"] += lean_line.startswith("A")
        if py != lean_line:
            report["disagreements"].append({"kind": kind, "lean": lean_line[:200], "python": py[:200],
                                            "vector": v[:300].decode("utf-8", "replace")})
    report["lean_interpreter_seconds"] = round(lean_seconds, 1)
    report["largest_vector_bytes"] = max(len(v) for _, v in vec)
    report["passed"] = not report["disagreements"]
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    assert report["passed"], f"{len(report['disagreements'])} disagreements"
    assert report["by_kind"]["committed"]["accepted"] == report["by_kind"]["committed"]["vectors"] >= 84
    assert report["by_kind"]["generated"]["accepted"] == report["by_kind"]["generated"]["vectors"]
    assert report["by_kind"]["forgery"]["accepted"] == 0
    assert report["by_kind"]["edge-accept"]["accepted"] == report["by_kind"]["edge-accept"]["vectors"], "an edge vector meant to be canonical was refused"
    assert report["by_kind"]["edge-reject"]["accepted"] == 0, "an edge vector meant to be refused was accepted"


if __name__ == "__main__":
    main()
