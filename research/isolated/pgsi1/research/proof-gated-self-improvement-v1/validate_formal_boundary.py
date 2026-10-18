"""Strict source fence and exact named theorem/approved-axiom inventory."""

import argparse
import json
from pathlib import Path
import re
from build_authority import source_inventory, ROOT

APPROVED = {"propext", "Classical.choice", "Quot.sound"}


def validate(audit_path):
    sources = source_inventory()
    expected = re.findall(
        r"^#print axioms ([A-Za-z0-9_.]+)$",
        (ROOT / "formal/PCS/V2/ProofGatedAudit.lean").read_text(),
        re.M,
    )
    raw = Path(audit_path).read_text()
    pattern = re.compile(
        r"'([^']+)' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)"
    )
    records = {}
    for match in pattern.finditer(raw):
        name, body = match.groups()
        if name in records:
            raise ValueError("Duplicate theorem audit")
        axioms = (
            [] if body is None else [x.strip() for x in body.split(",") if x.strip()]
        )
        if set(axioms) - APPROVED:
            raise ValueError("Unapproved theorem axiom: " + name)
        records[name] = axioms
    if set(records) != set(expected) or pattern.sub("", raw).strip():
        raise ValueError("Incomplete or unexpected formal audit output")
    return {
        "format": "pgsi-frozen-formal-boundary-audit-v1",
        "theorems": records,
        "source_sha256": sources,
        "formal_specification_changed": False,
        "native_execution_correspondence_proved": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audit", required=True, type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    r = validate(a.audit)
    if a.output:
        with a.output.open("x") as f:
            f.write(json.dumps(r, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "theorems_audited": len(r["theorems"]),
                "all_axioms_approved": True,
                "formal_source_fence": True,
            }
        )
    )
