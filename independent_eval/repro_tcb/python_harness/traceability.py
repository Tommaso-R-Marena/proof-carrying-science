"""Task 14 — Independent evidence traceability auditor.

Links claims in reports to commits, theorems, tests, hashes, and assumptions.
Flags claims that are unsupported, stale, or ambiguous.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from .environment import git_commit
from .hashing import sha256_file, sha256_json
from .paths import CLAIMS_FIXTURES, HASH_MANIFEST, REPO_ROOT, RESULTS

ClaimStatus = Literal["supported", "unsupported", "stale", "ambiguous"]

CLAIM_PATTERN = re.compile(
    r"(?P<indent>^\s*)-\s*\*\*Claim\s+(?P<id>[A-Za-z0-9_.-]+)\*\*:\s*(?P<text>.+)$",
    re.MULTILINE,
)
LINK_PATTERN = re.compile(
    r"^\s*-\s*(commit|theorem|test|hash|assumption):\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def load_evidence_catalog(repo: Path | None = None) -> dict[str, Any]:
    """Build a catalog of linkable evidence from the checkout (read-only)."""
    root = repo or REPO_ROOT
    commit = git_commit(root)

    theorems: dict[str, str] = {}
    for lean_rel in [
        "formal/PCS/V2/TCB.lean",
        "formal/PCS/V2/Authority.lean",
        "formal/PCS/V2/EndToEnd.lean",
    ]:
        lean_path = root / lean_rel
        if not lean_path.is_file():
            continue
        text = lean_path.read_text(encoding="utf-8", errors="replace")
        for name in re.findall(r"^theorem\s+(\w+)", text, flags=re.MULTILINE):
            theorems[name] = lean_rel
        for name in (
            "ProductionRefinesLean",
            "Sha256ProductionAgrees",
            "ZipDecoderFaithful",
            "NoForgery",
        ):
            if name in text:
                theorems[name] = lean_rel

    tests: dict[str, str] = {}
    for tests_dir in (
        root / "tests",
        root / "independent_eval" / "repro_tcb" / "tests",
    ):
        if not tests_dir.is_dir():
            continue
        for path in sorted(tests_dir.glob("test_*.py")):
            tests[path.name] = str(path.relative_to(root))

    hashes: dict[str, str] = {}
    if HASH_MANIFEST.is_file():
        payload = json.loads(HASH_MANIFEST.read_text(encoding="utf-8"))
        for key, value in payload.get("files", {}).items():
            hashes[key] = value

    assumptions = {
        "Sha256Collision": "cryptographic collision resistance (named hypothesis)",
        "NoForgery": "Ed25519 unforgeability for trust-anchor key",
        "ProductionRefinesLean": "production verifier accepts only Lean-accepted archives",
        "ZipDecoderFaithful": "ZIP decoder returns exact archive members",
        "ReplayFaithful": "replay executor fidelity",
        "CaptureSound": "capture fidelity",
        "OS_FILESYSTEM": "OS/filesystem delivers exact bytes",
        "LEAN_KERNEL": "Lean kernel / logic foundation",
        "SCIENTIFIC_PREDICATE": "user-supplied Holds/Describes meaning",
    }

    return {
        "git_commit": commit,
        "theorems": theorems,
        "tests": tests,
        "hashes": hashes,
        "assumptions": assumptions,
    }


def parse_claims_markdown(text: str) -> list[dict[str, Any]]:
    """Parse a lightweight claims report format used by this workstream."""
    claims: list[dict[str, Any]] = []
    blocks = re.split(r"(?=^\s*-\s*\*\*Claim\s+)", text, flags=re.MULTILINE)
    for block in blocks:
        m = CLAIM_PATTERN.search(block)
        if not m:
            continue
        claim_id = m.group("id")
        claim_text = m.group("text").strip()
        links: list[dict[str, str]] = []
        for lm in LINK_PATTERN.finditer(block):
            links.append({"kind": lm.group(1).lower(), "ref": lm.group(2).strip()})
        meta: dict[str, str] = {}
        for key in ("expected_commit", "note"):
            mm = re.search(
                rf"^\s*-\s*{key}:\s*(.+)$",
                block,
                flags=re.MULTILINE | re.IGNORECASE,
            )
            if mm:
                meta[key] = mm.group(1).strip()
        claims.append(
            {
                "claim_id": claim_id,
                "text": claim_text,
                "links": links,
                "meta": meta,
                "raw": block.strip(),
            }
        )
    return claims


def _resolve_link(link: dict[str, str], catalog: dict[str, Any]) -> dict[str, Any]:
    kind = link["kind"]
    ref = link["ref"]
    resolved: dict[str, Any] = {
        "kind": kind,
        "ref": ref,
        "found": False,
        "detail": "",
    }
    if kind == "commit":
        current = catalog.get("git_commit")
        if ref in {"HEAD", "current"} and current:
            resolved["found"] = True
            resolved["detail"] = current
        elif current and (
            ref == current or current.startswith(ref) or ref.startswith(current[:12])
        ):
            resolved["found"] = True
            resolved["detail"] = current
        else:
            resolved["detail"] = f"catalog commit={current}"
    elif kind == "theorem":
        theorems = catalog.get("theorems") or {}
        if ref in theorems:
            resolved["found"] = True
            resolved["detail"] = theorems[ref]
        else:
            for name, loc in theorems.items():
                if name.endswith(ref) or ref.endswith(name):
                    resolved["found"] = True
                    resolved["detail"] = loc
                    resolved["ref"] = name
                    break
    elif kind == "test":
        tests = catalog.get("tests") or {}
        if ref in tests:
            resolved["found"] = True
            resolved["detail"] = tests[ref]
        else:
            for name, loc in tests.items():
                if ref in name or ref in loc:
                    resolved["found"] = True
                    resolved["detail"] = loc
                    resolved["ref"] = name
                    break
    elif kind == "hash":
        hashes = catalog.get("hashes") or {}
        if "=" in ref:
            path, digest = ref.split("=", 1)
            path, digest = path.strip(), digest.strip().lower()
            known = (hashes.get(path) or "").lower()
            if known and known == digest:
                resolved["found"] = True
                resolved["detail"] = path
            elif known:
                resolved["found"] = False
                resolved["detail"] = f"manifest has {known}"
            else:
                resolved["found"] = False
                resolved["detail"] = "path not in hash manifest"
        elif ref in hashes:
            resolved["found"] = True
            resolved["detail"] = hashes[ref]
        elif re.fullmatch(r"[0-9a-fA-F]{64}", ref):
            matched = [p for p, d in hashes.items() if d.lower() == ref.lower()]
            if matched:
                resolved["found"] = True
                resolved["detail"] = ",".join(matched)
        else:
            resolved["detail"] = "unrecognized hash reference"
    elif kind == "assumption":
        assumptions = catalog.get("assumptions") or {}
        if ref in assumptions:
            resolved["found"] = True
            resolved["detail"] = assumptions[ref]
        else:
            resolved["detail"] = "unknown assumption id"
    else:
        resolved["detail"] = f"unknown link kind {kind}"
    return resolved


def classify_claim(claim: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    links = claim.get("links") or []
    resolved = [_resolve_link(link, catalog) for link in links]
    meta = claim.get("meta") or {}

    status: ClaimStatus
    reasons: list[str] = []

    if not links:
        status = "unsupported"
        reasons.append("no evidence links provided")
    else:
        missing = [r for r in resolved if not r["found"]]
        found = [r for r in resolved if r["found"]]
        kinds = {r["kind"] for r in found}

        expected = meta.get("expected_commit")
        current = catalog.get("git_commit")
        stale = False
        if expected and current and expected not in {current, "HEAD", "current"}:
            if not (current.startswith(expected) or expected.startswith(current[:12])):
                stale = True
                reasons.append(f"expected_commit {expected} != current {current}")

        if stale:
            status = "stale"
        elif not found:
            status = "unsupported"
            reasons.append("all evidence links failed to resolve")
        elif missing and found:
            status = "ambiguous"
            reasons.append("some links resolved and some did not")
        elif kinds <= {"assumption"} and not ({"hash", "theorem", "test", "commit"} & kinds):
            status = "ambiguous"
            reasons.append("only assumption links; no commit/theorem/test/hash anchor")
        else:
            status = "supported"
            reasons.append("all links resolved")

        text = claim.get("text") or ""
        if re.search(r"\b(always|never|all|guarantees|proven secure)\b", text, re.I) and "theorem" not in kinds:
            if status == "supported":
                status = "ambiguous"
            reasons.append("strong universal language without theorem link")

    return {
        "claim_id": claim["claim_id"],
        "text": claim["text"],
        "status": status,
        "reasons": reasons,
        "resolved_links": resolved,
        "meta": meta,
    }


def audit_report(
    report_path: Path | None = None,
    *,
    repo: Path | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    path = report_path or (CLAIMS_FIXTURES / "sample_claims_report.md")
    text = path.read_text(encoding="utf-8")
    catalog = load_evidence_catalog(repo)
    claims = parse_claims_markdown(text)
    audited = [classify_claim(c, catalog) for c in claims]

    counts = {"supported": 0, "unsupported": 0, "stale": 0, "ambiguous": 0}
    for row in audited:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    result: dict[str, Any] = {
        "format": "pcs-independent-eval-traceability-v1",
        "task": 14,
        "report_path": str(path),
        "report_sha256": sha256_file(path),
        "catalog_commit": catalog.get("git_commit"),
        "claims": audited,
        "counts": counts,
        "verdict": {
            "all_supported": counts["unsupported"] == 0
            and counts["stale"] == 0
            and counts["ambiguous"] == 0,
            "has_flags": counts["unsupported"] + counts["stale"] + counts["ambiguous"] > 0,
        },
    }
    result["audit_sha256"] = sha256_json({k: v for k, v in result.items() if k != "audit_sha256"})

    out = output or (RESULTS / "traceability_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["written_to"] = str(out)
    return result


if __name__ == "__main__":
    print(json.dumps(audit_report(), indent=2, sort_keys=True))
