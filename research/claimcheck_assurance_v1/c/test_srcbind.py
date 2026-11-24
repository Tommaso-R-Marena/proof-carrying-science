"""Differential and adversarial tests of pcs_srcbind.c against the Python obligation generator.

Builds the C file with address and undefined-behaviour sanitizers and checks, for real committed
data files, random data and mutated headers:
  * the C encoder writes exactly the bytes research/claimcheck_v1/lean.py writes;
  * the C decoder accepts a buffer only if it starts with the canonical header of the data it returns;
  * every single-byte mutation, truncation and non-canonical spelling of a header is rejected or
    decodes to data whose canonical header is the mutated prefix (which a mutation cannot produce
    unless it lands outside the header);
  * the decoder writes nothing at all when it rejects (the output buffer, pre-filled with a pattern,
    is unchanged), and when it accepts writes nothing beyond out[0..data);
  * the decoder's interface has no length pointer, so the aliasing of the first version (Aristotle's
    counterexample, aristotle/sim/) cannot be expressed: the only pointer it writes through is out.
Tests, not proofs.  Run: python3 research/claimcheck_assurance_v1/c/test_srcbind.py
"""
import ctypes, json, os, random, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MAX = 65536


def build(tmp):
    lib = os.path.join(tmp, "libpcs_srcbind_san.so")
    cc = os.environ.get("CC", "cc")
    subprocess.run([cc, "-std=c99", "-O1", "-g", "-Wall", "-Wextra", "-Wpedantic", "-Wconversion", "-Werror",
                    "-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fPIC", "-shared",
                    str(HERE / "pcs_srcbind.c"), "-o", lib], check=True)
    return lib


def canonical(data: bytes) -> bytes:
    """The header exactly as research/claimcheck_v1/lean.py (batch_tail) writes it."""
    return ("open PCS.ClaimCheck\n\n" + f"def pcs_src : Source := ⟨0x{data.hex() or '0'}, {len(data)}⟩\n\n").encode("utf-8")


