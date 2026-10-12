"""Check distributable experiment membership and bytes; never proof authority."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SEALS = (
    ("docs/evidence/platform-baseline-v1", "ARTIFACT_SHA256.json"),
    ("research/prospective-hybrid-v2", "EVIDENCE_SHA256.json"),
    ("research/abstraction-repair-v2", "EVIDENCE_SHA256.json"),
    ("research/scientific-assurance-v1", "ARTIFACT_SHA256.json"),
)


def main():
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0"))
    checked = 0
    for relative, manifest in SEALS:
        folder = ROOT / relative
        members = json.loads((folder / manifest).read_text())["files"]
        if not isinstance(members, dict) or not 1 <= len(members) <= 500:
            raise ValueError("bounded evidence membership required")
        for name, expected in members.items():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or not re.fullmatch("[0-9a-f]{64}", expected):
                raise ValueError("invalid sealed member")
            source = folder / path
            if source.is_symlink() or not source.is_file() or source.relative_to(ROOT).as_posix() not in tracked:
                raise ValueError("sealed artifact absent from clean checkout: " + str(source.relative_to(ROOT)))
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise ValueError("sealed artifact bytes changed: " + name)
            checked += 1
    public = ROOT / "research/scientific-assurance-v1/producer-public.pem"
    if not public.read_bytes().startswith(b"-----BEGIN PUBLIC KEY-----\n"):
        raise ValueError("example requires public verification material only")
    print(json.dumps({"sealed_tracked_artifacts": checked, "public_verification_key_present": True,
                      "signature_or_proof_authority": False}))


if __name__ == "__main__":
    main()
