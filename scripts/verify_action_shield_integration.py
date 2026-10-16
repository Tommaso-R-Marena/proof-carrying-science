"""Audit all static shield/composition theorems after their fresh kernel builds."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from audit_lean_source import active_code, audit
from verify_omega_dd_formal import check_inventory

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "formal/PCSActionShieldIntegrationAudit.lean"
SOURCES = [ROOT / "formal" / (name + ".lean") for name in (
    "PCSActionShield", "PCSActionShieldControls", "PCSConditionalShieldBridge",
    "PCSConditionalShieldRuntime", "PCSActionShieldIntegrationAudit")]


def verify(output: Path) -> dict:
    if output.exists():
        raise ValueError("new integration axiom evidence required")
    if findings := audit(SOURCES):
        raise ValueError("\n".join(findings))
    names = [line.removeprefix("#print axioms ") for line in DRIVER.read_text().splitlines()
             if line.startswith("#print axioms ")]
    declared = []
    for source in SOURCES[:-1]:
        namespace = ""
        for line in active_code(source.read_text()).splitlines():
            if match := re.match(r"^namespace (\S+)", line):
                namespace = match[1]
            if match := re.match(r"^(?:@\[[^\]]+\]\s*)*(?:theorem|lemma) (\S+)", line):
                declared.append(namespace + "." + match[1])
    if len(names) != 15 or len(set(names)) != 15 or set(names) != set(declared) or len(declared) != 15:
        raise ValueError("complete static integration inventory required")
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}
    result = subprocess.run(["lake", "env", "lean", "-j1", "-M6000", str(DRIVER)],
                            cwd=ROOT / "formal", capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    inventory = check_inventory(result.stdout, names)
    if before != {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}:
        raise ValueError("integration sources changed during audit")
    report = {"format": "pcs-action-shield-integration-axioms-v1", "source_sha256": before,
              "kernel_theorems": inventory, "command": result.args, "returncode": result.returncode,
              "stdout": result.stdout, "stderr": result.stderr,
              "native_execution_correspondence_proved": False, "deployment_safety": "OPEN",
              "scientific_acceptance": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as file:
        json.dump(report, file, indent=2)
        file.write("\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    result = verify(parser.parse_args().output)
    print(json.dumps({"static_kernel_theorems": len(result["kernel_theorems"]), "scientific_acceptance": False}))
