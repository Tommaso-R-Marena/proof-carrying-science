"""The proved Lean decoder, the C decoder and the Python runner's header check agree.

`ClaimCheckAssurance.Header` proves that `decode` accepts exactly the canonical headers and returns
their data.  This test executes that same `decode` (via `lean --run HeaderRefinement.lean`) and
compares it, vector by vector, with
  * `c/pcs_srcbind.c::pcs_header_decode` (through ctypes), on every vector and capacity;
  * the header part of the installed stand-alone runner
    (`research/claimcheck_v1_1/claimcheck_kernel_runner.py`: its PREAMBLE and SRC objects and size
    rule), on every vector whose capacity is the 65,536-byte limit (the runner has no capacity).
Vectors: the generated part of every committed obligation file, canonical headers of random data
of many sizes with random suffixes, every truncation and many single-byte mutations of headers,
non-canonical spellings, near-grammar fuzz, random bytes.  Agreement on these inputs is evidence
that the implementations compute the proved function; it is a test, not a proof.

Run (needs Lean 4.28.0 on PATH and a C compiler):
  python3 research/claimcheck_assurance_v1/conformance/test_header_refinement.py
"""
import ctypes, json, os, random, resource, struct, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parent
ROOT = ASSURANCE.parents[1]
sys.path.insert(0, str(ROOT))
from research.claimcheck_v1_1 import claimcheck_kernel_runner as strict_tail  # noqa: E402  (the installed runner)

MAX = 65536
MARKER = b"\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n"


def canonical(data: bytes) -> bytes:
    return ("open PCS.ClaimCheck\n\n" + f"def pcs_src : Source := ⟨0x{data.hex() or '0'}, {len(data)}⟩\n\n").encode("utf-8")


def python_header(buf: bytes):
    """The installed runner's header rule, applied to the start of `buf`: (header length, data) or None."""
    text = buf.decode("utf-8", "surrogateescape")
    if not text.startswith(strict_tail.PREAMBLE):
        return None
    m = strict_tail.SRC.match(text, len(strict_tail.PREAMBLE))
    if not m:
        return None
    digits, size = m.group(1), int(m.group(2))
    if size > strict_tail.MAX_DATA_BYTES or not ((size == 0 and digits == "0") or (size > 0 and len(digits) == 2 * size)):
        return None
    return len(text[:m.end()].encode("utf-8", "surrogateescape")), (bytes.fromhex(digits) if size else b"")


def h(d: bytes) -> int:
    v = 0
    for x in d:
        v = (v * 257 + x + 1) % 2305843009213693951
    return v


def vectors(rng):
    out = []  # (cap, bytes)
    for ob in sorted((ROOT / "research/claimcheck_v1/benchmark/results/bundles").glob("*/obligations/*.lean")):
        tail = ob.read_bytes().split(MARKER, 1)[1]
        out.append((MAX, tail, "real"))
    sizes = [0, 1, 2, 3, 7, 9, 10, 11, 99, 100, 101, 255, 1000, 4096]
    for n in sizes:
        d = rng.randbytes(n)
        c = canonical(d)
        for cap in sorted({0, max(0, n - 1), n, n + 1, MAX, 2 ** 32 - 1}):
            out.append((cap, c + rng.randbytes(rng.randrange(0, 12)), "canonical"))
    out.append((MAX, canonical(bytes(MAX)) + b"tail", "canonical"))
    out.append((2 ** 32 - 1, canonical(bytes(MAX)) + b"tail", "canonical"))
    for d in [b"", b"\0", b"a,b\n1,2\n", rng.randbytes(13)]:
        c = canonical(d)
        for cut in range(len(c) + 1):
            out.append((MAX, c[:cut], "truncation"))
        for i in range(len(c)):
            for delta in (1, 2, 0x10, 0x20, 0x80, 0xFF):
                m = bytearray(c); m[i] ^= delta
                out.append((MAX, bytes(m) + b"more", "mutation"))
    pre = "open PCS.ClaimCheck\n\ndef pcs_src : Source := ⟨"
    bodies = ["0x6162, 2", "0X6162, 2", "0x6162,2", "0x6162,  2", "0x6162, 02", "0x6162, 3", "0x6162, 1", "0x06162, 2",
              "0x616, 2", "0x6162AB, 3", "0x, 0", "0x00, 0", "0x0, 1", "0x0, 00", "0x1, 1", "0x0, 0", "0x6162, 2 ",
              " 0x6162, 2", "0x61_62, 2", "0x6162, 4294967298", "0x6162, 65537", "0x6162, 65536", "0x6162, 0002"]
    for body in bodies:
        for suffix in ["⟩\n\n", "⟩\n", "⟩\r\n\r\n", ">\n\n", "⟩ \n\n", ""]:
            out.append((MAX, (pre + body + suffix).encode("utf-8") + b"rest", "noncanonical"))
    alphabet = b"0123456789abcdefABx, \n"
    for _ in range(3000):
        body = bytes(rng.choice(alphabet) for _ in range(rng.randrange(0, 14)))
        suf = rng.choice([b"\xe2\x9f\xa9\n\n", b"\xe2\x9f\xa9\n", b""])
        out.append((rng.choice([0, 1, 2, 5, MAX]), pre.encode("utf-8") + body + suf, "fuzz"))
    for _ in range(500):
        out.append((rng.choice([0, 3, MAX]), rng.randbytes(rng.randrange(0, 80)), "random"))
    return out


