import argparse, json
from pathlib import Path
from .authority import Authority
from .verifier import verify, replay
from .parsing import MAX_BYTES, MAX_EVIDENCE_BYTES


def read(path, limit=MAX_BYTES):
    with path.open("rb") as f:
        raw = f.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Input byte budget exceeded")
    return raw


p = argparse.ArgumentParser(
    description="Research-only typed scientific proof packages; no production authority."
)
p.add_argument("command", choices=["prism", "aion", "risk-demo", "replay", "build"])
p.add_argument("input", type=Path)
p.add_argument("out", type=Path, nargs="?")
p.add_argument("--certificate", type=Path)
a = p.parse_args()
if a.command == "build":
    if a.out is not None or a.certificate is not None:
        p.error("build takes only a fresh output folder")
    authority = Authority(a.input)
    print(
        json.dumps(
            dict(built=True, theorems=len(authority.axioms), path=str(authority.out)),
            indent=2,
        )
    )
else:
    if a.out is None:
        p.error("Fresh output folder required")
    raw = read(a.input, MAX_EVIDENCE_BYTES if a.command == "replay" else MAX_BYTES)
    certificate = None if a.certificate is None else read(a.certificate)
    a.out.mkdir(parents=True, exist_ok=False)
    authority = Authority(a.out / "authority")
    result = (
        replay(raw, authority, out=a.out / "evidence.json")
        if a.command == "replay"
        else verify(
            a.command,
            raw,
            authority,
            certificate=certificate,
            out=a.out / "evidence.json",
        )
    )
    print(
        json.dumps(
            dict(
                claim=result["claim"],
                kernel_checked=result["proof"]["kernel_checked"],
                receipt_sha256=result["receipt_sha256"],
                production_authority=False,
            ),
            indent=2,
        )
    )
