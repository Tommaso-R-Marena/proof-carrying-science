"""Validate distributable continuation artifact membership; no proof authority."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/evidence/mathlib-continuation-v4/ARTIFACT_SHA256.json'

def main():
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0'))
    if MANIFEST.relative_to(ROOT).as_posix() not in tracked:
        raise ValueError('continuation manifest must be tracked in a clean checkout')
    manifest = json.loads(MANIFEST.read_text())
    files = manifest['files']
    if manifest.get('format') != 'pcs-continuation-artifact-membership-v4' or type(files) is not dict or not 1 <= len(files) <= 1024:
        raise ValueError('bounded continuation artifact manifest required')
    for name, expected in files.items():
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError('invalid artifact member')
        source = ROOT / p
        if name not in tracked or source.is_symlink() or not source.is_file() or source.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('artifact absent from bounded clean checkout: ' + name)
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('artifact digest mismatch: ' + name)
        if source.suffix == '.pem' and not data.startswith(b'-----BEGIN PUBLIC KEY-----\n'):
            raise ValueError('only public verification material may be distributed')
    print(json.dumps({'sealed_tracked_artifacts': len(files), 'artifact_manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest(), 'proof_or_production_authority': False}))

if __name__ == '__main__':
    main()