def main():
    rng = random.Random(20261115)
    vecs = vectors(rng)
    with tempfile.TemporaryDirectory() as tmp:
        lib_path = os.path.join(tmp, "libpcs_srcbind.so")
        subprocess.run([os.environ.get("CC", "cc"), "-std=c99", "-O2", "-fPIC", "-shared", str(ASSURANCE / "c/pcs_srcbind.c"),
                        "-o", lib_path], check=True)
        lib = ctypes.CDLL(lib_path)
        u8p = ctypes.POINTER(ctypes.c_uint8)
        lib.pcs_header_decode.argtypes = [u8p, ctypes.c_size_t, u8p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        lib.pcs_header_decode.restype = ctypes.c_size_t

        vin, vout = os.path.join(tmp, "vectors.bin"), os.path.join(tmp, "lean.txt")
        with open(vin, "wb") as f:
            for cap, buf, _kind in vecs:
                f.write(struct.pack(">II", cap, len(buf)) + buf)
        build = os.environ.get("PCS_ASSURANCE_BUILD", str(ASSURANCE / "formal/.build"))
        env = dict(os.environ, LEAN_PATH=build)
        def big_stack():  # the proved definitions are plain structural recursion; the interpreter needs stack
            hard = resource.getrlimit(resource.RLIMIT_STACK)[1]
            resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
        subprocess.run(["lean", "--run", str(HERE / "HeaderRefinement.lean"), vin, vout], check=True, env=env, cwd=str(HERE),
                       preexec_fn=big_stack)
        lean_lines = Path(vout).read_text().splitlines()
        assert len(lean_lines) == len(vecs), (len(lean_lines), len(vecs))

        counts = {"vectors": len(vecs), "accepted": 0, "rejected": 0, "compared_with_python": 0, "by_kind": {}}
        for (cap, buf, kind), lean in zip(vecs, lean_lines):
            b = (ctypes.c_uint8 * max(len(buf), 1)).from_buffer_copy(buf or b"\0")
            cap_alloc = min(cap, MAX + 16)
            out = (ctypes.c_uint8 * max(cap_alloc, 1))()
            m = ctypes.c_size_t(0)
            got = lib.pcs_header_decode(b, len(buf), out, min(cap, cap_alloc), ctypes.byref(m))
            # caps above the allocation are equivalent: the decoder never writes more than MAX bytes
            c_line = "N" if got == 0 else f"{got} {m.value} {h(bytes(out[:m.value]))}"
            assert c_line == lean, ("C and Lean differ", cap, buf[:120], c_line, lean)
            counts["accepted" if got else "rejected"] += 1
            if cap >= MAX:
                p = python_header(buf)
                p_line = "N" if p is None else f"{p[0]} {len(p[1])} {h(p[1])}"
                assert p_line == lean, ("Python and Lean differ", buf[:120], p_line, lean)
                counts["compared_with_python"] += 1
            k = counts["by_kind"].setdefault(kind, {"vectors": 0, "accepted": 0})
            k["vectors"] += 1
            k["accepted"] += bool(got)
        real = counts["by_kind"]["real"]
        assert real["vectors"] >= 84 and real["accepted"] == real["vectors"], real
        # of the hand-written spellings only "0x6162, 2" and "0x0, 0" followed by the exact suffix are canonical
        assert counts["by_kind"]["noncanonical"]["accepted"] == 2, counts["by_kind"]["noncanonical"]
        print(json.dumps({"passed": True, **counts}))


if __name__ == "__main__":
    main()
