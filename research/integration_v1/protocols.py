"""Explicit version dispatch for inspection only; never authorizes promotion."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TAGS = {"PGSI1": b"PGSI1", "PGSI2-WIDE": b"PGSI2-WIDE",
        "PGSC6": b"PGSC6", "PGSC7": b"PGSC7"}


def inspect_artifact(protocol: str, raw: bytes, *, arch=(8, 32)):
    if protocol not in TAGS or type(raw) is not bytes or len(raw) > 1_000_000:
        raise ValueError("unknown profile, wrong type, or host inspection resource limit")
    if raw.split(b"|", 1)[0] != TAGS[protocol]:
        raise ValueError("protocol/profile mismatch")
    # Separate interpreters preserve the historical module-resolution profiles.
    script = '''
import sys
from pathlib import Path
root=Path(sys.argv[1]); profile=sys.argv[2]
if profile=="PGSI1":
    sys.path.insert(0,str(root/"research/isolated/pgsi1/research/proof-gated-self-improvement-v1"))
    from sealed_inference import decode_sealed_model
    decode_sealed_model(sys.stdin.buffer.read())
else:
    sys.path.insert(0,str(root/"research/proof-gated-self-improvement-v1"))
    raw=sys.stdin.buffer.read()
    if profile=="PGSI2-WIDE":
        from pgsi2_wide_runtime import decode,Arch
        decode(raw,Arch(int(sys.argv[3]),int(sys.argv[4])))
    elif profile=="PGSC6":
        from pgsc6_reference import decode_certificate
        decode_certificate(raw)
    elif profile=="PGSC7":
        from v7_independent.v7_independent_audit import parse_cert
        parse_cert(raw)
    else: raise ValueError("unknown profile")
'''
    result = subprocess.run([sys.executable, "-I", "-c", script, str(ROOT), protocol,
                             str(arch[0]), str(arch[1])], input=raw, capture_output=True, timeout=20)
    if result.returncode:
        raise ValueError("original profile decoder rejected artifact")
    return {"profile": protocol, "artifact_sha256": hashlib.sha256(raw).hexdigest(),
            "canonical_parser": "original versioned research implementation",
            "authorization": "NOT_RUN", "pcs_authority": False,
            "promotion_authority": False}