def main():
    if os.environ.get("PCS_SRCBIND_CHILD") != "1":
        with tempfile.TemporaryDirectory() as tmp:
            lib = build(tmp)
            asan = subprocess.run([os.environ.get("CC", "cc"), "-print-file-name=libasan.so"], capture_output=True, text=True).stdout.strip()
            env = dict(os.environ, PCS_SRCBIND_CHILD="1", PCS_SRCBIND_LIB=lib, LD_PRELOAD=asan, ASAN_OPTIONS="detect_leaks=0")
            raise SystemExit(subprocess.run([sys.executable, __file__], env=env).returncode)

    lib = ctypes.CDLL(os.environ["PCS_SRCBIND_LIB"])
    u8p = ctypes.POINTER(ctypes.c_uint8)
    lib.pcs_header_size.argtypes = [ctypes.c_size_t]; lib.pcs_header_size.restype = ctypes.c_size_t
    lib.pcs_header_encode.argtypes = [u8p, ctypes.c_size_t, u8p, ctypes.c_size_t]; lib.pcs_header_encode.restype = ctypes.c_size_t

    class Decoded(ctypes.Structure):
        _fields_ = [("header", ctypes.c_size_t), ("data", ctypes.c_size_t)]
    # four arguments and a result by value: no argument is a pointer to a length (see the header)
    lib.pcs_header_decode.argtypes = [u8p, ctypes.c_size_t, u8p, ctypes.c_size_t]
    lib.pcs_header_decode.restype = Decoded
    header_text = (HERE / "pcs_srcbind.h").read_text()
    assert "pcs_decoded pcs_header_decode(const uint8_t *buf, size_t n, uint8_t *out, size_t cap);" in header_text
    assert "size_t *m" not in header_text.split("pcs_header_decode(", 1)[1].split(";", 1)[0]
    pattern = bytes((i * 131 + 7) & 0xFF for i in range(MAX + 64))  # what out holds before each call

    def exact(raw: bytes):
        """A heap buffer of exactly len(raw) bytes, so the sanitizer sees any read past the end."""
        return (ctypes.c_uint8 * max(len(raw), 1)).from_buffer_copy(raw or b"\0"), len(raw)

    def encode(data: bytes, cap=None):
        size = lib.pcs_header_size(len(data))
        cap = size if cap is None else cap
        out = (ctypes.c_uint8 * max(cap, 1))()
        d, m = exact(data)
        got = lib.pcs_header_encode(out, cap, d, m)
        return got, bytes(out[:got])

    def decode(buf: bytes, cap=MAX):
        """Decode into an output buffer of exactly cap bytes pre-filled with the pattern, and check that
        nothing is written on rejection and nothing beyond out[0..data) on acceptance."""
        b, n = exact(buf)
        out = (ctypes.c_uint8 * max(cap, 1)).from_buffer_copy(pattern[:max(cap, 1)])
        r = lib.pcs_header_decode(b, n, out, cap)
        after = bytes(out)
        if r.header == 0:
            assert r.data == 0, "a rejection reports no data"
            assert after == pattern[:max(cap, 1)], "the decoder wrote to out although it rejected"
            counts["rejections_without_write"] += 1
            return 0, None
        assert r.data <= cap and r.data <= MAX and r.header <= n
        assert after[r.data:] == pattern[r.data:max(cap, 1)], "the decoder wrote beyond out[0..data)"
        return r.header, after[:r.data]

    counts = {"real_files": 0, "random": 0, "mutations": 0, "mutations_rejected": 0, "noncanonical_rejected": 0, "truncations": 0,
              "rejections_without_write": 0}
    rng = random.Random(20261114)

    def roundtrip(data: bytes, rest: bytes = b""):
        want = canonical(data)
        size, got = encode(data)
        assert size == len(want) and got == want, "C encoder differs from the Python generator"
        assert lib.pcs_header_size(len(data)) == len(want)
        assert encode(data, cap=len(want) - 1)[0] == 0, "encoder must refuse a short buffer"
        n, back = decode(want + rest)
        assert n == len(want) and back == data, "decoder must accept the canonical header and return the data"
        if data:
            assert decode(want + rest, cap=len(data) - 1)[0] == 0, "decoder must refuse an output buffer that is too small"
        return want

    # 1. every data file of the committed ClaimCheck documents, with the real obligation files
    for doc in sorted((ROOT / "research/claimcheck_v1/benchmark").glob("*/*/document.json")):
        table = json.loads(doc.read_text())["table"]
        data = (doc.parent / table).read_bytes()
        if len(data) <= MAX:
            roundtrip(data, b"def pcs_c0 : Claim :=\n")
            counts["real_files"] += 1
    marker = "\n-- ===== generated obligations (data numeral, claims, expected outcomes) =====\n".encode()
    for ob in sorted((ROOT / "research/claimcheck_v1/benchmark/results/bundles").glob("*/obligations/*.lean")):
        tail = ob.read_bytes().split(marker, 1)[1]
        n, data = decode(tail)
        assert n > 0 and tail[:n] == canonical(data), ob
        counts["real_obligation_files"] = counts.get("real_obligation_files", 0) + 1

    # 2. random data, including the empty file, zero bytes and the size limit
    for data in [b"", b"\0", b"\0\0", b"0", b"\xff" * 3, bytes(range(256)), bytes(MAX)]:
        roundtrip(data)
    for _ in range(300):
        roundtrip(rng.randbytes(rng.choice([1, 2, 3, 7, 31, 32, 33, 255, 1000])), rng.randbytes(rng.randrange(0, 9)))
        counts["random"] += 1
    assert lib.pcs_header_size(MAX + 1) == 0 and encode(bytes(MAX + 1), cap=4 * MAX)[0] == 0

    # 3. every single-byte mutation and every truncation of a header
    for data in [b"", b"\0", b"a,b\n1,2\n", rng.randbytes(40)]:
        want = canonical(data)
        for cut in range(len(want)):
            assert decode(want[:cut])[0] == 0, "a truncated header must be rejected"
            counts["truncations"] += 1
        for i in range(len(want)):
            for delta in (1, 0x20, 0x80, 0xFF):
                mutated = bytearray(want); mutated[i] ^= delta
                n, back = decode(bytes(mutated) + b"tail")
                counts["mutations"] += 1
                if n == 0:
                    counts["mutations_rejected"] += 1
                else:  # accepted only if it is the canonical header of what it returns (a different file)
                    assert bytes(mutated)[:n] == canonical(back) and back != data
                    assert len(back) == len(data), "a mutation cannot change the length consistently"

    # 4. non-canonical spellings the Lean elaborator would read as the same or another numeral
    pre = "open PCS.ClaimCheck\n\ndef pcs_src : Source := ⟨"
    for body in ["0x6162, 2", "0X6162, 2", "0x6162,2", "0x6162,  2", "0x6162, 02", "0x6162, 3", "0x6162, 1", "0x06162, 2",
                 "0x616, 2", "0x6162AB, 3", "0x6162ab, 3 ", "24930, 2", "0x, 0", "0x00, 0", "0x0, 1", "0x0, 00", "0x1, 1",
                 "0x6162, 2 ", " 0x6162, 2", "0x61_62, 2", "0x6162, 4294967298", "0x6162, 18446744073709551618",
                 "0x6162, 2, 0", "0x" + "00" * (MAX + 1) + ", " + str(MAX + 1)]:
        for suffix in ["⟩\n\n", "⟩\n", "⟩\r\n\r\n", ">\n\n", "⟩ \n\n"]:
            text = (pre + body + suffix).encode("utf-8")
            n, back = decode(text + b"x")
            ok = n > 0 and text[:n] == canonical(back)
            if body in ("0x6162, 2", "0x6162ab, 3 "[:-1]) and suffix == "⟩\n\n":
                assert ok
            else:
                assert n == 0, (body, suffix)
                counts["noncanonical_rejected"] += 1
    for bad_pre in ["open PCS.ClaimCheck\n\ndef pcs_src : Source := <", "open PCS.ClaimCheck\ndef pcs_src : Source := ⟨",
                    "open PCS.ClaimCheck\n\ndef  pcs_src : Source := ⟨", "namespace X\nopen PCS.ClaimCheck\n\ndef pcs_src : Source := ⟨"]:
        assert decode((bad_pre + "0x6162, 2⟩\n\n").encode("utf-8"))[0] == 0
        counts["noncanonical_rejected"] += 1
    for n in range(0, 60):
        assert decode(bytes(n))[0] == 0 and decode(b"\xff" * n)[0] == 0

    assert counts["mutations_rejected"] < counts["mutations"], "some mutations of hex digits give other valid headers"
    print(json.dumps({"passed": True, "sanitizers": "address,undefined", **counts}))


if __name__ == "__main__":
    main()
